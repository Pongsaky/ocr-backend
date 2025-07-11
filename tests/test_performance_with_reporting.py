"""
Enhanced performance and load testing with comprehensive reporting.
Generates detailed performance reports, charts, and historical tracking.
"""

import json
import pytest
import asyncio
import time
from pathlib import Path
from PIL import Image, ImageDraw
import io
from typing import Dict, Any, List
import statistics
import concurrent.futures
import os

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig
from tests.performance_reporter import PerformanceReporter


class TestPerformanceWithReporting:
    """Enhanced performance testing with comprehensive reporting."""
    
    @pytest.fixture(scope="class")
    def performance_reporter(self):
        """Create performance reporter for the test session."""
        reporter = PerformanceReporter()
        yield reporter
        
        # Save reports at the end of test session
        if reporter.current_metrics:
            deployment_url = RemoteTestConfig.get_base_url()
            report_paths = reporter.save_reports(deployment_url, "performance_test")
            
            print(f"\n📊 Performance Reports Generated:")
            print(f"   HTML Report: {report_paths['html']}")
            print(f"   JSON Report: {report_paths['json']}")
            print(f"   Open HTML report in browser to view detailed analysis")
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def small_test_image(self):
        """Create a small image for performance testing."""
        image = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((50, 50), "Performance Test", fill='black')
        draw.text((50, 100), "Small document", fill='black')
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    @pytest.fixture
    def large_test_image(self):
        """Create a larger image for stress testing."""
        image = Image.new('RGB', (1200, 800), color='white')
        draw = ImageDraw.Draw(image)
        
        # Fill with more content
        for i in range(20):
            y = 40 + i * 35
            draw.text((50, y), f"Line {i+1}: Performance test content for load testing", fill='black')
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def make_ocr_request(self, client: RemoteTestClient, image_data: io.BytesIO, request_id: int) -> Dict[str, Any]:
        """Make a single OCR request and measure performance."""
        start_time = time.time()
        
        try:
            # Reset image data
            image_data.seek(0)
            
            request_data = {
                "mode": "basic",
                "threshold": 128
            }
            
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": (f"perf_test_{request_id}.jpg", image_data, "image/jpeg")},
                data={"request": json.dumps(request_data)}
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                "request_id": request_id,
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response_time,
                "task_id": response.json().get("task_id") if response.status_code == 200 else None,
                "error": None
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                "request_id": request_id,
                "success": False,
                "status_code": 0,
                "response_time": end_time - start_time,
                "task_id": None,
                "error": str(e)
            }
    
    def test_api_response_time_baseline(self, client, small_test_image, performance_reporter):
        """Test baseline API response times with reporting."""
        print(f"\n⏱️  Testing API response time baseline at: {client.base_url}")
        
        num_requests = 5
        response_times = []
        errors = []
        success_count = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            print(f"   Request {i+1}/{num_requests}...")
            
            result = self.make_ocr_request(client, small_test_image, i)
            
            if result["success"]:
                response_times.append(result["response_time"])
                success_count += 1
                print(f"   ✅ Response time: {result['response_time']:.2f}s")
            else:
                error_msg = result.get('error', f"HTTP {result['status_code']}")
                errors.append(error_msg)
                print(f"   ❌ Failed: {error_msg}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Record metrics with reporter
        performance_reporter.record_test_metrics(
            test_name="API Response Time Baseline",
            response_times=response_times,
            success_count=success_count,
            error_count=len(errors),
            duration=duration,
            errors=errors,
            metadata={"test_type": "baseline", "image_size": "small"}
        )
        
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Response Time Baseline:")
            print(f"   Successful requests: {success_count}/{num_requests}")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Median: {median_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s")
            
            # Basic performance assertions
            assert avg_time < 30, f"Average response time too high: {avg_time:.2f}s"
            assert success_count >= num_requests * 0.8, "Too many failed requests"
            
            print("✅ Response time baseline test PASSED")
        else:
            pytest.fail("No successful requests in baseline test")
    
    def test_concurrent_requests(self, client, small_test_image, performance_reporter):
        """Test handling of concurrent requests with reporting."""
        print(f"\n🔀 Testing concurrent requests at: {client.base_url}")
        
        concurrent_count = 3  # Conservative for testing
        
        def make_request(request_id: int) -> Dict[str, Any]:
            # Create new image data for each thread
            test_image = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(test_image)
            draw.text((50, 50), f"Concurrent Test {request_id}", fill='black')
            
            img_byte_arr = io.BytesIO()
            test_image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            # Use fresh client for each request
            thread_client = RemoteTestClient()
            return self.make_ocr_request(thread_client, img_byte_arr, request_id)
        
        print(f"   Sending {concurrent_count} concurrent requests...")
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze concurrent performance
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        response_times = [r["response_time"] for r in successful_requests]
        errors = [r.get("error", "Unknown") for r in failed_requests]
        
        # Record metrics
        performance_reporter.record_test_metrics(
            test_name="Concurrent Requests",
            response_times=response_times,
            success_count=len(successful_requests),
            error_count=len(failed_requests),
            duration=total_time,
            errors=errors,
            metadata={
                "test_type": "concurrent",
                "concurrent_count": concurrent_count,
                "image_size": "small"
            }
        )
        
        print(f"\n📊 Concurrent Request Results:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Successful: {len(successful_requests)}/{concurrent_count}")
        print(f"   Failed: {len(failed_requests)}")
        
        if successful_requests:
            avg_time = statistics.mean(response_times)
            print(f"   Average response time: {avg_time:.2f}s")
            
            # Check if concurrent requests were processed efficiently
            max_expected_time = max(response_times) + 2  # Allow 2s overhead
            if total_time <= max_expected_time:
                print("✅ Efficient concurrent processing")
            else:
                print(f"⚠️  Concurrent processing may be slower than expected")
        
        # Assertions
        success_rate = len(successful_requests) / concurrent_count
        assert success_rate >= 0.7, f"Low success rate for concurrent requests: {success_rate*100:.1f}%"
        
        print("✅ Concurrent requests test PASSED")
    
    def test_load_with_different_image_sizes(self, client, small_test_image, large_test_image, performance_reporter):
        """Test load with different image sizes with reporting."""
        print(f"\n📏 Testing load with different image sizes at: {client.base_url}")
        
        test_cases = [
            ("small", small_test_image),
            ("large", large_test_image)
        ]
        
        for size_name, image_data in test_cases:
            print(f"\n🔍 Testing {size_name} images...")
            
            num_requests = 3
            response_times = []
            errors = []
            success_count = 0
            
            start_time = time.time()
            
            for i in range(num_requests):
                result = self.make_ocr_request(client, image_data, i)
                
                if result["success"]:
                    response_times.append(result["response_time"])
                    success_count += 1
                    print(f"   Request {i+1}: {result['response_time']:.2f}s ✅")
                else:
                    error_msg = result.get("error", f"HTTP {result['status_code']}")
                    errors.append(error_msg)
                    print(f"   Request {i+1}: Failed ❌")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Record metrics for this image size
            performance_reporter.record_test_metrics(
                test_name=f"Image Size Test - {size_name.title()}",
                response_times=response_times,
                success_count=success_count,
                error_count=len(errors),
                duration=duration,
                errors=errors,
                metadata={
                    "test_type": "image_size",
                    "image_size": size_name,
                    "requests_per_size": num_requests
                }
            )
            
            if response_times:
                avg_time = statistics.mean(response_times)
                print(f"   {size_name.title()} images average: {avg_time:.2f}s")
        
        print("✅ Image size load test PASSED")
    
    def test_sustained_load(self, client, small_test_image, performance_reporter):
        """Test sustained load over time with reporting."""
        print(f"\n⏳ Testing sustained load at: {client.base_url}")
        
        duration_seconds = 30  # Test for 30 seconds
        request_interval = 3   # One request every 3 seconds
        
        print(f"   Running sustained load for {duration_seconds}s...")
        
        start_time = time.time()
        response_times = []
        errors = []
        success_count = 0
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            request_count += 1
            print(f"   Request {request_count}...", end=" ")
            
            result = self.make_ocr_request(client, small_test_image, request_count)
            
            if result["success"]:
                response_times.append(result["response_time"])
                success_count += 1
                print(f"{result['response_time']:.2f}s ✅")
            else:
                error_msg = result.get("error", f"HTTP {result['status_code']}")
                errors.append(error_msg)
                print("❌")
            
            # Wait before next request
            time.sleep(request_interval)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Record sustained load metrics
        performance_reporter.record_test_metrics(
            test_name="Sustained Load Test",
            response_times=response_times,
            success_count=success_count,
            error_count=len(errors),
            duration=actual_duration,
            errors=errors,
            metadata={
                "test_type": "sustained_load",
                "target_duration": duration_seconds,
                "request_interval": request_interval,
                "total_requests": request_count
            }
        )
        
        print(f"\n📊 Sustained Load Results:")
        print(f"   Duration: {actual_duration:.1f}s")
        print(f"   Total requests: {request_count}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {len(errors)}")
        print(f"   Success rate: {success_count/request_count*100:.1f}%")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            print(f"   Average response time: {avg_time:.2f}s")
            
            # Check for performance degradation over time
            if len(response_times) > 4:
                first_half = response_times[:len(response_times)//2]
                second_half = response_times[len(response_times)//2:]
                
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                
                print(f"   First half avg: {first_avg:.2f}s")
                print(f"   Second half avg: {second_avg:.2f}s")
                
                if second_avg > first_avg * 1.5:
                    print("⚠️  Performance degradation detected")
                else:
                    print("✅ Stable performance over time")
        
        # Assertions
        success_rate = success_count / request_count
        assert success_rate >= 0.8, f"Low success rate in sustained load: {success_rate*100:.1f}%"
        assert request_count >= 5, "Too few requests in sustained load test"
        
        print("✅ Sustained load test PASSED")
    
    def test_error_rate_under_load(self, client, small_test_image, performance_reporter):
        """Test error rates under increased load with reporting."""
        print(f"\n❌ Testing error rates under load at: {client.base_url}")
        
        # Send requests with shorter intervals to stress test
        rapid_requests = 8
        response_times = []
        errors = []
        success_count = 0
        
        print(f"   Sending {rapid_requests} rapid requests...")
        
        start_time = time.time()
        
        for i in range(rapid_requests):
            result = self.make_ocr_request(client, small_test_image, i)
            
            if result["success"]:
                response_times.append(result["response_time"])
                success_count += 1
            else:
                error_msg = result.get("error", f"HTTP {result['status_code']}")
                errors.append(error_msg)
            
            status = "✅" if result["success"] else "❌"
            print(f"   Request {i+1}: {result['response_time']:.2f}s {status}")
            
            # Short delay between requests
            time.sleep(0.5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Record rapid fire metrics
        performance_reporter.record_test_metrics(
            test_name="Error Rate Under Load",
            response_times=response_times,
            success_count=success_count,
            error_count=len(errors),
            duration=total_time,
            errors=errors,
            metadata={
                "test_type": "rapid_fire",
                "request_interval": 0.5,
                "total_rapid_requests": rapid_requests
            }
        )
        
        print(f"\n📊 Error Rate Analysis:")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   Request rate: {rapid_requests/total_time:.1f} req/s")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {len(errors)}")
        print(f"   Error rate: {len(errors)/rapid_requests*100:.1f}%")
        
        # Analyze error types
        if errors:
            error_summary = {}
            for error in errors:
                error_type = error.split(':')[0] if ':' in error else error
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
            print(f"   Error types: {error_summary}")
        
        # Check response time distribution
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            print(f"   Avg response time: {avg_time:.2f}s")
            print(f"   Max response time: {max_time:.2f}s")
        
        # Assertions for acceptable error rates
        error_rate = len(errors) / rapid_requests
        assert error_rate <= 0.3, f"High error rate under load: {error_rate*100:.1f}%"
        
        print("✅ Error rate test PASSED")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])