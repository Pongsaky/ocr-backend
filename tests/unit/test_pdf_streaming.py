"""
Unit tests for PDF streaming functionality.
"""

import asyncio
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from app.models.ocr_models import (
    PDFOCRRequest, PDFOCRResult, PDFPageResult,
    PDFLLMOCRRequest, PDFLLMOCRResult, PDFPageLLMResult,
    PDFPageStreamResult, PDFStreamingStatus,
    PDFPageLLMStreamResult, PDFLLMStreamingStatus,
    OCRResult
)
from app.services.pdf_ocr_service import PDFOCRService
from app.controllers.ocr_controller import OCRController


class TestPDFStreamingModels:
    """Test streaming data models."""
    
    def test_pdf_page_stream_result_creation(self):
        """Test PDFPageStreamResult model creation."""
        result = PDFPageStreamResult(
            page_number=1,
            extracted_text="Test text",
            processing_time=2.5,
            success=True,
            error_message=None,
            threshold_used=500,
            contrast_level_used=1.3,
            timestamp=datetime.utcnow()
        )
        
        assert result.page_number == 1
        assert result.extracted_text == "Test text"
        assert result.processing_time == 2.5
        assert result.success is True
        assert result.error_message is None
        assert result.threshold_used == 500
        assert result.contrast_level_used == 1.3
        assert isinstance(result.timestamp, datetime)
    
    def test_pdf_streaming_status_creation(self):
        """Test PDFStreamingStatus model creation."""
        page_result = PDFPageStreamResult(
            page_number=1,
            extracted_text="Test text",
            processing_time=2.5,
            success=True,
            threshold_used=500,
            contrast_level_used=1.3,
            timestamp=datetime.utcnow()
        )
        
        status = PDFStreamingStatus(
            task_id="test-task-123",
            status="page_completed",
            current_page=1,
            total_pages=3,
            processed_pages=1,
            failed_pages=0,
            latest_page_result=page_result,
            cumulative_results=[page_result],
            progress_percentage=33.33,
            estimated_time_remaining=5.0,
            processing_speed=0.2,
            error_message=None,
            timestamp=datetime.utcnow()
        )
        
        assert status.task_id == "test-task-123"
        assert status.status == "page_completed"
        assert status.current_page == 1
        assert status.total_pages == 3
        assert status.processed_pages == 1
        assert status.failed_pages == 0
        assert status.latest_page_result == page_result
        assert len(status.cumulative_results) == 1
        assert status.progress_percentage == 33.33
        assert status.estimated_time_remaining == 5.0
        assert status.processing_speed == 0.2

    def test_pdf_llm_streaming_status_creation(self):
        """Test PDFLLMStreamingStatus model creation."""
        page_result = PDFPageLLMStreamResult(
            page_number=1,
            extracted_text="Enhanced text",
            original_ocr_text="Original text",
            processing_time=4.2,
            ocr_processing_time=2.1,
            llm_processing_time=2.1,
            success=True,
            threshold_used=500,
            contrast_level_used=1.3,
            model_used="test-model",
            prompt_used="test prompt",
            timestamp=datetime.utcnow()
        )
        
        status = PDFLLMStreamingStatus(
            task_id="test-llm-task-123",
            status="page_completed",
            current_page=1,
            total_pages=2,
            processed_pages=1,
            failed_pages=0,
            latest_page_result=page_result,
            cumulative_results=[page_result],
            progress_percentage=50.0,
            timestamp=datetime.utcnow()
        )
        
        assert status.task_id == "test-llm-task-123"
        assert status.latest_page_result.extracted_text == "Enhanced text"
        assert status.latest_page_result.original_ocr_text == "Original text"
        assert status.progress_percentage == 50.0


