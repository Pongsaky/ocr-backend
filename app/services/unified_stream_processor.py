"""
Unified stream processor for all file types with automatic detection and routing.
"""

import asyncio
import uuid
import time
import tempfile
from typing import Dict, Any, Optional, AsyncGenerator, List
from pathlib import Path
from datetime import datetime, timezone

# Use timezone.utc instead of UTC for backward compatibility
UTC = timezone.utc

import fitz  # PyMuPDF for PDF page counting
from PIL import Image
from fastapi import UploadFile, HTTPException

from app.models.unified_models import (
    FileType, ProcessingMode, ProcessingStep, UnifiedOCRRequest, 
    UnifiedOCRResponse, UnifiedStreamingStatus, UnifiedPageResult,
    FileMetadata
)
from app.services.external_ocr_service import external_ocr_service
from app.services.pdf_ocr_service import pdf_ocr_service
from app.services.ocr_llm_service import ocr_llm_service
from app.services.url_download_service import url_download_service, URLDownloadError
from app.models.ocr_models import (
    OCRRequest, OCRLLMRequest, PDFOCRRequest, PDFLLMOCRRequest
)
from app.logger_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class FileTypeDetector:
    """Handles file type detection and validation."""
    
    SUPPORTED_MIME_TYPES = {
        FileType.IMAGE: [
            "image/jpeg", "image/jpg", "image/png", 
            "image/bmp", "image/tiff", "image/webp"
        ],
        FileType.PDF: ["application/pdf"],
        FileType.DOCX: [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
    }
    
    SUPPORTED_EXTENSIONS = {
        FileType.IMAGE: [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
        FileType.PDF: [".pdf"],
        FileType.DOCX: [".docx"]
    }
    
    FILE_SIZE_LIMITS = {
        FileType.IMAGE: 10 * 1024 * 1024,   # 10MB
        FileType.PDF: 50 * 1024 * 1024,     # 50MB
        FileType.DOCX: 25 * 1024 * 1024     # 25MB
    }
    
    @classmethod
    async def detect_file_type(cls, file: UploadFile) -> FileType:
        """Detect file type from MIME type and extension."""
        from config.settings import settings
        
        logger.debug(f"Detecting file type for: {file.filename} (MIME: {file.content_type})")
        
        # Primary: MIME type detection
        for file_type, mime_types in cls.SUPPORTED_MIME_TYPES.items():
            if file.content_type in mime_types:
                # Check if DOCX processing is disabled
                if file_type == FileType.DOCX and not settings.ENABLE_DOCX_PROCESSING:
                    logger.warning(f"🚫 DOCX file detected but DOCX processing is disabled")
                    raise HTTPException(
                        status_code=400,
                        detail="DOCX processing is currently disabled. Supported formats: images and PDFs only."
                    )
                logger.info(f"✅ Detected {file_type.value} from MIME type: {file.content_type}")
                return file_type
        
        # Fallback: Extension detection
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            for file_type, extensions in cls.SUPPORTED_EXTENSIONS.items():
                if file_ext in extensions:
                    # Check if DOCX processing is disabled
                    if file_type == FileType.DOCX and not settings.ENABLE_DOCX_PROCESSING:
                        logger.warning(f"🚫 DOCX file detected but DOCX processing is disabled")
                        raise HTTPException(
                            status_code=400,
                            detail="DOCX processing is currently disabled. Supported formats: images and PDFs only."
                        )
                    logger.info(f"✅ Detected {file_type.value} from extension: {file_ext}")
                    return file_type
        
        # No match found
        supported_types = []
        for ft, mimes in cls.SUPPORTED_MIME_TYPES.items():
            # Skip DOCX from supported types if disabled
            if ft == FileType.DOCX and not settings.ENABLE_DOCX_PROCESSING:
                continue
            supported_types.extend(mimes)
        
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. MIME: {file.content_type}, "
                   f"Filename: {file.filename}. Supported types: {supported_types}"
        )
    
    @classmethod
    async def validate_file_size(cls, file: UploadFile, file_type: FileType) -> None:
        """Validate file size based on file type."""
        max_size = cls.FILE_SIZE_LIMITS[file_type]
        
        if file.size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"{file_type.value.upper()} file too large. "
                       f"Size: {file.size:,} bytes, Max: {max_size:,} bytes"
            )
        
        logger.debug(f"✅ File size OK: {file.size:,} bytes (max: {max_size:,})")


