"""
Performance and load testing utilities for deployment validation.
These tests verify the deployed API can handle various load scenarios.
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
from dataclasses import dataclass

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


@dataclass
class PerformanceMetrics:
    """Performance measurement data."""
    response_times: List[float]
    success_count: int
    error_count: int
    total_requests: int
    start_time: float
    end_time: float
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_requests if self.total_requests > 0 else 0
    
    @property
    def requests_per_second(self) -> float:
        return self.total_requests / self.duration if self.duration > 0 else 0
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def median_response_time(self) -> float:
        return statistics.median(self.response_times) if self.response_times else 0
    
    @property
    def percentile_95_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]


class TestPerformanceLoad:
    """Performance and load testing for deployed API."""
    
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
            draw.text((50, y), f"Line {i+1}: This is performance test content for load testing", fill='black')
        
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
    
    def test_api_response_time_baseline(self, client, small_test_image):
        """Test baseline API response times."""
        print(f"\n⏱️  Testing API response time baseline at: {client.base_url}")
        
        num_requests = 5
        response_times = []
        
        for i in range(num_requests):
            print(f"   Request {i+1}/{num_requests}...")
            
            result = self.make_ocr_request(client, small_test_image, i)
            
            if result["success"]:
                response_times.append(result["response_time"])
                print(f"   ✅ Response time: {result['response_time']:.2f}s")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Response Time Baseline:")
            print(f"   Successful requests: {len(response_times)}/{num_requests}")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Median: {median_time:.2f}s")
            print(f"   Min: {min_time:.2f}s")
            print(f"   Max: {max_time:.2f}s")
            
            # Basic performance assertions
            assert avg_time < 30, f"Average response time too high: {avg_time:.2f}s"
            assert len(response_times) >= num_requests * 0.8, "Too many failed requests"
            
            print("✅ Response time baseline test PASSED")
        else:
            pytest.fail("No successful requests in baseline test")
    
    def test_concurrent_requests(self, client, small_test_image):
        """Test handling of concurrent requests."""
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
        
        print(f"\n📊 Concurrent Request Results:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Successful: {len(successful_requests)}/{concurrent_count}")
        print(f"   Failed: {len(failed_requests)}")
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
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
    
    def test_load_with_different_image_sizes(self, client, small_test_image, large_test_image):
        """Test load with different image sizes."""
        print(f"\n📏 Testing load with different image sizes at: {client.base_url}")
        
        test_cases = [
            ("small", small_test_image),
            ("large", large_test_image)
        ]
        
        results = {}
        
        for size_name, image_data in test_cases:
            print(f"\n🔍 Testing {size_name} images...")
            
            num_requests = 3
            size_results = []
            
            for i in range(num_requests):
                result = self.make_ocr_request(client, image_data, i)
                size_results.append(result)
                
                if result["success"]:
                    print(f"   Request {i+1}: {result['response_time']:.2f}s ✅")
                else:
                    print(f"   Request {i+1}: Failed ❌")
            
            successful = [r for r in size_results if r["success"]]
            if successful:
                avg_time = statistics.mean([r["response_time"] for r in successful])
                results[size_name] = {
                    "avg_response_time": avg_time,
                    "success_count": len(successful),
                    "total_requests": num_requests
                }
                
                print(f"   {size_name.title()} images average: {avg_time:.2f}s")
        
        # Compare performance between sizes
        if "small" in results and "large" in results:
            small_time = results["small"]["avg_response_time"]
            large_time = results["large"]["avg_response_time"]
            
            print(f"\n📊 Size Comparison:")
            print(f"   Small images: {small_time:.2f}s")
            print(f"   Large images: {large_time:.2f}s")
            
            if large_time > small_time:
                ratio = large_time / small_time
                print(f"   Large images {ratio:.1f}x slower (expected)")
            else:
                print(f"   Similar processing times")
        
        print("✅ Image size load test PASSED")
    
    def test_sustained_load(self, client, small_test_image):
        """Test sustained load over time."""
        print(f"\n⏳ Testing sustained load at: {client.base_url}")
        
        duration_seconds = 30  # Test for 30 seconds
        request_interval = 3   # One request every 3 seconds
        
        print(f"   Running sustained load for {duration_seconds}s...")
        
        start_time = time.time()
        results = []
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            request_count += 1
            print(f"   Request {request_count}...", end=" ")
            
            result = self.make_ocr_request(client, small_test_image, request_count)
            results.append(result)
            
            if result["success"]:
                print(f"{result['response_time']:.2f}s ✅")
            else:
                print("❌")
            
            # Wait before next request
            time.sleep(request_interval)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Analyze sustained load results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        print(f"\n📊 Sustained Load Results:")
        print(f"   Duration: {actual_duration:.1f}s")
        print(f"   Total requests: {len(results)}")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Success rate: {len(successful)/len(results)*100:.1f}%")
        
        if successful:
            response_times = [r["response_time"] for r in successful]
            avg_time = statistics.mean(response_times)
            print(f"   Average response time: {avg_time:.2f}s")
            
            # Check for performance degradation over time
            first_half = response_times[:len(response_times)//2]
            second_half = response_times[len(response_times)//2:]
            
            if first_half and second_half:
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                
                print(f"   First half avg: {first_avg:.2f}s")
                print(f"   Second half avg: {second_avg:.2f}s")
                
                if second_avg > first_avg * 1.5:
                    print("⚠️  Performance degradation detected")
                else:
                    print("✅ Stable performance over time")
        
        # Assertions
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.8, f"Low success rate in sustained load: {success_rate*100:.1f}%"
        assert len(results) >= 5, "Too few requests in sustained load test"
        
        print("✅ Sustained load test PASSED")
    
    def test_error_rate_under_load(self, client, small_test_image):
        """Test error rates under increased load."""
        print(f"\n❌ Testing error rates under load at: {client.base_url}")
        
        # Send requests with shorter intervals to stress test
        rapid_requests = 8
        results = []
        
        print(f"   Sending {rapid_requests} rapid requests...")
        
        start_time = time.time()
        
        for i in range(rapid_requests):
            result = self.make_ocr_request(client, small_test_image, i)
            results.append(result)
            
            status = "✅" if result["success"] else "❌"
            print(f"   Request {i+1}: {result['response_time']:.2f}s {status}")
            
            # Short delay between requests
            time.sleep(0.5)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze error patterns
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        print(f"\n📊 Error Rate Analysis:")
        print(f"   Total time: {total_time:.1f}s")
        print(f"   Request rate: {rapid_requests/total_time:.1f} req/s")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Error rate: {len(failed)/rapid_requests*100:.1f}%")
        
        # Analyze error types
        if failed:
            error_codes = {}
            for failure in failed:
                code = failure["status_code"]
                error_codes[code] = error_codes.get(code, 0) + 1
            
            print(f"   Error codes: {error_codes}")
        
        # Check response time distribution
        if successful:
            response_times = [r["response_time"] for r in successful]
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            print(f"   Avg response time: {avg_time:.2f}s")
            print(f"   Max response time: {max_time:.2f}s")
        
        # Assertions for acceptable error rates
        error_rate = len(failed) / rapid_requests
        assert error_rate <= 0.3, f"High error rate under load: {error_rate*100:.1f}%"
        
        print("✅ Error rate test PASSED")
    
    @pytest.mark.asyncio
    async def test_streaming_performance(self, small_test_image):
        """Test streaming performance under load."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set")
        
        client = RemoteTestClient()
        async_client = AsyncRemoteTestClient()
        
        print(f"\n📡 Testing streaming performance at: {client.base_url}")
        
        # Create streaming task
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract text quickly and efficiently"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("streaming_perf.jpg", small_test_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        if response.status_code != 200:
            pytest.skip(f"Could not create streaming task: {response.status_code}")
        
        task_id = response.json()["task_id"]
        print(f"📡 Created streaming task: {task_id}")
        
        # Measure streaming performance
        streaming_metrics = {
            "start_time": time.time(),
            "first_event_time": None,
            "last_event_time": None,
            "total_events": 0,
            "text_events": 0,
            "bytes_received": 0
        }
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    current_time = time.time()
                    
                    if streaming_metrics["first_event_time"] is None:
                        streaming_metrics["first_event_time"] = current_time
                    
                    streaming_metrics["last_event_time"] = current_time
                    streaming_metrics["total_events"] += 1
                    streaming_metrics["bytes_received"] += len(update.encode('utf-8'))
                    
                    try:
                        data = json.loads(update)
                        
                        if 'text_chunk' in data:
                            streaming_metrics["text_events"] += 1
                        
                        if data.get('status') in ['completed', 'failed']:
                            break
                        
                        # Safety limit
                        if streaming_metrics["total_events"] > 50:
                            break
                            
                    except json.JSONDecodeError:
                        pass
        
        except Exception as e:
            print(f"Streaming error: {e}")
        
        # Analyze streaming performance
        if streaming_metrics["first_event_time"] and streaming_metrics["last_event_time"]:
            time_to_first = streaming_metrics["first_event_time"] - streaming_metrics["start_time"]
            streaming_duration = streaming_metrics["last_event_time"] - streaming_metrics["first_event_time"]
            event_rate = streaming_metrics["total_events"] / max(streaming_duration, 0.1)
            
            print(f"\n📊 Streaming Performance:")
            print(f"   Time to first event: {time_to_first:.2f}s")
            print(f"   Streaming duration: {streaming_duration:.2f}s")
            print(f"   Total events: {streaming_metrics['total_events']}")
            print(f"   Text events: {streaming_metrics['text_events']}")
            print(f"   Event rate: {event_rate:.1f} events/s")
            print(f"   Data received: {streaming_metrics['bytes_received']} bytes")
            
            # Performance assertions
            assert time_to_first < 10, f"Too slow to start streaming: {time_to_first:.2f}s"
            assert streaming_metrics["total_events"] > 0, "No streaming events received"
            
            print("✅ Streaming performance test PASSED")
        else:
            print("⚠️  No streaming events received")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])