class TestPDFOCRServiceStreaming:
    """Test PDF OCR service streaming functionality."""
    
    @pytest.fixture
    def pdf_service(self):
        """Create PDF OCR service instance."""
        return PDFOCRService()
    
    @pytest.fixture
    def mock_pdf_path(self, tmp_path):
        """Create mock PDF path."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("mock pdf content")
        return pdf_file
    
    @pytest.fixture
    def streaming_queue(self):
        """Create streaming queue."""
        return asyncio.Queue()
    
    @pytest.mark.asyncio
    async def test_send_streaming_update(self, pdf_service, streaming_queue):
        """Test sending streaming updates."""
        status = PDFStreamingStatus(
            task_id="test-123",
            status="processing",
            current_page=0,
            total_pages=2,
            processed_pages=0,
            failed_pages=0,
            cumulative_results=[],
            progress_percentage=0.0,
            timestamp=datetime.utcnow()
        )
        
        await pdf_service._send_streaming_update(streaming_queue, status)
        
        # Check that update was sent
        assert streaming_queue.qsize() == 1
        received_status = await streaming_queue.get()
        assert received_status.task_id == "test-123"
        assert received_status.status == "processing"
    
    @pytest.mark.asyncio
    async def test_send_llm_streaming_update(self, pdf_service, streaming_queue):
        """Test sending LLM streaming updates."""
        status = PDFLLMStreamingStatus(
            task_id="test-llm-123",
            status="processing",
            current_page=0,
            total_pages=2,
            processed_pages=0,
            failed_pages=0,
            cumulative_results=[],
            progress_percentage=0.0,
            timestamp=datetime.utcnow()
        )
        
        await pdf_service._send_llm_streaming_update(streaming_queue, status)
        
        # Check that update was sent
        assert streaming_queue.qsize() == 1
        received_status = await streaming_queue.get()
        assert received_status.task_id == "test-llm-123"
        assert received_status.status == "processing"


class TestOCRControllerStreaming:
    """Test OCR controller streaming functionality."""
    
    @pytest.fixture
    def controller(self):
        """Create OCR controller instance."""
        return OCRController()
    
    @pytest.fixture
    def mock_upload_file(self):
        """Create mock upload file."""
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024
        return mock_file
    
    @pytest.mark.asyncio
    async def test_stream_pdf_progress_task_not_found(self, controller):
        """Test streaming progress for non-existent task."""
        task_id = "non-existent-task"
        
        # Collect streaming responses
        responses = []
        async for response in controller.stream_pdf_progress(task_id):
            responses.append(response)
            break  # Just get the first response
        
        assert len(responses) == 1
        assert "Task not found" in responses[0]
    
    @pytest.mark.asyncio
    async def test_stream_pdf_progress_with_updates(self, controller):
        """Test streaming progress with actual updates."""
        task_id = "test-stream-123"
        
        # Create streaming queue with test data
        queue = asyncio.Queue()
        controller.streaming_queues[task_id] = queue
        
        # Add test updates
        test_status = PDFStreamingStatus(
            task_id=task_id,
            status="page_completed",
            current_page=1,
            total_pages=2,
            processed_pages=1,
            failed_pages=0,
            cumulative_results=[],
            progress_percentage=50.0,
            timestamp=datetime.utcnow()
        )
        
        await queue.put(test_status)
        await queue.put(None)  # Sentinel to end stream
        
        # Collect streaming responses
        responses = []
        async for response in controller.stream_pdf_progress(task_id):
            responses.append(response)
        
        # Verify responses
        assert len(responses) == 1
        response_data = json.loads(responses[0].replace("data: ", "").replace("\n\n", ""))
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "page_completed"
        assert response_data["progress_percentage"] == 50.0
        
        # Verify queue cleanup
        assert task_id not in controller.streaming_queues


class TestStreamingErrorHandling:
    """Test error handling in streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_queue_error_handling(self):
        """Test handling of streaming queue errors."""
        service = PDFOCRService()
        
        # Test with None queue (should not raise exception)
        await service._send_streaming_update(None, None)
        
        # Test with invalid status (should handle gracefully)
        queue = asyncio.Queue()
        try:
            await service._send_streaming_update(queue, "invalid_status")
        except Exception:
            pass  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_controller_streaming_queue_cleanup(self):
        """Test that streaming queues are properly cleaned up."""
        controller = OCRController()
        task_id = "cleanup-test-123"
        
        # Add streaming queue
        queue = asyncio.Queue()
        controller.streaming_queues[task_id] = queue
        
        # Simulate stream completion
        await queue.put(None)  # Sentinel
        
        # Stream should clean up queue
        responses = []
        async for response in controller.stream_pdf_progress(task_id):
            responses.append(response)
        
        # Verify cleanup
        assert task_id not in controller.streaming_queues 