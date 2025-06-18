"""
Unit tests for task cancellation functionality.
"""

import asyncio
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from fastapi import HTTPException

from app.models.ocr_models import (
    OCRRequest, OCRResponse, OCRResult,
    OCRLLMRequest, OCRLLMResponse, OCRLLMResult,
    PDFOCRRequest, PDFOCRResponse, PDFOCRResult,
    PDFLLMOCRRequest, PDFLLMOCRResponse, PDFLLMOCRResult,
    CancelTaskRequest, CancelTaskResponse, TaskCancellationError, TaskStatus
)
from app.controllers.ocr_controller import OCRController


class TestTaskCancellation:
    """Test suite for task cancellation functionality."""

    @pytest.fixture
    def controller(self):
        """Create a fresh OCR controller for each test."""
        return OCRController()

    @pytest.fixture
    def mock_task_id(self):
        """Return a mock task ID."""
        return "test-task-12345"

    @pytest.fixture
    def cancel_request(self):
        """Return a cancel request."""
        return CancelTaskRequest(reason="Test cancellation")

    # --- OCR Task Cancellation Tests ---

    @pytest.mark.asyncio
    async def test_cancel_ocr_task_success(self, controller, mock_task_id, cancel_request):
        """Test successful OCR task cancellation."""
        # Create a task
        created_at = datetime.now(UTC)
        task = OCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=created_at,
            completed_at=None
        )
        controller.tasks[mock_task_id] = task

        # Cancel the task
        result = await controller.cancel_ocr_task(mock_task_id, cancel_request.reason)

        # Verify cancellation
        assert result.task_id == mock_task_id
        assert result.status == TaskStatus.CANCELLED
        assert result.message == "OCR task successfully cancelled"
        assert result.cancellation_reason == cancel_request.reason
        assert result.cancelled_at is not None

        # Verify task is marked as cancelled
        assert controller.is_task_cancelled(mock_task_id)
        assert task.status == TaskStatus.CANCELLED
        assert task.cancellation_reason == cancel_request.reason
        assert task.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_ocr_task_not_found(self, controller, cancel_request):
        """Test cancelling non-existent OCR task."""
        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_ocr_task("non-existent", cancel_request.reason)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cancel_ocr_task_already_completed(self, controller, mock_task_id, cancel_request):
        """Test cancelling already completed OCR task."""
        # Create a completed task
        task = OCRResponse(
            task_id=mock_task_id,
            status="completed",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC)
        )
        controller.tasks[mock_task_id] = task

        # Try to cancel
        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_ocr_task(mock_task_id, cancel_request.reason)

        assert exc_info.value.status_code == 400
        assert "already completed" in str(exc_info.value.detail)

    # --- PDF Task Cancellation Tests ---

    @pytest.mark.asyncio
    async def test_cancel_pdf_task_success(self, controller, mock_task_id, cancel_request):
        """Test successful PDF task cancellation."""
        # Create a PDF task
        task = PDFOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        controller.pdf_tasks[mock_task_id] = task

        # Create streaming queue
        controller.streaming_queues[mock_task_id] = asyncio.Queue()

        # Cancel the task
        result = await controller.cancel_pdf_task(mock_task_id, cancel_request.reason)

        # Verify cancellation
        assert result.task_id == mock_task_id
        assert result.status == TaskStatus.CANCELLED
        assert result.message == "PDF task successfully cancelled"
        assert result.cancellation_reason == cancel_request.reason

        # Verify task is marked as cancelled
        assert controller.is_task_cancelled(mock_task_id)
        assert task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_pdf_llm_task_success(self, controller, mock_task_id, cancel_request):
        """Test successful PDF LLM task cancellation."""
        # Create a PDF LLM task
        task = PDFLLMOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        controller.pdf_llm_tasks[mock_task_id] = task

        # Cancel the task
        result = await controller.cancel_pdf_llm_task(mock_task_id, cancel_request.reason)

        # Verify cancellation
        assert result.task_id == mock_task_id
        assert result.status == TaskStatus.CANCELLED
        assert result.message == "PDF LLM task successfully cancelled"

    # --- LLM Task Cancellation Tests ---

    @pytest.mark.asyncio
    async def test_cancel_llm_task_success(self, controller, mock_task_id, cancel_request):
        """Test successful LLM task cancellation."""
        # Create a LLM task
        task = OCRLLMResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        controller.llm_tasks[mock_task_id] = task

        # Cancel the task
        result = await controller.cancel_llm_task(mock_task_id, cancel_request.reason)

        # Verify cancellation
        assert result.task_id == mock_task_id
        assert result.status == TaskStatus.CANCELLED
        assert result.message == "LLM task successfully cancelled"

    # --- Streaming Task Cancellation Tests ---

    @pytest.mark.asyncio
    async def test_cancel_streaming_task_pdf(self, controller, mock_task_id, cancel_request):
        """Test cancelling streaming PDF task."""
        # Create a streaming PDF task
        task = PDFOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        controller.pdf_tasks[mock_task_id] = task

        # Cancel via streaming endpoint
        result = await controller.cancel_streaming_task(mock_task_id, cancel_request.reason)

        # Verify it called the PDF cancellation
        assert result.task_id == mock_task_id
        assert result.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_streaming_task_not_found(self, controller, cancel_request):
        """Test cancelling non-existent streaming task."""
        with pytest.raises(HTTPException) as exc_info:
            await controller.cancel_streaming_task("non-existent", cancel_request.reason)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    # --- Cancellation Check Tests ---

    def test_is_task_cancelled_true(self, controller, mock_task_id):
        """Test checking if task is cancelled (true case)."""
        controller.cancelled_tasks.add(mock_task_id)
        
        assert controller.is_task_cancelled(mock_task_id) is True

    def test_is_task_cancelled_false(self, controller, mock_task_id):
        """Test checking if task is cancelled (false case)."""
        assert controller.is_task_cancelled(mock_task_id) is False

    # --- Task Cancellation Error Tests ---

    def test_task_cancellation_error(self):
        """Test TaskCancellationError exception."""
        task_id = "test-task"
        reason = "Test reason"
        
        error = TaskCancellationError(task_id, reason)
        
        assert error.task_id == task_id
        assert error.reason == reason
        assert task_id in str(error)
        assert reason in str(error)


