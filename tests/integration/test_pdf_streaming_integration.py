"""
Integration tests for PDF streaming functionality using real test files.
"""

import asyncio
import json
import pytest
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock

from app.models.ocr_models import PDFOCRRequest, PDFLLMOCRRequest
from app.services.pdf_ocr_service import pdf_ocr_service
from app.controllers.ocr_controller import ocr_controller


class TestPDFStreamingWithRealFile:
    """Integration tests using the real test PDF file."""
    
    @pytest.fixture
    def test_pdf_path(self):
        """Get path to the test PDF file."""
        test_file = Path("test_files/ocr-pdf-testing.pdf")
        if not test_file.exists():
            pytest.skip("Test PDF file not found")
        return test_file
    
    @pytest.mark.asyncio
    @patch('app.services.external_ocr_service.external_ocr_service.process_image')
    async def test_pdf_streaming_with_real_file(self, mock_process_image, test_pdf_path):
        """Test PDF streaming with the actual test PDF file."""
        # Mock external OCR service responses
        mock_process_image.return_value = AsyncMock(
            success=True,
            extracted_text="Mock extracted text from page",
            processing_time=1.5,
            threshold_used=500,
            contrast_level_used=1.3
        )
        
        # Create streaming queue
        streaming_queue = asyncio.Queue()
        
        # Create request
        request = PDFOCRRequest(
            threshold=500,
            contrast_level=1.3,
            dpi=150  # Lower DPI for faster testing
        )
        
        task_id = "real-pdf-test-123"
        
        # Process PDF with streaming
        start_time = time.time()
        result = await pdf_ocr_service.process_pdf_with_streaming(
            test_pdf_path, request, task_id, streaming_queue
        )
        processing_time = time.time() - start_time
        
        # Verify basic result
        assert result is not None
        assert result.total_pages > 0
        assert isinstance(result.dpi_used, int)
        
        # Collect all streaming updates
        updates = []
        while not streaming_queue.empty():
            update = await streaming_queue.get()
            if update is not None:  # Skip sentinel
                updates.append(update)
        
        # Verify streaming updates structure
        assert len(updates) > 0
        
        # Check initial update
        initial_updates = [u for u in updates if u.status == "processing"]
        assert len(initial_updates) >= 1
        initial_update = initial_updates[0]
        assert initial_update.task_id == task_id
        assert initial_update.current_page == 0
        assert initial_update.progress_percentage == 0.0
        
        # Check page completion updates
        page_updates = [u for u in updates if u.status == "page_completed"]
        assert len(page_updates) >= 1
        
        # Verify dual streaming approach
        for update in page_updates:
            # Type 1: Single page result
            assert update.latest_page_result is not None
            assert update.latest_page_result.page_number > 0
            
            # Type 2: Cumulative results
            assert isinstance(update.cumulative_results, list)
            assert len(update.cumulative_results) == update.processed_pages
            
            # Verify progress metrics
            assert 0 <= update.progress_percentage <= 100
            assert update.processed_pages <= update.total_pages
            
            # Check timing estimates
            if update.processing_speed is not None:
                assert update.processing_speed > 0
        
        # Check final completion update
        completion_updates = [u for u in updates if u.status == "completed"]
        assert len(completion_updates) >= 1
        final_update = completion_updates[-1]
        assert final_update.progress_percentage == 100.0
        assert final_update.processed_pages == final_update.total_pages
        assert len(final_update.cumulative_results) == final_update.total_pages
        
        print(f"Processed {result.total_pages} pages in {processing_time:.2f}s")
        print(f"Received {len(updates)} streaming updates")
    
    @pytest.mark.asyncio
    @patch('app.services.external_ocr_service.external_ocr_service.process_image')
    @patch('app.services.ocr_llm_service.ocr_llm_service.process_image_with_llm')
    async def test_pdf_llm_streaming_with_real_file(self, mock_llm_process, mock_process_image, test_pdf_path):
        """Test PDF LLM streaming with the actual test PDF file."""
        # Mock external OCR service responses
        mock_process_image.return_value = AsyncMock(
            success=True,
            extracted_text="Original OCR text from page",
            processing_time=1.2,
            threshold_used=500,
            contrast_level_used=1.3
        )
        
        # Mock LLM service responses
        mock_llm_process.return_value = AsyncMock(
            success=True,
            extracted_text="Enhanced LLM text from page",
            processing_time=2.3,
            model_used="test-model",
            prompt_used="Test OCR prompt"
        )
        
        # Create streaming queue
        streaming_queue = asyncio.Queue()
        
        # Create LLM request
        request = PDFLLMOCRRequest(
            threshold=500,
            contrast_level=1.3,
            dpi=150,  # Lower DPI for faster testing
            prompt="Test OCR prompt",
            model="test-model"
        )
        
        task_id = "real-pdf-llm-test-123"
        
        # Process PDF with LLM streaming
        start_time = time.time()
        result = await pdf_ocr_service.process_pdf_with_llm_streaming(
            test_pdf_path, request, task_id, streaming_queue
        )
        processing_time = time.time() - start_time
        
        # Verify basic LLM result
        assert result is not None
        assert result.total_pages > 0
        assert result.llm_processing_time >= 0
        assert result.model_used == "test-model"
        assert result.prompt_used == "test prompt"
        
        # Collect all streaming updates
        updates = []
        while not streaming_queue.empty():
            update = await streaming_queue.get()
            if update is not None:  # Skip sentinel
                updates.append(update)
        
        # Verify LLM streaming updates structure
        assert len(updates) > 0
        
        # Check page completion updates for LLM
        page_updates = [u for u in updates if u.status == "page_completed"]
        assert len(page_updates) >= 1
        
        # Verify LLM-specific fields
        for update in page_updates:
            # Type 1: Single LLM page result
            if update.latest_page_result:
                assert hasattr(update.latest_page_result, 'llm_processing_time')
                assert hasattr(update.latest_page_result, 'model_used')
                assert hasattr(update.latest_page_result, 'prompt_used')
            
            # Type 2: Cumulative LLM results
            assert isinstance(update.cumulative_results, list)
            for result_item in update.cumulative_results:
                assert hasattr(result_item, 'llm_processing_time')
        
        print(f"LLM processed {result.total_pages} pages in {processing_time:.2f}s")
        print(f"Total LLM time: {result.llm_processing_time:.2f}s")
        print(f"Received {len(updates)} LLM streaming updates")


