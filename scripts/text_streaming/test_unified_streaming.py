#!/usr/bin/env python3
"""
Test script for unified streaming functionality.
Tests both image and PDF processing with streaming support.
"""

import asyncio
import httpx
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
UNIFIED_ENDPOINT = f"{BASE_URL}/v1/ocr/process-stream"
STREAMING_ENDPOINT = f"{BASE_URL}/v1/ocr/stream"

# Test files
IMAGE_FILE = Path("test_image.png")
PDF_FILE = Path("/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/ocr-pdf-testing.pdf")

async def test_image_streaming():
    """Test image processing with streaming."""
    print("🖼️  Testing Image Streaming...")
    
    if not IMAGE_FILE.exists():
        print(f"❌ Image file not found: {IMAGE_FILE}")
        return False
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Create streaming task
        print("📤 Creating streaming task...")
        files = {"file": (IMAGE_FILE.name, open(IMAGE_FILE, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "threshold": 500,
            "contrast_level": 1.3,
            "stream": True,
            "prompt": "อ่านข้อความในภาพนี้"
        })}
        
        response = await client.post(UNIFIED_ENDPOINT, files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed to create task: {response.status_code} - {response.text}")
            return False
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Created task: {task_id}")
        print(f"🎯 File type: {task_data['file_type']}")
        print(f"⚙️  Mode: {task_data['processing_mode']}")
        
        # Step 2: Connect to streaming endpoint
        print(f"🌊 Connecting to streaming endpoint...")
        stream_url = f"{STREAMING_ENDPOINT}/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            if stream_response.status_code != 200:
                print(f"❌ Failed to connect to stream: {stream_response.status_code}")
                return False
            
            print("🌊 Connected to stream, processing updates...")
            collected_text = ""
            
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    data_content = line[6:]
                    
                    # Skip heartbeat messages
                    if '"heartbeat"' in data_content:
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        status = update.get("status", "unknown")
                        step = update.get("current_step", "unknown")
                        progress = update.get("progress_percentage", 0)
                        
                        print(f"📊 Progress: {progress:.1f}% | Step: {step} | Status: {status}")
                        
                        # Handle streaming text
                        if "text_chunk" in update and update["text_chunk"]:
                            print(f"📝 Text chunk: {update['text_chunk'][:50]}...")
                            collected_text += update["text_chunk"]
                        
                        # Handle page completion
                        if "latest_page_result" in update and update["latest_page_result"]:
                            result = update["latest_page_result"]
                            print(f"📄 Page {result['page_number']} completed")
                            print(f"✅ Extracted text: {result['extracted_text'][:100]}...")
                        
                        # Check completion
                        if status in ["completed", "failed", "cancelled"]:
                            print(f"🏁 Final status: {status}")
                            if status == "completed":
                                print(f"📝 Final collected text: {collected_text[:200]}...")
                                return True
                            else:
                                print(f"❌ Processing failed: {update.get('error_message', 'Unknown error')}")
                                return False
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Invalid JSON: {data_content}")
                        continue
        
        print("❌ Stream ended without completion")
        return False

async def test_pdf_streaming():
    """Test PDF processing with streaming."""
    print("\n📄 Testing PDF Streaming...")
    
    if not PDF_FILE.exists():
        print(f"❌ PDF file not found: {PDF_FILE}")
        return False
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Create streaming task
        print("📤 Creating streaming task...")
        files = {"file": (PDF_FILE.name, open(PDF_FILE, "rb"), "application/pdf")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "threshold": 500,
            "contrast_level": 1.3,
            "dpi": 300,
            "stream": True,
            "prompt": "อ่านข้อความในภาพนี้อย่างแม่นยำ"
        })}
        
        response = await client.post(UNIFIED_ENDPOINT, files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed to create task: {response.status_code} - {response.text}")
            return False
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Created task: {task_id}")
        print(f"🎯 File type: {task_data['file_type']}")
        print(f"⚙️  Mode: {task_data['processing_mode']}")
        
        # Step 2: Connect to streaming endpoint
        print(f"🌊 Connecting to streaming endpoint...")
        stream_url = f"{STREAMING_ENDPOINT}/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            if stream_response.status_code != 200:
                print(f"❌ Failed to connect to stream: {stream_response.status_code}")
                return False
            
            print("🌊 Connected to stream, processing updates...")
            page_results = []
            
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    data_content = line[6:]
                    
                    # Skip heartbeat messages
                    if '"heartbeat"' in data_content:
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        status = update.get("status", "unknown")
                        step = update.get("current_step", "unknown")
                        progress = update.get("progress_percentage", 0)
                        current_page = update.get("current_page", 0)
                        total_pages = update.get("total_pages", 0)
                        
                        print(f"📊 Progress: {progress:.1f}% | Step: {step} | Status: {status} | Page: {current_page}/{total_pages}")
                        
                        # Handle streaming text (for LLM processing)
                        if "text_chunk" in update and update["text_chunk"]:
                            print(f"📝 Text chunk: {update['text_chunk'][:50]}...")
                        
                        # Handle page completion
                        if "latest_page_result" in update and update["latest_page_result"]:
                            result = update["latest_page_result"]
                            page_results.append(result)
                            print(f"📄 Page {result['page_number']} completed")
                            print(f"✅ Extracted text: {result['extracted_text'][:100]}...")
                        
                        # Check completion
                        if status in ["completed", "failed", "cancelled"]:
                            print(f"🏁 Final status: {status}")
                            if status == "completed":
                                print(f"📚 Total pages processed: {len(page_results)}")
                                for i, result in enumerate(page_results[:3]):  # Show first 3 pages
                                    print(f"📄 Page {i+1}: {result['extracted_text'][:100]}...")
                                return True
                            else:
                                print(f"❌ Processing failed: {update.get('error_message', 'Unknown error')}")
                                return False
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Invalid JSON: {data_content}")
                        continue
        
        print("❌ Stream ended without completion")
        return False

async def main():
    """Run all streaming tests."""
    print("🚀 Starting Unified Streaming Tests...")
    
    # Test 1: Image streaming
    image_success = await test_image_streaming()
    
    # Test 2: PDF streaming
    pdf_success = await test_pdf_streaming()
    
    # Results
    print("\n📊 Test Results:")
    print(f"🖼️  Image streaming: {'✅ PASSED' if image_success else '❌ FAILED'}")
    print(f"📄 PDF streaming: {'✅ PASSED' if pdf_success else '❌ FAILED'}")
    
    if image_success and pdf_success:
        print("🎉 All tests passed! Unified streaming is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)