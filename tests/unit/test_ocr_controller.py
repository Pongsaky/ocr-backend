"""
Unit tests for the OCR controller.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from datetime import datetime

from fastapi import UploadFile, HTTPException

from app.controllers.ocr_controller import OCRController
from app.models.ocr_models import OCRRequest, OCRResponse, OCRResult


class TestOCRController:
    """Test cases for OCRController."""
    
    @pytest.fixture
    def ocr_controller(self):
        """Create an instance of OCRController for testing."""
        return OCRController()
    
    @pytest.fixture
    def mock_upload_file(self, sample_image_path):
        """Create a mock UploadFile for testing."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test_image.jpg"
        mock_file.size = 1000
        mock_file.read = AsyncMock(return_value=b"fake_image_data")
        return mock_file
    
    @pytest.mark.asyncio
    async def test_process_image_success(self, ocr_controller, mock_upload_file, sample_ocr_request):
        """Test successful image processing."""
        with patch.object(ocr_controller, '_validate_upload_file', new_callable=AsyncMock) as mock_validate, \
             patch.object(ocr_controller, '_save_uploaded_file', new_callable=AsyncMock) as mock_save, \
             patch('asyncio.create_task') as mock_create_task:
            
            mock_save.return_value = Path("/tmp/test_image.jpg")
            
            response = await ocr_controller.process_image(mock_upload_file, sample_ocr_request)
            
            assert isinstance(response, OCRResponse)
            assert response.status == "processing"
            assert response.task_id is not None
            assert response.created_at is not None
            
            # Verify methods were called
            mock_validate.assert_called_once_with(mock_upload_file)
            mock_save.assert_called_once()
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_validation_error(self, ocr_controller, mock_upload_file, sample_ocr_request):
        """Test image processing with validation error."""
        with patch.object(ocr_controller, '_validate_upload_file', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid file")
            
            response = await ocr_controller.process_image(mock_upload_file, sample_ocr_request)
            
            assert response.status == "failed"
            assert response.error_message is not None
    
    @pytest.mark.asyncio
    async def test_get_task_status_success(self, ocr_controller, sample_ocr_result):
        """Test successful task status retrieval."""
        # Add a task to the controller
        task_id = "test-task-id"
        task_response = OCRResponse(
            task_id=task_id,
            status="completed",
            result=sample_ocr_result,
            error_message=None,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        ocr_controller.tasks[task_id] = task_response
        
        response = await ocr_controller.get_task_status(task_id)
        
        assert response.task_id == task_id
        assert response.status == "completed"
        assert response.result == sample_ocr_result
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, ocr_controller):
        """Test task status retrieval for non-existent task."""
        with pytest.raises(HTTPException) as exc_info:
            await ocr_controller.get_task_status("non-existent-task")
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_process_image_sync_success(self, ocr_controller, mock_upload_file, sample_ocr_request, sample_ocr_result):
        """Test successful synchronous image processing."""
        with patch.object(ocr_controller, '_validate_upload_file', new_callable=AsyncMock) as mock_validate, \
             patch.object(ocr_controller, '_save_uploaded_file', new_callable=AsyncMock) as mock_save, \
             patch.object(ocr_controller, '_cleanup_file', new_callable=AsyncMock) as mock_cleanup, \
             patch('app.services.external_ocr_service.external_ocr_service.process_image', new_callable=AsyncMock) as mock_external, \
             patch('app.services.ocr_llm_service.ocr_llm_service.process_image_with_llm', new_callable=AsyncMock) as mock_llm:
            
            from app.services.external_ocr_service import ImageProcessingResult
            from app.models.ocr_models import OCRLLMResult
            
            mock_save.return_value = Path("/tmp/test_image.jpg")
            
            # Mock external service result (preprocessing)
            mock_external_result = ImageProcessingResult(
                success=True,
                processed_image_base64="base64_data",
                processing_time=1.0
            )
            mock_external.return_value = mock_external_result
            
            # Mock LLM service result
            mock_llm_result = OCRLLMResult(
                success=True,
                extracted_text="Test text",
                processing_time=2.0,
                threshold_used=128,
                contrast_level_used=1.0,
                original_ocr_text="",
                image_processing_time=1.0,
                llm_processing_time=1.0,
                model_used="gpt-4",
                prompt_used="Extract text"
            )
            mock_llm.return_value = mock_llm_result
            
            result = await ocr_controller.process_image_sync(mock_upload_file, sample_ocr_request)
            
            assert result.success is True
            assert result.extracted_text == "Test text"
            mock_validate.assert_called_once()
            mock_save.assert_called_once()
            mock_external.assert_called_once()
            mock_llm.assert_called_once()
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_sync_failure(self, ocr_controller, mock_upload_file, sample_ocr_request):
        """Test synchronous image processing failure."""
        with patch.object(ocr_controller, '_validate_upload_file', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("Processing error")
            
            with pytest.raises(HTTPException) as exc_info:
                await ocr_controller.process_image_sync(mock_upload_file, sample_ocr_request)
            
            assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_success(self, ocr_controller, mock_upload_file):
        """Test successful file validation."""
        # Should not raise any exception
        await ocr_controller._validate_upload_file(mock_upload_file)
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_too_large(self, ocr_controller, mock_upload_file):
        """Test file validation with file too large."""
        mock_upload_file.size = 20 * 1024 * 1024  # 20MB
        
        with pytest.raises(HTTPException) as exc_info:
            await ocr_controller._validate_upload_file(mock_upload_file)
        
        assert exc_info.value.status_code == 413
    
    @pytest.mark.asyncio
    async def test_validate_upload_file_unsupported_format(self, ocr_controller, mock_upload_file):
        """Test file validation with unsupported format."""
        mock_upload_file.filename = "test_file.txt"
        
        with pytest.raises(HTTPException) as exc_info:
            await ocr_controller._validate_upload_file(mock_upload_file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file(self, ocr_controller, mock_upload_file):
        """Test saving uploaded file."""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('builtins.open', create=True) as mock_open:
            
            file_path = await ocr_controller._save_uploaded_file(mock_upload_file, "test-task-id")
            
            assert isinstance(file_path, Path)
            assert "test-task-id" in str(file_path)
            mock_mkdir.assert_called_once()
            mock_open.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_file(self, ocr_controller, sample_image_path):
        """Test file cleanup."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            await ocr_controller._cleanup_file(sample_image_path)
            
            mock_unlink.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_file_not_exists(self, ocr_controller):
        """Test file cleanup when file doesn't exist."""
        non_existent_path = Path("/non/existent/file.jpg")
        
        # Should not raise any exception
        await ocr_controller._cleanup_file(non_existent_path)
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, ocr_controller):
        """Test listing all tasks."""
        # Add some tasks
        ocr_controller.tasks["task1"] = OCRResponse(
            task_id="task1",
            status="completed",
            result=None,
            error_message=None,
            created_at=datetime.utcnow()
        )
        ocr_controller.tasks["task2"] = OCRResponse(
            task_id="task2",
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.utcnow()
        )
        
        tasks = await ocr_controller.list_tasks()
        
        assert len(tasks) == 2
        assert tasks["task1"] == "completed"
        assert tasks["task2"] == "processing"
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self, ocr_controller):
        """Test cleanup of completed tasks."""
        # Add some tasks
        ocr_controller.tasks["completed1"] = OCRResponse(
            task_id="completed1",
            status="completed",
            result=None,
            error_message=None,
            created_at=datetime.utcnow()
        )
        ocr_controller.tasks["failed1"] = OCRResponse(
            task_id="failed1",
            status="failed",
            result=None,
            error_message="Error",
            created_at=datetime.utcnow()
        )
        ocr_controller.tasks["processing1"] = OCRResponse(
            task_id="processing1",
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.utcnow()
        )
        
        count = await ocr_controller.cleanup_completed_tasks()
        
        assert count == 2  # completed1 and failed1 should be removed
        assert len(ocr_controller.tasks) == 1
        assert "processing1" in ocr_controller.tasks
    
    def test_controller_initialization(self, ocr_controller):
        """Test controller initialization."""
        assert ocr_controller.settings is not None
        assert isinstance(ocr_controller.tasks, dict)
        assert ocr_controller.executor is not None 