#!/usr/bin/env python3
"""
Simple test to verify unified streaming endpoints are working.
"""

import asyncio
import httpx
import json
from pathlib import Path

async def test_endpoint():
    """Test unified endpoint with basic request."""
    print("🚀 Testing unified streaming endpoint...")
    
    # Create a simple test image (if it doesn't exist)
    test_image = Path("test_image.png")
    if not test_image.exists():
        print("❌ Test image not found, skipping test")
        return
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test basic endpoint availability
        print("📡 Testing endpoint availability...")
        try:
            files = {"file": (test_image.name, open(test_image, "rb"), "image/png")}
            data = {"request": json.dumps({
                "mode": "basic",
                "threshold": 500,
                "stream": False
            })}
            
            response = await client.post(
                "http://localhost:8000/v1/ocr/process-stream",
                files=files,
                data=data
            )
            
            print(f"📊 Status: {response.status_code}")
            print(f"📄 Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("✅ Endpoint is working!")
                task_data = response.json()
                print(f"🎯 Task ID: {task_data.get('task_id')}")
                print(f"🗂️  File type: {task_data.get('file_type')}")
                print(f"⚙️  Processing mode: {task_data.get('processing_mode')}")
                return True
            else:
                print(f"❌ Endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_endpoint())
    if success:
        print("🎉 Basic test passed!")
    else:
        print("❌ Basic test failed!")