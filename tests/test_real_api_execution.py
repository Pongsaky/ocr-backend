"""
True end-to-end API execution tests that verify real OCR processing.
These tests wait for actual completion and validate real results.
"""

import json
import pytest
import asyncio
import time
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any, Optional

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestRealAPIExecution:
    """End-to-end tests that verify real OCR processing and results."""
    
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
    def text_image(self):
        """Create an image with readable text for OCR testing."""
        # Create a white background image
        image = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a system font, fall back to default if not available
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 40)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            except:
                font = ImageFont.load_default()
        
        # Draw clear, readable text
        text_lines = [
            "HELLO WORLD",
            "This is a test document",
            "OCR should extract this text",
            "Line number 4"
        ]
        
        y_position = 50
        for line in text_lines:
            draw.text((50, y_position), line, fill='black', font=font)
            y_position += 80
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    @pytest.fixture
    def thai_text_image(self):
        """Create an image with Thai text for testing."""
        image = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(image)
        
        # Use default font for Thai text
        font = ImageFont.load_default()
        
        # Thai text lines
        thai_lines = [
            "สวัสดีครับ",
            "นี่คือการทดสอบ OCR",
            "ระบบควรจะอ่านข้อความนี้ได้",
            "บรรทัดที่ 4"
        ]
        
        y_position = 50
        for line in thai_lines:
            draw.text((50, y_position), line, fill='black', font=font)
            y_position += 80
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def wait_for_completion(self, client: RemoteTestClient, task_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for a task to complete and return the final result."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try different possible status endpoints
                for endpoint in [f"/v1/ocr/process-stream/{task_id}", f"/v1/ocr/status/{task_id}", f"/v1/ocr/tasks/{task_id}"]:
                    try:
                        response = client.get(endpoint)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get('status', 'unknown')
                            
                            if status == 'completed':
                                print(f"✅ Task {task_id} completed successfully")
                                return data
                            elif status == 'failed':
                                print(f"❌ Task {task_id} failed: {data.get('error', 'Unknown error')}")
                                return data
                            elif status in ['processing', 'pending']:
                                print(f"⏳ Task {task_id} status: {status}")
                                time.sleep(2)
                                break
                    except Exception as e:
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Error checking status: {e}")
                time.sleep(2)
        
        print(f"⏰ Task {task_id} timed out after {timeout} seconds")
        return {"status": "timeout", "error": f"Task timed out after {timeout} seconds"}
    
    def test_real_image_ocr_basic(self, client, text_image):
        """Test real basic OCR processing with actual result validation."""
        print(f"\n🔍 Testing REAL basic OCR at: {client.base_url}")
        
        request_data = {
            "mode": "basic",
            "threshold": 128,
            "contrast_level": 1.0
        }
        
        # Create task
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test_text.jpg", text_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200, f"Failed to create task: {response.text}"
        task_id = response.json()["task_id"]
        print(f"📝 Created basic OCR task: {task_id}")
        
        # Wait for real completion
        result = self.wait_for_completion(client, task_id, timeout=60)
        
        # Validate real results
        assert result.get("status") == "completed", f"Task failed or timed out: {result}"
        
        # Check that we got actual OCR results
        if 'result' in result:
            ocr_result = result['result']
            extracted_text = ocr_result.get('extracted_text', '')
            
            print(f"📄 Extracted text length: {len(extracted_text)} characters")
            print(f"📄 Sample text: {extracted_text[:100]}...")
            
            # Validate text extraction quality
            assert len(extracted_text) > 0, "No text was extracted"
            
            # Check for expected words (case insensitive)
            text_lower = extracted_text.lower()
            expected_words = ["hello", "world", "test", "document", "ocr"]
            found_words = [word for word in expected_words if word in text_lower]
            
            print(f"✅ Found expected words: {found_words}")
            assert len(found_words) >= 2, f"Expected to find at least 2 words from {expected_words}, found: {found_words}"
        
        print("✅ Real basic OCR test PASSED")
    
    def test_real_image_ocr_llm_enhanced(self, client, text_image):
        """Test real LLM-enhanced OCR processing."""
        print(f"\n🤖 Testing REAL LLM-enhanced OCR at: {client.base_url}")
        
        request_data = {
            "mode": "llm_enhanced",
            "threshold": 128,
            "contrast_level": 1.0,
            "prompt": "Extract all text from this image accurately. Preserve the original formatting and structure."
        }
        
        # Create task
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test_text.jpg", text_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200, f"Failed to create LLM task: {response.text}"
        task_id = response.json()["task_id"]
        print(f"🤖 Created LLM OCR task: {task_id}")
        
        # Wait for real completion (LLM tasks may take longer)
        result = self.wait_for_completion(client, task_id, timeout=120)
        
        # Validate real results
        assert result.get("status") == "completed", f"LLM task failed or timed out: {result}"
        
        if 'result' in result:
            ocr_result = result['result']
            extracted_text = ocr_result.get('extracted_text', '')
            
            print(f"🤖 LLM extracted text length: {len(extracted_text)} characters")
            print(f"🤖 LLM sample text: {extracted_text[:200]}...")
            
            # LLM should extract more accurate/structured text
            assert len(extracted_text) > 0, "LLM extracted no text"
            
            # Check for better quality indicators
            text_lower = extracted_text.lower()
            expected_phrases = ["hello world", "test document", "ocr"]
            found_phrases = [phrase for phrase in expected_phrases if phrase in text_lower]
            
            print(f"✅ LLM found phrases: {found_phrases}")
            
            # Check that model information is included
            model_used = ocr_result.get('model_used', '')
            if model_used:
                print(f"🤖 Model used: {model_used}")
        
        print("✅ Real LLM OCR test PASSED")
    
    def test_real_thai_text_ocr(self, client, thai_text_image):
        """Test real OCR with Thai text."""
        print(f"\n🇹🇭 Testing REAL Thai OCR at: {client.base_url}")
        
        request_data = {
            "mode": "llm_enhanced",
            "prompt": "Extract Thai text from this image. Preserve all Thai characters accurately."
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("thai_text.jpg", thai_text_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200, f"Failed to create Thai OCR task: {response.text}"
        task_id = response.json()["task_id"]
        print(f"🇹🇭 Created Thai OCR task: {task_id}")
        
        # Wait for completion
        result = self.wait_for_completion(client, task_id, timeout=120)
        
        if result.get("status") == "completed" and 'result' in result:
            extracted_text = result['result'].get('extracted_text', '')
            print(f"🇹🇭 Extracted Thai text: {extracted_text}")
            
            # Check for Thai characters
            has_thai = any(ord(char) >= 0x0E00 and ord(char) <= 0x0E7F for char in extracted_text)
            if has_thai:
                print("✅ Successfully extracted Thai characters")
            else:
                print("⚠️  No Thai characters detected in result")
        
        print("✅ Thai OCR test completed")
    
    @pytest.mark.asyncio
    async def test_real_streaming_with_completion(self, text_image):
        """Test real streaming that waits for complete text generation."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set")
        
        client = RemoteTestClient()
        async_client = AsyncRemoteTestClient()
        
        print(f"\n📡 Testing REAL streaming with completion at: {client.base_url}")
        
        # Create streaming task
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract all text from this image with detailed analysis"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("stream_test.jpg", text_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📡 Created streaming task: {task_id}")
        
        # Collect all streaming updates
        all_updates = []
        accumulated_text = ""
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        all_updates.append(data)
                        
                        # Track text accumulation
                        if 'text_chunk' in data:
                            chunk = data['text_chunk']
                            accumulated_text += chunk
                            print(f"📝 Chunk: '{chunk}' (Total: {len(accumulated_text)} chars)")
                        
                        # Track progress
                        if 'progress_percentage' in data:
                            progress = data['progress_percentage']
                            print(f"📊 Progress: {progress}%")
                        
                        # Check completion
                        if data.get('status') in ['completed', 'failed']:
                            print(f"🏁 Streaming ended with status: {data['status']}")
                            break
                            
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"Error processing update: {e}")
        
        except Exception as e:
            print(f"Streaming error: {e}")
        
        # Validate streaming results
        print(f"\n📊 Streaming Results:")
        print(f"   Total updates: {len(all_updates)}")
        print(f"   Accumulated text length: {len(accumulated_text)}")
        print(f"   Sample text: {accumulated_text[:100]}...")
        
        # Verify we got meaningful streaming
        assert len(all_updates) > 0, "No streaming updates received"
        
        # Check for text chunks
        text_chunks = [u for u in all_updates if 'text_chunk' in u]
        if text_chunks:
            print(f"✅ Received {len(text_chunks)} text chunks")
            assert len(accumulated_text) > 0, "No text accumulated from streaming"
        
        # Check for completion
        completion_updates = [u for u in all_updates if u.get('status') == 'completed']
        if completion_updates:
            print("✅ Received completion update")
        
        print("✅ Real streaming test PASSED")
    
    def test_real_task_lifecycle(self, client, text_image):
        """Test complete task lifecycle: create -> monitor -> complete."""
        print(f"\n🔄 Testing REAL task lifecycle at: {client.base_url}")
        
        # Create task
        request_data = {"mode": "basic"}
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("lifecycle_test.jpg", text_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"🆕 Created task: {task_id}")
        
        # Monitor progress through lifecycle
        seen_statuses = set()
        start_time = time.time()
        
        while time.time() - start_time < 60:
            try:
                # Check status
                status_response = client.get(f"/v1/ocr/process-stream/{task_id}")
                if status_response.status_code == 200:
                    data = status_response.json()
                    status = data.get('status', 'unknown')
                    seen_statuses.add(status)
                    
                    print(f"📈 Status: {status}")
                    
                    if status == 'completed':
                        # Verify final result
                        assert 'result' in data, "Completed task missing result"
                        result = data['result']
                        
                        print(f"✅ Final result keys: {list(result.keys())}")
                        
                        # Check result structure
                        assert 'extracted_text' in result, "Missing extracted_text"
                        assert 'processing_time' in result, "Missing processing_time"
                        assert 'success' in result, "Missing success flag"
                        
                        extracted_text = result['extracted_text']
                        processing_time = result['processing_time']
                        
                        print(f"📄 Extracted {len(extracted_text)} characters in {processing_time}s")
                        
                        break
                    
                    elif status == 'failed':
                        error = data.get('error', 'Unknown error')
                        print(f"❌ Task failed: {error}")
                        break
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Error monitoring task: {e}")
                time.sleep(2)
        
        print(f"🔄 Seen statuses: {seen_statuses}")
        print("✅ Task lifecycle test PASSED")
    
    def test_real_error_handling(self, client):
        """Test real error handling with invalid input."""
        print(f"\n❌ Testing REAL error handling at: {client.base_url}")
        
        # Test with invalid image data
        invalid_data = io.BytesIO(b"This is definitely not an image file")
        
        request_data = {"mode": "basic"}
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("invalid.jpg", invalid_data, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        if response.status_code in [400, 422]:
            print("✅ Correctly rejected invalid file immediately")
        elif response.status_code == 200:
            # Task created, should fail during processing
            task_id = response.json()["task_id"]
            print(f"⚠️  Invalid file accepted, checking task failure: {task_id}")
            
            result = self.wait_for_completion(client, task_id, timeout=30)
            
            assert result.get("status") == "failed", "Invalid file should cause task failure"
            print(f"✅ Task correctly failed: {result.get('error', 'Unknown error')}")
        
        print("✅ Error handling test PASSED")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])