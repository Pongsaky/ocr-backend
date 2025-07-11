"""
Example tests for testing against remote deployed instances.

Usage:
    # Test against local instance (default)
    pytest tests/test_remote_deployment.py
    
    # Test against remote deployed instance
    export REMOTE_API_URL="https://your-deployed-api.com"
    pytest tests/test_remote_deployment.py
    
    # With authentication
    export REMOTE_API_URL="https://your-deployed-api.com"
    export REMOTE_API_KEY="your-api-key"
    pytest tests/test_remote_deployment.py
"""

import json
import pytest
import asyncio
from pathlib import Path
import tempfile
from PIL import Image
import io

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestRemoteDeployment:
    """Test suite for remote deployment testing."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        return RemoteTestClient()
    
    @pytest.fixture
    def async_client(self):
        """Create an async remote test client."""
        return AsyncRemoteTestClient()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        image = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        
        # Log where we tested
        print(f"\nTested health check at: {client.base_url}")
    
    def test_ocr_process_stream_basic(self, client, sample_image):
        """Test basic OCR processing with streaming."""
        # Prepare request data
        request_data = {
            "mode": "basic",
            "threshold": 128,
            "contrast_level": 1.0
        }
        
        # Upload file with request data
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a task ID
        assert "task_id" in data
        task_id = data["task_id"]
        
        print(f"\nCreated OCR task: {task_id} at {client.base_url}")
        
        # Check task status
        status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert "status" in status_data
        assert status_data["status"] in ["processing", "completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_ocr_streaming_updates(self, async_client, sample_image):
        """Test streaming updates from OCR processing."""
        # First create a task
        client = RemoteTestClient()  # Use sync client for task creation
        
        request_data = {
            "mode": "basic",
            "threshold": 128,
            "contrast_level": 1.0
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        print(f"\nStreaming updates for task: {task_id}")
        
        # Stream updates
        updates_received = []
        async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
            if update:
                try:
                    data = json.loads(update)
                    updates_received.append(data)
                    print(f"Update: {data.get('status')} - {data.get('message', '')}")
                    
                    # Stop after receiving completion
                    if data.get("status") in ["completed", "failed"]:
                        break
                except json.JSONDecodeError:
                    pass
        
        # Should have received at least one update
        assert len(updates_received) > 0
    
    def test_pdf_processing_with_page_selection(self, client):
        """Test PDF processing with page selection."""
        # Create a simple PDF for testing
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            c = canvas.Canvas(tmp_file.name, pagesize=letter)
            
            # Create 3 pages
            for i in range(1, 4):
                c.drawString(100, 750, f"Page {i} - Test Content")
                c.showPage()
            
            c.save()
            
            # Test with page selection
            request_data = {
                "mode": "basic",
                "pdf_config": {
                    "page_select": [1, 3]  # Only process pages 1 and 3
                }
            }
            
            with open(tmp_file.name, "rb") as pdf_file:
                response = client.post(
                    "/v1/ocr/process-stream",
                    files={"file": ("test.pdf", pdf_file, "application/pdf")},
                    data={"request": json.dumps(request_data)}
                )
            
            # Clean up
            Path(tmp_file.name).unlink()
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        print(f"\nCreated PDF task with page selection: {data['task_id']}")
    
    def test_url_processing(self, client):
        """Test URL-based OCR processing."""
        request_data = {
            "url": "https://example.com/sample-image.jpg",  # This would be a real image URL in production
            "mode": "basic"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            data={"request": json.dumps(request_data)}
        )
        
        # Note: This might fail if the URL doesn't exist or isn't accessible
        # In real tests, you'd use a known good URL or mock the download
        print(f"\nURL processing response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
    
    def test_error_handling(self, client):
        """Test error handling with invalid requests."""
        # Test with invalid file type
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.txt", b"Not an image", "text/plain")},
            data={"request": json.dumps({"mode": "basic"})}
        )
        
        # Should return an error
        assert response.status_code in [400, 422]
        
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data
        
        print(f"\nError handling test passed at: {client.base_url}")
    
    @pytest.mark.parametrize("mode", ["basic", "llm_enhanced"])
    def test_different_ocr_modes(self, client, sample_image, mode):
        """Test different OCR processing modes."""
        request_data = {
            "mode": mode,
            "threshold": 128,
            "contrast_level": 1.0
        }
        
        if mode == "llm_enhanced":
            request_data["prompt"] = "Extract all text from this image"
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        print(f"\nTested {mode} mode: {data['task_id']}")


class TestRemoteConfiguration:
    """Test the remote configuration itself."""
    
    def test_configuration_values(self):
        """Test that configuration values are properly set."""
        config = RemoteTestConfig()
        
        print(f"\nRemote Test Configuration:")
        print(f"  Base URL: {config.get_base_url()}")
        print(f"  Is Remote: {config.is_remote_testing()}")
        print(f"  Timeout: {config.get_timeout()}s")
        print(f"  Headers: {config.get_headers()}")
        
        # If testing remotely, ensure URL is set
        if config.is_remote_testing():
            assert config.get_remote_url() is not None
            assert config.get_base_url() != "http://localhost:8000"