class MetadataExtractor:
    """Extracts metadata from different file types."""
    
    @staticmethod
    async def extract_image_metadata(file_path: Path) -> Dict[str, int]:
        """Extract image dimensions."""
        try:
            with Image.open(file_path) as img:
                return {"width": img.width, "height": img.height}
        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")
            return {"width": 0, "height": 0}
    
    @staticmethod
    async def extract_pdf_metadata(file_path: Path) -> int:
        """Extract PDF page count."""
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {e}")
            return 0
    
    @staticmethod
    async def extract_docx_metadata(file_path: Path) -> int:
        """Extract estimated DOCX page count."""
        # For now, estimate based on file size (will improve when we add python-docx)
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            estimated_pages = max(1, int(file_size_mb * 2))  # Rough estimate
            return estimated_pages
        except Exception as e:
            logger.warning(f"Failed to extract DOCX metadata: {e}")
            return 1


class ProcessingTimeEstimator:
    """Estimates processing time based on file type and size."""
    
    # Base processing times per page (in seconds)
    BASE_TIMES = {
        FileType.IMAGE: {"basic": 2.0, "llm_enhanced": 4.0},
        FileType.PDF: {"basic": 1.5, "llm_enhanced": 3.0},
        FileType.DOCX: {"basic": 3.0, "llm_enhanced": 5.0}  # Includes conversion time
    }
    
    @classmethod
    def estimate_duration(
        cls, 
        file_type: FileType, 
        file_size: int, 
        mode: ProcessingMode,
        page_count: int = 1
    ) -> float:
        """Estimate total processing duration."""
        base_time = cls.BASE_TIMES[file_type][mode.value]
        
        # Size factor (larger files take slightly longer)
        size_factor = 1.0 + (file_size / (10 * 1024 * 1024)) * 0.2  # +20% per 10MB
        
        # Page count factor
        total_time = base_time * page_count * size_factor
        
        # Add overhead for DOCX conversion
        if file_type == FileType.DOCX:
            total_time += 5.0  # DOCX -> PDF conversion overhead
        
        return round(total_time, 1)


