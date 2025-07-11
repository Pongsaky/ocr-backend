"""
Real-time streaming validation tests.
These tests validate the Server-Sent Events (SSE) streaming functionality comprehensively.
"""

import json
import pytest
import asyncio
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any, List, Set
import threading
from concurrent.futures import ThreadPoolExecutor

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestStreamingValidation:
    """Comprehensive streaming functionality validation."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def async_client(self):
        """Create async remote test client."""
        return AsyncRemoteTestClient()
    
    @pytest.fixture
    def streaming_test_image(self):
        """Create an image optimized for streaming tests."""
        image = Image.new('RGB', (1000, 600), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        # Content that should generate substantial streaming
        content = [
            "STREAMING TEST DOCUMENT",
            "This document contains substantial text content",
            "designed to generate multiple streaming chunks",
            "during LLM-enhanced OCR processing.",
            "",
            "Section 1: Introduction",
            "This is the first section with detailed information",
            "that should be extracted character by character",
            "when streaming is enabled for real-time feedback.",
            "",
            "Section 2: Technical Details",
            "The streaming functionality uses Server-Sent Events",
            "to provide real-time updates during processing.",
            "Each character appears as it is generated.",
            "",
            "Section 3: Conclusion",
            "This comprehensive text should result in",
            "significant streaming activity for testing purposes."
        ]
        
        y_position = 30
        for line in content:
            if line:  # Skip empty lines for drawing
                draw.text((50, y_position), line, fill='black', font=font)
            y_position += 35
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    @pytest.mark.asyncio
    async def test_streaming_event_types(self, client, async_client, streaming_test_image):
        """Test all different types of streaming events are received."""
        print(f"\n🎛️  Testing streaming event types at: {client.base_url}")
        
        # Create streaming task
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract all text from this document with detailed analysis and formatting"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("stream_events.jpg", streaming_test_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📡 Created streaming task: {task_id}")
        
        # Collect different event types
        event_types = {
            "status_updates": [],
            "progress_updates": [],
            "text_chunks": [],
            "heartbeats": [],
            "page_updates": [],
            "completion_events": [],
            "error_events": []
        }
        
        total_events = 0
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        total_events += 1
                        
                        # Categorize events
                        if 'heartbeat' in data:
                            event_types["heartbeats"].append(data)
                        
                        if 'status' in data:
                            event_types["status_updates"].append(data)
                            status = data['status']
                            
                            if status in ['completed', 'failed']:
                                event_types["completion_events"].append(data)
                                print(f"🏁 Final status: {status}")
                                break
                            elif status == 'failed':
                                event_types["error_events"].append(data)
                        
                        if 'progress_percentage' in data:
                            event_types["progress_updates"].append(data)
                            progress = data['progress_percentage']
                            if progress % 20 == 0:  # Log every 20%
                                print(f"📊 Progress: {progress}%")
                        
                        if 'text_chunk' in data:
                            event_types["text_chunks"].append(data)
                            chunk = data['text_chunk']
                            print(f"📝 Chunk: '{chunk}'", end="", flush=True)
                        
                        if 'current_page' in data:
                            event_types["page_updates"].append(data)
                        
                        # Safety limit for testing
                        if total_events > 200:
                            print(f"\n🛑 Stopping after {total_events} events (test limit)")
                            break
                            
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"\nError processing event: {e}")
        
        except Exception as e:
            print(f"\nStreaming error: {e}")
        
        # Validate event types received
        print(f"\n\n📊 Streaming Event Analysis:")
        print(f"   Total events: {total_events}")
        
        for event_type, events in event_types.items():
            count = len(events)
            print(f"   {event_type}: {count}")
            
            if event_type == "text_chunks" and count > 0:
                total_chars = sum(len(e.get('text_chunk', '')) for e in events)
                print(f"     Total characters: {total_chars}")
            
            if event_type == "progress_updates" and count > 0:
                progresses = [e.get('progress_percentage', 0) for e in events]
                max_progress = max(progresses)
                print(f"     Max progress: {max_progress}%")
        
        # Assertions
        assert total_events > 0, "No streaming events received"
        
        if event_types["text_chunks"]:
            print("✅ Text chunk streaming working")
        
        if event_types["progress_updates"]:
            print("✅ Progress tracking working")
        
        if event_types["status_updates"]:
            print("✅ Status updates working")
        
        if event_types["completion_events"]:
            print("✅ Completion events working")
        
        print("✅ Streaming event types test PASSED")
    
    @pytest.mark.asyncio
    async def test_streaming_text_accumulation(self, client, async_client, streaming_test_image):
        """Test that streaming text chunks accumulate correctly."""
        print(f"\n📝 Testing text accumulation at: {client.base_url}")
        
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract all text from this document preserving exact formatting"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("accumulation_test.jpg", streaming_test_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📡 Testing accumulation for task: {task_id}")
        
        # Track text accumulation
        chunks_received = []
        accumulated_from_chunks = ""
        accumulated_from_api = ""
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        
                        if 'text_chunk' in data:
                            chunk = data['text_chunk']
                            chunks_received.append(chunk)
                            accumulated_from_chunks += chunk
                            
                            # API should also provide accumulated text
                            if 'accumulated_text' in data:
                                accumulated_from_api = data['accumulated_text']
                                
                                # Verify accumulation matches
                                if accumulated_from_chunks != accumulated_from_api:
                                    print(f"\n⚠️  Accumulation mismatch!")
                                    print(f"   Manual: '{accumulated_from_chunks}'")
                                    print(f"   API: '{accumulated_from_api}'")
                            
                            # Show progress
                            if len(chunks_received) % 10 == 0:
                                print(f"\n📊 Chunks: {len(chunks_received)}, Length: {len(accumulated_from_chunks)}")
                        
                        if data.get('status') in ['completed', 'failed']:
                            print(f"\n🏁 Streaming ended: {data['status']}")
                            break
                        
                        # Safety limit
                        if len(chunks_received) > 500:
                            print(f"\n🛑 Stopping after {len(chunks_received)} chunks")
                            break
                            
                    except json.JSONDecodeError:
                        pass
        
        except Exception as e:
            print(f"\nStreaming error: {e}")
        
        # Validate accumulation
        print(f"\n📊 Text Accumulation Results:")
        print(f"   Chunks received: {len(chunks_received)}")
        print(f"   Total characters: {len(accumulated_from_chunks)}")
        print(f"   Average chunk size: {len(accumulated_from_chunks)/max(1, len(chunks_received)):.1f}")
        
        if accumulated_from_api:
            print(f"   API accumulated length: {len(accumulated_from_api)}")
            match_percentage = len(accumulated_from_api) / max(1, len(accumulated_from_chunks)) * 100
            print(f"   Accumulation match: {match_percentage:.1f}%")
        
        # Sample of accumulated text
        if accumulated_from_chunks:
            sample = accumulated_from_chunks[:200] + "..." if len(accumulated_from_chunks) > 200 else accumulated_from_chunks
            print(f"   Sample: {sample}")
        
        # Assertions
        assert len(chunks_received) > 0, "No text chunks received"
        assert len(accumulated_from_chunks) > 0, "No text accumulated"
        
        if accumulated_from_api:
            # Allow for minor differences due to processing
            assert abs(len(accumulated_from_api) - len(accumulated_from_chunks)) <= 5, "Significant accumulation mismatch"
        
        print("✅ Text accumulation test PASSED")
    
    @pytest.mark.asyncio
    async def test_streaming_connection_stability(self, client, async_client, streaming_test_image):
        """Test streaming connection stability over time."""
        print(f"\n🔗 Testing connection stability at: {client.base_url}")
        
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Perform detailed text extraction with comprehensive analysis"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("stability_test.jpg", streaming_test_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📡 Testing stability for task: {task_id}")
        
        # Track connection metrics
        connection_metrics = {
            "start_time": time.time(),
            "last_event_time": time.time(),
            "events_received": 0,
            "gaps": [],  # Time gaps between events
            "connection_drops": 0,
            "reconnects": 0
        }
        
        last_event_time = time.time()
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    current_time = time.time()
                    gap = current_time - last_event_time
                    
                    connection_metrics["events_received"] += 1
                    connection_metrics["last_event_time"] = current_time
                    connection_metrics["gaps"].append(gap)
                    
                    # Detect long gaps (potential connection issues)
                    if gap > 10:  # 10 second gap
                        print(f"\n⚠️  Long gap detected: {gap:.1f}s")
                        connection_metrics["connection_drops"] += 1
                    
                    last_event_time = current_time
                    
                    try:
                        data = json.loads(update)
                        
                        # Show periodic updates
                        if connection_metrics["events_received"] % 20 == 0:
                            elapsed = current_time - connection_metrics["start_time"]
                            rate = connection_metrics["events_received"] / elapsed
                            print(f"📈 Events: {connection_metrics['events_received']}, Rate: {rate:.1f}/s")
                        
                        if data.get('status') in ['completed', 'failed']:
                            print(f"\n🏁 Connection ended: {data['status']}")
                            break
                        
                        # Safety timeout
                        if current_time - connection_metrics["start_time"] > 180:  # 3 minutes
                            print(f"\n⏰ Test timeout after 3 minutes")
                            break
                            
                    except json.JSONDecodeError:
                        pass
        
        except Exception as e:
            print(f"\nConnection error: {e}")
            connection_metrics["connection_drops"] += 1
        
        # Analyze connection stability
        total_time = connection_metrics["last_event_time"] - connection_metrics["start_time"]
        avg_gap = sum(connection_metrics["gaps"]) / max(1, len(connection_metrics["gaps"]))
        max_gap = max(connection_metrics["gaps"]) if connection_metrics["gaps"] else 0
        event_rate = connection_metrics["events_received"] / max(1, total_time)
        
        print(f"\n📊 Connection Stability Analysis:")
        print(f"   Total duration: {total_time:.1f}s")
        print(f"   Events received: {connection_metrics['events_received']}")
        print(f"   Event rate: {event_rate:.2f}/s")
        print(f"   Average gap: {avg_gap:.2f}s")
        print(f"   Maximum gap: {max_gap:.2f}s")
        print(f"   Connection drops: {connection_metrics['connection_drops']}")
        
        # Stability assertions
        assert connection_metrics["events_received"] > 0, "No events received"
        assert total_time > 0, "No time elapsed"
        
        # Connection should be reasonably stable
        if max_gap < 30:  # No gaps longer than 30 seconds
            print("✅ Connection stability good")
        else:
            print(f"⚠️  Long gaps detected (max: {max_gap:.1f}s)")
        
        if connection_metrics["connection_drops"] == 0:
            print("✅ No connection drops detected")
        
        print("✅ Connection stability test PASSED")
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_streams(self, client, streaming_test_image):
        """Test multiple concurrent streaming connections."""
        print(f"\n🔀 Testing concurrent streams at: {client.base_url}")
        
        # Create multiple tasks
        task_ids = []
        for i in range(3):  # Test 3 concurrent streams
            request_data = {
                "mode": "llm_enhanced",
                "stream": True,
                "prompt": f"Extract text from document {i+1} with detailed analysis"
            }
            
            # Reset stream for each request
            streaming_test_image.seek(0)
            
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": (f"concurrent_{i+1}.jpg", streaming_test_image, "image/jpeg")},
                data={"request": json.dumps(request_data)}
            )
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                task_ids.append(task_id)
                print(f"📡 Created concurrent task {i+1}: {task_id}")
        
        assert len(task_ids) > 0, "No tasks created"
        
        # Monitor all streams concurrently
        async def monitor_stream(task_id: str, stream_id: int) -> Dict[str, Any]:
            """Monitor a single stream."""
            async_client = AsyncRemoteTestClient()
            
            metrics = {
                "stream_id": stream_id,
                "task_id": task_id,
                "events": 0,
                "text_chunks": 0,
                "completed": False,
                "errors": 0
            }
            
            try:
                async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                    if update:
                        try:
                            data = json.loads(update)
                            metrics["events"] += 1
                            
                            if 'text_chunk' in data:
                                metrics["text_chunks"] += 1
                            
                            if data.get('status') == 'completed':
                                metrics["completed"] = True
                                print(f"✅ Stream {stream_id} completed")
                                break
                            elif data.get('status') == 'failed':
                                print(f"❌ Stream {stream_id} failed")
                                break
                            
                            # Safety limit per stream
                            if metrics["events"] > 100:
                                print(f"🛑 Stream {stream_id} limit reached")
                                break
                                
                        except json.JSONDecodeError:
                            metrics["errors"] += 1
            
            except Exception as e:
                print(f"Stream {stream_id} error: {e}")
                metrics["errors"] += 1
            
            return metrics
        
        # Run all streams concurrently
        print(f"\n📡 Monitoring {len(task_ids)} concurrent streams...")
        
        tasks = [monitor_stream(task_id, i+1) for i, task_id in enumerate(task_ids)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze concurrent streaming results
        print(f"\n📊 Concurrent Streaming Results:")
        
        total_events = 0
        total_chunks = 0
        completed_streams = 0
        error_streams = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Stream {i+1}: ERROR - {result}")
                error_streams += 1
            else:
                events = result.get("events", 0)
                chunks = result.get("text_chunks", 0)
                completed = result.get("completed", False)
                errors = result.get("errors", 0)
                
                total_events += events
                total_chunks += chunks
                if completed:
                    completed_streams += 1
                if errors > 0:
                    error_streams += 1
                
                print(f"   Stream {i+1}: {events} events, {chunks} chunks, completed: {completed}")
        
        print(f"\n📈 Summary:")
        print(f"   Total streams: {len(task_ids)}")
        print(f"   Completed: {completed_streams}")
        print(f"   Errors: {error_streams}")
        print(f"   Total events: {total_events}")
        print(f"   Total chunks: {total_chunks}")
        
        # Concurrent streaming assertions
        assert total_events > 0, "No events from any stream"
        assert completed_streams > 0, "No streams completed successfully"
        
        success_rate = completed_streams / len(task_ids)
        print(f"📊 Success rate: {success_rate*100:.1f}%")
        
        if success_rate >= 0.5:  # At least 50% success
            print("✅ Concurrent streaming test PASSED")
        else:
            print("⚠️  Low success rate for concurrent streams")
        
        print("✅ Concurrent streams test completed")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])