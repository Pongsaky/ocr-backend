"""
DOCX OCR Service - Full implementation with LibreOffice integration.

This service handles the complete DOCX processing pipeline:
1. DOCX → PDF conversion using LibreOffice
2. PDF → OCR processing using existing PDF service
3. Streaming progress updates
4. Error handling and cleanup
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.models.unified_models import (
    UnifiedPageResult, ProcessingStep, UnifiedOCRRequest,
    ProcessingMode, FileType, UnifiedStreamingStatus
)
from app.services.libreoffice_client import libreoffice_client, LibreOfficeConversionError
from app.services.pdf_ocr_service import pdf_ocr_service
from app.models.ocr_models import PDFOCRRequest, PDFLLMOCRRequest
from app.logger_config import get_logger

UTC = timezone.utc
logger = get_logger(__name__)


class DOCXOCRService:
    """
    Enhanced DOCX OCR Service with LibreOffice integration.
    
    Provides complete DOCX processing pipeline:
    - Document conversion via LibreOffice HTTP service
    - PDF processing integration
    - Streaming progress updates
    - Error handling and resource cleanup
    """
    
    def __init__(self):
        """Initialize the DOCX OCR service."""
        self.libreoffice = libreoffice_client
        logger.info("DOCX OCR Service initialized with LibreOffice integration")
    
    async def health_check(self) -> bool:
        """
        Check if DOCX processing is available.
        
        Returns:
            bool: True if LibreOffice service is available
        """
        try:
            is_healthy = await self.libreoffice.health_check()
            logger.debug(f"DOCX service health check: {'✅ OK' if is_healthy else '❌ FAILED'}")
            return is_healthy
        except Exception as e:
            logger.error(f"DOCX health check failed: {e}")
            return False
    
    async def convert_docx_to_pdf(self, docx_path: Path, temp_dir: Optional[Path] = None) -> Path:
        """
        Convert DOCX file to PDF using LibreOffice service.
        
        Args:
            docx_path: Path to input DOCX file
            temp_dir: Optional temporary directory for output
            
        Returns:
            Path to converted PDF file
            
        Raises:
            LibreOfficeConversionError: If conversion fails
            FileNotFoundError: If input file doesn't exist
        """
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")
        
        # Determine output path
        if temp_dir:
            temp_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_dir / f"{docx_path.stem}.pdf"
        else:
            pdf_path = docx_path.with_suffix('.pdf')
        
        logger.info(f"Converting DOCX to PDF: {docx_path} -> {pdf_path}")
        
        try:
            # Use LibreOffice client for conversion
            converted_path = await self.libreoffice.convert_docx_to_pdf(docx_path, pdf_path)
            
            # Verify PDF was created and has content
            if not converted_path.exists() or converted_path.stat().st_size == 0:
                raise LibreOfficeConversionError("Converted PDF is empty or missing")
            
            logger.info(f"✅ DOCX conversion successful: {converted_path} ({converted_path.stat().st_size} bytes)")
            return converted_path
            
        except Exception as e:
            logger.error(f"❌ DOCX conversion failed: {e}")
            raise
    
    async def estimate_pages(self, docx_path: Path) -> int:
        """
        Estimate number of pages in DOCX file.
        
        Uses file size estimation until LibreOffice provides page count.
        
        Args:
            docx_path: Path to DOCX file
            
        Returns:
            Estimated number of pages (minimum 1)
        """
        try:
            file_size_mb = docx_path.stat().st_size / (1024 * 1024)
            
            # Estimation based on file size:
            # - Small files (< 1MB): 1-3 pages
            # - Medium files (1-5MB): 3-10 pages  
            # - Large files (> 5MB): 10+ pages
            if file_size_mb < 1.0:
                estimated_pages = max(1, int(file_size_mb * 3))
            elif file_size_mb < 5.0:
                estimated_pages = max(3, int(file_size_mb * 2))
            else:
                estimated_pages = max(10, int(file_size_mb * 1.5))
            
            logger.info(f"📊 Estimated {estimated_pages} pages for DOCX ({file_size_mb:.1f}MB): {docx_path}")
            return estimated_pages
            
        except Exception as e:
            logger.warning(f"Failed to estimate DOCX pages: {e}")
            return 1
    
    async def process_docx_with_streaming(
        self,
        docx_path: Path,
        request: UnifiedOCRRequest,
        task_id: str,
        streaming_queue: asyncio.Queue
    ) -> Dict[str, Any]:
        """
        Process DOCX file with complete pipeline and streaming updates.
        
        Pipeline:
        1. DOCX → PDF conversion (20% progress)
        2. PDF → OCR processing (20% → 100% progress)
        3. Optional LLM enhancement
        4. Cleanup and return results
        
        Args:
            docx_path: Path to DOCX file
            request: Processing request parameters
            task_id: Unique task identifier
            streaming_queue: Queue for streaming updates
            
        Returns:
            Processing result dictionary
        """
        temp_dir = None
        pdf_path = None
        
        try:
            logger.info(f"🚀 Starting DOCX processing for task {task_id}")
            
            # Check LibreOffice service availability
            if not await self.health_check():
                error_msg = (
                    "LibreOffice service is not available. For local development, start LibreOffice with:\n"
                    "docker run -d --name libreoffice-converter --rm -p 8080:2004 libreofficedocker/libreoffice-unoserver:3.19"
                )
                logger.error(f"❌ {error_msg}")
                
                await self._send_progress(
                    streaming_queue, task_id, request.mode,
                    ProcessingStep.FAILED, 0.0, "LibreOffice service not available"
                )
                
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "LibreOffice service not available"
                }
            
            # Create temporary directory for intermediate files
            temp_dir = Path(tempfile.mkdtemp(prefix=f"docx_{task_id}_"))
            logger.debug(f"Created temp directory: {temp_dir}")
            
            # Step 1: Convert DOCX to PDF (20% progress)
            await self._send_progress(
                streaming_queue, task_id, request.mode,
                ProcessingStep.CONVERSION, 10.0, "Starting DOCX conversion..."
            )
            
            pdf_path = await self.convert_docx_to_pdf(docx_path, temp_dir)
            
            await self._send_progress(
                streaming_queue, task_id, request.mode,
                ProcessingStep.CONVERSION, 20.0, "DOCX converted to PDF successfully"
            )
            
            # Step 2: Process PDF with OCR (20% → 100% progress)
            await self._send_progress(
                streaming_queue, task_id, request.mode,
                ProcessingStep.OCR_PROCESSING, 25.0, "Starting OCR processing..."
            )
            
            # Delegate to PDF service with progress offset
            pdf_results = await self._process_pdf_with_offset(
                pdf_path, request, task_id, streaming_queue
            )
            
            logger.info(f"✅ DOCX processing completed for task {task_id}")
            
            return {
                "success": True,
                "results": pdf_results,
                "pages_processed": len(pdf_results),
                "message": "DOCX processing completed successfully"
            }
            
        except LibreOfficeConversionError as e:
            logger.error(f"❌ DOCX conversion failed for task {task_id}: {e}")
            
            await self._send_progress(
                streaming_queue, task_id, request.mode,
                ProcessingStep.FAILED, 0.0, f"DOCX conversion failed: {e}"
            )
            
            return {
                "success": False,
                "error": f"DOCX conversion failed: {e}",
                "message": "Failed to convert DOCX to PDF"
            }
            
        except Exception as e:
            logger.error(f"❌ DOCX processing failed for task {task_id}: {e}")
            
            await self._send_progress(
                streaming_queue, task_id, request.mode,
                ProcessingStep.FAILED, 0.0, f"DOCX processing failed: {e}"
            )
            
            return {
                "success": False,
                "error": str(e),
                "message": "DOCX processing failed"
            }
            
        finally:
            # Cleanup temporary files
            await self._cleanup_temp_files(temp_dir, pdf_path)
    
    async def _process_pdf_with_offset(
        self,
        pdf_path: Path,
        request: UnifiedOCRRequest,
        task_id: str,
        streaming_queue: asyncio.Queue
    ) -> List[UnifiedPageResult]:
        """
        Process PDF using existing PDF service with progress adaptation.
        
        Creates a separate queue for PDF progress and translates to unified format.
        
        Args:
            pdf_path: Path to converted PDF file
            request: Processing request
            task_id: Task identifier
            streaming_queue: Streaming queue for unified updates
            
        Returns:
            List of page results
        """
        # Create separate queue for PDF service progress
        pdf_queue = asyncio.Queue()
        
        # Start background task to translate PDF progress to unified progress
        progress_task = asyncio.create_task(
            self._translate_pdf_progress(pdf_queue, streaming_queue, task_id, request.mode)
        )
        
        try:
            # Convert unified request to PDF request format
            if request.mode == ProcessingMode.BASIC:
                pdf_request = PDFOCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level,
                    dpi=request.dpi or 300
                )
                
                # Process with basic OCR (using original PDF service)
                result = await pdf_ocr_service.process_pdf_with_streaming(
                    pdf_path, pdf_request, task_id, pdf_queue
                )
                
            else:  # LLM_ENHANCED
                pdf_llm_request = PDFLLMOCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level,
                    dpi=request.dpi or 300,
                    prompt=request.prompt,
                    model=request.model
                )
                
                # Process with LLM enhancement (using original PDF service)
                result = await pdf_ocr_service.process_pdf_with_llm_streaming(
                    pdf_path, pdf_llm_request, task_id, pdf_queue
                )
            
            # Wait for progress translation to complete
            await progress_task
            
            # Convert PDF results to unified format
            if result and hasattr(result, 'results') and result.results:
                return [
                    UnifiedPageResult(
                        page_number=page_result.page_number,
                        extracted_text=page_result.extracted_text,
                        processing_time=page_result.processing_time,
                        success=page_result.success,
                        threshold_used=page_result.threshold_used,
                        contrast_level_used=page_result.contrast_level_used,
                        image_processing_time=getattr(page_result, 'image_processing_time', None),
                        llm_processing_time=getattr(page_result, 'llm_processing_time', None),
                        model_used=getattr(page_result, 'model_used', None),
                        prompt_used=getattr(page_result, 'prompt_used', None),
                        timestamp=page_result.timestamp
                    )
                    for page_result in result.results
                ]
            else:
                # Fallback result
                return [UnifiedPageResult(
                    page_number=1,
                    extracted_text="PDF processing completed but no results returned",
                    processing_time=0.0,
                    success=True,
                    threshold_used=request.threshold,
                    contrast_level_used=request.contrast_level,
                    timestamp=datetime.now(UTC)
                )]
                
        except Exception as e:
            # Cancel progress translation task
            progress_task.cancel()
            logger.error(f"PDF processing failed in DOCX pipeline: {e}")
            raise
    
    async def _translate_pdf_progress(
        self,
        pdf_queue: asyncio.Queue,
        unified_queue: asyncio.Queue,
        task_id: str,
        mode: ProcessingMode
    ):
        """
        Translate PDF progress updates to unified format with 25%-100% range.
        
        Args:
            pdf_queue: Queue receiving PDF progress updates
            unified_queue: Queue for unified streaming updates  
            task_id: Task identifier
            mode: Processing mode
        """
        try:
            while True:
                # Get PDF progress update
                pdf_update = await pdf_queue.get()
                
                # Check for stream end sentinel
                if pdf_update is None:
                    break
                
                # Calculate adjusted progress (25% to 100%)
                original_progress = pdf_update.progress_percentage
                adjusted_progress = 25.0 + (original_progress * 0.75)
                
                # Convert latest PDF result to unified format if present
                unified_latest_result = None
                if hasattr(pdf_update, 'latest_page_result') and pdf_update.latest_page_result:
                    pdf_result = pdf_update.latest_page_result
                    unified_latest_result = UnifiedPageResult(
                        page_number=pdf_result.page_number,
                        extracted_text=pdf_result.extracted_text,
                        processing_time=pdf_result.processing_time,
                        success=pdf_result.success,
                        threshold_used=pdf_result.threshold_used,
                        contrast_level_used=pdf_result.contrast_level_used,
                        image_processing_time=getattr(pdf_result, 'image_processing_time', None),
                        llm_processing_time=getattr(pdf_result, 'llm_processing_time', None),
                        model_used=getattr(pdf_result, 'model_used', None),
                        prompt_used=getattr(pdf_result, 'prompt_used', None),
                        timestamp=pdf_result.timestamp
                    )
                
                # Convert cumulative results
                unified_cumulative_results = []
                if hasattr(pdf_update, 'cumulative_results') and pdf_update.cumulative_results:
                    for pdf_result in pdf_update.cumulative_results:
                        unified_cumulative_results.append(UnifiedPageResult(
                            page_number=pdf_result.page_number,
                            extracted_text=pdf_result.extracted_text,
                            processing_time=pdf_result.processing_time,
                            success=pdf_result.success,
                            threshold_used=pdf_result.threshold_used,
                            contrast_level_used=pdf_result.contrast_level_used,
                            image_processing_time=getattr(pdf_result, 'image_processing_time', None),
                            llm_processing_time=getattr(pdf_result, 'llm_processing_time', None),
                            model_used=getattr(pdf_result, 'model_used', None),
                            prompt_used=getattr(pdf_result, 'prompt_used', None),
                            timestamp=pdf_result.timestamp
                        ))
                
                # Send unified progress update
                await self._send_progress(
                    unified_queue, task_id, mode,
                    ProcessingStep.OCR_PROCESSING if adjusted_progress < 100.0 else ProcessingStep.COMPLETED,
                    adjusted_progress,
                    f"Processing PDF page {pdf_update.current_page}/{pdf_update.total_pages}",
                    unified_latest_result,
                    unified_cumulative_results
                )
                
        except asyncio.CancelledError:
            logger.debug(f"PDF progress translation cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"PDF progress translation failed for task {task_id}: {e}")
    
    async def _send_progress(
        self,
        queue: asyncio.Queue,
        task_id: str,
        mode: ProcessingMode,
        step: ProcessingStep,
        progress: float,
        message: str,
        result: Optional[UnifiedPageResult] = None,
        cumulative_results: Optional[List[UnifiedPageResult]] = None
    ):
        """Send progress update to streaming queue."""
        try:
            update = UnifiedStreamingStatus(
                task_id=task_id,
                file_type=FileType.DOCX,
                processing_mode=mode,
                status="completed" if step == ProcessingStep.COMPLETED else "processing",
                current_step=step,
                progress_percentage=progress,
                current_page=result.page_number if result else 1,
                total_pages=len(cumulative_results) if cumulative_results else 1,
                processed_pages=len(cumulative_results) if cumulative_results else 0,
                latest_page_result=result,
                cumulative_results=cumulative_results or [],
                timestamp=datetime.now(UTC)
            )
            
            await queue.put(update)
            logger.debug(f"📤 DOCX progress: {step.value} ({progress}%)")
            
        except Exception as e:
            logger.error(f"Failed to send DOCX progress: {e}")
    
    async def _cleanup_temp_files(self, temp_dir: Optional[Path], pdf_path: Optional[Path]):
        """Clean up temporary files and directories."""
        try:
            # Remove PDF file if it exists
            if pdf_path and pdf_path.exists():
                pdf_path.unlink()
                logger.debug(f"🗑️ Removed PDF: {pdf_path}")
            
            # Remove temp directory if it exists and is not empty
            if temp_dir and temp_dir.exists():
                # Remove all files in temp directory
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"🗑️ Removed temp file: {file_path}")
                
                # Remove directory
                temp_dir.rmdir()
                logger.debug(f"🗑️ Removed temp directory: {temp_dir}")
                
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


# Singleton instance
docx_ocr_service = DOCXOCRService() 