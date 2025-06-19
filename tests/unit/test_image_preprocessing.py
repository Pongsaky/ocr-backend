"""
Unit tests for image preprocessing functionality.
"""

import uuid
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
from PIL import Image
import base64
from io import BytesIO

from app.controllers.ocr_controller import OCRController
from app.models.ocr_models import (
    OCRRequest, ImagePreprocessResult, ImagePreprocessResponse
)
from app.services.external_ocr_service import ImageProcessingResult


@pytest.fixture
def ocr_controller():
    """Fixture for OCR controller."""
    return OCRController()


@pytest.fixture
def sample_image_file():
    """Fixture for creating a sample image file."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Save to BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    # Create UploadFile
    return UploadFile(
        filename="test_image.jpg",
        file=img_bytes,
        size=len(img_bytes.getvalue())
    )


@pytest.fixture
def ocr_request():
    """Fixture for OCR request."""
    return OCRRequest(threshold=500, contrast_level=1.3)


class TestImagePreprocessing:
    """Test image preprocessing functionality."""
    
    @pytest.mark.asyncio
    async def test_preprocess_image_success(self, ocr_controller, sample_image_file, ocr_request):
        """Test successful image preprocessing."""
        # Mock external service
        mock_result = ImageProcessingResult(
            success=True,
            processed_image_base64="dGVzdF9wcm9jZXNzZWRfaW1hZ2U=",  # "test_processed_image" encoded
            processing_time=1.5,
            threshold_used=500,
            contrast_level_used=1.3,
            extracted_text="",
            error_message=""
        )
        
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
             patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):  # "test_original_image" encoded
            
            response = await ocr_controller.preprocess_image(sample_image_file, ocr_request)
            
            # Verify response
            assert isinstance(response, ImagePreprocessResponse)
            assert response.status == "completed"
            assert response.result is not None
            assert response.result.success
            assert response.result.processed_image_base64 == "dGVzdF9wcm9jZXNzZWRfaW1hZ2U="
            assert response.result.original_image_base64 == "dGVzdF9vcmlnaW5hbF9pbWFnZQ=="
            assert response.result.processing_time == 1.5
            assert response.result.threshold_used == 500
            assert response.result.contrast_level_used == 1.3
            assert response.error_message is None
    
    @pytest.mark.asyncio
    async def test_preprocess_image_external_service_failure(self, ocr_controller, sample_image_file, ocr_request):
        """Test image preprocessing when external service fails."""
        # Mock external service failure
        mock_result = ImageProcessingResult(
            success=False,
            processed_image_base64="",
            processing_time=0.5,
            threshold_used=500,
            contrast_level_used=1.3,
            extracted_text="",
            error_message="External service unavailable"
        )
        
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
             patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
            
            response = await ocr_controller.preprocess_image(sample_image_file, ocr_request)
            
            # Verify response
            assert isinstance(response, ImagePreprocessResponse)
            assert response.status == "failed"
            assert response.result is None
            assert response.error_message == "Preprocessing failed"
    
    @pytest.mark.asyncio
    async def test_preprocess_image_sync_success(self, ocr_controller, ocr_request):
        """Test successful synchronous image preprocessing."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(tmp_file, format='JPEG')
            image_path = Path(tmp_file.name)
        
        try:
            # Mock external service
            mock_result = ImageProcessingResult(
                success=True,
                processed_image_base64="dGVzdF9wcm9jZXNzZWRfaW1hZ2U=",
                processing_time=2.0,
                threshold_used=500,
                contrast_level_used=1.3,
                extracted_text="",
                error_message=""
            )
            
            with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
                 patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
                
                result = await ocr_controller._preprocess_image_sync(image_path, ocr_request)
                
                # Verify result
                assert isinstance(result, ImagePreprocessResult)
                assert result.success
                assert result.processed_image_base64 == "dGVzdF9wcm9jZXNzZWRfaW1hZ2U="
                assert result.original_image_base64 == "dGVzdF9vcmlnaW5hbF9pbWFnZQ=="
                assert result.processing_time == 2.0
                assert result.threshold_used == 500
                assert result.contrast_level_used == 1.3
                assert result.image_metadata["external_service_used"]
                assert result.image_metadata["processing_successful"]
        
        finally:
            # Cleanup
            if image_path.exists():
                image_path.unlink()
    
    @pytest.mark.asyncio
    async def test_preprocess_image_sync_failure(self, ocr_controller, ocr_request):
        """Test synchronous image preprocessing failure."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (100, 100), color='green')
            img.save(tmp_file, format='JPEG')
            image_path = Path(tmp_file.name)
        
        try:
            # Mock external service failure
            mock_result = ImageProcessingResult(
                success=False,
                processed_image_base64="",
                processing_time=0.2,
                threshold_used=500,
                contrast_level_used=1.3,
                extracted_text="",
                error_message="Processing failed"
            )
            
            with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
                 patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
                
                result = await ocr_controller._preprocess_image_sync(image_path, ocr_request)
                
                # Verify result
                assert isinstance(result, ImagePreprocessResult)
                assert not result.success
                assert result.processed_image_base64 == ""
                assert result.original_image_base64 == "dGVzdF9vcmlnaW5hbF9pbWFnZQ=="
                assert result.processing_time == 0.2
                assert result.threshold_used == 500
                assert result.contrast_level_used == 1.3
                assert "error" in result.image_metadata
                assert result.image_metadata["error"] == "Processing failed"
        
        finally:
            # Cleanup
            if image_path.exists():
                image_path.unlink()
    
    @pytest.mark.asyncio
    async def test_preprocess_image_sync_exception(self, ocr_controller, ocr_request):
        """Test synchronous image preprocessing with exception."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (100, 100), color='yellow')
            img.save(tmp_file, format='JPEG')
            image_path = Path(tmp_file.name)
        
        try:
            # Mock external service to raise an exception
            with patch('app.controllers.ocr_controller.external_ocr_service.process_image', side_effect=Exception("Service unavailable")), \
                 patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
                
                result = await ocr_controller._preprocess_image_sync(image_path, ocr_request)
                
                # Verify result
                assert isinstance(result, ImagePreprocessResult)
                assert not result.success
                assert result.processed_image_base64 == ""
                assert result.original_image_base64 == ""
                assert result.processing_time == 0.0
                assert result.threshold_used == 500
                assert result.contrast_level_used == 1.3
                assert "error" in result.image_metadata
                assert "Service unavailable" in result.image_metadata["error"]
        
        finally:
            # Cleanup
            if image_path.exists():
                image_path.unlink()
    
    @pytest.mark.asyncio
    async def test_image_to_base64_success(self, ocr_controller):
        """Test successful image to base64 conversion."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (50, 50), color='purple')
            img.save(tmp_file, format='JPEG')
            image_path = Path(tmp_file.name)
        
        try:
            result = await ocr_controller._image_to_base64(image_path)
            
            # Verify result
            assert result != ""
            assert isinstance(result, str)
            
            # Verify it's valid base64
            try:
                decoded = base64.b64decode(result)
                assert len(decoded) > 0
            except Exception:
                pytest.fail("Result is not valid base64")
        
        finally:
            # Cleanup
            if image_path.exists():
                image_path.unlink()
    
    @pytest.mark.asyncio
    async def test_image_to_base64_invalid_file(self, ocr_controller):
        """Test image to base64 conversion with invalid file."""
        # Non-existent file
        image_path = Path("/non/existent/file.jpg")
        
        result = await ocr_controller._image_to_base64(image_path)
        
        # Verify result
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_preprocess_image_with_rgba_image(self, ocr_controller, ocr_request):
        """Test preprocessing with RGBA image (should be converted to RGB)."""
        # Create RGBA image
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        
        # Save to BytesIO
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Create UploadFile
        upload_file = UploadFile(
            filename="test_rgba.png",
            file=img_bytes,
            size=len(img_bytes.getvalue())
        )
        
        # Mock external service
        mock_result = ImageProcessingResult(
            success=True,
            processed_image_base64="dGVzdF9wcm9jZXNzZWRfaW1hZ2U=",
            processing_time=1.0,
            threshold_used=500,
            contrast_level_used=1.3,
            extracted_text="",
            error_message=""
        )
        
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
             patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
            
            response = await ocr_controller.preprocess_image(upload_file, ocr_request)
            
            # Verify response
            assert isinstance(response, ImagePreprocessResponse)
            assert response.status == "completed"
            assert response.result is not None
            assert response.result.success
    
    @pytest.mark.asyncio
    async def test_preprocess_image_with_default_parameters(self, ocr_controller, sample_image_file):
        """Test preprocessing with default parameters."""
        # Use default OCR request
        default_request = OCRRequest()
        
        # Mock external service
        mock_result = ImageProcessingResult(
            success=True,
            processed_image_base64="dGVzdF9wcm9jZXNzZWRfaW1hZ2U=",
            processing_time=1.2,
            threshold_used=500,  # Default value
            contrast_level_used=1.3,  # Default value
            extracted_text="",
            error_message=""
        )
        
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', return_value=mock_result), \
             patch.object(ocr_controller, '_image_to_base64', return_value="dGVzdF9vcmlnaW5hbF9pbWFnZQ=="):
            
            response = await ocr_controller.preprocess_image(sample_image_file, default_request)
            
            # Verify response
            assert isinstance(response, ImagePreprocessResponse)
            assert response.status == "completed"
            assert response.result is not None
            assert response.result.success
            assert response.result.threshold_used == 500
            assert response.result.contrast_level_used == 1.3 