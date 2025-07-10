#!/usr/bin/env python3
"""
Quick test script for streaming text functionality.
Simple and focused on showing real-time text streaming.
"""

import asyncio
import httpx
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE = "/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/test_image.png"
TEST_PDF = "/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/ocr-pdf-testing.pdf"

async def test_streaming_text():
    """Test streaming text functionality with real-time display."""
    print("🌊 Testing Streaming Text Functionality")
    print("=" * 50)
    
    # Test file (use image for faster testing)
    test_file = TEST_IMAGE
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"📁 Using test file: {Path(test_file).name}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Create streaming task
        print("\n📤 Creating streaming task...")
        
        files = {"file": (Path(test_file).name, open(test_file, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "stream": True,
            "threshold": 500,
            "contrast_level": 1.3,
            "prompt": "อ่านข้อความในภาพนี้อย่างชัดเจน"
        })}
        
        response = await client.post(f"{BASE_URL}/v1/ocr/process-stream", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        task_data = response.json()
        task_id = task_data["task_id"]
        
        print(f"✅ Task created: {task_id}")
        print(f"🎯 File type: {task_data['file_type']}")
        print(f"⚙️  Mode: {task_data['processing_mode']}")
        
        # Step 2: Connect to streaming endpoint
        print(f"\n🌊 Connecting to streaming endpoint...")
        stream_url = f"{BASE_URL}/v1/ocr/stream/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            if stream_response.status_code != 200:
                print(f"❌ Stream connection failed: {stream_response.status_code}")
                return False
            
            print("✅ Connected to stream!")
            print("\n📊 Real-time Updates:")
            print("-" * 50)
            
            # Track streaming data
            start_time = time.time()
            accumulated_text = ""
            chunk_count = 0
            
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    data_content = line[6:]
                    
                    # Skip heartbeat messages
                    if '"heartbeat"' in data_content:
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        
                        # Extract basic info
                        status = update.get("status", "unknown")
                        step = update.get("current_step", "unknown")
                        progress = update.get("progress_percentage", 0)
                        
                        # Show progress for non-streaming steps
                        if not update.get("text_chunk"):
                            print(f"📈 {progress:5.1f}% | {step:15} | {status}")
                        
                        # Handle streaming text chunks
                        if "text_chunk" in update and update["text_chunk"]:
                            chunk = update["text_chunk"]
                            accumulated = update.get("accumulated_text", "")
                            chunk_count += 1
                            
                            # Show streaming text with nice formatting
                            print(f"\n🔤 Chunk #{chunk_count}: '{chunk}'")
                            print(f"📝 Current text: '{accumulated}'")
                            print(f"📏 Length: {len(accumulated)} characters")
                            
                            accumulated_text = accumulated
                        
                        # Check completion
                        if status in ["completed", "failed", "cancelled"]:
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            print(f"\n🏁 Final Status: {status}")
                            print(f"⏱️  Duration: {duration:.2f} seconds")
                            print(f"📊 Text chunks received: {chunk_count}")
                            
                            if status == "completed":
                                print(f"\n✅ FINAL RESULT:")
                                print(f"📖 Complete text: '{accumulated_text}'")
                                print(f"📏 Total length: {len(accumulated_text)} characters")
                                
                                # Show final results if available
                                if "cumulative_results" in update and update["cumulative_results"]:
                                    results = update["cumulative_results"]
                                    print(f"📄 Pages processed: {len(results)}")
                                    
                                    for i, result in enumerate(results):
                                        text = result.get('extracted_text', '')
                                        print(f"   Page {i+1}: {text[:50]}...")
                                
                                return True
                            else:
                                error_msg = update.get("error_message", "Unknown error")
                                print(f"❌ Error: {error_msg}")
                                return False
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Invalid JSON: {data_content}")
                        continue
            
            print("❌ Stream ended without completion")
            return False

async def test_both_modes():
    """Test both streaming and non-streaming modes for comparison."""
    print("\n🔄 COMPARISON TEST: Streaming vs Non-Streaming")
    print("=" * 60)
    
    test_file = TEST_IMAGE
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test 1: Streaming mode
        print("\n1️⃣  Testing STREAMING mode...")
        
        files = {"file": (Path(test_file).name, open(test_file, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "อ่านข้อความในภาพนี้"
        })}
        
        start_time = time.time()
        response = await client.post(f"{BASE_URL}/v1/ocr/process-stream", files=files, data=data)
        
        if response.status_code == 200:
            task_data = response.json()
            print(f"✅ Streaming task created: {task_data['task_id']}")
            
            # Quick stream check (just get first few updates)
            stream_url = f"{BASE_URL}/v1/ocr/stream/{task_data['task_id']}"
            async with client.stream("GET", stream_url) as stream_response:
                chunk_count = 0
                async for line in stream_response.aiter_lines():
                    if line.startswith("data: ") and '"text_chunk"' in line:
                        chunk_count += 1
                        if chunk_count >= 3:  # Just check first few chunks
                            break
                
                streaming_time = time.time() - start_time
                print(f"✅ Streaming mode: {chunk_count} chunks received in {streaming_time:.2f}s")
        else:
            print(f"❌ Streaming mode failed: {response.status_code}")
        
        # Test 2: Non-streaming mode
        print("\n2️⃣  Testing NON-STREAMING mode...")
        
        files = {"file": (Path(test_file).name, open(test_file, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "stream": False,
            "prompt": "อ่านข้อความในภาพนี้"
        })}
        
        start_time = time.time()
        response = await client.post(f"{BASE_URL}/v1/ocr/process-stream", files=files, data=data)
        
        if response.status_code == 200:
            task_data = response.json()
            print(f"✅ Non-streaming task created: {task_data['task_id']}")
            
            # Wait for completion
            stream_url = f"{BASE_URL}/v1/ocr/stream/{task_data['task_id']}"
            async with client.stream("GET", stream_url) as stream_response:
                async for line in stream_response.aiter_lines():
                    if line.startswith("data: ") and '"status":"completed"' in line:
                        non_streaming_time = time.time() - start_time
                        print(f"✅ Non-streaming mode: completed in {non_streaming_time:.2f}s")
                        break
        else:
            print(f"❌ Non-streaming mode failed: {response.status_code}")

async def main():
    """Main test function."""
    print("🚀 Quick Streaming Text Test")
    print("Testing streaming text functionality with real-time display")
    print("=" * 60)
    
    try:
        # Test 1: Full streaming test
        success = await test_streaming_text()
        
        if success:
            print("\n🎉 Streaming text test completed successfully!")
            
            # Test 2: Comparison test
            await test_both_modes()
            
        else:
            print("\n❌ Streaming text test failed!")
            
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit(1)