class UnifiedStreamProcessor:
    """Unified processor for all file types with streaming support."""
    
    def __init__(self):
        self.file_detector = FileTypeDetector()
        self.metadata_extractor = MetadataExtractor()
        self.time_estimator = ProcessingTimeEstimator()
        self.streaming_queues: Dict[str, asyncio.Queue] = {}
        self.task_metadata: Dict[str, Dict] = {}  # Store task metadata
        
        logger.info("🚀 Unified Stream Processor initialized")
    
    async def process_file_stream(
        self, 
        file: Optional[UploadFile], 
        request: UnifiedOCRRequest,
        task_id: str
    ) -> UnifiedOCRResponse:
        """
        Process any supported file type with streaming.
        Supports both file upload and URL download methods.
        
        Args:
            file: Uploaded file (None for URL downloads)
            request: Unified processing parameters (may contain URL)
            task_id: Unique task identifier
            
        Returns:
            UnifiedOCRResponse: Task response for streaming
        """
        start_time = time.time()
        file_path = None
        download_metadata = None
        
        try:
            # Step 1: Handle URL download if applicable
            if request.url:
                logger.info(f"🌐 Processing URL download for task {task_id}: {request.url}")
                
                # Create streaming queue early for URL download updates
                streaming_queue = asyncio.Queue()
                self.streaming_queues[task_id] = streaming_queue
                
                # Send initial download progress update
                await self._send_progress_update(
                    task_id, None, request.mode, "processing", 
                    ProcessingStep.URL_DOWNLOAD, 5.0,
                    f"Starting download from URL: {request.url}"
                )
                
                try:
                    file_path, download_metadata = await url_download_service.download_file(
                        request.url, task_id
                    )
                    
                    # Create a mock UploadFile object for downstream compatibility
                    file = MockUploadFile(
                        filename=download_metadata["downloaded_filename"],
                        content_type=download_metadata["content_type"],
                        size=download_metadata["file_size_bytes"]
                    )
                    
                    await self._send_progress_update(
                        task_id, None, request.mode, "processing",
                        ProcessingStep.URL_DOWNLOAD, 15.0,
                        f"Downloaded file: {file.filename} ({file.size:,} bytes)"
                    )
                    
                except URLDownloadError as e:
                    logger.error(f"❌ URL download failed for {task_id}: {e}")
                    # Cleanup on download failure
                    if task_id in self.streaming_queues:
                        del self.streaming_queues[task_id]
                    raise HTTPException(status_code=400, detail=str(e))
            
            # Step 2: Detect file type
            file_type = await self.file_detector.detect_file_type(file)
            logger.info(f"🎯 Processing {file_type.value} file: {file.filename}")
            
            # Step 3: Validate file size (skip for URL downloads - already validated)
            if not request.url:
                await self.file_detector.validate_file_size(file, file_type)
            
            # Step 4: Create streaming queue (if not already created for URL)
            if not request.url:
                streaming_queue = asyncio.Queue()
                self.streaming_queues[task_id] = streaming_queue
            
            # Step 5: Save uploaded file (if not URL download)
            if not request.url:
                file_path = await self._save_uploaded_file(file, task_id)
            
            # Step 6: Extract metadata
            file_metadata = await self._extract_file_metadata(file, file_type, file_path)
            
            # Add download info to metadata if applicable
            if download_metadata:
                file_metadata.original_filename = f"Downloaded: {download_metadata['original_url']}"
            
            # Step 7: Estimate processing time
            page_count = 1
            if file_type == FileType.PDF:
                page_count = file_metadata.pdf_page_count or 1
            elif file_type == FileType.DOCX:
                page_count = file_metadata.docx_page_count or 1
            
            estimated_duration = self.time_estimator.estimate_duration(
                file_type, file.size, request.mode, page_count
            )
            
            # Add URL download time if applicable
            if request.url:
                estimated_duration += 5.0  # Add download overhead
            
            # Step 8: Store task metadata
            self.task_metadata[task_id] = {
                "file_type": file_type,
                "file_path": file_path,
                "request": request,
                "start_time": start_time,
                "metadata": file_metadata,
                "from_url": bool(request.url),
                "download_metadata": download_metadata
            }
            
            # Step 9: Create initial response
            response = UnifiedOCRResponse(
                task_id=task_id,
                file_type=file_type,
                processing_mode=request.mode,
                status="processing",
                created_at=datetime.now(UTC),
                estimated_duration=estimated_duration,
                file_metadata=file_metadata
            )
            
            # Step 10: Send initial progress update (if not URL download)
            if not request.url:
                await self._send_progress_update(
                    task_id, file_type, request.mode, "processing", 
                    ProcessingStep.UPLOAD, 5.0, "File uploaded successfully"
                )
            
            # Step 11: Start async processing
            asyncio.create_task(
                self._process_file_async(task_id, file_type, file_path, request)
            )
            
            source_type = "URL" if request.url else "uploaded file"
            logger.info(
                f"✅ Created {file_type.value} streaming task {task_id} from {source_type} "
                f"(mode: {request.mode.value}, estimated: {estimated_duration}s)"
            )
            
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions without wrapping
            if task_id in self.streaming_queues:
                del self.streaming_queues[task_id]
            if task_id in self.task_metadata:
                del self.task_metadata[task_id]
            raise
        except Exception as e:
            logger.error(f"❌ Failed to start unified processing for {task_id}: {e}")
            
            # Cleanup on failure
            if task_id in self.streaming_queues:
                del self.streaming_queues[task_id]
            if task_id in self.task_metadata:
                del self.task_metadata[task_id]
                
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_file_async(
        self, 
        task_id: str, 
        file_type: FileType, 
        file_path: Path, 
        request: UnifiedOCRRequest
    ):
        """Process file asynchronously with type-specific logic."""
        try:
            streaming_queue = self.streaming_queues.get(task_id)
            if not streaming_queue:
                logger.error(f"No streaming queue found for task {task_id}")
                return
            
            # Send validation progress
            await self._send_progress_update(
                task_id, file_type, request.mode, "processing",
                ProcessingStep.VALIDATION, 10.0, f"Validating {file_type.value} file..."
            )
            
            # Route to appropriate processor
            if file_type == FileType.IMAGE:
                await self._process_image_stream(task_id, file_path, request, streaming_queue)
            elif file_type == FileType.PDF:
                await self._process_pdf_stream(task_id, file_path, request, streaming_queue)
            elif file_type == FileType.DOCX:
                await self._process_docx_stream(task_id, file_path, request, streaming_queue)
                
        except Exception as e:
            logger.error(f"❌ Processing failed for {task_id}: {e}")
            await self._send_progress_update(
                task_id, file_type, request.mode, "failed",
                ProcessingStep.FAILED, 0.0, f"Processing failed: {e}"
            )
            # Note: Cleanup is now handled by the stream generator when stream ends
    
    async def _process_image_stream(
        self, 
        task_id: str, 
        file_path: Path, 
        request: UnifiedOCRRequest, 
        streaming_queue: asyncio.Queue
    ):
        """Process image with streaming updates."""
        try:
            # Step 1: OCR Processing (20% -> 80%)
            await self._send_progress_update(
                task_id, FileType.IMAGE, request.mode, "processing",
                ProcessingStep.OCR_PROCESSING, 20.0, "Starting OCR processing..."
            )
            
            # Convert to appropriate request type
            if request.mode == ProcessingMode.BASIC:
                ocr_request = OCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level
                )
                
                # Process with external OCR service
                result = await external_ocr_service.process_image(file_path, ocr_request)
                
                if not result.success:
                    raise Exception(f"Image processing failed: {result.error_message}")
                
                # Create unified page result
                page_result = UnifiedPageResult(
                    page_number=1,
                    extracted_text=result.extracted_text,
                    processing_time=result.processing_time,
                    success=True,
                    threshold_used=result.threshold_used,
                    contrast_level_used=result.contrast_level_used,
                    timestamp=datetime.now(UTC)
                )
                
            else:  # LLM_ENHANCED
                await self._send_progress_update(
                    task_id, FileType.IMAGE, request.mode, "processing",
                    ProcessingStep.OCR_PROCESSING, 40.0, "Processing with external OCR..."
                )
                
                # First do basic OCR
                ocr_request = OCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level
                )
                ocr_result = await external_ocr_service.process_image(file_path, ocr_request)
                
                if not ocr_result.success:
                    raise Exception(f"Image preprocessing failed: {ocr_result.error_message}")
                
                await self._send_progress_update(
                    task_id, FileType.IMAGE, request.mode, "processing",
                    ProcessingStep.LLM_ENHANCEMENT, 60.0, "Enhancing with LLM..."
                )
                
                # Then enhance with LLM
                llm_request = OCRLLMRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level,
                    prompt=request.prompt,
                    model=request.model
                )
                
                llm_result = await ocr_llm_service.process_image_with_llm(
                    processed_image_base64=ocr_result.processed_image_base64,
                    ocr_request=llm_request,
                    image_processing_time=ocr_result.processing_time
                )
                
                if not llm_result.success:
                    raise Exception(f"LLM processing failed: {llm_result.error_message}")
                
                # Create unified page result
                page_result = UnifiedPageResult(
                    page_number=1,
                    extracted_text=llm_result.extracted_text,
                    processing_time=llm_result.processing_time,
                    success=True,
                    threshold_used=llm_result.threshold_used,
                    contrast_level_used=llm_result.contrast_level_used,
                    image_processing_time=llm_result.image_processing_time,
                    llm_processing_time=llm_result.llm_processing_time,
                    model_used=llm_result.model_used,
                    prompt_used=llm_result.prompt_used,
                    timestamp=datetime.now(UTC)
                )
            
            # Send completion update
            await self._send_progress_update(
                task_id, FileType.IMAGE, request.mode, "completed",
                ProcessingStep.COMPLETED, 100.0, "Image processing completed",
                latest_result=page_result,
                cumulative_results=[page_result]
            )
            
        except Exception as e:
            logger.error(f"Image processing failed for {task_id}: {e}")
            raise
    
    async def _process_pdf_stream(
        self, 
        task_id: str, 
        file_path: Path, 
        request: UnifiedOCRRequest, 
        streaming_queue: asyncio.Queue
    ):
        """Process PDF with streaming updates using existing PDF service."""
        try:
            # Convert to PDF request format
            if request.mode == ProcessingMode.BASIC:
                pdf_request = PDFOCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level,
                    dpi=request.dpi or 300
                )
                
                # Use existing PDF streaming service
                result = await pdf_ocr_service.process_pdf_with_streaming(
                    file_path, pdf_request, task_id, streaming_queue
                )
                
            else:  # LLM_ENHANCED
                pdf_llm_request = PDFLLMOCRRequest(
                    threshold=request.threshold,
                    contrast_level=request.contrast_level,
                    dpi=request.dpi or 300,
                    prompt=request.prompt,
                    model=request.model
                )
                
                # Use existing PDF LLM streaming service
                result = await pdf_ocr_service.process_pdf_with_llm_streaming(
                    file_path, pdf_llm_request, task_id, streaming_queue
                )
            
            logger.info(f"✅ PDF processing completed for {task_id}")
            
        except Exception as e:
            logger.error(f"PDF processing failed for {task_id}: {e}")
            raise
    
    async def _process_docx_stream(
        self, 
        task_id: str, 
        file_path: Path, 
        request: UnifiedOCRRequest, 
        streaming_queue: asyncio.Queue
    ):
        """Process DOCX with streaming updates using LibreOffice service."""
        try:
            # Import the DOCX service
            from app.services.docx_ocr_service import docx_ocr_service
            
            logger.info(f"🎯 Processing DOCX file for task {task_id}")
            
            # Use the LibreOffice DOCX service with unified request directly
            result = await docx_ocr_service.process_docx_with_streaming(
                file_path, request, task_id, streaming_queue
            )
            
            if not result.get("success", False):
                error_msg = result.get("error", "Unknown DOCX processing error")
                raise Exception(f"DOCX processing failed: {error_msg}")
            
            logger.info(f"✅ DOCX processing completed for {task_id}")
            
        except Exception as e:
            logger.error(f"DOCX processing failed for {task_id}: {e}")
            raise
    
    async def get_stream_generator(self, task_id: str) -> AsyncGenerator[str, None]:
        """Get streaming generator for any file type."""
        if task_id not in self.streaming_queues:
            raise HTTPException(404, f"Streaming task {task_id} not found")
        
        queue = self.streaming_queues[task_id]
        logger.debug(f"🌊 Starting stream for task {task_id}")
        
        try:
            while True:
                try:
                    # Wait for next update with timeout
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Send SSE formatted data
                    yield f"data: {update.model_dump_json()}\n\n"
                    
                    # Check if processing completed
                    if update.status in ["completed", "failed", "cancelled"]:
                        logger.debug(f"🏁 Stream completed for {task_id} with status: {update.status}")
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = {
                        "heartbeat": True,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "task_id": task_id
                    }
                    yield f"data: {heartbeat}\n\n"
                    
        except Exception as e:
            logger.error(f"❌ Streaming error for {task_id}: {e}")
            error_update = {
                "task_id": task_id,
                "status": "failed",
                "error_message": f"Streaming error: {e}",
                "timestamp": datetime.now(UTC).isoformat()
            }
            yield f"data: {error_update}\n\n"
        finally:
            logger.debug(f"🔌 Closing stream for {task_id}")
            # Cleanup task resources when stream ends
            await self._cleanup_task(task_id)
    
    async def _send_progress_update(
        self,
        task_id: str,
        file_type: Optional[FileType],
        mode: ProcessingMode,
        status: str,
        step: ProcessingStep,
        progress: float,
        message: str,
        latest_result: Optional[UnifiedPageResult] = None,
        cumulative_results: Optional[List[UnifiedPageResult]] = None
    ):
        """Send progress update to streaming queue."""
        queue = self.streaming_queues.get(task_id)
        if not queue:
            return
        
        # Get task metadata for page counts
        task_meta = self.task_metadata.get(task_id, {})
        metadata = task_meta.get("metadata")
        
        total_pages = 1
        current_page = 1
        processed_pages = len(cumulative_results) if cumulative_results else 0
        
        if metadata and file_type:
            if file_type == FileType.PDF and metadata.pdf_page_count:
                total_pages = metadata.pdf_page_count
            elif file_type == FileType.DOCX and metadata.docx_page_count:
                total_pages = metadata.docx_page_count
        
        if latest_result:
            current_page = latest_result.page_number
        
        update = UnifiedStreamingStatus(
            task_id=task_id,
            file_type=file_type,
            processing_mode=mode,
            status=status,
            current_step=step,
            progress_percentage=progress,
            current_page=current_page,
            total_pages=total_pages,
            processed_pages=processed_pages,
            latest_page_result=latest_result,
            cumulative_results=cumulative_results or [],
            timestamp=datetime.now(UTC)
        )
        
        try:
            await queue.put(update)
            logger.debug(f"📤 Sent progress update for {task_id}: {step.value} ({progress}%)")
        except Exception as e:
            logger.error(f"Failed to send progress update for {task_id}: {e}")
    
    async def _save_uploaded_file(self, file: UploadFile, task_id: str) -> Path:
        """Save uploaded file to temporary location."""
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        original_ext = Path(file.filename).suffix if file.filename else ""
        file_path = upload_dir / f"{task_id}{original_ext}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.debug(f"💾 Saved file to: {file_path}")
        return file_path
    
    async def _extract_file_metadata(
        self, 
        file: UploadFile, 
        file_type: FileType, 
        file_path: Path
    ) -> FileMetadata:
        """Extract comprehensive file metadata."""
        metadata = FileMetadata(
            original_filename=file.filename or "unknown",
            file_size_bytes=file.size,
            mime_type=file.content_type or "unknown",
            detected_file_type=file_type
        )
        
        # Extract type-specific metadata
        if file_type == FileType.IMAGE:
            metadata.image_dimensions = await self.metadata_extractor.extract_image_metadata(file_path)
            
        elif file_type == FileType.PDF:
            metadata.pdf_page_count = await self.metadata_extractor.extract_pdf_metadata(file_path)
            
        elif file_type == FileType.DOCX:
            metadata.docx_page_count = await self.metadata_extractor.extract_docx_metadata(file_path)
        
        return metadata
    
    async def _cleanup_task(self, task_id: str):
        """Cleanup task resources including URL download files."""
        try:
            # Remove from streaming queues immediately to stop streaming
            if task_id in self.streaming_queues:
                del self.streaming_queues[task_id]
            
            # Clean up files
            if task_id in self.task_metadata:
                task_meta = self.task_metadata[task_id]
                file_path = task_meta.get("file_path")
                from_url = task_meta.get("from_url", False)
                download_metadata = task_meta.get("download_metadata")
                
                # Clean up main file
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    logger.debug(f"🗑️ Cleaned up file: {file_path}")
                
                # Clean up URL download directory if applicable
                if from_url and download_metadata:
                    temp_directory = download_metadata.get("temp_directory")
                    if temp_directory:
                        import shutil
                        temp_dir_path = Path(temp_directory)
                        if temp_dir_path.exists() and temp_dir_path.is_dir():
                            shutil.rmtree(temp_dir_path)
                            logger.debug(f"🗑️ Cleaned up URL download directory: {temp_directory}")
                
                # Mark task as completed but keep metadata for a grace period
                # This prevents race conditions with cancellation requests
                task_meta["status"] = "completed"
                task_meta["cleanup_time"] = datetime.now(UTC)
                logger.debug(f"🏁 Marked task {task_id} as completed, keeping metadata for grace period")
                
                # Schedule delayed cleanup of metadata (after 30 seconds)
                asyncio.create_task(self._delayed_metadata_cleanup(task_id))
            
            logger.debug(f"🧹 Cleaned up task {task_id}")
            
        except Exception as e:
            logger.error(f"Cleanup error for {task_id}: {e}")
    
    async def _delayed_metadata_cleanup(self, task_id: str):
        """Remove task metadata after a grace period to prevent race conditions."""
        try:
            # Wait 30 seconds before final cleanup
            await asyncio.sleep(30)
            
            if task_id in self.task_metadata:
                del self.task_metadata[task_id]
                logger.debug(f"🗑️ Final cleanup of metadata for task {task_id}")
                
        except Exception as e:
            logger.error(f"Delayed cleanup error for {task_id}: {e}")


class MockUploadFile:
    """Mock UploadFile object for URL downloads to maintain compatibility."""
    
    def __init__(self, filename: str, content_type: str, size: int):
        self.filename = filename
        self.content_type = content_type
        self.size = size


# Singleton instance
unified_processor = UnifiedStreamProcessor() 