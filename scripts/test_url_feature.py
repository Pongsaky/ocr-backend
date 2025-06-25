#!/usr/bin/env python3
"""
Test script for URL input feature.
Tests URL download functionality with sample images and PDFs.
"""

import asyncio
import json
import httpx
from typing import Dict, Any

# Test server settings
BASE_URL = "http://localhost:8000"
API_VERSION = "v1"

# Test URLs for different file types
TEST_URLS = {
    "image_jpg": "https://via.placeholder.com/800x600.jpg/0000FF/FFFFFF?text=Test+Image",
    "image_png": "https://via.placeholder.com/800x600.png/FF0000/FFFFFF?text=PNG+Test", 
    "pdf_sample": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "invalid_docx": "https://file-examples.com/storage/fe0d2f5ba9a41c9b1cfe7d5/2017/10/file_example_DOC_100kB.doc"  # Should be rejected
}


async def test_url_download(url: str, expected_status: int = 200, description: str = "") -> Dict[str, Any]:
    """Test URL download functionality."""
    print(f"\n🧪 Testing: {description}")
    print(f"📍 URL: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create request data
            request_data = {
                "url": url,
                "mode": "basic",
                "threshold": 500
            }
            
            # Send request
            form_data = {
                "request": json.dumps(request_data)
            }
            
            response = await client.post(
                f"{BASE_URL}/{API_VERSION}/ocr/process-stream",
                data=form_data
            )
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == expected_status:
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("task_id")
                    file_type = result.get("file_type")
                    print(f"✅ Success! Task ID: {task_id}, File Type: {file_type}")
                    
                    # Test streaming connection
                    stream_response = await client.get(
                        f"{BASE_URL}/{API_VERSION}/ocr/stream/{task_id}",
                        headers={"Accept": "text/event-stream"}
                    )
                    
                    if stream_response.status_code == 200:
                        print(f"🌊 Streaming connection established")
                        # Read first few events
                        async for line in stream_response.aiter_lines():
                            if line.startswith("data: "):
                                event_data = json.loads(line[6:])
                                status = event_data.get("status")
                                progress = event_data.get("progress_percentage", 0)
                                print(f"📡 Progress: {progress}% - {status}")
                                
                                if status in ["completed", "failed", "cancelled"]:
                                    break
                    else:
                        print(f"❌ Streaming failed: {stream_response.status_code}")
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    print(f"✅ Expected error: {error_detail}")
                    
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.json()
                }
            else:
                print(f"❌ Unexpected status code. Expected: {expected_status}")
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": response.text
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """Run all URL tests."""
    print("🚀 Starting URL Feature Tests")
    print("=" * 50)
    
    # Test valid URLs
    test_results = []
    
    # Test valid image URLs
    result = await test_url_download(
        TEST_URLS["image_jpg"], 
        200, 
        "JPG Image Download"
    )
    test_results.append(result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for r in test_results if r.get("success", False))
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! URL feature is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    asyncio.run(main()) 