"""
Unit tests for unified router - testing all unified API endpoints.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from starlette.requests import Request as StarletteRequest

from app.routers.unified_router import (
    process_any_file_stream, stream_universal_progress,
    cancel_universal_task, get_universal_task_status
)
from app.models.unified_models import (
    FileType, ProcessingMode, UnifiedOCRRequest, UnifiedOCRResponse,
    UnifiedTaskCancellationRequest, UnifiedTaskCancellationResponse,
    FileMetadata
)


@pytest.mark.asyncio
async def test_process_any_file_stream_success():
    """Test successful unified file processing."""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.size = 1000000
    
    mock_response = UnifiedOCRResponse(
        task_id="test-task-123",
        file_type=FileType.PDF,
        processing_mode=ProcessingMode.BASIC,
        status="processing",
        created_at=datetime.now(timezone.utc),
        estimated_duration=10.0
    )
    
    with patch('app.routers.unified_router.unified_processor') as mock_processor, \
         patch('uuid.uuid4') as mock_uuid:
        
        mock_uuid.return_value = "test-task-123"
        mock_processor.process_file_stream = AsyncMock(return_value=mock_response)
        
        # Create proper Request mock for rate limiter
        mock_request = Mock(spec=StarletteRequest)
        mock_request.client = Mock(host="127.0.0.1")
        
        response = await process_any_file_stream(
            file=mock_file, 
            request_data=None,  # Explicitly set request_data
            request=mock_request
        )
        
        assert response.task_id == "test-task-123"
        assert response.file_type == FileType.PDF
        assert response.status == "processing"


@pytest.mark.asyncio
async def test_stream_universal_progress_success():
    """Test successful streaming response."""
    task_id = "stream-test-task"
    
    async def mock_generator():
        yield "data: {\"status\": \"processing\"}\n\n"
        yield "data: {\"status\": \"completed\"}\n\n"
    
    with patch('app.routers.unified_router.unified_processor') as mock_processor:
        mock_processor.get_stream_generator = Mock(return_value=mock_generator())
        
        mock_request = Mock(spec=StarletteRequest)
        response = await stream_universal_progress(task_id, mock_request)
        
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        assert response.headers.get("Cache-Control") == "no-cache"


@pytest.mark.asyncio
async def test_process_any_file_stream_with_request_data():
    """Test processing with request data."""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.size = 500000
    
    request_data = '{"mode": "llm_enhanced", "threshold": 600}'
    
    mock_response = UnifiedOCRResponse(
        task_id="custom-test",
        file_type=FileType.IMAGE,
        processing_mode=ProcessingMode.LLM_ENHANCED,
        status="processing",
        created_at=datetime.now(timezone.utc)
    )
    
    with patch('app.routers.unified_router.unified_processor') as mock_processor, \
         patch('uuid.uuid4') as mock_uuid:
        
        mock_uuid.return_value = "custom-test"
        mock_processor.process_file_stream = AsyncMock(return_value=mock_response)
        
        mock_request = Mock(spec=StarletteRequest)
        response = await process_any_file_stream(
            file=mock_file,
            request_data=request_data,
            request=mock_request
        )
        
        # Verify processor was called
        call_args = mock_processor.process_file_stream.call_args
        request = call_args.kwargs['request']
        assert request.mode == ProcessingMode.LLM_ENHANCED
        assert request.threshold == 600


@pytest.mark.asyncio
async def test_processing_error_handling():
    """Test error handling in processing."""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    
    with patch('app.routers.unified_router.unified_processor') as mock_processor, \
         patch('uuid.uuid4') as mock_uuid:
        
        mock_uuid.return_value = "error-task"
        mock_processor.process_file_stream = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        
        mock_request = Mock(spec=StarletteRequest)
        with pytest.raises(HTTPException) as exc_info:
            await process_any_file_stream(file=mock_file, request=mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Failed to start processing" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_streaming_not_found():
    """Test streaming when task not found."""
    task_id = "non-existent"
    
    with patch('app.routers.unified_router.unified_processor') as mock_processor:
        mock_processor.get_stream_generator = Mock(
            side_effect=HTTPException(status_code=404, detail="Task not found")
        )
        
        mock_request = Mock(spec=StarletteRequest)
        with pytest.raises(HTTPException) as exc_info:
            await stream_universal_progress(task_id, mock_request)
        
        assert exc_info.value.status_code == 500


class TestTaskCancellationEndpoint:
    """Test the task cancellation endpoint."""
    
    @pytest.mark.asyncio
    async def test_cancel_unified_task_success(self):
        """Test successful task cancellation."""
        task_id = "cancel-test-task"
        
        # Create cancellation request
        cancel_request = UnifiedTaskCancellationRequest(
            reason="User requested cancellation"
        )
        
        # Mock cancellation response
        mock_response = UnifiedTaskCancellationResponse(
            task_id=task_id,
            status="cancelled",
            message="Task cancelled successfully",
            cancelled_at=datetime.now(timezone.utc),
            cancellation_reason="User requested cancellation"
        )
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            # Mock the attributes that the router checks directly
            mock_processor.streaming_queues = {task_id: "mock_queue"}
            mock_processor.task_metadata = {
                task_id: {
                    "file_type": "pdf",
                    "request": Mock(mode="basic"),
                    "start_time": 1234567890
                }
            }
            mock_processor._send_progress_update = AsyncMock()
            mock_processor._cleanup_task = AsyncMock()
            
            # Execute endpoint with proper request mock
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            response = await cancel_universal_task(task_id, cancel_request, mock_request)
            
            # Verify response
            assert response.task_id == task_id
            assert response.status == "cancelled"
            assert response.message == "Task cancelled successfully"
            assert response.cancellation_reason == "User requested cancellation"
            
            # Verify methods were called correctly
            mock_processor._send_progress_update.assert_called_once()
            mock_processor._cleanup_task.assert_called_once_with(task_id)
    
    @pytest.mark.asyncio
    async def test_cancel_unified_task_not_found(self):
        """Test cancellation when task is not found."""
        task_id = "non-existent-task"
        cancel_request = UnifiedTaskCancellationRequest()
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            mock_processor.cancel_task = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="Task not found")
            )
            mock_processor.get_task_status = AsyncMock()
            
            # Should propagate HTTPException
            with pytest.raises(HTTPException) as exc_info:
                mock_request = Mock(spec=StarletteRequest)
                mock_request.client = Mock(host="127.0.0.1")
                await cancel_universal_task(task_id, cancel_request, mock_request)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Task non-existent-task not found or already completed"


class TestTaskStatusEndpoint:
    """Test the task status endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_unified_task_status_success(self):
        """Test successful task status retrieval."""
        task_id = "status-test-task"
        
        # Mock status response
        mock_response = UnifiedOCRResponse(
            task_id=task_id,
            file_type=FileType.PDF,
            processing_mode=ProcessingMode.BASIC,
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            result={"extracted_text": "Sample text", "pages_processed": 3}
        )
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            # Mock the attributes that the router checks directly
            # Create proper FileMetadata mock
            from app.models.unified_models import FileMetadata
            file_metadata = FileMetadata(
                original_filename="status-test.pdf",
                file_size_bytes=1024000,
                mime_type="application/pdf",
                detected_file_type=FileType.PDF,
                pdf_page_count=3
            )
            
            mock_processor.task_metadata = {
                task_id: {
                    "file_type": FileType.PDF,
                    "request": Mock(mode=ProcessingMode.BASIC),
                    "start_time": 1234567890,
                    "metadata": file_metadata
                }
            }
            mock_processor.streaming_queues = {}  # Empty = completed
            
            # Execute endpoint
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            response = await get_universal_task_status(task_id, mock_request)
            
            # Verify response
            assert response.task_id == task_id
            assert response.file_type == FileType.PDF
            assert response.status == "completed"
            assert response.processing_mode == ProcessingMode.BASIC
            
            # Verify task metadata was checked
            assert task_id in mock_processor.task_metadata
    
    @pytest.mark.asyncio
    async def test_get_unified_task_status_not_found(self):
        """Test status retrieval when task is not found."""
        task_id = "non-existent-task"
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            mock_processor.get_task_status = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="Task not found")
            )
            mock_processor.cancel_task = AsyncMock()
            
            # Should propagate HTTPException
            with pytest.raises(HTTPException) as exc_info:
                mock_request = Mock(spec=StarletteRequest)
                mock_request.client = Mock(host="127.0.0.1")
                await get_universal_task_status(task_id, mock_request)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Task non-existent-task not found"


