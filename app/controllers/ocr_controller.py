"""
OCR controller for handling OCR business logic.
"""

import uuid
import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, UploadFile

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, OCRResponse, OCRResult,
    OCRLLMRequest, OCRLLMResponse, OCRLLMResult,
    PDFOCRRequest, PDFOCRResponse, PDFOCRResult,
    PDFLLMOCRRequest, PDFLLMOCRResponse, PDFLLMOCRResult,
    CancelTaskRequest, CancelTaskResponse, TaskCancellationError, TaskStatus
)
from app.services.external_ocr_service import external_ocr_service
from app.services.ocr_llm_service import ocr_llm_service
from app.services.pdf_ocr_service import pdf_ocr_service
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class OCRController:
    """Controller for OCR operations."""
    
    def __init__(self):
        """Initialize OCR controller."""
        self.settings = settings
        self.tasks: Dict[str, OCRResponse] = {}
        self.llm_tasks: Dict[str, OCRLLMResponse] = {}
        self.pdf_tasks: Dict[str, PDFOCRResponse] = {}
        self.pdf_llm_tasks: Dict[str, PDFLLMOCRResponse] = {}
        # New streaming queues for real-time updates
        self.streaming_queues: Dict[str, asyncio.Queue] = {}
        # Task cancellation tracking
        self.cancelled_tasks: set = set()
        self.cancellation_reasons: Dict[str, str] = {}
        self.executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_TASKS
        )
        logger.info("OCR Controller initialized with streaming support and task cancellation")
    
    async def process_image(
        self, 
        file: UploadFile, 
        ocr_request: OCRRequest
    ) -> OCRResponse:
        """
        Process uploaded image for OCR using external preprocessing + LLM text extraction.
        
        Args:
            file: Uploaded image file
            ocr_request: OCR processing parameters
            
        Returns:
            OCRResponse: Processing response with task ID
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate file
            await self._validate_upload_file(file)
            
            # Save uploaded file
            image_path = await self._save_uploaded_file(file, task_id)
            
            # Create initial task response
            task_response = OCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.tasks[task_id] = task_response
            
            # Start processing asynchronously
            asyncio.create_task(
                self._process_image_async(task_id, image_path, ocr_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start OCR task {task_id}: {str(e)}")
            
            error_response = OCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.tasks[task_id] = error_response
            return error_response
    
    async def get_task_status(self, task_id: str) -> OCRResponse:
        """
        Get the status of an OCR task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            OCRResponse: Task status and result
            
        Raises:
            HTTPException: If task not found
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        return self.tasks[task_id]
    
    async def process_image_sync(
        self, 
        file: UploadFile, 
        ocr_request: OCRRequest
    ) -> OCRResult:
        """
        Process uploaded image synchronously using external preprocessing + LLM text extraction.
        
        Args:
            file: Uploaded image file
            ocr_request: OCR processing parameters
            
        Returns:
            OCRResult: Direct OCR processing result
            
        Raises:
            HTTPException: If processing fails
        """
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting synchronous OCR for file {file.filename}")
        
        try:
            # Validate file
            await self._validate_upload_file(file)
            
            # Save uploaded file
            image_path = await self._save_uploaded_file(file, task_id)
            
            # Step 1: Process image with external service (preprocessing)
            logger.debug("Step 1: Processing image with external preprocessing service")
            processed_result = await external_ocr_service.process_image(image_path, ocr_request)
            
            if not processed_result.success:
                raise Exception(f"Image preprocessing failed: {processed_result.error_message}")
            
            # Step 2: Extract text using LLM service
            logger.debug("Step 2: Extracting text with LLM service")
            
            # Convert to OCRLLMRequest for LLM processing
            ocr_llm_request = OCRLLMRequest(
                threshold=ocr_request.threshold,
                contrast_level=ocr_request.contrast_level,
                prompt=None,  # Use default prompt
                model=None    # Use default model
            )
            
            # Use LLM service to extract text from processed image
            llm_result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result.processed_image_base64,
                original_ocr_text="",  # No original text from preprocessing
                ocr_request=ocr_llm_request,
                image_processing_time=processed_result.processing_time
            )
            
            # Cleanup temporary file
            await self._cleanup_file(image_path)
            
            # Convert LLM result to OCR result format
            return OCRResult(
                success=llm_result.success,
                extracted_text=llm_result.extracted_text,
                processing_time=llm_result.processing_time,
                threshold_used=llm_result.threshold_used,
                contrast_level_used=llm_result.contrast_level_used
            )
            
        except Exception as e:
            logger.error(f"Synchronous OCR processing failed: {str(e)}")
            
            # Try to cleanup file if it exists
            try:
                if 'image_path' in locals():
                    await self._cleanup_file(image_path)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed: {str(e)}"
            )
    
    async def _process_image_async(
        self, 
        task_id: str, 
        image_path: Path, 
        ocr_request: OCRRequest
    ) -> None:
        """
        Process image asynchronously and update task status.
        
        Args:
            task_id: Unique task identifier
            image_path: Path to uploaded image
            ocr_request: OCR processing parameters
        """
        try:
            logger.info(f"Processing OCR task {task_id} asynchronously")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"OCR task {task_id} was cancelled before processing started")
                return
            
            # Step 1: Process image with external service (preprocessing)
            processed_result = await external_ocr_service.process_image(image_path, ocr_request)
            
            if not processed_result.success:
                raise Exception(f"Image preprocessing failed: {processed_result.error_message}")
            
            # Step 2: Extract text using LLM service
            ocr_llm_request = OCRLLMRequest(
                threshold=ocr_request.threshold,
                contrast_level=ocr_request.contrast_level,
                prompt=None,  # Use default prompt
                model=None    # Use default model
            )
            
            llm_result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result.processed_image_base64,
                original_ocr_text="",  # No original text from preprocessing
                ocr_request=ocr_llm_request,
                image_processing_time=processed_result.processing_time
            )
            
            # Convert LLM result to OCR result format
            result = OCRResult(
                success=llm_result.success,
                extracted_text=llm_result.extracted_text,
                processing_time=llm_result.processing_time,
                threshold_used=llm_result.threshold_used,
                contrast_level_used=llm_result.contrast_level_used
            )
            
            # Update task with result
            completed_at = datetime.utcnow()
            
            self.tasks[task_id] = OCRResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "OCR processing failed",
                created_at=self.tasks[task_id].created_at,
                completed_at=completed_at
            )
            
            logger.info(f"OCR task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Async OCR processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            self.tasks[task_id] = OCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
        
        finally:
            # Cleanup temporary file
            await self._cleanup_file(image_path)
    
    # --- LLM-Enhanced OCR Methods ---
    
    async def process_image_with_llm(
        self, 
        file: UploadFile, 
        ocr_llm_request: OCRLLMRequest
    ) -> OCRLLMResponse:
        """
        Process uploaded image for LLM-enhanced OCR with custom prompts/models.
        
        Args:
            file: Uploaded image file
            ocr_llm_request: OCR LLM processing parameters
            
        Returns:
            OCRLLMResponse: Processing response with task ID
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting LLM OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate file
            await self._validate_upload_file(file)
            
            # Save uploaded file
            image_path = await self._save_uploaded_file(file, task_id)
            
            # Create initial task response
            task_response = OCRLLMResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.llm_tasks[task_id] = task_response
            
            # Start processing asynchronously
            asyncio.create_task(
                self._process_image_with_llm_async(task_id, image_path, ocr_llm_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start LLM OCR task {task_id}: {str(e)}")
            
            error_response = OCRLLMResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.llm_tasks[task_id] = error_response
            return error_response
    
    async def get_llm_task_status(self, task_id: str) -> OCRLLMResponse:
        """
        Get the status of an LLM OCR task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            OCRLLMResponse: Task status and result
            
        Raises:
            HTTPException: If task not found
        """
        if task_id not in self.llm_tasks:
            logger.warning(f"LLM task {task_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"LLM task {task_id} not found"
            )
        
        return self.llm_tasks[task_id]
    
    async def process_image_with_llm_sync(
        self, 
        file: UploadFile, 
        ocr_llm_request: OCRLLMRequest
    ) -> OCRLLMResult:
        """
        Process uploaded image with LLM synchronously with custom prompts/models.
        
        Args:
            file: Uploaded image file
            ocr_llm_request: OCR LLM processing parameters
            
        Returns:
            OCRLLMResult: Direct LLM OCR processing result
            
        Raises:
            HTTPException: If processing fails
        """
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting synchronous LLM OCR for file {file.filename}")
        
        try:
            # Validate file
            await self._validate_upload_file(file)
            
            # Save uploaded file
            image_path = await self._save_uploaded_file(file, task_id)
            
            # Step 1: Process image with external service (preprocessing)
            ocr_request = OCRRequest(
                threshold=ocr_llm_request.threshold,
                contrast_level=ocr_llm_request.contrast_level
            )
            
            processed_result = await external_ocr_service.process_image(image_path, ocr_request)
            
            if not processed_result.success:
                raise Exception(f"Image preprocessing failed: {processed_result.error_message}")
            
            # Step 2: Extract text using LLM service
            result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result.processed_image_base64,
                original_ocr_text="",  # No original text from preprocessing
                ocr_request=ocr_llm_request,
                image_processing_time=processed_result.processing_time
            )
            
            # Cleanup temporary file
            await self._cleanup_file(image_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Synchronous LLM OCR processing failed: {str(e)}")
            
            # Try to cleanup file if it exists
            try:
                if 'image_path' in locals():
                    await self._cleanup_file(image_path)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"LLM OCR processing failed: {str(e)}"
            )
    
    async def _process_image_with_llm_async(
        self, 
        task_id: str, 
        image_path: Path, 
        ocr_llm_request: OCRLLMRequest
    ) -> None:
        """
        Process image with LLM asynchronously and update task status.
        
        Args:
            task_id: Unique task identifier
            image_path: Path to uploaded image
            ocr_llm_request: OCR LLM processing parameters
        """
        try:
            logger.info(f"Processing LLM OCR task {task_id} asynchronously")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"LLM OCR task {task_id} was cancelled before processing started")
                return
            
            # Step 1: Process image with external service (preprocessing)
            ocr_request = OCRRequest(
                threshold=ocr_llm_request.threshold,
                contrast_level=ocr_llm_request.contrast_level
            )
            
            processed_result = await external_ocr_service.process_image(image_path, ocr_request)
            
            if not processed_result.success:
                raise Exception(f"Image preprocessing failed: {processed_result.error_message}")
            
            # Step 2: Extract text using LLM service
            result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result.processed_image_base64,
                original_ocr_text="",  # No original text from preprocessing
                ocr_request=ocr_llm_request,
                image_processing_time=processed_result.processing_time
            )
            
            # Update task with result
            completed_at = datetime.utcnow()
            
            self.llm_tasks[task_id] = OCRLLMResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "LLM OCR processing failed",
                created_at=self.llm_tasks[task_id].created_at,
                completed_at=completed_at
            )
            
            logger.info(f"LLM OCR task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Async LLM OCR processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            self.llm_tasks[task_id] = OCRLLMResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.llm_tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
        
        finally:
            # Cleanup temporary file
            await self._cleanup_file(image_path)
    
    async def _validate_upload_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file.
        
        Args:
            file: Uploaded file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        if file.size and file.size > self.settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.settings.MAX_FILE_SIZE} bytes"
            )
        
        # Check file extension
        if file.filename:
            extension = Path(file.filename).suffix.lower().lstrip('.')
            if extension not in self.settings.ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {extension}. "
                           f"Supported formats: {', '.join(self.settings.ALLOWED_IMAGE_EXTENSIONS)}"
                )
    
    async def _save_uploaded_file(self, file: UploadFile, task_id: str) -> Path:
        """
        Save uploaded file to temporary location.
        
        Args:
            file: Uploaded file
            task_id: Unique task identifier
            
        Returns:
            Path: Path to saved file
        """
        # Create upload directory if it doesn't exist
        upload_dir = Path(self.settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        extension = Path(file.filename).suffix if file.filename else '.jpg'
        filename = f"{task_id}{extension}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.debug(f"Saved uploaded file to {file_path}")
        return file_path
    
    async def _cleanup_file(self, file_path: Path) -> None:
        """
        Remove temporary file.
        
        Args:
            file_path: Path to file to remove
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {str(e)}")
    
    # --- PDF Processing Methods ---
    
    async def process_pdf(
        self, 
        file: UploadFile, 
        pdf_request: PDFOCRRequest
    ) -> PDFOCRResponse:
        """
        Process uploaded PDF for OCR.
        
        Args:
            file: Uploaded PDF file
            pdf_request: PDF OCR processing parameters
            
        Returns:
            PDFOCRResponse: Processing response with task ID
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting PDF OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Create initial task response
            task_response = PDFOCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.pdf_tasks[task_id] = task_response
            
            # Start processing asynchronously
            asyncio.create_task(
                self._process_pdf_async(task_id, pdf_path, pdf_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start PDF OCR task {task_id}: {str(e)}")
            
            error_response = PDFOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_tasks[task_id] = error_response
            return error_response
    
    async def process_pdf_sync(
        self, 
        file: UploadFile, 
        pdf_request: PDFOCRRequest
    ) -> PDFOCRResult:
        """
        Process uploaded PDF synchronously.
        
        Args:
            file: Uploaded PDF file
            pdf_request: PDF OCR processing parameters
            
        Returns:
            PDFOCRResult: Direct PDF OCR processing result
            
        Raises:
            HTTPException: If processing fails
        """
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting synchronous PDF OCR for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Process PDF
            result = await pdf_ocr_service.process_pdf(pdf_path, pdf_request)
            
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Synchronous PDF OCR processing failed: {str(e)}")
            
            # Try to cleanup file if it exists
            try:
                if 'pdf_path' in locals():
                    await self._cleanup_file(pdf_path)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"PDF OCR processing failed: {str(e)}"
            )
    
    async def process_pdf_with_llm(
        self, 
        file: UploadFile, 
        pdf_llm_request: PDFLLMOCRRequest
    ) -> PDFLLMOCRResponse:
        """
        Process uploaded PDF with LLM-enhanced OCR.
        
        Args:
            file: Uploaded PDF file
            pdf_llm_request: PDF LLM OCR processing parameters
            
        Returns:
            PDFLLMOCRResponse: Processing response with task ID
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting PDF LLM OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Create initial task response
            task_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.pdf_llm_tasks[task_id] = task_response
            
            # Start processing asynchronously
            asyncio.create_task(
                self._process_pdf_with_llm_async(task_id, pdf_path, pdf_llm_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start PDF LLM OCR task {task_id}: {str(e)}")
            
            error_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_llm_tasks[task_id] = error_response
            return error_response
    
    async def process_pdf_with_llm_sync(
        self, 
        file: UploadFile, 
        pdf_llm_request: PDFLLMOCRRequest
    ) -> PDFLLMOCRResult:
        """
        Process uploaded PDF with LLM-enhanced OCR synchronously.
        
        Args:
            file: Uploaded PDF file
            pdf_llm_request: PDF LLM OCR processing parameters
            
        Returns:
            PDFLLMOCRResult: Direct PDF LLM OCR processing result
            
        Raises:
            HTTPException: If processing fails
        """
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting synchronous PDF LLM OCR for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Process PDF with LLM
            result = await pdf_ocr_service.process_pdf_with_llm(pdf_path, pdf_llm_request)
            
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Synchronous PDF LLM OCR processing failed: {str(e)}")
            
            # Try to cleanup file if it exists
            try:
                if 'pdf_path' in locals():
                    await self._cleanup_file(pdf_path)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"PDF LLM OCR processing failed: {str(e)}"
            )
    
    async def get_pdf_task_status(self, task_id: str) -> PDFOCRResponse:
        """
        Get the status of a PDF OCR task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            PDFOCRResponse: Task status and result
            
        Raises:
            HTTPException: If task not found
        """
        if task_id not in self.pdf_tasks:
            logger.warning(f"PDF task {task_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"PDF task {task_id} not found"
            )
        
        return self.pdf_tasks[task_id]
    
    async def get_pdf_llm_task_status(self, task_id: str) -> PDFLLMOCRResponse:
        """
        Get the status of a PDF LLM OCR task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            PDFLLMOCRResponse: Task status and result
            
        Raises:
            HTTPException: If task not found
        """
        if task_id not in self.pdf_llm_tasks:
            logger.warning(f"PDF LLM task {task_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"PDF LLM task {task_id} not found"
            )
        
        return self.pdf_llm_tasks[task_id]
    
    async def _process_pdf_async(
        self, 
        task_id: str, 
        pdf_path: Path, 
        pdf_request: PDFOCRRequest
    ) -> None:
        """
        Process PDF asynchronously and update task status.
        
        Args:
            task_id: Unique task identifier
            pdf_path: Path to uploaded PDF
            pdf_request: PDF OCR processing parameters
        """
        try:
            logger.info(f"Processing PDF OCR task {task_id} asynchronously")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"PDF task {task_id} was cancelled before processing started")
                return
            
            # Process PDF
            result = await pdf_ocr_service.process_pdf(pdf_path, pdf_request)
            
            # Update task with result
            completed_at = datetime.utcnow()
            
            self.pdf_tasks[task_id] = PDFOCRResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "PDF OCR processing failed",
                created_at=self.pdf_tasks[task_id].created_at,
                completed_at=completed_at
            )
            
            logger.info(f"PDF OCR task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Async PDF OCR processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            self.pdf_tasks[task_id] = PDFOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.pdf_tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
        
        finally:
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)
    
    async def _process_pdf_with_llm_async(
        self, 
        task_id: str, 
        pdf_path: Path, 
        pdf_llm_request: PDFLLMOCRRequest
    ) -> None:
        """
        Process PDF with LLM asynchronously and update task status.
        
        Args:
            task_id: Unique task identifier
            pdf_path: Path to uploaded PDF
            pdf_llm_request: PDF LLM OCR processing parameters
        """
        try:
            logger.info(f"Processing PDF LLM OCR task {task_id} asynchronously")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"PDF LLM task {task_id} was cancelled before processing started")
                return
            
            # Process PDF with LLM
            result = await pdf_ocr_service.process_pdf_with_llm(pdf_path, pdf_llm_request)
            
            # Update task with result
            completed_at = datetime.utcnow()
            
            self.pdf_llm_tasks[task_id] = PDFLLMOCRResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "PDF LLM OCR processing failed",
                created_at=self.pdf_llm_tasks[task_id].created_at,
                completed_at=completed_at
            )
            
            logger.info(f"PDF LLM OCR task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Async PDF LLM OCR processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            error_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.pdf_llm_tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_llm_tasks[task_id] = error_response
            
        finally:
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)
    
    async def _validate_pdf_file(self, file: UploadFile) -> None:
        """
        Validate uploaded PDF file.
        
        Args:
            file: Uploaded PDF file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file size
        if file.size and file.size > self.settings.MAX_PDF_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"PDF file too large. Maximum size: {self.settings.MAX_PDF_SIZE} bytes"
            )
        
        # Check file extension
        if file.filename:
            extension = Path(file.filename).suffix.lower().lstrip('.')
            if extension not in self.settings.ALLOWED_PDF_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported PDF format: {extension}. "
                           f"Supported formats: {', '.join(self.settings.ALLOWED_PDF_EXTENSIONS)}"
                )
    
    async def list_tasks(self) -> Dict[str, str]:
        """
        List all tasks and their statuses.
        
        Returns:
            Dict[str, str]: Task IDs and their statuses
        """
        return {
            task_id: task.status 
            for task_id, task in self.tasks.items()
        }
    
    async def cleanup_completed_tasks(self) -> int:
        """
        Remove completed tasks from memory.
        
        Returns:
            int: Number of tasks cleaned up
        """
        completed_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.status in ["completed", "failed"]
        ]
        
        for task_id in completed_tasks:
            del self.tasks[task_id]
        
        logger.info(f"Cleaned up {len(completed_tasks)} completed tasks")
        return len(completed_tasks)

    # --- STREAMING METHODS ---

    async def process_pdf_with_streaming(
        self, 
        file: UploadFile, 
        pdf_request: PDFOCRRequest
    ) -> PDFOCRResponse:
        """
        Process uploaded PDF with streaming support.
        
        Args:
            file: Uploaded PDF file
            pdf_request: PDF OCR processing parameters
            
        Returns:
            PDFOCRResponse: Processing response with task ID for streaming
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting streaming PDF OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Create streaming queue for this task
            streaming_queue = asyncio.Queue()
            self.streaming_queues[task_id] = streaming_queue
            
            # Create initial task response
            task_response = PDFOCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.pdf_tasks[task_id] = task_response
            
            # Start processing asynchronously with streaming
            asyncio.create_task(
                self._process_pdf_with_streaming_async(task_id, pdf_path, pdf_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start streaming PDF OCR task {task_id}: {str(e)}")
            
            error_response = PDFOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_tasks[task_id] = error_response
            return error_response

    async def process_pdf_with_llm_streaming(
        self, 
        file: UploadFile, 
        pdf_llm_request: PDFLLMOCRRequest
    ) -> PDFLLMOCRResponse:
        """
        Process uploaded PDF with LLM enhancement and streaming support.
        
        Args:
            file: Uploaded PDF file
            pdf_llm_request: PDF LLM OCR processing parameters
            
        Returns:
            PDFLLMOCRResponse: Processing response with task ID for streaming
            
        Raises:
            HTTPException: If file validation fails
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        logger.info(f"Starting streaming PDF LLM OCR task {task_id} for file {file.filename}")
        
        try:
            # Validate PDF file
            await self._validate_pdf_file(file)
            
            # Save uploaded PDF
            pdf_path = await self._save_uploaded_file(file, task_id)
            
            # Create streaming queue for this task
            streaming_queue = asyncio.Queue()
            self.streaming_queues[task_id] = streaming_queue
            
            # Create initial task response
            task_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=created_at,
                completed_at=None
            )
            
            # Store task
            self.pdf_llm_tasks[task_id] = task_response
            
            # Start processing asynchronously with streaming
            asyncio.create_task(
                self._process_pdf_with_llm_streaming_async(task_id, pdf_path, pdf_llm_request)
            )
            
            return task_response
            
        except Exception as e:
            logger.error(f"Failed to start streaming PDF LLM OCR task {task_id}: {str(e)}")
            
            error_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_llm_tasks[task_id] = error_response
            return error_response

    async def stream_pdf_progress(self, task_id: str) -> AsyncGenerator[str, None]:
        """
        Stream PDF processing progress via Server-Sent Events.
        
        Args:
            task_id: Unique task identifier
            
        Yields:
            str: Server-Sent Events formatted progress updates
            
        Raises:
            HTTPException: If task not found
        """
        # Check if task exists
        if task_id not in self.streaming_queues:
            logger.warning(f"Streaming task {task_id} not found")
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return
        
        queue = self.streaming_queues[task_id]
        logger.info(f"Starting stream for task {task_id}")
        
        try:
            while True:
                try:
                    # Wait for update with timeout
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Check for sentinel (None = stream complete)
                    if update is None:
                        logger.info(f"Stream completed for task {task_id}")
                        break
                    
                    # Convert update to JSON and send as SSE
                    update_json = update.model_dump_json()
                    yield f"data: {update_json}\n\n"
                    
                    logger.debug(f"Sent streaming update for {task_id}: {update.status}")
                    
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'keepalive': True, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    logger.debug(f"Sent keepalive for task {task_id}")
                    
        except Exception as e:
            logger.error(f"Stream error for task {task_id}: {str(e)}")
            yield f"data: {json.dumps({'error': f'Stream error: {str(e)}'})}\n\n"
            
        finally:
            # Cleanup streaming queue
            if task_id in self.streaming_queues:
                del self.streaming_queues[task_id]
                logger.debug(f"Cleaned up streaming queue for task {task_id}")

    async def _process_pdf_with_streaming_async(
        self, 
        task_id: str, 
        pdf_path: Path, 
        pdf_request: PDFOCRRequest
    ) -> None:
        """
        Process PDF asynchronously with streaming updates.
        
        Args:
            task_id: Unique task identifier
            pdf_path: Path to the uploaded PDF file
            pdf_request: PDF processing parameters
        """
        try:
            logger.info(f"Starting async streaming PDF processing for task {task_id}")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"Streaming PDF task {task_id} was cancelled before processing started")
                return
            
            # Get streaming queue
            streaming_queue = self.streaming_queues.get(task_id)
            if not streaming_queue:
                logger.error(f"No streaming queue found for task {task_id}")
                return
            
            # Process PDF with streaming
            result = await pdf_ocr_service.process_pdf_with_streaming(
                pdf_path, pdf_request, task_id, streaming_queue
            )
            
            # Update task status
            completed_response = PDFOCRResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "Processing completed with errors",
                created_at=self.pdf_tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_tasks[task_id] = completed_response
            
            logger.info(f"Async streaming PDF processing completed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Async streaming PDF processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            error_response = PDFOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.pdf_tasks[task_id].created_at if task_id in self.pdf_tasks else datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.pdf_tasks[task_id] = error_response
            
        finally:
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)

    async def _process_pdf_with_llm_streaming_async(
        self, 
        task_id: str, 
        pdf_path: Path, 
        pdf_llm_request: PDFLLMOCRRequest
    ) -> None:
        """
        Process PDF with LLM asynchronously with streaming updates.
        
        Args:
            task_id: Unique task identifier
            pdf_path: Path to the uploaded PDF file
            pdf_llm_request: PDF LLM processing parameters
        """
        try:
            logger.info(f"Starting async streaming PDF LLM processing for task {task_id}")
            
            # Check for cancellation before starting
            if self.is_task_cancelled(task_id):
                logger.info(f"Streaming PDF LLM task {task_id} was cancelled before processing started")
                return
            
            # Get streaming queue
            streaming_queue = self.streaming_queues.get(task_id)
            if not streaming_queue:
                logger.error(f"No streaming queue found for task {task_id}")
                return
            
            # Process PDF with LLM and streaming
            result = await pdf_ocr_service.process_pdf_with_llm_streaming(
                pdf_path, pdf_llm_request, task_id, streaming_queue
            )
            
            # Update task status
            completed_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="completed" if result.success else "failed",
                result=result,
                error_message=None if result.success else "Processing completed with errors",
                created_at=self.pdf_llm_tasks[task_id].created_at,
                completed_at=datetime.utcnow()
            )
            
            self.pdf_llm_tasks[task_id] = completed_response
            
            logger.info(f"Async streaming PDF LLM processing completed for task {task_id}")
            
        except Exception as e:
            logger.error(f"Async streaming PDF LLM processing failed for task {task_id}: {str(e)}")
            
            # Update task with error
            error_response = PDFLLMOCRResponse(
                task_id=task_id,
                status="failed",
                result=None,
                error_message=str(e),
                created_at=self.pdf_llm_tasks[task_id].created_at if task_id in self.pdf_llm_tasks else datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.pdf_llm_tasks[task_id] = error_response
            
        finally:
            # Cleanup temporary file
            await self._cleanup_file(pdf_path)

    # --- Task Cancellation Methods ---

    def is_task_cancelled(self, task_id: str) -> bool:
        """
        Check if a task has been cancelled.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            bool: True if task is cancelled
        """
        return task_id in self.cancelled_tasks

    async def cancel_ocr_task(self, task_id: str, reason: str = "User requested cancellation") -> CancelTaskResponse:
        """
        Cancel an OCR task.
        
        Args:
            task_id: Unique task identifier
            reason: Cancellation reason
            
        Returns:
            CancelTaskResponse: Cancellation confirmation
            
        Raises:
            HTTPException: If task not found or already completed
        """
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"OCR task {task_id} not found")
        
        task = self.tasks[task_id]
        
        # Check if task is already completed/failed
        if task.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task {task_id}: already {task.status}"
            )
        
        # Mark task as cancelled
        self.cancelled_tasks.add(task_id)
        self.cancellation_reasons[task_id] = reason
        
        # Update task status
        cancelled_at = datetime.utcnow()
        task.status = TaskStatus.CANCELLED
        task.cancellation_reason = reason
        task.cancelled_at = cancelled_at
        task.completed_at = cancelled_at
        
        logger.info(f"OCR task {task_id} cancelled: {reason}")
        
        return CancelTaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message="OCR task successfully cancelled",
            cancelled_at=cancelled_at,
            cancellation_reason=reason
        )

    async def cancel_pdf_task(self, task_id: str, reason: str = "User requested cancellation") -> CancelTaskResponse:
        """
        Cancel a PDF OCR task.
        
        Args:
            task_id: Unique task identifier
            reason: Cancellation reason
            
        Returns:
            CancelTaskResponse: Cancellation confirmation
            
        Raises:
            HTTPException: If task not found or already completed
        """
        if task_id not in self.pdf_tasks:
            raise HTTPException(status_code=404, detail=f"PDF task {task_id} not found")
        
        task = self.pdf_tasks[task_id]
        
        # Check if task is already completed/failed
        if task.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task {task_id}: already {task.status}"
            )
        
        # Mark task as cancelled
        self.cancelled_tasks.add(task_id)
        self.cancellation_reasons[task_id] = reason
        
        # Update task status
        cancelled_at = datetime.utcnow()
        task.status = TaskStatus.CANCELLED
        task.cancellation_reason = reason
        task.cancelled_at = cancelled_at
        task.completed_at = cancelled_at
        
        # Send cancellation to streaming queue if exists
        if task_id in self.streaming_queues:
            try:
                await self.streaming_queues[task_id].put(None)  # Signal stream end
            except Exception as e:
                logger.warning(f"Failed to signal stream cancellation for {task_id}: {e}")
        
        logger.info(f"PDF task {task_id} cancelled: {reason}")
        
        return CancelTaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message="PDF task successfully cancelled",
            cancelled_at=cancelled_at,
            cancellation_reason=reason
        )

    async def cancel_pdf_llm_task(self, task_id: str, reason: str = "User requested cancellation") -> CancelTaskResponse:
        """
        Cancel a PDF LLM OCR task.
        
        Args:
            task_id: Unique task identifier
            reason: Cancellation reason
            
        Returns:
            CancelTaskResponse: Cancellation confirmation
            
        Raises:
            HTTPException: If task not found or already completed
        """
        if task_id not in self.pdf_llm_tasks:
            raise HTTPException(status_code=404, detail=f"PDF LLM task {task_id} not found")
        
        task = self.pdf_llm_tasks[task_id]
        
        # Check if task is already completed/failed
        if task.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task {task_id}: already {task.status}"
            )
        
        # Mark task as cancelled
        self.cancelled_tasks.add(task_id)
        self.cancellation_reasons[task_id] = reason
        
        # Update task status
        cancelled_at = datetime.utcnow()
        task.status = TaskStatus.CANCELLED
        task.cancellation_reason = reason
        task.cancelled_at = cancelled_at
        task.completed_at = cancelled_at
        
        # Send cancellation to streaming queue if exists
        if task_id in self.streaming_queues:
            try:
                await self.streaming_queues[task_id].put(None)  # Signal stream end
            except Exception as e:
                logger.warning(f"Failed to signal stream cancellation for {task_id}: {e}")
        
        logger.info(f"PDF LLM task {task_id} cancelled: {reason}")
        
        return CancelTaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message="PDF LLM task successfully cancelled",
            cancelled_at=cancelled_at,
            cancellation_reason=reason
        )

    async def cancel_llm_task(self, task_id: str, reason: str = "User requested cancellation") -> CancelTaskResponse:
        """
        Cancel an LLM OCR task.
        
        Args:
            task_id: Unique task identifier
            reason: Cancellation reason
            
        Returns:
            CancelTaskResponse: Cancellation confirmation
            
        Raises:
            HTTPException: If task not found or already completed
        """
        if task_id not in self.llm_tasks:
            raise HTTPException(status_code=404, detail=f"LLM task {task_id} not found")
        
        task = self.llm_tasks[task_id]
        
        # Check if task is already completed/failed
        if task.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task {task_id}: already {task.status}"
            )
        
        # Mark task as cancelled
        self.cancelled_tasks.add(task_id)
        self.cancellation_reasons[task_id] = reason
        
        # Update task status
        cancelled_at = datetime.utcnow()
        task.status = TaskStatus.CANCELLED
        task.cancellation_reason = reason
        task.cancelled_at = cancelled_at
        task.completed_at = cancelled_at
        
        logger.info(f"LLM task {task_id} cancelled: {reason}")
        
        return CancelTaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message="LLM task successfully cancelled",
            cancelled_at=cancelled_at,
            cancellation_reason=reason
        )

    async def cancel_streaming_task(self, task_id: str, reason: str = "User requested cancellation") -> CancelTaskResponse:
        """
        Cancel a streaming task (PDF or PDF LLM).
        
        Args:
            task_id: Unique task identifier
            reason: Cancellation reason
            
        Returns:
            CancelTaskResponse: Cancellation confirmation
        """
        # Try to find task in PDF tasks first, then PDF LLM tasks
        if task_id in self.pdf_tasks:
            return await self.cancel_pdf_task(task_id, reason)
        elif task_id in self.pdf_llm_tasks:
            return await self.cancel_pdf_llm_task(task_id, reason)
        else:
            raise HTTPException(status_code=404, detail=f"Streaming task {task_id} not found")

# Global OCR controller instance
ocr_controller = OCRController() 