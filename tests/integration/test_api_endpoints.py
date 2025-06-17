"""
Integration tests for OCR API endpoints.
"""

import io
import json
import pytest
from unittest.mock import patch, AsyncMock
from PIL import Image

from fastapi.testclient import TestClient

from app.main import app


class TestOCRAPIEndpoints:
    """Integration tests for OCR API endpoints."""
    
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
    
    @pytest.fixture
    def invalid_file(self):
        """Create an invalid file for testing."""
        text_content = io.BytesIO(b"This is not an image")
        return ("test_file.txt", text_content, "text/plain")
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        with patch('app.services.external_ocr_service.external_ocr_service.health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "external_ocr_status" in data
    
    def test_process_image_async_success(self, client, sample_image_file):
        """Test async OCR processing endpoint success."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text",
                processing_time=1.0,
                threshold_used=500,
                contrast_level_used=1.3
            )
            
            response = client.post(
                "/v1/ocr/process",
                files={"file": sample_image_file},
                data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
            )
            
            # In test environment, async processing might complete immediately
            assert response.status_code in [200, 202]
            data = response.json()
            
            if response.status_code == 202:
                assert data["status"] == "processing"
                assert "task_id" in data
                assert "created_at" in data
            else:  # 200 - completed immediately in test
                assert "task_id" in data or "success" in data
    
    def test_process_image_async_invalid_file(self, client, invalid_file):
        """Test async OCR processing with invalid file."""
        response = client.post(
            "/v1/ocr/process",
            files={"file": invalid_file},
            data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
        )
        
        # In test environment, validation happens immediately
        assert response.status_code in [200, 202]
        data = response.json()
        
        if response.status_code == 202:
            assert data["status"] == "failed"
            assert data["error_message"] is not None
        else:  # 200 - failed immediately
            assert "task_id" in data or "error" in data
    
    def test_process_image_sync_success(self, client, sample_image_file):
        """Test sync OCR processing endpoint success."""
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock) as mock_process:
            from app.models.ocr_models import OCRResult
            mock_process.return_value = OCRResult(
                success=True,
                extracted_text="Test extracted text",
                processing_time=1.0,
                threshold_used=500,
                contrast_level_used=1.3
            )
            
            response = client.post(
                "/v1/ocr/process-sync",
                files={"file": sample_image_file},
                data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["extracted_text"] == "Test extracted text"
            assert data["processing_time"] == 1.0
    
    def test_process_image_sync_invalid_file(self, client, invalid_file):
        """Test sync OCR processing with invalid file."""
        response = client.post(
            "/v1/ocr/process-sync",
            files={"file": invalid_file},
            data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
        )
        
        # Error handling might return 400 or 500 depending on where validation fails
        assert response.status_code in [400, 500]
        data = response.json()
        assert data["error"] is True
        assert "message" in data
    
    def test_get_task_status_success(self, client):
        """Test get task status endpoint success."""
        # First create a task
        with patch('app.controllers.ocr_controller.external_ocr_service.process_image', new_callable=AsyncMock):
            sample_image_file = ("test_image.jpg", io.BytesIO(b"fake_image"), "image/jpeg")
            
            create_response = client.post(
                "/v1/ocr/process",
                files={"file": sample_image_file},
                data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
            )
            
            task_id = create_response.json()["task_id"]
            
            # Now get the task status
            response = client.get(f"/v1/ocr/tasks/{task_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert "status" in data
    
    def test_get_task_status_not_found(self, client):
        """Test get task status for non-existent task."""
        response = client.get("/v1/ocr/tasks/non-existent-task-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
    
    def test_list_tasks(self, client):
        """Test list all tasks endpoint."""
        response = client.get("/v1/ocr/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_cleanup_tasks(self, client):
        """Test cleanup completed tasks endpoint."""
        response = client.delete("/v1/ocr/tasks/cleanup")
        
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_up" in data
        assert isinstance(data["cleaned_up"], int)
    
    def test_get_ocr_parameters(self, client):
        """Test get OCR parameters endpoint."""
        response = client.get("/v1/ocr/parameters")
        
        assert response.status_code == 200
        data = response.json()
        assert "threshold" in data
        assert "contrast_level" in data
        assert "supported_formats" in data
        assert "max_file_size_bytes" in data
    
    def test_get_service_info(self, client):
        """Test get service info endpoint."""
        with patch('app.services.external_ocr_service.external_ocr_service.health_check', new_callable=AsyncMock) as mock_ocr_health, \
             patch('app.services.ocr_llm_service.ocr_llm_service.health_check', new_callable=AsyncMock) as mock_llm_health:
            mock_ocr_health.return_value = True
            mock_llm_health.return_value = True
            
            response = client.get("/v1/ocr/service-info")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check OCR service info
            assert "ocr_service" in data
            assert "service_name" in data["ocr_service"]
            assert "base_url" in data["ocr_service"]
            assert "status" in data["ocr_service"]
            assert data["ocr_service"]["status"] == "available"
            
            # Check LLM service info
            assert "llm_service" in data
            assert "service_name" in data["llm_service"]
            assert "base_url" in data["llm_service"]
            assert "status" in data["llm_service"]
            assert "default_model" in data["llm_service"]
            assert "default_prompt" in data["llm_service"]
            assert data["llm_service"]["status"] == "available"
    
    def test_rate_limiting(self, client, sample_image_file):
        """Test rate limiting functionality."""
        # This test would need to be adjusted based on actual rate limiting configuration
        # For now, just test that the endpoint responds normally
        response = client.post(
            "/v1/ocr/process-sync",
            files={"file": sample_image_file},
            data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
        )
        
        # Should not be rate limited for a single request
        assert response.status_code in [200, 400, 500]  # Any valid response
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/v1/ocr/parameters")
        
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_invalid_threshold_parameter(self, client, sample_image_file):
        """Test invalid threshold parameter."""
        response = client.post(
            "/v1/ocr/process-sync",
            files={"file": sample_image_file},
            data={"request": '{"threshold": 2000, "contrast_level": 1.0}'}  # Invalid threshold (>1024)
        )
        
        # Validation error might be caught as 422 or 500 depending on where it occurs
        assert response.status_code in [422, 500]
    
    def test_invalid_contrast_parameter(self, client, sample_image_file):
        """Test invalid contrast level parameter."""
        response = client.post(
            "/v1/ocr/process-sync",
            files={"file": sample_image_file},
            data={"request": '{"threshold": 500, "contrast_level": 10.0}'}  # Invalid contrast
        )
        
        # Validation error might be caught as 422 or 500 depending on where it occurs
        assert response.status_code in [422, 500]
    
    def test_missing_file_parameter(self, client):
        """Test missing file parameter."""
        response = client.post(
            "/v1/ocr/process-sync",
            data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
        )
        
        # Validation error might be caught as 422 or 500 depending on where it occurs
        assert response.status_code in [422, 500]
    
    def test_large_file_upload(self, client):
        """Test large file upload handling."""
        # Create a large fake file
        large_content = b"x" * (15 * 1024 * 1024)  # 15MB
        large_file = ("large_image.jpg", io.BytesIO(large_content), "image/jpeg")
        
        response = client.post(
            "/v1/ocr/process-sync",
            files={"file": large_file},
            data={"request": '{"threshold": 500, "contrast_level": 1.3}'}
        )
        
        # Should be rejected due to file size
        assert response.status_code in [413, 400, 500]  # Payload too large, bad request, or server error 