class TestParameterValidation:
    """Test parameter validation and processing in router."""
    
    @pytest.mark.asyncio
    async def test_process_mode_validation(self):
        """Test processing mode validation and conversion."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 500000
        
        mock_response = UnifiedOCRResponse(
            task_id="mode-test",
            file_type=FileType.IMAGE,
            processing_mode=ProcessingMode.LLM_ENHANCED,
            status="processing",
            created_at=datetime.now(timezone.utc)
        )
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "mode-test"
            mock_processor.process_file_stream = AsyncMock(return_value=mock_response)
            
            # Test valid mode string conversion
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            response = await process_any_file_stream(
                file=mock_file,
                request_data='{"mode": "llm_enhanced"}',
                request=mock_request
            )
            
            # Verify mode was converted correctly
            call_args = mock_processor.process_file_stream.call_args
            request = call_args.kwargs['request']
            assert request.mode == ProcessingMode.LLM_ENHANCED
    
    @pytest.mark.asyncio
    async def test_invalid_processing_mode(self):
        """Test invalid processing mode handling."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 500000
        
        # Should raise HTTPException for invalid mode
        with pytest.raises(HTTPException) as exc_info:
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            await process_any_file_stream(
                file=mock_file,
                request_data='{"mode": "invalid_mode"}',
                request=mock_request
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to start processing" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_request_building_from_form_data(self):
        """Test unified request building from form data."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1000000
        
        mock_response = UnifiedOCRResponse(
            task_id="form-build-test",
            file_type=FileType.PDF,
            processing_mode=ProcessingMode.LLM_ENHANCED,
            status="processing",
            created_at=datetime.now(timezone.utc)
        )
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "form-build-test"
            mock_processor.process_file_stream = AsyncMock(return_value=mock_response)
            
            # Test with all parameters
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            response = await process_any_file_stream(
                file=mock_file,
                request_data='{"threshold": 550, "contrast_level": 1.4, "dpi": 350, "mode": "llm_enhanced", "prompt": "Extract everything", "model": "gpt-4-vision-preview"}',
                request=mock_request
            )
            
            # Verify request was built correctly
            call_args = mock_processor.process_file_stream.call_args
            request = call_args.kwargs['request']
            
            assert request.threshold == 550
            assert request.contrast_level == 1.4
            assert request.dpi == 350
            assert request.mode == ProcessingMode.LLM_ENHANCED
            assert request.prompt == "Extract everything"
            assert request.model == "gpt-4-vision-preview"


class TestRouterIntegration:
    """Test integration scenarios for the unified router."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_simulation(self):
        """Test a complete workflow through the router endpoints."""
        # 1. Start processing
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "workflow.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 2000000
        
        init_response = UnifiedOCRResponse(
            task_id="workflow-task",
            file_type=FileType.PDF,
            processing_mode=ProcessingMode.BASIC,
            status="processing",
            created_at=datetime.now(timezone.utc),
            estimated_duration=10.0
        )
        
        # 2. Mock status response
        status_response = UnifiedOCRResponse(
            task_id="workflow-task",
            file_type=FileType.PDF,
            processing_mode=ProcessingMode.BASIC,
            status="completed",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            result={"extracted_text": "Workflow complete", "pages_processed": 1}
        )
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value.hex = "workflow-task"
            mock_processor.process_file_stream = AsyncMock(return_value=init_response)
            
            # Mock the task metadata for status endpoint
            from app.models.unified_models import FileMetadata
            file_metadata = FileMetadata(
                original_filename="workflow.pdf",
                file_size_bytes=2000000,
                mime_type="application/pdf",
                detected_file_type=FileType.PDF,
                pdf_page_count=1
            )
            
            mock_processor.task_metadata = {
                "workflow-task": {
                    "file_type": FileType.PDF,
                    "request": Mock(mode=ProcessingMode.BASIC),
                    "start_time": 1234567890,
                    "metadata": file_metadata
                }
            }
            mock_processor.streaming_queues = {}  # Empty = completed
            
            # 1. Initiate processing
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            process_response = await process_any_file_stream(
                file=mock_file, 
                request_data=None, 
                request=mock_request
            )
            assert process_response.task_id == "workflow-task"
            assert process_response.status == "processing"
            
            # 2. Check status
            status_response_result = await get_universal_task_status("workflow-task", mock_request)
            assert status_response_result.task_id == "workflow-task"
            assert status_response_result.status == "completed"
            assert status_response_result.file_type == FileType.PDF
    
    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test that errors are properly propagated through the router."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "error.txt"  # Unsupported file type
        mock_file.content_type = "text/plain"
        mock_file.size = 1024
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            mock_processor.process_file_stream = AsyncMock(
                side_effect=HTTPException(
                    status_code=400, 
                    detail="Unsupported file type: .txt"
                )
            )
            
            # Error should propagate correctly
            with pytest.raises(HTTPException) as exc_info:
                mock_request = Mock(spec=StarletteRequest)
                mock_request.client = Mock(host="127.0.0.1")
                await process_any_file_stream(
                    file=mock_file, 
                    request_data=None, 
                    request=mock_request
                )
            
            assert exc_info.value.status_code == 500
            assert "Failed to start processing" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_streaming_response_headers(self):
        """Test that streaming response has correct headers for CORS and caching."""
        task_id = "headers-test-task"
        
        async def mock_generator():
            yield "data: test\n\n"
        
        with patch('app.routers.unified_router.unified_processor') as mock_processor:
            mock_processor.get_stream_generator = Mock(return_value=mock_generator())
            
            mock_request = Mock(spec=StarletteRequest)
            mock_request.client = Mock(host="127.0.0.1")
            response = await stream_universal_progress(task_id, mock_request)
            
            # Verify streaming response properties
            assert response.media_type == "text/event-stream"
            
            # Check basic required headers (may vary by implementation)
            headers = response.headers
            assert "Cache-Control" in headers or "cache-control" in headers 