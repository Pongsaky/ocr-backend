"""
Unit tests for PDF OCR Service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC
from pathlib import Path

from app.services.pdf_ocr_service import PDFOCRService
from app.models.ocr_models import (
    PDFOCRRequest, PDFLLMOCRRequest, OCRResult, OCRLLMResult,
    PDFPageStreamResult, PDFStreamingStatus, PDFLLMStreamingStatus
)


class TestPDFOCRService:
    """Test cases for PDF OCR Service."""
    
    @pytest.fixture
    def pdf_service(self):
        """Create PDF OCR service instance."""
        return PDFOCRService()
    
    @pytest.fixture
    def mock_pdf_request(self):
        """Create mock PDF OCR request."""
        return PDFOCRRequest(
            threshold=128,
            contrast_level=1.0,
            process_sync=False
        )
    
    @pytest.fixture
    def mock_pdf_llm_request(self):
        """Create mock PDF LLM OCR request."""
        return PDFLLMOCRRequest(
            threshold=128,
            contrast_level=1.0,
            process_sync=False,
            prompt="Extract text from this document",
            model="gpt-4"
        )
    
    @pytest.fixture
    def mock_pdf_path(self):
        """Create mock PDF path."""
        return Path("/tmp/test.pdf")
    
    @pytest.mark.asyncio
    async def test_check_task_cancellation_not_cancelled(self, pdf_service):
        """Test check_task_cancellation when task is not cancelled."""
        task_id = "test-task-123"
        
        # Should not raise exception when task is not cancelled
        await pdf_service.check_task_cancellation(task_id)
    
    @pytest.mark.asyncio
    async def test_check_task_cancellation_cancelled(self, pdf_service):
        """Test check_task_cancellation when task is cancelled."""
        from app.controllers.ocr_controller import ocr_controller
        
        task_id = "test-task-123"
        ocr_controller.cancelled_tasks.add(task_id)
        ocr_controller.cancellation_reasons[task_id] = "Test cancellation"
        
        with pytest.raises(Exception, match="Task test-task-123 was cancelled"):
            await pdf_service.check_task_cancellation(task_id)
        
        # Cleanup
        ocr_controller.cancelled_tasks.discard(task_id)
        ocr_controller.cancellation_reasons.pop(task_id, None)
    
    def test_pdf_ocr_service_cancellation_integration(self, pdf_service):
        """Test that PDF OCR service integrates properly with cancellation system."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Test that we can access the controller and check cancellation state
        task_id = "test-integration-123"
        
        # Initially task should not be cancelled
        assert not ocr_controller.is_task_cancelled(task_id)
        
        # Add task to cancelled set
        ocr_controller.cancelled_tasks.add(task_id)
        ocr_controller.cancellation_reasons[task_id] = "Test integration"
        
        # Now task should be cancelled
        assert ocr_controller.is_task_cancelled(task_id)
        
        # Cleanup
        ocr_controller.cancelled_tasks.discard(task_id)
        ocr_controller.cancellation_reasons.pop(task_id, None)
    
    def test_pdf_ocr_service_initialization(self, pdf_service):
        """Test PDF OCR service initialization."""
        assert pdf_service is not None
        # Test that the service has the basic methods we expect
        assert hasattr(pdf_service, 'check_task_cancellation')
    
    def test_pdf_ocr_service_has_cancellation_check(self, pdf_service):
        """Test that PDF OCR service has cancellation check method."""
        import inspect
        assert hasattr(pdf_service, 'check_task_cancellation')
        assert inspect.iscoroutinefunction(pdf_service.check_task_cancellation) 