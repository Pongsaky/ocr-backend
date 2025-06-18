"""
PDF OCR service for processing PDF files with comprehensive cleanup and error handling.
"""

import asyncio
import time
import gc
from pathlib import Path
from typing import List, Optional
import tempfile
import os

import fitz  # PyMuPDF
from PIL import Image
import base64
from io import BytesIO

from app.logger_config import get_logger
from app.models.ocr_models import (
    PDFOCRRequest, PDFOCRResult, PDFPageResult,
    PDFLLMOCRRequest, PDFLLMOCRResult, PDFPageLLMResult,
    OCRRequest, OCRLLMRequest
)
from app.services.external_ocr_service import external_ocr_service
from app.services.ocr_llm_service import ocr_llm_service
from app.utils.image_utils import validate_and_scale_image, ImageProcessingError
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class PDFProcessingContext:
    """Context manager for PDF processing resources."""
    
    def __init__(self):
        """Initialize processing context."""
        self.temp_files: List[Path] = []
        self.pdf_document: Optional[fitz.Document] = None
        
    async def __aenter__(self):
        """Enter context manager."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup all resources."""
        await self.cleanup_all()
        
    def add_temp_file(self, file_path: Path) -> None:
        """Add a temporary file to track for cleanup."""
        self.temp_files.append(file_path)
        
    async def cleanup_all(self) -> None:
        """Clean up all tracked resources."""
        cleanup_errors = []
        
        # Close PDF document
        if self.pdf_document:
            try:
                self.pdf_document.close()
                logger.debug("Closed PDF document")
            except Exception as e:
                cleanup_errors.append(f"PDF document: {e}")
        
        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                cleanup_errors.append(f"{temp_file}: {e}")
        
        # Force garbage collection
        gc.collect()
        
        if cleanup_errors:
            logger.warning(f"Some cleanup errors occurred: {cleanup_errors}")
        else:
            logger.debug(f"Successfully cleaned up {len(self.temp_files)} temp files")