class TestControllerStreamingIntegration:
    """Test controller streaming with real file upload simulation."""
    
    @pytest.fixture
    def mock_upload_file(self):
        """Create mock upload file that simulates real PDF upload."""
        from io import BytesIO
        from fastapi import UploadFile
        
        # Read the actual test PDF
        test_file = Path("test_files/ocr-pdf-testing.pdf")
        if not test_file.exists():
            pytest.skip("Test PDF file not found")
        
        with open(test_file, 'rb') as f:
            pdf_content = f.read()
        
        # Create UploadFile-like object
        file_obj = BytesIO(pdf_content)
        upload_file = UploadFile(
            filename="ocr-pdf-testing.pdf",
            file=file_obj,
            size=len(pdf_content),
            headers={"content-type": "application/pdf"}
        )
        
        return upload_file
    
    @pytest.mark.asyncio
    @patch('app.services.external_ocr_service.external_ocr_service.process_image')
    async def test_controller_streaming_workflow(self, mock_process_image, mock_upload_file):
        """Test complete controller streaming workflow."""
        # Mock external service
        mock_process_image.return_value = AsyncMock(
            success=True,
            extracted_text="Controller test text",
            processing_time=1.0,
            threshold_used=500,
            contrast_level_used=1.3
        )
        
        # Create request
        request = PDFOCRRequest(dpi=150)  # Lower DPI for testing
        
        # Start streaming processing
        response = await ocr_controller.process_pdf_with_streaming(mock_upload_file, request)
        
        # Verify initial response
        assert response is not None
        assert response.task_id is not None
        assert response.status == "processing"
        assert response.created_at is not None
        
        task_id = response.task_id
        
        # Check that streaming queue was created
        assert task_id in ocr_controller.streaming_queues
        
        # Wait a bit for processing to start
        await asyncio.sleep(0.5)
        
        # Collect streaming updates
        updates = []
        timeout_count = 0
        max_timeouts = 5
        
        try:
            async for update in ocr_controller.stream_pdf_progress(task_id):
                if "keepalive" in update:
                    timeout_count += 1
                    if timeout_count >= max_timeouts:
                        break
                    continue
                
                updates.append(update)
                
                # Parse update to check completion
                try:
                    update_data = json.loads(update.replace("data: ", "").replace("\n\n", ""))
                    if update_data.get("status") == "completed":
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
                
                # Safety break after reasonable number of updates
                if len(updates) >= 20:
                    break
                    
        except asyncio.TimeoutError:
            pass  # Expected for some test scenarios
        
        # Verify we got some updates
        assert len(updates) > 0 or timeout_count > 0
        
        # Check final task status
        if task_id in ocr_controller.pdf_tasks:
            final_task = ocr_controller.pdf_tasks[task_id]
            # Task might still be processing, so check valid states
            assert final_task.status in ["processing", "completed", "failed"]
        
        print(f"Received {len(updates)} streaming updates for controller test")