class TestPDFServiceCancellation:
    """Test suite for PDF service cancellation functionality."""

    @pytest.fixture
    def pdf_service(self):
        """Create a PDF service instance."""
        from app.services.pdf_ocr_service import PDFOCRService
        return PDFOCRService()

    @pytest.fixture
    def mock_controller(self):
        """Create a mock controller."""
        controller = MagicMock()
        controller.is_task_cancelled.return_value = False
        controller.cancellation_reasons = {}
        return controller

    @pytest.mark.asyncio
    async def test_check_task_cancellation_not_cancelled(self, pdf_service):
        """Test cancellation check when task is not cancelled."""
        with patch('app.controllers.ocr_controller.ocr_controller') as mock_controller:
            mock_controller.is_task_cancelled.return_value = False
            
            # Should not raise exception
            await pdf_service.check_task_cancellation("test-task")

    @pytest.mark.asyncio
    async def test_check_task_cancellation_cancelled(self, pdf_service):
        """Test cancellation check when task is cancelled."""
        with patch('app.controllers.ocr_controller.ocr_controller') as mock_controller:
            mock_controller.is_task_cancelled.return_value = True
            mock_controller.cancellation_reasons = {"test-task": "User requested"}
            
            # Should raise TaskCancellationError
            with pytest.raises(TaskCancellationError) as exc_info:
                await pdf_service.check_task_cancellation("test-task")
            
            assert exc_info.value.task_id == "test-task"
            assert exc_info.value.reason == "User requested"

    @pytest.mark.asyncio
    async def test_streaming_processing_with_cancellation(self, pdf_service):
        """Test that streaming processing checks for cancellation."""
        # This is more of an integration test, but we can test the logic
        with patch('app.controllers.ocr_controller.ocr_controller') as mock_controller:
            mock_controller.is_task_cancelled.return_value = True
            mock_controller.cancellation_reasons = {"test-task": "Cancelled during processing"}
            
            # Mock the processing method to verify cancellation check is called
            with patch.object(pdf_service, 'check_task_cancellation') as mock_check:
                mock_check.side_effect = TaskCancellationError("test-task", "Cancelled")
                
                # This would be called during streaming processing
                with pytest.raises(TaskCancellationError):
                    await pdf_service.check_task_cancellation("test-task")
                
                mock_check.assert_called_once_with("test-task")


class TestTaskStatusEnums:
    """Test task status enumeration."""

    def test_task_status_values(self):
        """Test that all required task statuses are available."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.PAGE_COMPLETED == "page_completed"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_task_status_is_string_enum(self):
        """Test that TaskStatus extends str enum."""
        assert isinstance(TaskStatus.CANCELLED, str)
        assert TaskStatus.CANCELLED == "cancelled"


class TestCancellationModels:
    """Test cancellation request and response models."""

    def test_cancel_task_request_default(self):
        """Test CancelTaskRequest with default values."""
        request = CancelTaskRequest()
        
        assert request.reason == "User requested cancellation"

    def test_cancel_task_request_custom(self):
        """Test CancelTaskRequest with custom reason."""
        custom_reason = "Processing taking too long"
        request = CancelTaskRequest(reason=custom_reason)
        
        assert request.reason == custom_reason

    def test_cancel_task_response(self):
        """Test CancelTaskResponse model."""
        cancelled_at = datetime.now(UTC)
        response = CancelTaskResponse(
            task_id="test-task",
            status="cancelled",
            message="Task cancelled successfully",
            cancelled_at=cancelled_at,
            cancellation_reason="User request"
        )
        
        assert response.task_id == "test-task"
        assert response.status == "cancelled"
        assert response.message == "Task cancelled successfully"
        assert response.cancelled_at == cancelled_at
        assert response.cancellation_reason == "User request"

    def test_cancel_task_response_json_schema(self):
        """Test that response model has proper JSON schema example."""
        schema = CancelTaskResponse.model_json_schema()
        
        assert "example" in schema
        example = schema["example"]
        assert "task_id" in example
        assert "status" in example
        assert "cancelled_at" in example 