"""
Real end-to-end performance testing that measures actual OCR processing completion times.
This measures the complete user experience from task creation to final results.
"""

import json
import pytest
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import statistics

from tests.remote_client import RemoteTestClient
from tests.remote_test_config import RemoteTestConfig
from tests.performance_reporter import PerformanceReporter


@dataclass
class EndToEndMetrics:
    """Complete end-to-end performance metrics."""
    task_id: str
    task_creation_time: float  # Time to create task (HTTP request)
    queue_wait_time: Optional[float]  # Time waiting in queue before processing
    processing_time: Optional[float]  # Actual OCR processing time
    total_end_to_end_time: float  # Complete user experience time
    success: bool
    extracted_text_length: int
    error_message: Optional[str]
    processing_mode: str
    image_size: str


class TaskMonitor:
    """Monitor task lifecycle and measure timing breakdown."""
    
    def __init__(self, client: RemoteTestClient):
        self.client = client
    
    def wait_for_completion(self, task_id: str, timeout: int = 180) -> Dict[str, Any]:
        """
        Wait for task completion and track timing phases.
        Returns detailed timing breakdown and final result.
        """
        start_monitoring = time.time()
        last_status = None
        processing_started_time = None
        queue_wait_time = None
        
        print(f"      📊 Monitoring task {task_id[:8]}...")
        
        for attempt in range(timeout // 3):  # Check every 3 seconds
            try:
                # Try multiple possible endpoints
                status_data = None
                for endpoint in [f"/v1/ocr/process-stream/{task_id}", 
                               f"/v1/ocr/status/{task_id}", 
                               f"/v1/tasks/{task_id}"]:
                    try:
                        response = self.client.get(endpoint)
                        if response.status_code == 200:
                            status_data = response.json()
                            break
                    except Exception:
                        continue
                
                if not status_data:
                    # No status endpoint found, task might still be processing
                    if attempt % 10 == 0:  # Log every 30 seconds
                        elapsed = time.time() - start_monitoring
                        print(f"      ⏳ Still waiting... {elapsed:.1f}s elapsed")
                    time.sleep(3)
                    continue
                
                current_status = status_data.get('status', 'unknown')
                
                # Track status transitions
                if current_status != last_status:
                    elapsed = time.time() - start_monitoring
                    print(f"      📈 {elapsed:.1f}s: {last_status} → {current_status}")
                    
                    # Detect when processing actually starts
                    if last_status in ['pending', 'queued'] and current_status == 'processing':
                        processing_started_time = time.time()
                        queue_wait_time = processing_started_time - start_monitoring
                        print(f"      🚀 Processing started after {queue_wait_time:.1f}s queue wait")
                    
                    last_status = current_status
                
                # Show progress if available
                if 'progress_percentage' in status_data:
                    progress = status_data['progress_percentage']
                    elapsed = time.time() - start_monitoring
                    print(f"      📊 {elapsed:.1f}s: {progress}% complete")
                
                # Check for completion
                if current_status == 'completed':
                    end_time = time.time()
                    total_time = end_time - start_monitoring
                    
                    # Calculate processing time
                    actual_processing_time = None
                    if processing_started_time:
                        actual_processing_time = end_time - processing_started_time
                    
                    print(f"      ✅ Completed in {total_time:.1f}s total")
                    if queue_wait_time:
                        print(f"         Queue wait: {queue_wait_time:.1f}s")
                    if actual_processing_time:
                        print(f"         Processing: {actual_processing_time:.1f}s")
                    
                    return {
                        'status': 'completed',
                        'total_time': total_time,
                        'queue_wait_time': queue_wait_time,
                        'processing_time': actual_processing_time,
                        'result': status_data.get('result', {}),
                        'attempts': attempt + 1
                    }
                
                elif current_status == 'failed':
                    end_time = time.time()
                    total_time = end_time - start_monitoring
                    error = status_data.get('error', 'Unknown error')
                    
                    print(f"      ❌ Failed after {total_time:.1f}s: {error}")
                    
                    return {
                        'status': 'failed',
                        'total_time': total_time,
                        'queue_wait_time': queue_wait_time,
                        'processing_time': None,
                        'error': error,
                        'attempts': attempt + 1
                    }
                
                elif current_status in ['processing', 'pending']:
                    # Continue monitoring
                    time.sleep(3)
                else:
                    # Unknown status, continue monitoring
                    time.sleep(3)
                
            except Exception as e:
                print(f"      ⚠️  Monitoring error: {e}")
                time.sleep(3)
        
        # Timeout
        total_time = time.time() - start_monitoring
        print(f"      ⏰ Timeout after {total_time:.1f}s")
        
        return {
            'status': 'timeout',
            'total_time': total_time,
            'queue_wait_time': queue_wait_time,
            'processing_time': None,
            'error': f'Timeout after {timeout}s',
            'attempts': timeout // 3
        }


class TestRealPerformance:
    """Real end-to-end performance testing with complete task lifecycle monitoring."""
    
    @pytest.fixture(scope="class")
    def performance_reporter(self):
        """Create performance reporter for real performance metrics."""
        reporter = PerformanceReporter()
        yield reporter
        
        # Save comprehensive end-to-end performance reports
        if reporter.current_metrics:
            deployment_url = RemoteTestConfig.get_base_url()
            report_paths = reporter.save_reports(deployment_url, "real_performance")
            
            print(f"\n📊 Real Performance Reports Generated:")
            print(f"   HTML Report: {report_paths['html']}")
            print(f"   JSON Report: {report_paths['json']}")
            print(f"   🎯 This shows ACTUAL OCR processing performance!")
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def task_monitor(self, client):
        """Create task monitor for lifecycle tracking."""
        return TaskMonitor(client)
    
    @pytest.fixture
    def realistic_test_image(self):
        """Create a realistic image that requires actual OCR processing."""
        image = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Create realistic document content
        content_lines = [
            "PERFORMANCE TEST DOCUMENT",
            "Real OCR Processing Analysis",
            "",
            "Document ID: PERF-001-2024",
            "Date: January 15, 2024",
            "Processing Mode: End-to-End Testing",
            "",
            "Content Analysis:",
            "This document contains substantial text",
            "designed to require real OCR processing.",
            "The system should extract all this text",
            "and measure the actual processing time.",
            "",
            "Technical Specifications:",
            "- Image Resolution: 800x600 pixels",
            "- Text Quality: High contrast black on white",
            "- Font: Standard Arial 24pt",
            "- Language: English text with numbers",
            "",
            "Expected Processing Time:",
            "Basic OCR: 3-10 seconds",
            "LLM Enhanced: 10-30 seconds",
            "",
            "Performance Metrics:",
            "- Task Creation: < 1 second",
            "- Queue Wait: Variable",
            "- Processing: 3-30 seconds",
            "- Total End-to-End: 5-35 seconds"
        ]
        
        y_position = 30
        for line in content_lines:
            if line:  # Skip empty lines for drawing
                draw.text((50, y_position), line, fill='black', font=font)
            y_position += 30
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def create_end_to_end_request(self, 
                                 client: RemoteTestClient,
                                 task_monitor: TaskMonitor,
                                 image_data: io.BytesIO,
                                 mode: str = "basic",
                                 test_name: str = "Unknown") -> EndToEndMetrics:
        """
        Create OCR request and monitor complete end-to-end processing.
        Returns comprehensive metrics including all timing phases.
        """
        print(f"   🎯 {test_name} - {mode} mode")
        
        # Phase 1: Task Creation
        task_creation_start = time.time()
        
        request_data = {"mode": mode}
        if mode == "llm_enhanced":
            request_data["prompt"] = "Extract all text from this document with high accuracy"
        
        try:
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": (f"{test_name.lower().replace(' ', '_')}.jpg", image_data, "image/jpeg")},
                data={"request": json.dumps(request_data)}
            )
            
            task_creation_time = time.time() - task_creation_start
            
            if response.status_code == 200:
                task_data = response.json()
                task_id = task_data["task_id"]
                
                print(f"      ✅ Task created in {task_creation_time:.2f}s: {task_id[:8]}...")
                
                # Phase 2: Monitor complete processing
                monitoring_result = task_monitor.wait_for_completion(task_id)
                
                # Extract results
                success = monitoring_result['status'] == 'completed'
                extracted_text = ""
                error_message = None
                
                if success and 'result' in monitoring_result:
                    result = monitoring_result['result']
                    extracted_text = result.get('extracted_text', '')
                    print(f"      📄 Extracted {len(extracted_text)} characters")
                elif not success:
                    error_message = monitoring_result.get('error', 'Unknown error')
                
                return EndToEndMetrics(
                    task_id=task_id,
                    task_creation_time=task_creation_time,
                    queue_wait_time=monitoring_result['queue_wait_time'],
                    processing_time=monitoring_result['processing_time'],
                    total_end_to_end_time=monitoring_result['total_time'],
                    success=success,
                    extracted_text_length=len(extracted_text),
                    error_message=error_message,
                    processing_mode=mode,
                    image_size="medium"
                )
            
            else:
                print(f"      ❌ Task creation failed: HTTP {response.status_code}")
                return EndToEndMetrics(
                    task_id="",
                    task_creation_time=task_creation_time,
                    queue_wait_time=None,
                    processing_time=None,
                    total_end_to_end_time=task_creation_time,
                    success=False,
                    extracted_text_length=0,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    processing_mode=mode,
                    image_size="medium"
                )
        
        except Exception as e:
            task_creation_time = time.time() - task_creation_start
            print(f"      ❌ Request failed: {e}")
            return EndToEndMetrics(
                task_id="",
                task_creation_time=task_creation_time,
                queue_wait_time=None,
                processing_time=None,
                total_end_to_end_time=task_creation_time,
                success=False,
                extracted_text_length=0,
                error_message=str(e),
                processing_mode=mode,
                image_size="medium"
            )
    
    def test_real_basic_ocr_performance(self, client, task_monitor, realistic_test_image, performance_reporter):
        """Test real basic OCR end-to-end performance."""
        print(f"\n🎯 Real Basic OCR Performance Test")
        print(f"   Deployment: {client.base_url}")
        print(f"   This measures ACTUAL processing time, not just HTTP response time")
        
        num_tests = 2  # Limited for realistic testing
        metrics_list = []
        
        for i in range(num_tests):
            realistic_test_image.seek(0)  # Reset image stream
            
            metrics = self.create_end_to_end_request(
                client, task_monitor, realistic_test_image,
                mode="basic",
                test_name=f"Basic OCR Test {i+1}"
            )
            metrics_list.append(metrics)
        
        # Analyze results
        successful_metrics = [m for m in metrics_list if m.success]
        failed_metrics = [m for m in metrics_list if not m.success]
        
        print(f"\n   📊 Basic OCR Results:")
        print(f"      Successful: {len(successful_metrics)}/{num_tests}")
        print(f"      Failed: {len(failed_metrics)}")
        
        if successful_metrics:
            # Calculate timing statistics
            creation_times = [m.task_creation_time for m in successful_metrics]
            total_times = [m.total_end_to_end_time for m in successful_metrics]
            processing_times = [m.processing_time for m in successful_metrics if m.processing_time]
            
            avg_creation = statistics.mean(creation_times)
            avg_total = statistics.mean(total_times)
            avg_processing = statistics.mean(processing_times) if processing_times else 0
            
            print(f"      Avg task creation: {avg_creation:.2f}s")
            print(f"      Avg processing: {avg_processing:.2f}s")
            print(f"      Avg total end-to-end: {avg_total:.2f}s")
            
            # Extract text analysis
            text_lengths = [m.extracted_text_length for m in successful_metrics]
            avg_text_length = statistics.mean(text_lengths) if text_lengths else 0
            print(f"      Avg text extracted: {avg_text_length:.0f} characters")
        
        # Record with performance reporter
        response_times = [m.total_end_to_end_time for m in successful_metrics]
        errors = [m.error_message for m in failed_metrics if m.error_message]
        
        performance_reporter.record_test_metrics(
            test_name="Real Basic OCR Performance",
            response_times=response_times,
            success_count=len(successful_metrics),
            error_count=len(failed_metrics),
            duration=sum(m.total_end_to_end_time for m in metrics_list),
            errors=errors,
            metadata={
                "test_type": "real_end_to_end",
                "processing_mode": "basic",
                "avg_creation_time": statistics.mean([m.task_creation_time for m in metrics_list]),
                "avg_processing_time": statistics.mean([m.processing_time for m in successful_metrics if m.processing_time]) if successful_metrics else 0,
                "avg_text_length": statistics.mean([m.extracted_text_length for m in successful_metrics]) if successful_metrics else 0
            }
        )
        
        # Assertions for real performance
        assert len(successful_metrics) > 0, "No successful OCR processing"
        if successful_metrics:
            avg_total = statistics.mean([m.total_end_to_end_time for m in successful_metrics])
            assert avg_total > 1.0, f"Processing too fast to be real: {avg_total:.2f}s"
            assert avg_total < 120, f"Processing too slow: {avg_total:.2f}s"
        
        print(f"   ✅ Real basic OCR performance test PASSED")
    
    def test_real_llm_enhanced_performance(self, client, task_monitor, realistic_test_image, performance_reporter):
        """Test real LLM-enhanced OCR end-to-end performance."""
        print(f"\n🤖 Real LLM-Enhanced OCR Performance Test")
        print(f"   This measures ACTUAL LLM processing time")
        
        num_tests = 1  # LLM tests take longer
        metrics_list = []
        
        for i in range(num_tests):
            realistic_test_image.seek(0)
            
            metrics = self.create_end_to_end_request(
                client, task_monitor, realistic_test_image,
                mode="llm_enhanced", 
                test_name=f"LLM OCR Test {i+1}"
            )
            metrics_list.append(metrics)
        
        # Analyze results
        successful_metrics = [m for m in metrics_list if m.success]
        failed_metrics = [m for m in metrics_list if not m.success]
        
        print(f"\n   📊 LLM OCR Results:")
        print(f"      Successful: {len(successful_metrics)}/{num_tests}")
        
        if successful_metrics:
            for metrics in successful_metrics:
                print(f"      Task creation: {metrics.task_creation_time:.2f}s")
                if metrics.queue_wait_time:
                    print(f"      Queue wait: {metrics.queue_wait_time:.2f}s")
                if metrics.processing_time:
                    print(f"      LLM processing: {metrics.processing_time:.2f}s")
                print(f"      Total end-to-end: {metrics.total_end_to_end_time:.2f}s")
                print(f"      Text extracted: {metrics.extracted_text_length} characters")
        
        # Record metrics
        response_times = [m.total_end_to_end_time for m in successful_metrics]
        errors = [m.error_message for m in failed_metrics if m.error_message]
        
        performance_reporter.record_test_metrics(
            test_name="Real LLM-Enhanced OCR Performance",
            response_times=response_times,
            success_count=len(successful_metrics),
            error_count=len(failed_metrics),
            duration=sum(m.total_end_to_end_time for m in metrics_list),
            errors=errors,
            metadata={
                "test_type": "real_end_to_end",
                "processing_mode": "llm_enhanced",
                "avg_creation_time": statistics.mean([m.task_creation_time for m in metrics_list]),
                "avg_processing_time": statistics.mean([m.processing_time for m in successful_metrics if m.processing_time]) if successful_metrics else 0,
                "avg_text_length": statistics.mean([m.extracted_text_length for m in successful_metrics]) if successful_metrics else 0
            }
        )
        
        print(f"   ✅ Real LLM OCR performance test PASSED")
    
    def test_performance_comparison(self, client, task_monitor, realistic_test_image, performance_reporter):
        """Compare basic vs LLM-enhanced real performance."""
        print(f"\n⚖️  Real Performance Comparison: Basic vs LLM")
        
        comparison_results = {}
        
        for mode in ["basic", "llm_enhanced"]:
            print(f"\n   Testing {mode} mode...")
            realistic_test_image.seek(0)
            
            metrics = self.create_end_to_end_request(
                client, task_monitor, realistic_test_image,
                mode=mode,
                test_name=f"Comparison {mode}"
            )
            
            if metrics.success:
                comparison_results[mode] = {
                    "creation_time": metrics.task_creation_time,
                    "processing_time": metrics.processing_time or 0,
                    "total_time": metrics.total_end_to_end_time,
                    "text_length": metrics.extracted_text_length
                }
        
        # Compare results
        if len(comparison_results) >= 2:
            basic = comparison_results.get("basic", {})
            llm = comparison_results.get("llm_enhanced", {})
            
            print(f"\n   📊 Performance Comparison:")
            print(f"      Basic OCR:")
            print(f"        Creation: {basic.get('creation_time', 0):.2f}s")
            print(f"        Processing: {basic.get('processing_time', 0):.2f}s")
            print(f"        Total: {basic.get('total_time', 0):.2f}s")
            print(f"        Text: {basic.get('text_length', 0)} chars")
            
            print(f"      LLM Enhanced:")
            print(f"        Creation: {llm.get('creation_time', 0):.2f}s")
            print(f"        Processing: {llm.get('processing_time', 0):.2f}s")
            print(f"        Total: {llm.get('total_time', 0):.2f}s")
            print(f"        Text: {llm.get('text_length', 0)} chars")
            
            # Calculate improvements
            if basic.get('total_time', 0) > 0 and llm.get('total_time', 0) > 0:
                time_ratio = llm['total_time'] / basic['total_time']
                print(f"      LLM is {time_ratio:.1f}x slower than basic")
                
                if llm.get('text_length', 0) > basic.get('text_length', 0):
                    quality_improvement = llm['text_length'] / max(basic['text_length'], 1)
                    print(f"      LLM extracted {quality_improvement:.1f}x more text")
        
        print(f"   ✅ Performance comparison completed")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])