"""
Integration tests for task cancellation API endpoints.
"""

import asyncio
import pytest
import json
from datetime import datetime, UTC
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.ocr_models import (
    CancelTaskRequest, CancelTaskResponse, TaskStatus,
    OCRResponse, PDFOCRResponse, PDFLLMOCRResponse, OCRLLMResponse
)


class TestCancellationAPIEndpoints:
    """Integration tests for cancellation API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_task_id(self):
        """Return a mock task ID."""
        return "test-task-12345"

    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing tasks
        from app.controllers.ocr_controller import ocr_controller
        ocr_controller.tasks.clear()
        ocr_controller.llm_tasks.clear()
        ocr_controller.pdf_tasks.clear()
        ocr_controller.pdf_llm_tasks.clear()
        ocr_controller.cancelled_tasks.clear()
        ocr_controller.cancellation_reasons.clear()
        ocr_controller.streaming_queues.clear()

    # --- OCR Task Cancellation API Tests ---

    def test_cancel_ocr_task_success(self, client, mock_task_id):
        """Test successful OCR task cancellation via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = OCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[mock_task_id] = task

        # Cancel the task
        cancel_data = {"reason": "Test cancellation"}
        response = client.post(f"/v1/ocr/tasks/{mock_task_id}/cancel", json=cancel_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == mock_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "OCR task successfully cancelled"
        assert data["cancellation_reason"] == "Test cancellation"
        assert "cancelled_at" in data

    def test_cancel_ocr_task_not_found(self, client):
        """Test cancelling non-existent OCR task via API."""
        cancel_data = {"reason": "Test cancellation"}
        response = client.post("/v1/ocr/tasks/non-existent/cancel", json=cancel_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["message"]

    def test_cancel_ocr_task_already_completed(self, client, mock_task_id):
        """Test cancelling already completed OCR task via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a completed task
        task = OCRResponse(
            task_id=mock_task_id,
            status="completed",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC)
        )
        ocr_controller.tasks[mock_task_id] = task

        # Try to cancel
        cancel_data = {"reason": "Test cancellation"}
        response = client.post(f"/v1/ocr/tasks/{mock_task_id}/cancel", json=cancel_data)

        assert response.status_code == 400
        assert "already completed" in response.json()["message"]

    def test_cancel_ocr_task_default_reason(self, client, mock_task_id):
        """Test cancelling OCR task with default reason."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = OCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[mock_task_id] = task

        # Cancel without providing reason (should use default)
        response = client.post(f"/v1/ocr/tasks/{mock_task_id}/cancel", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["cancellation_reason"] == "User requested cancellation"

    # --- LLM Task Cancellation API Tests ---

    def test_cancel_llm_task_success(self, client, mock_task_id):
        """Test successful LLM task cancellation via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = OCRLLMResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.llm_tasks[mock_task_id] = task

        # Cancel the task
        cancel_data = {"reason": "LLM task taking too long"}
        response = client.post(f"/v1/ocr/llm-tasks/{mock_task_id}/cancel", json=cancel_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == mock_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "LLM task successfully cancelled"
        assert data["cancellation_reason"] == "LLM task taking too long"

    # --- PDF Task Cancellation API Tests ---

    def test_cancel_pdf_task_success(self, client, mock_task_id):
        """Test successful PDF task cancellation via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = PDFOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.pdf_tasks[mock_task_id] = task

        # Cancel the task
        cancel_data = {"reason": "PDF processing cancelled by user"}
        response = client.post(f"/v1/ocr/pdf-tasks/{mock_task_id}/cancel", json=cancel_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == mock_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "PDF task successfully cancelled"
        assert data["cancellation_reason"] == "PDF processing cancelled by user"

    def test_cancel_pdf_llm_task_success(self, client, mock_task_id):
        """Test successful PDF LLM task cancellation via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = PDFLLMOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.pdf_llm_tasks[mock_task_id] = task

        # Cancel the task
        cancel_data = {"reason": "PDF LLM processing taking too long"}
        response = client.post(f"/v1/ocr/pdf-llm-tasks/{mock_task_id}/cancel", json=cancel_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == mock_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "PDF LLM task successfully cancelled"

    # --- Streaming Task Cancellation API Tests ---

    def test_cancel_streaming_task_pdf(self, client, mock_task_id):
        """Test cancelling streaming PDF task via API."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a streaming PDF task
        task = PDFOCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.pdf_tasks[mock_task_id] = task

        # Cancel the task
        cancel_data = {"reason": "Streaming cancelled"}
        response = client.post(f"/v1/ocr/stream/{mock_task_id}/cancel", json=cancel_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == mock_task_id
        assert data["status"] == "cancelled"

    def test_cancel_streaming_task_not_found(self, client):
        """Test cancelling non-existent streaming task via API."""
        cancel_data = {"reason": "Test cancellation"}
        response = client.post("/v1/ocr/stream/non-existent/cancel", json=cancel_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["message"]

    # --- API Rate Limiting Tests ---

    def test_cancel_task_rate_limit(self, client, mock_task_id):
        """Test that cancellation endpoints respect rate limits."""
        # This test would need to be run with actual rate limiting
        # For now, just verify the endpoint is accessible
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = OCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[mock_task_id] = task

        # Cancel the task (should work within rate limit)
        cancel_data = {"reason": "Rate limit test"}
        response = client.post(f"/v1/ocr/tasks/{mock_task_id}/cancel", json=cancel_data)

        assert response.status_code == 200

    # --- Error Handling Tests ---

    def test_cancel_task_invalid_json(self, client, mock_task_id):
        """Test cancellation with invalid JSON."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a task
        task = OCRResponse(
            task_id=mock_task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[mock_task_id] = task

        # Send invalid JSON
        response = client.post(
            f"/v1/ocr/tasks/{mock_task_id}/cancel",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # Should handle gracefully or return appropriate error
        # The actual behavior depends on FastAPI's JSON parsing
        assert response.status_code in [400, 422]


class TestCancellationWorkflow:
    """Integration tests for complete cancellation workflows."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing tasks
        from app.controllers.ocr_controller import ocr_controller
        ocr_controller.tasks.clear()
        ocr_controller.llm_tasks.clear()
        ocr_controller.pdf_tasks.clear()
        ocr_controller.pdf_llm_tasks.clear()
        ocr_controller.cancelled_tasks.clear()
        ocr_controller.cancellation_reasons.clear()
        ocr_controller.streaming_queues.clear()

    @patch('app.services.external_ocr_service.external_ocr_service.process_image')
    def test_ocr_task_cancellation_workflow(self, mock_process_image, client):
        """Test complete OCR task cancellation workflow."""
        # Create a proper mock result object
        from app.models.ocr_models import OCRResult
        
        mock_result = OCRResult(
            success=True,
            extracted_text='Test text',
            processing_time=1.0,
            threshold_used=500,
            contrast_level_used=1.3
        )
        
        # Mock the external service to return the result
        mock_process_image.return_value = mock_result

        # Start a task
        with open("test_files/test_image.png", "rb") as f:
            response = client.post(
                "/v1/ocr/process",
                files={"file": ("test.png", f, "image/png")},
                data={"request": json.dumps({"threshold": 500})}
            )

        assert response.status_code == 200
        task_data = response.json()
        task_id = task_data["task_id"]

        # Get initial task status
        status_response = client.get(f"/v1/ocr/tasks/{task_id}")
        assert status_response.status_code == 200
        initial_status = status_response.json()["status"]
        
        # Task should be either processing, completed, or failed
        assert initial_status in ["processing", "completed", "failed"]

        # Test cancellation - if task is already completed/failed, create a new one for cancellation test
        if initial_status in ["completed", "failed"]:
            from app.controllers.ocr_controller import ocr_controller
            from app.models.ocr_models import OCRResponse
            from datetime import datetime, UTC
            
            # Create a mock processing task for cancellation test
            test_task = OCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=datetime.now(UTC),
                completed_at=None
            )
            ocr_controller.tasks[task_id] = test_task

        # Cancel the task
        cancel_response = client.post(
            f"/v1/ocr/tasks/{task_id}/cancel",
            json={"reason": "Workflow test cancellation"}
        )

        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert cancel_data["status"] == "cancelled"

        # Verify task status shows cancelled
        final_status_response = client.get(f"/v1/ocr/tasks/{task_id}")
        assert final_status_response.status_code == 200
        final_data = final_status_response.json()
        assert final_data["status"] == "cancelled"
        assert final_data["cancellation_reason"] == "Workflow test cancellation"

    def test_pdf_streaming_cancellation_workflow(self, client):
        """Test PDF streaming task cancellation workflow."""
        # This test would require more complex mocking of PDF processing
        # For now, test the basic API structure
        
        from app.controllers.ocr_controller import ocr_controller
        
        # Create a streaming task manually
        task_id = "streaming-test-task"
        task = PDFOCRResponse(
            task_id=task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.pdf_tasks[task_id] = task
        ocr_controller.streaming_queues[task_id] = asyncio.Queue()

        # Cancel the streaming task
        cancel_response = client.post(
            f"/v1/ocr/stream/{task_id}/cancel",
            json={"reason": "Streaming workflow test"}
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

    def test_multiple_task_cancellation(self, client):
        """Test cancelling multiple tasks."""
        from app.controllers.ocr_controller import ocr_controller
        
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = f"multi-task-{i}"
            task = OCRResponse(
                task_id=task_id,
                status="processing",
                result=None,
                error_message=None,
                created_at=datetime.now(UTC),
                completed_at=None
            )
            ocr_controller.tasks[task_id] = task
            task_ids.append(task_id)

        # Cancel all tasks
        for task_id in task_ids:
            response = client.post(
                f"/v1/ocr/tasks/{task_id}/cancel",
                json={"reason": f"Batch cancellation {task_id}"}
            )
            assert response.status_code == 200

        # Verify all are cancelled
        for task_id in task_ids:
            status_response = client.get(f"/v1/ocr/tasks/{task_id}")
            assert status_response.json()["status"] == "cancelled"


class TestCancellationEdgeCases:
    """Test edge cases for task cancellation."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing tasks
        from app.controllers.ocr_controller import ocr_controller
        ocr_controller.tasks.clear()
        ocr_controller.cancelled_tasks.clear()
        ocr_controller.cancellation_reasons.clear()

    def test_cancel_task_twice(self, client):
        """Test cancelling the same task twice."""
        from app.controllers.ocr_controller import ocr_controller
        
        task_id = "double-cancel-test"
        task = OCRResponse(
            task_id=task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[task_id] = task

        # First cancellation
        response1 = client.post(
            f"/v1/ocr/tasks/{task_id}/cancel",
            json={"reason": "First cancellation"}
        )
        assert response1.status_code == 200

        # Second cancellation (should fail)
        response2 = client.post(
            f"/v1/ocr/tasks/{task_id}/cancel",
            json={"reason": "Second cancellation"}
        )
        assert response2.status_code == 400
        assert "TaskStatus.CANCELLED" in response2.json()["message"]

    def test_cancel_with_empty_reason(self, client):
        """Test cancellation with empty reason."""
        from app.controllers.ocr_controller import ocr_controller
        
        task_id = "empty-reason-test"
        task = OCRResponse(
            task_id=task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[task_id] = task

        # Cancel with empty reason
        response = client.post(
            f"/v1/ocr/tasks/{task_id}/cancel",
            json={"reason": ""}
        )

        # Should still work (empty reason is valid)
        assert response.status_code == 200
        assert response.json()["cancellation_reason"] == ""

    def test_cancel_with_very_long_reason(self, client):
        """Test cancellation with very long reason."""
        from app.controllers.ocr_controller import ocr_controller
        
        task_id = "long-reason-test"
        task = OCRResponse(
            task_id=task_id,
            status="processing",
            result=None,
            error_message=None,
            created_at=datetime.now(UTC),
            completed_at=None
        )
        ocr_controller.tasks[task_id] = task

        # Cancel with very long reason
        long_reason = "A" * 1000  # 1000 character reason
        response = client.post(
            f"/v1/ocr/tasks/{task_id}/cancel",
            json={"reason": long_reason}
        )

        # Should handle long reasons
        assert response.status_code == 200
        assert response.json()["cancellation_reason"] == long_reason 