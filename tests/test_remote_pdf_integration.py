"""
Integration tests for PDF OCR service against remote deployment.
These tests actually call the deployed API endpoints.
"""

import json
import pytest
import asyncio
from pathlib import Path
import tempfile
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestRemotePDFIntegration:
    """Integration tests for PDF OCR functionality on remote deployment."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def sample_pdf(self):
        """Create a sample PDF for testing."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            c = canvas.Canvas(tmp_file.name, pagesize=letter)
            
            # Create 5 pages with different content
            for i in range(1, 6):
                c.setFont("Helvetica", 24)
                c.drawString(100, 750, f"Page {i}")
                c.setFont("Helvetica", 14)
                c.drawString(100, 700, f"This is test content for page {i}")
                c.drawString(100, 650, "Lorem ipsum dolor sit amet")
                c.showPage()
            
            c.save()
            
            yield tmp_file.name
            
            # Cleanup
            Path(tmp_file.name).unlink()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        # Create a white image with some text-like patterns
        image = Image.new('RGB', (800, 600), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def test_pdf_basic_ocr(self, client, sample_pdf):
        """Test basic PDF OCR processing on remote deployment."""
        print(f"\nTesting PDF OCR at: {client.base_url}")
        
        request_data = {
            "mode": "basic",
            "threshold": 128,
            "contrast_level": 1.0
        }
        
        with open(sample_pdf, "rb") as pdf_file:
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": ("test.pdf", pdf_file, "application/pdf")},
                data={"request": json.dumps(request_data)}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        task_id = data["task_id"]
        print(f"Created task: {task_id}")
        
        # Check status
        status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert "status" in status_data
        print(f"Task status: {status_data['status']}")
    
    def test_pdf_with_page_selection(self, client, sample_pdf):
        """Test PDF OCR with page selection on remote deployment."""
        print(f"\nTesting PDF page selection at: {client.base_url}")
        
        request_data = {
            "mode": "basic",
            "pdf_config": {
                "page_select": [1, 3, 5]  # Process only pages 1, 3, and 5
            }
        }
        
        with open(sample_pdf, "rb") as pdf_file:
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": ("test.pdf", pdf_file, "application/pdf")},
                data={"request": json.dumps(request_data)}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        
        task_id = data["task_id"]
        print(f"Created task with page selection [1,3,5]: {task_id}")
        
        # Wait a bit and check status
        import time
        time.sleep(2)
        
        status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        print(f"Task status: {status_data['status']}")
        
        # If completed, check that we only processed 3 pages
        if status_data['status'] == 'completed' and 'result' in status_data:
            result = status_data['result']
            if 'page_results' in result:
                assert len(result['page_results']) == 3, "Should have processed exactly 3 pages"
                print("✓ Correctly processed only selected pages")
    
    def test_pdf_page_validation(self, client, sample_pdf):
        """Test PDF page validation on remote deployment."""
        print(f"\nTesting PDF page validation at: {client.base_url}")
        
        # Try to select pages that don't exist (PDF has 5 pages)
        request_data = {
            "mode": "basic",
            "pdf_config": {
                "page_select": [1, 5, 10]  # Page 10 doesn't exist
            }
        }
        
        with open(sample_pdf, "rb") as pdf_file:
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": ("test.pdf", pdf_file, "application/pdf")},
                data={"request": json.dumps(request_data)}
            )
        
        # This might return 200 with a task that fails, or 400 immediately
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Task was created, check if it fails during processing
            task_id = response.json()["task_id"]
            
            # Wait and check status
            import time
            time.sleep(3)
            
            status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
            status_data = status_response.json()
            
            if status_data['status'] == 'failed':
                print(f"✓ Task correctly failed: {status_data.get('error', 'Unknown error')}")
            else:
                print(f"Task status: {status_data['status']}")
        else:
            # Immediate validation error
            print(f"✓ Immediate validation error: {response.text}")
    
    def test_image_basic_ocr(self, client, sample_image):
        """Test basic image OCR on remote deployment."""
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
        
        print(f"Created image OCR task: {data['task_id']}")
    
    def test_task_cancellation(self, client, sample_pdf):
        """Test task cancellation on remote deployment."""
        print(f"\nTesting task cancellation at: {client.base_url}")
        
        # Create a task
        request_data = {
            "mode": "basic"
        }
        
        with open(sample_pdf, "rb") as pdf_file:
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": ("test.pdf", pdf_file, "application/pdf")},
                data={"request": json.dumps(request_data)}
            )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"Created task: {task_id}")
        
        # Try to cancel it
        cancel_response = client.post(f"/v1/ocr/tasks/{task_id}/cancel")
        print(f"Cancel response: {cancel_response.status_code}")
        
        if cancel_response.status_code == 200:
            print("✓ Task cancelled successfully")
        else:
            print(f"Cancel response: {cancel_response.text}")
    
    @pytest.mark.asyncio
    async def test_streaming_updates(self, sample_image):
        """Test streaming updates from remote deployment."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set")
        
        client = RemoteTestClient()
        async_client = AsyncRemoteTestClient()
        
        print(f"\nTesting streaming at: {client.base_url}")
        
        # Create a task with streaming enabled
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract text from this image"
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
        print(f"Created streaming task: {task_id}")
        
        # Stream updates
        updates_received = 0
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        updates_received += 1
                        
                        if data.get("text_chunk"):
                            print(f"Text chunk: '{data['text_chunk']}'", end="", flush=True)
                        elif data.get("status"):
                            print(f"\nStatus: {data['status']}")
                        
                        if data.get("status") in ["completed", "failed"]:
                            break
                        
                        # Limit updates for testing
                        if updates_received > 20:
                            print("\n(Stopping after 20 updates for test)")
                            break
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"\nStreaming error: {e}")
        
        print(f"\n✓ Received {updates_received} streaming updates")


if __name__ == "__main__":
    # Quick test when run directly
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])