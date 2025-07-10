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
            dpi=300
        )
    
    @pytest.fixture
    def mock_pdf_llm_request(self):
        """Create mock PDF LLM OCR request."""
        return PDFLLMOCRRequest(
            threshold=128,
            contrast_level=1.0,
            dpi=300,
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
    
    # --- Page Selection Tests ---
    
    def test_pdf_ocr_request_with_page_select(self):
        """Test PDFOCRRequest with page selection."""
        request = PDFOCRRequest(
            threshold=128,
            contrast_level=1.0,
            dpi=300,
            page_select=[1, 3, 5]
        )
        assert request.page_select == [1, 3, 5]
    
    def test_pdf_ocr_request_without_page_select(self):
        """Test PDFOCRRequest without page selection."""
        request = PDFOCRRequest(
            threshold=128,
            contrast_level=1.0,
            dpi=300
        )
        assert request.page_select is None
    
    def test_pdf_ocr_request_page_select_validation(self):
        """Test PDFOCRRequest page selection validation."""
        # Test empty list
        with pytest.raises(ValueError, match="page_select cannot be empty"):
            PDFOCRRequest(
                threshold=128,
                contrast_level=1.0,
                dpi=300,
                page_select=[]
            )
        
        # Test invalid page numbers
        with pytest.raises(ValueError, match="Page numbers must be 1-indexed"):
            PDFOCRRequest(
                threshold=128,
                contrast_level=1.0,
                dpi=300,
                page_select=[0, 1, 2]
            )
        
        # Test duplicate page numbers
        with pytest.raises(ValueError, match="Duplicate page numbers are not allowed"):
            PDFOCRRequest(
                threshold=128,
                contrast_level=1.0,
                dpi=300,
                page_select=[1, 2, 2, 3]
            )
    
    def test_pdf_ocr_request_page_select_sorting(self):
        """Test PDFOCRRequest page selection sorting."""
        request = PDFOCRRequest(
            threshold=128,
            contrast_level=1.0,
            dpi=300,
            page_select=[5, 1, 3]
        )
        assert request.page_select == [1, 3, 5]
    
    def test_pdf_llm_ocr_request_with_page_select(self):
        """Test PDFLLMOCRRequest with page selection."""
        request = PDFLLMOCRRequest(
            threshold=128,
            contrast_level=1.0,
            dpi=300,
            prompt="Extract text",
            model="gpt-4",
            page_select=[1, 3, 5]
        )
        assert request.page_select == [1, 3, 5]
    
    def test_pdf_llm_ocr_request_page_select_validation(self):
        """Test PDFLLMOCRRequest page selection validation."""
        # Test empty list
        with pytest.raises(ValueError, match="page_select cannot be empty"):
            PDFLLMOCRRequest(
                threshold=128,
                contrast_level=1.0,
                dpi=300,
                prompt="Extract text",
                model="gpt-4",
                page_select=[]
            )
    
    @pytest.mark.asyncio
    async def test_pdf_to_images_page_selection(self, pdf_service):
        """Test _pdf_to_images with page selection."""
        with patch('fitz.open') as mock_fitz_open:
            # Mock PDF document
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=5)  # 5 pages total
            mock_doc.load_page = Mock()
            mock_fitz_open.return_value = mock_doc
            
            # Mock page processing
            mock_page = Mock()
            mock_page.get_pixmap = Mock(return_value=Mock())
            mock_doc.load_page.return_value = mock_page
            
            # Mock context
            mock_context = Mock()
            mock_context.pdf_document = None
            mock_context.add_temp_file = Mock()
            
            # Mock file operations
            with patch('pathlib.Path.mkdir'), \
                 patch('pathlib.Path.exists', return_value=True), \
                 patch('app.utils.image_utils.validate_and_scale_image') as mock_validate:
                
                mock_validate.return_value = (Path("/tmp/test.png"), {})
                
                # Test with page selection
                result = await pdf_service._pdf_to_images(
                    Path("/tmp/test.pdf"),
                    300,
                    mock_context,
                    page_select=[1, 3, 5]
                )
                
                # Should only process selected pages
                assert len(result) == 3
                assert mock_doc.load_page.call_count == 3
                
                # Verify correct pages were loaded (0-indexed)
                mock_doc.load_page.assert_any_call(0)  # Page 1
                mock_doc.load_page.assert_any_call(2)  # Page 3
                mock_doc.load_page.assert_any_call(4)  # Page 5
    
    @pytest.mark.asyncio
    async def test_pdf_to_images_invalid_page_selection(self, pdf_service):
        """Test _pdf_to_images with invalid page selection."""
        with patch('fitz.open') as mock_fitz_open:
            # Mock PDF document with only 3 pages
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=3)
            mock_fitz_open.return_value = mock_doc
            
            mock_context = Mock()
            mock_context.pdf_document = None
            mock_context.add_temp_file = Mock()
            
            # Test with invalid page selection (page 5 doesn't exist)
            with pytest.raises(ValueError, match="Invalid page numbers: \\[5\\]. PDF only has 3 pages"):
                await pdf_service._pdf_to_images(
                    Path("/tmp/test.pdf"),
                    300,
                    mock_context,
                    page_select=[1, 3, 5]  # Page 5 doesn't exist
                ) 