class PDFOCRService:
    """Service for processing PDF files with OCR."""
    
    def __init__(self):
        """Initialize PDF OCR service."""
        self.settings = settings
        logger.info("PDF OCR Service initialized")
    
    async def process_pdf(
        self, 
        pdf_path: Path, 
        request: PDFOCRRequest
    ) -> PDFOCRResult:
        """
        Process PDF file and extract text from each page.
        
        Args:
            pdf_path: Path to the PDF file
            request: PDF OCR processing parameters
            
        Returns:
            PDFOCRResult: Complete PDF processing result
        """
        start_time = time.time()
        
        async with PDFProcessingContext() as context:
            try:
                logger.info(f"Starting PDF OCR processing: {pdf_path}")
                
                # 1. Validate PDF and get page count
                page_count = await self._validate_and_get_page_count(pdf_path)
                logger.info(f"PDF has {page_count} pages")
                
                # 2. Convert PDF to images
                pdf_start_time = time.time()
                temp_images = await self._pdf_to_images(pdf_path, request.dpi, context)
                pdf_processing_time = time.time() - pdf_start_time
                
                logger.info(f"Converted PDF to {len(temp_images)} images in {pdf_processing_time:.2f}s")
                
                # 3. Process images in batches for memory efficiency
                ocr_start_time = time.time()
                page_results = await self._process_images_batch(temp_images, request)
                ocr_processing_time = time.time() - ocr_start_time
                
                total_processing_time = time.time() - start_time
                processed_pages = sum(1 for result in page_results if result.success)
                
                logger.info(
                    f"PDF processing completed: {processed_pages}/{page_count} pages successful "
                    f"in {total_processing_time:.2f}s"
                )
                
                return PDFOCRResult(
                    success=processed_pages > 0,
                    total_pages=page_count,
                    processed_pages=processed_pages,
                    results=page_results,
                    total_processing_time=total_processing_time,
                    pdf_processing_time=pdf_processing_time,
                    ocr_processing_time=ocr_processing_time,
                    dpi_used=request.dpi
                )
                
            except Exception as e:
                total_processing_time = time.time() - start_time
                logger.error(f"PDF processing failed: {str(e)}")
                
                return PDFOCRResult(
                    success=False,
                    total_pages=0,
                    processed_pages=0,
                    results=[],
                    total_processing_time=total_processing_time,
                    pdf_processing_time=0.0,
                    ocr_processing_time=0.0,
                    dpi_used=request.dpi
                )
    
    async def _validate_and_get_page_count(self, pdf_path: Path) -> int:
        """
        Validate PDF file and get page count.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            int: Number of pages in PDF
            
        Raises:
            ValueError: If PDF is invalid or has too many pages
        """
        try:
            if not pdf_path.exists():
                raise ValueError(f"PDF file not found: {pdf_path}")
            
            # Check file size
            file_size = pdf_path.stat().st_size
            if file_size > settings.MAX_PDF_SIZE:
                raise ValueError(
                    f"PDF file too large: {file_size} bytes. "
                    f"Maximum allowed: {settings.MAX_PDF_SIZE} bytes"
                )
            
            # Open and validate PDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            if page_count == 0:
                raise ValueError("PDF file has no pages")
            
            if page_count > settings.MAX_PDF_PAGES:
                raise ValueError(
                    f"PDF has too many pages: {page_count}. "
                    f"Maximum allowed: {settings.MAX_PDF_PAGES} pages"
                )
            
            logger.debug(f"PDF validation successful: {page_count} pages")
            return page_count
            
        except Exception as e:
            logger.error(f"PDF validation failed: {str(e)}")
            raise ValueError(f"Invalid PDF file: {str(e)}")
    
    async def _pdf_to_images(
        self, 
        pdf_path: Path, 
        dpi: int, 
        context: PDFProcessingContext
    ) -> List[Path]:
        """
        Convert PDF pages to images with automatic scaling for LLM context limits.
        
        Args:
            pdf_path: Path to PDF file
            dpi: DPI for image conversion
            context: Processing context for resource management
            
        Returns:
            List[Path]: Paths to temporary image files (scaled if necessary)
        """
        temp_images = []
        
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            context.pdf_document = doc
            
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="pdf_ocr_"))
            context.add_temp_file(temp_dir)
            
            # Convert each page to image
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Create matrix for DPI scaling
                mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat)
                
                # Save as PNG (original)
                original_img_path = temp_dir / f"page_{page_num + 1:03d}_original.png"
                pix.save(str(original_img_path))
                context.add_temp_file(original_img_path)
                
                # Clean up pixmap
                pix = None
                
                logger.debug(f"Converted PDF page {page_num + 1} to {original_img_path}")
                
                # Validate and scale image if necessary
                try:
                    scaled_img_path = temp_dir / f"page_{page_num + 1:03d}.png"
                    final_img_path, scaling_metadata = validate_and_scale_image(
                        original_img_path, 
                        scaled_img_path
                    )
                    
                    # Log scaling information
                    if scaling_metadata.get("scaling_applied", False):
                        original_pixels = scaling_metadata.get("original_pixel_count", 0)
                        scaled_pixels = scaling_metadata.get("scaled_pixel_count", 0)
                        scale_factor = scaling_metadata.get("scale_factor", 1.0)
                        
                        logger.info(
                            f"Page {page_num + 1} scaled: {original_pixels:,} -> {scaled_pixels:,} pixels "
                            f"(factor: {scale_factor:.3f})"
                        )
                    else:
                        logger.debug(f"Page {page_num + 1} within limits, no scaling needed")
                    
                    temp_images.append(final_img_path)
                    context.add_temp_file(final_img_path)
                    
                except ImageProcessingError as e:
                    logger.error(f"Failed to process image for page {page_num + 1}: {str(e)}")
                    # Fall back to original image if scaling fails
                    temp_images.append(original_img_path)
                
            logger.info(f"Successfully converted {len(temp_images)} PDF pages to images")
            return temp_images
            
        except Exception as e:
            logger.error(f"PDF to images conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert PDF to images: {str(e)}")
    
    async def _process_images_batch(
        self, 
        image_paths: List[Path], 
        request: PDFOCRRequest
    ) -> List[PDFPageResult]:
        """
        Process images in batches for memory efficiency.
        
        Args:
            image_paths: List of image file paths
            request: PDF OCR processing parameters
            
        Returns:
            List[PDFPageResult]: Results for each page
        """
        results = []
        batch_size = settings.PDF_BATCH_SIZE
        
        # Convert PDF request to OCR request
        ocr_request = OCRRequest(
            threshold=request.threshold,
            contrast_level=request.contrast_level
        )
        
        # Process images in batches
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: pages {i+1}-{min(i+batch_size, len(image_paths))}")
            
            # Process batch concurrently
            batch_tasks = [
                self._process_single_image(img_path, idx + i + 1, ocr_request)
                for idx, img_path in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Page {i + idx + 1} processing failed: {result}")
                    results.append(PDFPageResult(
                        page_number=i + idx + 1,
                        extracted_text="",
                        processing_time=0.0,
                        success=False,
                        error_message=str(result),
                        threshold_used=request.threshold,
                        contrast_level_used=request.contrast_level
                    ))
                else:
                    results.append(result)
            
            # Force garbage collection between batches
            gc.collect()
            
            logger.info(f"Completed batch {i//batch_size + 1}")
        
        return results
    
    async def _process_single_image(
        self, 
        image_path: Path, 
        page_number: int, 
        ocr_request: OCRRequest
    ) -> PDFPageResult:
        """
        Process a single image with OCR.
        
        Args:
            image_path: Path to image file
            page_number: PDF page number (1-indexed)
            ocr_request: OCR processing parameters
            
        Returns:
            PDFPageResult: Processing result for the page
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Processing page {page_number}: {image_path}")
            
            # Process image with external OCR service
            result = await external_ocr_service.process_image(image_path, ocr_request)
            
            processing_time = time.time() - start_time
            
            if result.success:
                logger.debug(f"Page {page_number} processed successfully in {processing_time:.2f}s")
                return PDFPageResult(
                    page_number=page_number,
                    extracted_text=result.extracted_text,
                    processing_time=processing_time,
                    success=True,
                    error_message=None,
                    threshold_used=result.threshold_used,
                    contrast_level_used=result.contrast_level_used
                )
            else:
                logger.warning(f"Page {page_number} OCR failed")
                return PDFPageResult(
                    page_number=page_number,
                    extracted_text="",
                    processing_time=processing_time,
                    success=False,
                    error_message="OCR processing failed",
                    threshold_used=result.threshold_used,
                    contrast_level_used=result.contrast_level_used
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Page {page_number} processing failed: {str(e)}")
            
            return PDFPageResult(
                page_number=page_number,
                extracted_text="",
                processing_time=processing_time,
                success=False,
                error_message=str(e),
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level
            )

    async def process_pdf_with_llm(
        self, 
        pdf_path: Path, 
        request: PDFLLMOCRRequest
    ) -> PDFLLMOCRResult:
        """
        Process PDF file with LLM-enhanced OCR for each page.
        
        Args:
            pdf_path: Path to the PDF file
            request: PDF LLM OCR processing parameters
            
        Returns:
            PDFLLMOCRResult: Complete PDF LLM processing result
        """
        start_time = time.time()
        
        async with PDFProcessingContext() as context:
            try:
                logger.info(f"Starting PDF LLM OCR processing: {pdf_path}")
                
                # 1. Validate PDF and get page count
                page_count = await self._validate_and_get_page_count(pdf_path)
                logger.info(f"PDF has {page_count} pages for LLM processing")
                
                # 2. Convert PDF to images
                pdf_start_time = time.time()
                temp_images = await self._pdf_to_images(pdf_path, request.dpi, context)
                pdf_processing_time = time.time() - pdf_start_time
                
                logger.info(f"Converted PDF to {len(temp_images)} images in {pdf_processing_time:.2f}s")
                
                # 3. Process images with LLM in batches for memory efficiency
                ocr_start_time = time.time()
                page_results = await self._process_images_batch_with_llm(temp_images, request)
                ocr_processing_time = time.time() - ocr_start_time
                
                # 4. Calculate LLM processing time from page results
                llm_processing_time = sum(result.llm_processing_time for result in page_results if result.success)
                
                total_processing_time = time.time() - start_time
                processed_pages = sum(1 for result in page_results if result.success)
                
                logger.info(
                    f"PDF LLM processing completed: {processed_pages}/{page_count} pages successful "
                    f"in {total_processing_time:.2f}s (LLM: {llm_processing_time:.2f}s)"
                )
                
                return PDFLLMOCRResult(
                    success=processed_pages > 0,
                    total_pages=page_count,
                    processed_pages=processed_pages,
                    results=page_results,
                    total_processing_time=total_processing_time,
                    pdf_processing_time=pdf_processing_time,
                    ocr_processing_time=ocr_processing_time,
                    llm_processing_time=llm_processing_time,
                    dpi_used=request.dpi,
                    model_used=request.model or settings.OCR_LLM_MODEL,
                    prompt_used=request.prompt or settings.OCR_LLM_DEFAULT_PROMPT
                )
                
            except Exception as e:
                total_processing_time = time.time() - start_time
                logger.error(f"PDF LLM processing failed: {str(e)}")
                
                return PDFLLMOCRResult(
                    success=False,
                    total_pages=0,
                    processed_pages=0,
                    results=[],
                    total_processing_time=total_processing_time,
                    pdf_processing_time=0.0,
                    ocr_processing_time=0.0,
                    llm_processing_time=0.0,
                    dpi_used=request.dpi,
                    model_used=request.model or settings.OCR_LLM_MODEL,
                    prompt_used=request.prompt or settings.OCR_LLM_DEFAULT_PROMPT
                )

    async def _process_images_batch_with_llm(
        self, 
        image_paths: List[Path], 
        request: PDFLLMOCRRequest
    ) -> List[PDFPageLLMResult]:
        """
        Process images in batches with LLM enhancement for memory efficiency.
        
        Args:
            image_paths: List of image file paths
            request: PDF LLM OCR processing parameters
            
        Returns:
            List[PDFPageLLMResult]: LLM-enhanced results for each page
        """
        results = []
        batch_size = settings.PDF_BATCH_SIZE
        
        # Convert PDF LLM request to OCR LLM request
        ocr_llm_request = OCRLLMRequest(
            threshold=request.threshold,
            contrast_level=request.contrast_level,
            prompt=request.prompt,
            model=request.model
        )
        
        # Process images in batches
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]
            logger.info(f"Processing LLM batch {i//batch_size + 1}: pages {i+1}-{min(i+batch_size, len(image_paths))}")
            
            # Process batch concurrently
            batch_tasks = [
                self._process_single_image_with_llm(img_path, idx + i + 1, ocr_llm_request)
                for idx, img_path in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Page {i + idx + 1} LLM processing failed: {result}")
                    results.append(PDFPageLLMResult(
                        page_number=i + idx + 1,
                        extracted_text="",
                        original_ocr_text="",
                        processing_time=0.0,
                        ocr_processing_time=0.0,
                        llm_processing_time=0.0,
                        success=False,
                        error_message=str(result),
                        threshold_used=request.threshold,
                        contrast_level_used=request.contrast_level,
                        model_used=request.model or settings.OCR_LLM_MODEL,
                        prompt_used=request.prompt or settings.OCR_LLM_DEFAULT_PROMPT
                    ))
                else:
                    results.append(result)
            
            # Force garbage collection between batches
            gc.collect()
            
            logger.info(f"Completed LLM batch {i//batch_size + 1}")
        
        return results

    async def _process_single_image_with_llm(
        self, 
        image_path: Path, 
        page_number: int, 
        ocr_llm_request: OCRLLMRequest
    ) -> PDFPageLLMResult:
        """
        Process a single image with LLM-enhanced OCR.
        
        Args:
            image_path: Path to image file
            page_number: PDF page number (1-indexed)
            ocr_llm_request: OCR LLM processing parameters
            
        Returns:
            PDFPageLLMResult: LLM-enhanced processing result for the page
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Processing page {page_number} with LLM: {image_path}")
            
            # First, get processed image and original OCR text
            ocr_request = OCRRequest(
                threshold=ocr_llm_request.threshold,
                contrast_level=ocr_llm_request.contrast_level
            )
            
            # Get processed image and OCR text (using controller's helper method pattern)
            processed_data = await self._get_processed_image_and_text_for_pdf(image_path, ocr_request)
            
            # Process with LLM using the OCR LLM service
            llm_result = await ocr_llm_service.process_image_with_llm(
                processed_data["processed_image_base64"],
                processed_data["original_ocr_text"],
                ocr_llm_request,
                processed_data["ocr_processing_time"]
            )
            
            total_processing_time = time.time() - start_time
            
            if llm_result.success:
                logger.debug(f"Page {page_number} LLM processing successful in {total_processing_time:.2f}s")
                return PDFPageLLMResult(
                    page_number=page_number,
                    extracted_text=llm_result.extracted_text,
                    original_ocr_text=llm_result.original_ocr_text,
                    processing_time=total_processing_time,
                    ocr_processing_time=llm_result.ocr_processing_time,
                    llm_processing_time=llm_result.llm_processing_time,
                    success=True,
                    error_message=None,
                    threshold_used=llm_result.threshold_used,
                    contrast_level_used=llm_result.contrast_level_used,
                    model_used=llm_result.model_used,
                    prompt_used=llm_result.prompt_used
                )
            else:
                logger.warning(f"Page {page_number} LLM processing failed")
                return PDFPageLLMResult(
                    page_number=page_number,
                    extracted_text="",
                    original_ocr_text=llm_result.original_ocr_text,
                    processing_time=total_processing_time,
                    ocr_processing_time=llm_result.ocr_processing_time,
                    llm_processing_time=llm_result.llm_processing_time,
                    success=False,
                    error_message="LLM processing failed",
                    threshold_used=llm_result.threshold_used,
                    contrast_level_used=llm_result.contrast_level_used,
                    model_used=llm_result.model_used,
                    prompt_used=llm_result.prompt_used
                )
                
        except Exception as e:
            total_processing_time = time.time() - start_time
            logger.error(f"Page {page_number} LLM processing failed: {str(e)}")
            
            return PDFPageLLMResult(
                page_number=page_number,
                extracted_text="",
                original_ocr_text="",
                processing_time=total_processing_time,
                ocr_processing_time=0.0,
                llm_processing_time=0.0,
                success=False,
                error_message=str(e),
                threshold_used=ocr_llm_request.threshold,
                contrast_level_used=ocr_llm_request.contrast_level,
                model_used=ocr_llm_request.model or settings.OCR_LLM_MODEL,
                prompt_used=ocr_llm_request.prompt or settings.OCR_LLM_DEFAULT_PROMPT
            )

    async def _get_processed_image_and_text_for_pdf(self, image_path: Path, ocr_request: OCRRequest) -> dict:
        """
        Process image using external preprocessing service for PDF processing.
        
        Args:
            image_path: Path to image file
            ocr_request: OCR processing parameters
            
        Returns:
            dict: Processed image data from external service
        """
        start_time = time.time()
        
        try:
            # Use external service for image preprocessing
            processed_result = await external_ocr_service.process_image(image_path, ocr_request)
            
            ocr_processing_time = time.time() - start_time
            
            return {
                "processed_image_base64": processed_result.processed_image_base64 if processed_result.success else "",
                "original_ocr_text": "",  # No original text from preprocessing service
                "ocr_processing_time": ocr_processing_time
            }
            
        except Exception as e:
            logger.error(f"Failed to process image for PDF LLM: {str(e)}")
            ocr_processing_time = time.time() - start_time
            
            return {
                "processed_image_base64": "",
                "original_ocr_text": "",
                "ocr_processing_time": ocr_processing_time
            }


# Global PDF OCR service instance
pdf_ocr_service = PDFOCRService()