"""
Unit tests for DOCX OCR Service - Updated for current implementation.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open

from app.services.docx_ocr_service import DOCXOCRService
from app.models.unified_models import (
    UnifiedOCRRequest, ProcessingMode, UnifiedPageResult
)


class TestDOCXOCRService:
    """Test suite for DOCX OCR Service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = DOCXOCRService()
    
    def test_initialization(self):
        """Test service initialization."""
        assert hasattr(self.service, 'conversion_tools')
        assert isinstance(self.service.conversion_tools, dict)
        # Check expected conversion tools
        expected_tools = ["libreoffice", "unoconv", "python_docx"]
        for tool in expected_tools:
            assert tool in self.service.conversion_tools
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test the health check method."""
        result = await self.service.health_check()
        assert result is True  # Currently always returns True
    
    @pytest.mark.asyncio
    async def test_convert_docx_to_pdf_placeholder(self):
        """Test the placeholder DOCX to PDF conversion."""
        docx_path = Path("test.docx")
        
        # Mock the file creation
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('asyncio.sleep') as mock_sleep:
            
            pdf_path = await self.service.convert_docx_to_pdf(docx_path)
            
            # Verify output path is correct
            expected_pdf_path = docx_path.with_suffix('.pdf')
            assert pdf_path == expected_pdf_path
            
            # Verify placeholder file was created
            mock_file.assert_called_once_with(expected_pdf_path, 'w')
            mock_sleep.assert_called_once_with(2.0)
    
    @pytest.mark.asyncio
    async def test_estimate_pages(self):
        """Test page estimation for DOCX files."""
        docx_path = Path("test.docx")
        
        # Mock file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB
            
            pages = await self.service.estimate_pages(docx_path)
            
            assert isinstance(pages, int)
            assert pages >= 1
    
    @pytest.mark.asyncio
    async def test_process_docx_with_streaming_success(self):
        """Test successful DOCX processing with streaming."""
        request = UnifiedOCRRequest(
            mode=ProcessingMode.BASIC,
            threshold=500,
            contrast_level=1.3,
            dpi=300
        )
        
        mock_queue = asyncio.Queue()
        docx_path = Path("test_document.docx")
        task_id = "docx-test-task"
        
        # Mock the convert_docx_to_pdf method
        with patch.object(self.service, 'convert_docx_to_pdf', 
                         new_callable=AsyncMock) as mock_convert:
            
            mock_convert.return_value = Path("tmp/test.pdf")
            
            # Execute processing
            result = await self.service.process_docx_with_streaming(
                docx_path=docx_path,
                request=request,
                streaming_queue=mock_queue,
                task_id=task_id
            )
            
            # Verify results
            assert result["success"] is True
            assert "result" in result
            assert isinstance(result["result"], UnifiedPageResult)
            assert result["result"].page_number == 1
            assert "placeholder" in result["result"].extracted_text.lower()
            
            # Verify method calls
            mock_convert.assert_called_once_with(docx_path)
    
    @pytest.mark.asyncio
    async def test_process_docx_with_streaming_failure(self):
        """Test DOCX processing when conversion fails."""
        request = UnifiedOCRRequest(mode=ProcessingMode.BASIC)
        mock_queue = asyncio.Queue()
        docx_path = Path("failing_document.docx")
        task_id = "docx-fail-task"
        
        with patch.object(self.service, 'convert_docx_to_pdf', 
                         side_effect=Exception("Conversion failed")) as mock_convert:
            
            # Should handle conversion failure gracefully
            result = await self.service.process_docx_with_streaming(
                docx_path=docx_path,
                request=request,
                streaming_queue=mock_queue,
                task_id=task_id
            )
            
            # Should return failure result
            assert result["success"] is False
            assert "error" in result
            
            # Verify conversion was attempted
            mock_convert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_streaming_progress_updates(self):
        """Test that processing sends appropriate streaming updates."""
        request = UnifiedOCRRequest(mode=ProcessingMode.BASIC)
        mock_queue = asyncio.Queue()
        docx_path = Path("streaming_test.docx")
        task_id = "streaming-test-task"
        
        # Mock conversion
        with patch.object(self.service, 'convert_docx_to_pdf', 
                         new_callable=AsyncMock) as mock_convert:
            
            mock_convert.return_value = Path("tmp/test.pdf")
            
            # Execute processing
            result = await self.service.process_docx_with_streaming(
                docx_path=docx_path,
                request=request,
                streaming_queue=mock_queue,
                task_id=task_id
            )
            
            # Check that streaming updates were sent
            updates = []
            try:
                while True:
                    update = mock_queue.get_nowait()
                    updates.append(update)
            except asyncio.QueueEmpty:
                pass
            
            # Should have sent progress updates
            assert len(updates) >= 2  # At least start and completion
            
            # Verify update structure
            for update in updates:
                assert hasattr(update, 'task_id')
                assert hasattr(update, 'progress_percentage')
                assert update.task_id == task_id


class TestDOCXServiceIntegration:
    """Integration tests for DOCX service."""
    
    def test_service_singleton_access(self):
        """Test that service can be accessed and initialized."""
        service1 = DOCXOCRService()
        service2 = DOCXOCRService()
        
        # Should create separate instances (no singleton pattern)
        assert service1 is not service2
        assert hasattr(service1, 'conversion_tools')
        assert hasattr(service2, 'conversion_tools')
    
    @pytest.mark.asyncio
    async def test_end_to_end_placeholder_flow(self):
        """Test end-to-end DOCX processing flow (placeholder)."""
        service = DOCXOCRService()
        request = UnifiedOCRRequest(mode=ProcessingMode.LLM_ENHANCED)
        mock_queue = asyncio.Queue()
        task_id = "e2e-test"
        
        with patch.object(service, 'convert_docx_to_pdf', 
                         new_callable=AsyncMock) as mock_convert:
            
            mock_convert.return_value = Path("temp.pdf")
            
            result = await service.process_docx_with_streaming(
                docx_path=Path("test.docx"),
                request=request,
                streaming_queue=mock_queue,
                task_id=task_id
            )
            
            # Verify successful placeholder execution
            assert result["success"] is True
            assert "placeholder implementation" in result["message"]
    
    @pytest.mark.asyncio
    async def test_different_processing_modes(self):
        """Test processing with different modes."""
        service = DOCXOCRService()
        mock_queue = asyncio.Queue()
        
        modes = [ProcessingMode.BASIC, ProcessingMode.LLM_ENHANCED]
        
        for mode in modes:
            request = UnifiedOCRRequest(mode=mode)
            
            with patch.object(service, 'convert_docx_to_pdf', 
                             new_callable=AsyncMock) as mock_convert:
                
                mock_convert.return_value = Path("temp.pdf")
                
                result = await service.process_docx_with_streaming(
                    docx_path=Path("test.docx"),
                    request=request,
                    streaming_queue=mock_queue,
                    task_id=f"mode-test-{mode}"
                )
                
                # Should succeed with any mode (placeholder implementation)
                assert result["success"] is True
                assert result["result"].threshold_used == request.threshold
                assert result["result"].contrast_level_used == request.contrast_level