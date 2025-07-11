"""
Simple integration tests for remote deployment without external dependencies.
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


class TestRemoteSimpleIntegration:
    """Simple integration tests for remote deployment."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        # Create a white image with some patterns
        image = Image.new('RGB', (800, 600), color='white')
        
        # Add some simple patterns that might be recognized as text
        pixels = image.load()
        
        # Draw some simple rectangles (simulating text blocks)
        for y in range(100, 150):
            for x in range(100, 400):
                pixels[x, y] = (0, 0, 0)  # Black rectangle
        
        for y in range(200, 250):
            for x in range(100, 500):
                pixels[x, y] = (0, 0, 0)  # Another black rectangle
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        print(f"\nTesting health check at: {client.base_url}")
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        
        print(f"✓ Health check passed: {data}")
    
    def test_image_basic_ocr(self, client, sample_image):
        """Test basic image OCR processing."""
        print(f"\nTesting image OCR at: {client.base_url}")
        
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
        data = response.json()
        assert "task_id" in data
        
        task_id = data["task_id"]
        print(f"✓ Created image OCR task: {task_id}")
        
        # Check task status
        status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert "status" in status_data
        print(f"✓ Task status: {status_data['status']}")
        
        # Wait a bit and check again if still processing
        if status_data['status'] == 'processing':
            import time
            time.sleep(3)
            
            status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
            status_data = status_response.json()
            print(f"✓ Updated task status: {status_data['status']}")
    
    def test_image_llm_enhanced_ocr(self, client, sample_image):
        """Test LLM-enhanced image OCR processing."""
        print(f"\nTesting LLM-enhanced OCR at: {client.base_url}")
        
        request_data = {
            "mode": "llm_enhanced",
            "threshold": 128,
            "contrast_level": 1.0,
            "prompt": "Extract any text you can find in this image"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        task_id = data["task_id"]
        print(f"✓ Created LLM-enhanced OCR task: {task_id}")
        
        # Check task status
        status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        print(f"✓ Task status: {status_data['status']}")
    
    def test_url_processing(self, client):
        """Test URL-based processing."""
        print(f"\nTesting URL processing at: {client.base_url}")
        
        # Use a publicly available test image
        request_data = {
            "url": "https://httpbin.org/image/jpeg",  # Simple test image
            "mode": "basic"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            data={"request": json.dumps(request_data)}
        )
        
        print(f"URL processing response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            print(f"✓ Created URL processing task: {data['task_id']}")
        else:
            # This might fail if URL is not accessible from your deployment
            print(f"URL processing failed (expected): {response.text}")
    
    def test_invalid_file_handling(self, client):
        """Test error handling with invalid files."""
        print(f"\nTesting error handling at: {client.base_url}")
        
        # Create invalid file content
        invalid_content = io.BytesIO(b"This is not an image file")
        
        request_data = {
            "mode": "basic"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.txt", invalid_content, "text/plain")},
            data={"request": json.dumps(request_data)}
        )
        
        print(f"Invalid file response: {response.status_code}")
        
        # Should return an error (400 or 422)
        if response.status_code in [400, 422]:
            print("✓ Correctly rejected invalid file")
        elif response.status_code == 200:
            # Task created but might fail during processing
            task_id = response.json()["task_id"]
            print(f"Task created, checking if it fails: {task_id}")
            
            import time
            time.sleep(2)
            
            status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
            status_data = status_response.json()
            
            if status_data['status'] == 'failed':
                print(f"✓ Task correctly failed: {status_data.get('error', 'Unknown error')}")
    
    def test_task_cancellation(self, client, sample_image):
        """Test task cancellation."""
        print(f"\nTesting task cancellation at: {client.base_url}")
        
        # Create a task
        request_data = {
            "mode": "basic"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"Created task: {task_id}")
        
        # Try to cancel it immediately
        cancel_response = client.post(f"/v1/ocr/tasks/{task_id}/cancel")
        print(f"Cancel response: {cancel_response.status_code}")
        
        if cancel_response.status_code == 200:
            print("✓ Task cancellation request accepted")
            
            # Check if task is actually cancelled
            status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
            status_data = status_response.json()
            print(f"Task status after cancellation: {status_data['status']}")
        else:
            print(f"Cancel response: {cancel_response.text}")
    
    @pytest.mark.asyncio
    async def test_streaming_basic(self, sample_image):
        """Test basic streaming functionality."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set")
        
        client = RemoteTestClient()
        async_client = AsyncRemoteTestClient()
        
        print(f"\nTesting streaming at: {client.base_url}")
        
        # Create a task first
        request_data = {
            "mode": "basic"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.jpg", sample_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        if response.status_code != 200:
            print(f"Failed to create task: {response.text}")
            return
        
        task_id = response.json()["task_id"]
        print(f"Created task for streaming: {task_id}")
        
        # Try to stream updates
        updates_received = 0
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        updates_received += 1
                        print(f"Update {updates_received}: {data.get('status', 'unknown')}")
                        
                        if data.get("status") in ["completed", "failed"]:
                            break
                        
                        # Limit for testing
                        if updates_received > 10:
                            break
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"Error parsing update: {e}")
        except Exception as e:
            print(f"Streaming error: {e}")
        
        print(f"✓ Received {updates_received} streaming updates")


if __name__ == "__main__":
    # Quick test when run directly
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])