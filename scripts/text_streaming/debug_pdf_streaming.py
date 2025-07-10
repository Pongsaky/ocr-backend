#!/usr/bin/env python3
"""
Debug PDF streaming functionality to see streaming text chunks.
"""

import asyncio
import httpx
import json
from pathlib import Path

async def debug_pdf_streaming():
    """Debug PDF streaming with detailed logging."""
    
    print("🔍 Debugging PDF Streaming...")
    
    # Test file
    test_file = "/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/ocr-pdf-testing.pdf"
    
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Create streaming task
        print("📤 Creating PDF streaming task...")
        
        files = {"file": (Path(test_file).name, open(test_file, "rb"), "application/pdf")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "stream": True,
            "threshold": 500,
            "contrast_level": 1.3,
            "dpi": 300,
            "prompt": "อ่านข้อความในภาพนี้อย่างชัดเจน"
        })}
        
        response = await client.post("http://localhost:8000/v1/ocr/process-stream", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Task created: {task_id}")
        
        # Connect to stream
        print("🌊 Connecting to streaming endpoint...")
        stream_url = f"http://localhost:8000/v1/ocr/stream/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            if stream_response.status_code != 200:
                print(f"❌ Stream failed: {stream_response.status_code}")
                return
            
            print("✅ Connected to stream!")
            print("📊 Streaming updates:")
            
            update_count = 0
            text_chunks = []
            
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    update_count += 1
                    data_content = line[6:]
                    
                    # Skip heartbeat
                    if '"heartbeat"' in data_content:
                        print(f"💓 Heartbeat {update_count}")
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        
                        # Extract key info
                        status = update.get("status", "unknown")
                        step = update.get("current_step", "unknown")
                        progress = update.get("progress_percentage", 0)
                        message = update.get("message", "")
                        
                        # Check for text chunks
                        if "text_chunk" in update and update["text_chunk"]:
                            chunk = update["text_chunk"]
                            accumulated = update.get("accumulated_text", "")
                            text_chunks.append(chunk)
                            print(f"🔤 #{len(text_chunks)} TEXT CHUNK: '{chunk}'")
                            print(f"📝 Accumulated: '{accumulated}'")
                        else:
                            print(f"📈 Update {update_count}: {progress:.1f}% | {step} | {status} | {message}")
                        
                        # Show page results
                        if "latest_page_result" in update and update["latest_page_result"]:
                            page_result = update["latest_page_result"]
                            page_num = page_result.get("page_number", "?")
                            text = page_result.get("extracted_text", "")
                            print(f"📄 Page {page_num} completed: {text[:100]}...")
                        
                        # Check completion
                        if status in ["completed", "failed", "cancelled"]:
                            print(f"🏁 Final status: {status}")
                            print(f"📊 Total text chunks received: {len(text_chunks)}")
                            
                            if text_chunks:
                                print("✅ Text chunks found!")
                                for i, chunk in enumerate(text_chunks[:5]):  # Show first 5
                                    print(f"  {i+1}. '{chunk}'")
                            else:
                                print("❌ No text chunks found")
                            
                            return
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  JSON error: {data_content}")
            
            print("❌ Stream ended unexpectedly")

if __name__ == "__main__":
    asyncio.run(debug_pdf_streaming())