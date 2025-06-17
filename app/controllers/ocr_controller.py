"""
OCR controller for handling OCR business logic.
"""

import uuid
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, UploadFile

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, OCRResponse, OCRResult,
    OCRLLMRequest, OCRLLMResponse, OCRLLMResult
)
from app.services.external_ocr_service import external_ocr_service
from app.services.ocr_llm_service import ocr_llm_service
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class OCRController:
    """Controller for OCR operations."""
    
    def __init__(self):
        """Initialize OCR controller."""
        self.settings = settings
        self.tasks: Dict[str, OCRResponse] = {}
        self.executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_TASKS
        )
        logger.info("OCR Controller initialized")
    
    async def process_image(
        self, 
        file: UploadFile, 
        ocr_request: OCRRequest
    ) -> OCRResponse:
        """
        Process uploaded image for OCR.
        
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
        Process uploaded image synchronously.
        
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
            
            # Process image
            result = await external_ocr_service.process_image(image_path, ocr_request)
            
            # Cleanup temporary file
            await self._cleanup_file(image_path)
            
            return result
            
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
            
            # Process image
            result = await external_ocr_service.process_image(image_path, ocr_request)
            
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
        Process uploaded image for LLM-enhanced OCR.
        
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
            
            # Store task (we'll need a new dictionary for LLM tasks)
            if not hasattr(self, 'llm_tasks'):
                self.llm_tasks: Dict[str, OCRLLMResponse] = {}
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
            
            if not hasattr(self, 'llm_tasks'):
                self.llm_tasks: Dict[str, OCRLLMResponse] = {}
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
        if not hasattr(self, 'llm_tasks') or task_id not in self.llm_tasks:
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
        Process uploaded image with LLM synchronously.
        
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
            
            # Convert OCRLLMRequest to OCRRequest for initial processing
            ocr_request = OCRRequest(
                threshold=ocr_llm_request.threshold,
                contrast_level=ocr_llm_request.contrast_level
            )
            
            # First, get processed image from external OCR
            logger.info("Step 1: Processing image with external OCR service")
            processed_result = await self._get_processed_image_and_text(image_path, ocr_request)
            
            # Then, enhance with LLM
            logger.info("Step 2: Enhancing with LLM")
            result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result["image"],
                original_ocr_text=processed_result["text"],
                ocr_request=ocr_llm_request,
                ocr_processing_time=processed_result["processing_time"]
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
            
            # Convert OCRLLMRequest to OCRRequest for initial processing
            ocr_request = OCRRequest(
                threshold=ocr_llm_request.threshold,
                contrast_level=ocr_llm_request.contrast_level
            )
            
            # First, get processed image from external OCR
            processed_result = await self._get_processed_image_and_text(image_path, ocr_request)
            
            # Then, enhance with LLM
            result = await ocr_llm_service.process_image_with_llm(
                processed_image_base64=processed_result["image"],
                original_ocr_text=processed_result["text"],
                ocr_request=ocr_llm_request,
                ocr_processing_time=processed_result["processing_time"]
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
    
    async def _get_processed_image_and_text(self, image_path: Path, ocr_request: OCRRequest) -> dict:
        """
        Get processed image and text from external OCR service.
        
        Args:
            image_path: Path to image file
            ocr_request: OCR processing parameters
            
        Returns:
            dict: Contains processed image base64, extracted text, and processing time
        """
        import httpx
        import base64
        
        # Convert image to base64
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Call external OCR API directly to get both processed image and text
        url = f"{self.settings.EXTERNAL_OCR_BASE_URL}{self.settings.EXTERNAL_OCR_ENDPOINT}"
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self.settings.EXTERNAL_OCR_TIMEOUT) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "accept": "application/json"
                },
                json={
                    "image": image_base64,
                    "threshold": ocr_request.threshold,
                    "contrast_level": ocr_request.contrast_level
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            processing_time = time.time() - start_time
            
            return {
                "image": data.get("image", image_base64),  # Processed image
                "text": data.get("text_response", ""),      # Extracted text
                "processing_time": processing_time
            }
    
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


# Global OCR controller instance
ocr_controller = OCRController() 