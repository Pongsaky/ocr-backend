"""
Unit tests for unified stream processor - testing file detection, processing, and streaming logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from io import BytesIO
from fastapi import UploadFile, HTTPException

from app.services.unified_stream_processor import (
    FileTypeDetector, MetadataExtractor, ProcessingTimeEstimator,
    UnifiedStreamProcessor, unified_processor
)
from app.models.unified_models import (
    FileType, ProcessingMode, UnifiedOCRRequest, FileMetadata
)


class TestFileTypeDetector:
    """Test file type detection and validation."""
    
    @pytest.mark.asyncio
    async def test_detect_image_from_mime_type(self):
        """Test image detection from MIME type."""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "test.jpg"
        
        file_type = await FileTypeDetector.detect_file_type(mock_file)
        assert file_type == FileType.IMAGE
    
    @pytest.mark.asyncio
    async def test_detect_pdf_from_mime_type(self):
        """Test PDF detection from MIME type."""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.filename = "document.pdf"
        
        file_type = await FileTypeDetector.detect_file_type(mock_file)
        assert file_type == FileType.PDF
    
    @pytest.mark.asyncio
    async def test_detect_docx_from_mime_type(self):
        """Test DOCX detection from MIME type."""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_file.filename = "report.docx"
        
        file_type = await FileTypeDetector.detect_file_type(mock_file)
        assert file_type == FileType.DOCX
    
    @pytest.mark.asyncio
    async def test_detect_from_extension_fallback(self):
        """Test file type detection from extension when MIME type is unknown."""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "application/octet-stream"  # Generic MIME type
        mock_file.filename = "image.png"
        
        file_type = await FileTypeDetector.detect_file_type(mock_file)
        assert file_type == FileType.IMAGE
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self):
        """Test exception for unsupported file types."""
        mock_file = Mock(spec=UploadFile)
        mock_file.content_type = "text/plain"
        mock_file.filename = "document.txt"
        
        with pytest.raises(HTTPException) as exc_info:
            await FileTypeDetector.detect_file_type(mock_file)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_file_size_success(self):
        """Test successful file size validation."""
        mock_file = Mock(spec=UploadFile)
        mock_file.size = 5 * 1024 * 1024  # 5MB - should pass for image
        
        # Should not raise exception
        await FileTypeDetector.validate_file_size(mock_file, FileType.IMAGE)
    
    @pytest.mark.asyncio
    async def test_validate_file_size_too_large(self):
        """Test file size validation failure."""
        mock_file = Mock(spec=UploadFile)
        mock_file.size = 15 * 1024 * 1024  # 15MB - too large for image (10MB limit)
        
        with pytest.raises(HTTPException) as exc_info:
            await FileTypeDetector.validate_file_size(mock_file, FileType.IMAGE)
        
        assert exc_info.value.status_code == 413
        assert "file too large" in str(exc_info.value.detail).lower()


class TestMetadataExtractor:
    """Test metadata extraction for different file types."""
    
    @pytest.mark.asyncio
    async def test_extract_image_metadata_success(self):
        """Test successful image metadata extraction."""
        # Create a mock image file path
        mock_path = Mock(spec=Path)
        
        with patch('PIL.Image.open') as mock_image_open:
            # Mock PIL Image
            mock_image = Mock()
            mock_image.width = 1920
            mock_image.height = 1080
            mock_image_open.return_value.__enter__ = Mock(return_value=mock_image)
            mock_image_open.return_value.__exit__ = Mock(return_value=None)
            
            metadata = await MetadataExtractor.extract_image_metadata(mock_path)
            
            assert metadata == {"width": 1920, "height": 1080}
    
    @pytest.mark.asyncio
    async def test_extract_image_metadata_failure(self):
        """Test image metadata extraction with error handling."""
        mock_path = Mock(spec=Path)
        
        with patch('PIL.Image.open', side_effect=Exception("Cannot open image")):
            metadata = await MetadataExtractor.extract_image_metadata(mock_path)
            
            assert metadata == {"width": 0, "height": 0}
    
    @pytest.mark.asyncio
    async def test_extract_pdf_metadata_success(self):
        """Test successful PDF metadata extraction."""
        mock_path = Mock(spec=Path)
        
        with patch('fitz.open') as mock_fitz_open:
            # Mock PyMuPDF document
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=5)  # 5 pages
            mock_doc.close = Mock()
            mock_fitz_open.return_value = mock_doc
            
            page_count = await MetadataExtractor.extract_pdf_metadata(mock_path)
            
            assert page_count == 5
            mock_doc.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_pdf_metadata_failure(self):
        """Test PDF metadata extraction with error handling."""
        mock_path = Mock(spec=Path)
        
        with patch('fitz.open', side_effect=Exception("Cannot open PDF")):
            page_count = await MetadataExtractor.extract_pdf_metadata(mock_path)
            
            assert page_count == 0
    
    @pytest.mark.asyncio
    async def test_extract_docx_metadata(self):
        """Test DOCX metadata extraction (file size estimation)."""
        mock_path = Mock(spec=Path)
        mock_stat = Mock()
        mock_stat.st_size = 3 * 1024 * 1024  # 3MB
        mock_path.stat.return_value = mock_stat
        
        page_count = await MetadataExtractor.extract_docx_metadata(mock_path)
        
        # Should estimate ~6 pages (3MB * 2)
        assert page_count == 6


class TestProcessingTimeEstimator:
    """Test processing time estimation logic."""
    
    def test_estimate_image_basic(self):
        """Test time estimation for basic image processing."""
        duration = ProcessingTimeEstimator.estimate_duration(
            file_type=FileType.IMAGE,
            file_size=5 * 1024 * 1024,  # 5MB
            mode=ProcessingMode.BASIC,
            page_count=1
        )
        
        # Base time (2.0) * 1 page * size factor
        expected_base = 2.0 * 1 * (1.0 + (5 / 10) * 0.2)  # Size factor: +10%
        assert duration == round(expected_base, 1)
    
    def test_estimate_pdf_llm_enhanced(self):
        """Test time estimation for LLM-enhanced PDF processing."""
        duration = ProcessingTimeEstimator.estimate_duration(
            file_type=FileType.PDF,
            file_size=10 * 1024 * 1024,  # 10MB
            mode=ProcessingMode.LLM_ENHANCED,
            page_count=5
        )
        
        # Base time (3.0) * 5 pages * size factor
        expected_base = 3.0 * 5 * (1.0 + (10 / 10) * 0.2)  # Size factor: +20%
        assert duration == round(expected_base, 1)
    
    def test_estimate_docx_with_conversion_overhead(self):
        """Test time estimation for DOCX with conversion overhead."""
        duration = ProcessingTimeEstimator.estimate_duration(
            file_type=FileType.DOCX,
            file_size=5 * 1024 * 1024,  # 5MB
            mode=ProcessingMode.BASIC,
            page_count=3
        )
        
        # Base time (3.0) * 3 pages * size factor + 5.0 conversion overhead
        expected_base = 3.0 * 3 * (1.0 + (5 / 10) * 0.2) + 5.0
        assert duration == round(expected_base, 1)


class TestUnifiedStreamProcessor:
    """Test the main unified stream processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = UnifiedStreamProcessor()
    
    def test_initialization(self):
        """Test processor initialization."""
        assert isinstance(self.processor.file_detector, FileTypeDetector)
        assert isinstance(self.processor.metadata_extractor, MetadataExtractor)
        assert isinstance(self.processor.time_estimator, ProcessingTimeEstimator)
        assert isinstance(self.processor.streaming_queues, dict)
        assert isinstance(self.processor.task_metadata, dict)
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file(self):
        """Test file saving functionality."""
        # Create mock upload file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.read = AsyncMock(return_value=b"fake image data")
        
        task_id = "test-task-123"
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open := Mock()) as mock_open_func:
            
            # Mock the file operations
            mock_open_func.return_value.__enter__ = Mock()
            mock_open_func.return_value.__exit__ = Mock()
            mock_open_func.return_value.write = Mock()
            
            with patch('app.services.unified_stream_processor.settings') as mock_settings:
                mock_settings.UPLOAD_DIR = "/tmp/uploads"
                
                file_path = await self.processor._save_uploaded_file(mock_file, task_id)
                
                assert str(file_path).endswith(f"{task_id}.jpg")
                mock_file.read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_file_metadata_image(self):
        """Test file metadata extraction for images."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.size = 1024000
        mock_file.content_type = "image/jpeg"
        
        mock_path = Mock(spec=Path)
        
        with patch.object(self.processor.metadata_extractor, 'extract_image_metadata', 
                         new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"width": 1920, "height": 1080}
            
            metadata = await self.processor._extract_file_metadata(
                mock_file, FileType.IMAGE, mock_path
            )
            
            assert metadata.original_filename == "test.jpg"
            assert metadata.file_size_bytes == 1024000
            assert metadata.mime_type == "image/jpeg"
            assert metadata.detected_file_type == FileType.IMAGE
            assert metadata.image_dimensions == {"width": 1920, "height": 1080}
            assert metadata.pdf_page_count is None
            assert metadata.docx_page_count is None
    
    @pytest.mark.asyncio
    async def test_process_file_stream_image_detection(self):
        """Test the main process_file_stream method with image detection."""
        # Create mock upload file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.size = 1024000
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"fake image data")
        
        # Create request
        request = UnifiedOCRRequest(mode=ProcessingMode.BASIC)
        task_id = "test-task-456"
        
        # Mock all the dependencies
        with patch.object(self.processor.file_detector, 'detect_file_type', 
                         new_callable=AsyncMock) as mock_detect, \
             patch.object(self.processor.file_detector, 'validate_file_size', 
                         new_callable=AsyncMock) as mock_validate, \
             patch.object(self.processor, '_save_uploaded_file', 
                         new_callable=AsyncMock) as mock_save, \
             patch.object(self.processor, '_extract_file_metadata', 
                         new_callable=AsyncMock) as mock_extract, \
             patch.object(self.processor, '_send_progress_update', 
                         new_callable=AsyncMock) as mock_progress, \
             patch('asyncio.create_task') as mock_create_task:
            
            # Set up return values
            mock_detect.return_value = FileType.IMAGE
            mock_save.return_value = Path("/tmp/test.jpg")
            mock_extract.return_value = FileMetadata(
                original_filename="test.jpg",
                file_size_bytes=1024000,
                mime_type="image/jpeg",
                detected_file_type=FileType.IMAGE,
                image_dimensions={"width": 1920, "height": 1080}
            )
            
            # Execute
            response = await self.processor.process_file_stream(
                file=mock_file,
                request=request,
                task_id=task_id
            )
            
            # Verify results
            assert response.task_id == task_id
            assert response.file_type == FileType.IMAGE
            assert response.processing_mode == ProcessingMode.BASIC
            assert response.status == "processing"
            assert response.estimated_duration is not None
            
            # Verify method calls
            mock_detect.assert_called_once_with(mock_file)
            mock_validate.assert_called_once_with(mock_file, FileType.IMAGE)
            mock_save.assert_called_once()
            mock_extract.assert_called_once()
            mock_progress.assert_called_once()
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_stream_generator_not_found(self):
        """Test stream generator for non-existent task."""
        with pytest.raises(HTTPException) as exc_info:
            async for _ in self.processor.get_stream_generator("non-existent-task"):
                pass
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_get_stream_generator_with_updates(self):
        """Test stream generator with mock updates."""
        task_id = "test-stream-task"
        
        # Create mock queue with test data
        mock_queue = asyncio.Queue()
        
        # Create mock streaming status
        from app.models.unified_models import UnifiedStreamingStatus, ProcessingStep
        from datetime import datetime, timezone
        
        test_status = UnifiedStreamingStatus(
            task_id=task_id,
            file_type=FileType.IMAGE,
            processing_mode=ProcessingMode.BASIC,
            status="completed",
            current_step=ProcessingStep.COMPLETED,
            progress_percentage=100.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add status to queue
        await mock_queue.put(test_status)
        
        # Add queue to processor
        self.processor.streaming_queues[task_id] = mock_queue
        
        # Test generator
        updates = []
        async for update in self.processor.get_stream_generator(task_id):
            updates.append(update)
            # Break after first update since status is "completed"
            break
        
        assert len(updates) == 1
        assert f'"task_id":"{task_id}"' in updates[0]
        assert '"status":"completed"' in updates[0]
        
        # Cleanup
        if task_id in self.processor.streaming_queues:
            del self.processor.streaming_queues[task_id]
    
    @pytest.mark.asyncio
    async def test_cleanup_task(self):
        """Test task cleanup functionality."""
        task_id = "cleanup-test-task"
        
        # Set up task data
        mock_queue = asyncio.Queue()
        self.processor.streaming_queues[task_id] = mock_queue
        
        mock_file_path = Mock(spec=Path)
        mock_file_path.exists.return_value = True
        mock_file_path.unlink = Mock()
        
        self.processor.task_metadata[task_id] = {
            "file_path": mock_file_path,
            "file_type": FileType.IMAGE
        }
        
        # Execute cleanup
        await self.processor._cleanup_task(task_id)
        
        # Verify cleanup
        assert task_id not in self.processor.streaming_queues
        # Note: task_metadata cleanup depends on implementation


class TestUnifiedProcessorIntegration:
    """Test integration scenarios with the unified processor."""
    
    @pytest.mark.asyncio
    async def test_processor_error_handling(self):
        """Test error handling in processor."""
        processor = UnifiedStreamProcessor()
        
        # Create mock file that will cause an error
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.size = 1024000
        mock_file.content_type = "image/jpeg"
        
        # Mock file detector to raise exception
        with patch.object(processor.file_detector, 'detect_file_type', 
                         side_effect=Exception("Detection failed")):
            
            request = UnifiedOCRRequest()
            task_id = "error-test-task"
            
            with pytest.raises(HTTPException) as exc_info:
                await processor.process_file_stream(
                    file=mock_file,
                    request=request,
                    task_id=task_id
                )
            
            assert exc_info.value.status_code == 500
            # Error message should contain the original error
            assert "Detection failed" in str(exc_info.value.detail)
            
            # Verify cleanup happened
            assert task_id not in processor.streaming_queues
            assert task_id not in processor.task_metadata
    
    def test_singleton_instance(self):
        """Test that unified_processor is a singleton instance."""
        from app.services.unified_stream_processor import unified_processor
        
        assert isinstance(unified_processor, UnifiedStreamProcessor)
        
        # Import again to ensure it's the same instance
        from app.services.unified_stream_processor import unified_processor as processor2
        
        assert unified_processor is processor2 