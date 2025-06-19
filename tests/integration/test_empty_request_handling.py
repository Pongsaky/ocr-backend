"""
Tests for handling empty request parameters with default values.
"""

import io
import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


class TestEmptyRequestHandling:
    """Test cases for empty request parameter handling."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        # Create a simple test image
        image = Image.new('RGB', (100, 50), color='white')
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)
        
        return ("test_image.jpg", image_bytes, "image/jpeg")
    
    def test_sync_processing_with_empty_request(self, client, sample_image_file):
        """Test sync OCR processing with empty request parameter."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_external_process, \
             patch('app.controllers.ocr_controller.ocr_llm_service.process_image_with_llm', new_callable=AsyncMock) as mock_llm_process:
            
            from app.services.external_ocr_service import ImageProcessingResult
            from app.models.ocr_models import OCRLLMResult
            
            # Mock external service returning processed image
            mock_external_process.return_value = ImageProcessingResult(
                success=True,
                processed_image_base64="fake_base64_processed_image",
                processing_time=0.5,
                threshold_used=500,
                contrast_level_used=1.3,
                extracted_text=""
            )
            
            # Mock LLM service returning extracted text
            mock_llm_process.return_value = OCRLLMResult(
                success=True,
                extracted_text="Test extracted text with defaults",
                processing_time=1.0,
                image_processing_time=0.5,
                llm_processing_time=0.5,
                threshold_used=500,  # Default value
                contrast_level_used=1.3,  # Default value
                model_used="test-model",
                prompt_used="test-prompt"
            )
            
            # Send request without request parameter
            response = client.post(
                "/v1/ocr/process-sync",
                files={"file": sample_image_file}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["extracted_text"] == "Test extracted text with defaults"
            assert data["threshold_used"] == 500
            assert data["contrast_level_used"] == 1.3
            
            # Verify the external service was called with default values
            mock_external_process.assert_called_once()
            call_args = mock_external_process.call_args[0]
            ocr_request = call_args[1]
            assert ocr_request.threshold == 500
            assert ocr_request.contrast_level == 1.3
    
    def test_async_processing_with_empty_request(self, client, sample_image_file):
        """Test async OCR processing with empty request parameter."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text with defaults",
                processing_time=1.0,
                threshold_used=500,
                contrast_level_used=1.3
            )
            
            # Send request without request parameter
            response = client.post(
                "/v1/ocr/process",
                files={"file": sample_image_file}
            )
            
            # In test environment, async processing might complete immediately
            # but still return task information
            assert response.status_code == 200
            data = response.json()
            
            # Check if it's a task response format or a direct result
            if "task_id" in data:
                # Task-based response
                assert "status" in data
                assert "created_at" in data
            elif "success" in data:
                # Direct result response  
                assert data["success"] is True
            else:
                # Debug: print what we actually got
                print(f"Unexpected response format: {data}")
                assert False, f"Unexpected response format: {data}"
            
            # Verify the service was called with default values
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            ocr_request = call_args[1]
            assert ocr_request.threshold == 500
            assert ocr_request.contrast_level == 1.3
    
    def test_sync_processing_with_empty_string_request(self, client, sample_image_file):
        """Test sync OCR processing with empty string request parameter."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text with defaults",
                processing_time=1.0,
                threshold_used=500,
                contrast_level_used=1.3
            )
            
            # Send request with empty string request parameter
            response = client.post(
                "/v1/ocr/process-sync",
                files={"file": sample_image_file},
                data={"request": ""}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["threshold_used"] == 500
            assert data["contrast_level_used"] == 1.3
    
    def test_sync_processing_with_partial_request(self, client, sample_image_file):
        """Test sync OCR processing with partial request parameters."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text with partial params",
                processing_time=1.0,
                threshold_used=300,  # Custom value
                contrast_level_used=1.3  # Default value
            )
            
            # Send request with only threshold parameter
            response = client.post(
                "/v1/ocr/process-sync",
                files={"file": sample_image_file},
                data={"request": '{"threshold": 300}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["threshold_used"] == 300  # Custom value
            assert data["contrast_level_used"] == 1.3  # Default value
            
            # Verify the service was called with mixed values
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            ocr_request = call_args[1]
            assert ocr_request.threshold == 300  # Custom
            assert ocr_request.contrast_level == 1.3  # Default
    
    def test_sync_processing_with_custom_request(self, client, sample_image_file):
        """Test sync OCR processing with custom request parameters."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text with custom params",
                processing_time=1.0,
                threshold_used=200,
                contrast_level_used=2.0
            )
            
            # Send request with custom parameters
            response = client.post(
                "/v1/ocr/process-sync",
                files={"file": sample_image_file},
                data={"request": '{"threshold": 200, "contrast_level": 2.0}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["threshold_used"] == 200
            assert data["contrast_level_used"] == 2.0
            
            # Verify the service was called with custom values
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            ocr_request = call_args[1]
            assert ocr_request.threshold == 200
            assert ocr_request.contrast_level == 2.0
    
    def test_default_values_in_ocr_request_model(self):
        """Test that OCRRequest model has correct default values."""
        from app.models.ocr_models import OCRRequest
        
        # Create OCRRequest without parameters
        ocr_request = OCRRequest()
        
        assert ocr_request.threshold == 500
        assert ocr_request.contrast_level == 1.3
    
    def test_get_ocr_parameters_shows_correct_defaults(self, client):
        """Test that the parameters endpoint shows correct default values."""
        response = client.get("/v1/ocr/parameters")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check image processing defaults
        assert data["image_processing"]["threshold"]["default"] == 500
        assert data["image_processing"]["threshold"]["max"] == 1024
        assert data["image_processing"]["contrast_level"]["default"] == 1.3
        assert "500 for general use" in data["image_processing"]["threshold"]["recommended"]
        assert "1.3 for enhanced contrast" in data["image_processing"]["contrast_level"]["recommended"]
        
        # Check PDF processing defaults
        assert data["pdf_processing"]["threshold"]["default"] == 500
        assert data["pdf_processing"]["dpi"]["default"] == 300
        assert data["pdf_processing"]["max_pages"] == 10 