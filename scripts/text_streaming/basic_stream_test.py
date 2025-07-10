#!/usr/bin/env python3
"""
Test basic streaming functionality without LLM.
"""

import asyncio
import httpx
import json
from pathlib import Path

async def test_basic_streaming():
    """Test basic streaming."""
    print("🌊 Testing basic streaming functionality...")
    
    # Create a test request
    test_image = Path("test_image.png")
    if not test_image.exists():
        print("❌ Test image not found")
        return False
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create streaming task
        print("📤 Creating basic streaming task...")
        files = {"file": (test_image.name, open(test_image, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "basic",
            "threshold": 500,
            "stream": False  # Basic mode doesn't need streaming
        })}
        
        response = await client.post(
            "http://localhost:8000/v1/ocr/process-stream",
            files=files,
            data=data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Task created: {task_id}")
        
        # Step 2: Connect to streaming
        print("🌊 Connecting to stream...")
        stream_url = f"http://localhost:8000/v1/ocr/stream/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            print(f"📊 Stream status: {stream_response.status_code}")
            
            if stream_response.status_code != 200:
                print(f"❌ Stream failed: {stream_response.status_code}")
                return False
            
            update_count = 0
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    update_count += 1
                    data_content = line[6:]
                    
                    # Skip heartbeat
                    if '"heartbeat"' in data_content:
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        status = update.get("status", "unknown")
                        step = update.get("current_step", "unknown")
                        progress = update.get("progress_percentage", 0)
                        
                        print(f"📊 Update {update_count}: {progress:.1f}% | {step} | {status}")
                        
                        # Show page results
                        if "latest_page_result" in update and update["latest_page_result"]:
                            result = update["latest_page_result"]
                            print(f"📄 Page result: {result.get('extracted_text', 'No text')[:100]}...")
                        
                        # Check completion
                        if status in ["completed", "failed", "cancelled"]:
                            print(f"🏁 Final status: {status}")
                            
                            if "cumulative_results" in update:
                                results = update["cumulative_results"]
                                if results:
                                    print(f"✅ Final text: {results[0].get('extracted_text', 'No text')[:100]}...")
                            
                            return status == "completed"
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  JSON error: {data_content}")
        
        print("❌ Stream ended unexpectedly")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_streaming())
    if success:
        print("🎉 Basic streaming test passed!")
    else:
        print("❌ Basic streaming test failed!")