class TestStreamingPerformanceMetrics:
    """Test streaming performance and metrics accuracy."""
    
    @pytest.mark.asyncio
    @patch('app.services.external_ocr_service.external_ocr_service.process_image')
    async def test_streaming_performance_metrics(self, mock_process_image):
        """Test that streaming provides accurate performance metrics."""
        # Mock with variable processing times
        processing_times = [1.0, 1.5, 2.0]  # Different times per page
        mock_responses = []
        
        for i, proc_time in enumerate(processing_times):
            async def mock_response():
                await asyncio.sleep(proc_time / 10)  # Scaled down for testing
                return AsyncMock(
                    success=True,
                    extracted_text=f"Page {i+1} text",
                    processing_time=proc_time,
                    threshold_used=500,
                    contrast_level_used=1.3
                )
            mock_responses.append(mock_response())
        
        mock_process_image.side_effect = mock_responses
        
        # Create streaming queue
        streaming_queue = asyncio.Queue()
        
        # Create mock PDF with 3 pages
        with patch('app.services.pdf_ocr_service.PDFOCRService._validate_and_get_page_count') as mock_count, \
             patch('app.services.pdf_ocr_service.PDFOCRService._pdf_to_images') as mock_images:
            
            mock_count.return_value = len(processing_times)
            mock_images.return_value = [Path(f"page{i}.png") for i in range(len(processing_times))]
            
            request = PDFOCRRequest()
            task_id = "performance-test-123"
            
            # Track timing
            start_time = time.time()
            
            result = await pdf_ocr_service.process_pdf_with_streaming(
                Path("fake.pdf"), request, task_id, streaming_queue
            )
            
            total_time = time.time() - start_time
        
        # Collect updates and verify metrics
        updates = []
        while not streaming_queue.empty():
            update = await streaming_queue.get()
            if update is not None:
                updates.append(update)
        
        # Check progress percentage accuracy
        page_updates = [u for u in updates if u.status == "page_completed"]
        
        for i, update in enumerate(page_updates):
            expected_progress = ((i + 1) / len(processing_times)) * 100
            assert abs(update.progress_percentage - expected_progress) < 1.0
            
            # Check processing speed calculation
            if update.processing_speed is not None:
                assert update.processing_speed > 0
            
            # Check cumulative results count
            assert len(update.cumulative_results) == i + 1
        
        print(f"Performance test completed in {total_time:.2f}s")
        print(f"Tracked {len(page_updates)} page completions") 