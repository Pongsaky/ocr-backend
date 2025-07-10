#!/usr/bin/env python3
"""
Test script for the new streaming OCR LLM endpoint.
"""

import asyncio
import httpx
import json
import base64
from pathlib import Path


async def test_app_streaming():
    """Test the new /ocr/process-with-llm-stream endpoint"""
    
    # Create a simple test image (1x1 white pixel PNG)
    white_pixel_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Save as temporary file
    temp_path = Path("/tmp/test_streaming.png")
    with open(temp_path, "wb") as f:
        f.write(white_pixel_png)
    
    try:
        print("Testing new streaming endpoint: /v1/ocr/process-with-llm-stream")
        
        # Prepare request
        url = "http://localhost:8000/v1/ocr/process-with-llm-stream"
        
        # Create form data
        files = {
            'file': ('test_image.png', white_pixel_png, 'image/png')
        }
        
        # Request parameters
        request_data = {
            "threshold": 500,
            "contrast_level": 1.3,
            "prompt": "ข้อความในภาพนี้",
            "model": "nectec/Pathumma-vision-ocr-lora-dev",
            "stream": True
        }
        
        data = {
            'request': json.dumps(request_data)
        }
        
        print("Sending request to streaming endpoint...")
        
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream('POST', url, files=files, data=data) as response:
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    print("\n🎉 Streaming response:")
                    print("-" * 50)
                    
                    collected_chunks = []
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_content = line[6:]  # Remove "data: " prefix
                            
                            try:
                                chunk_data = json.loads(data_content)
                                
                                if "chunk" in chunk_data:
                                    chunk = chunk_data["chunk"]
                                    collected_chunks.append(chunk)
                                    print(chunk, end="", flush=True)
                                elif "status" in chunk_data:
                                    print(f"\n[{chunk_data['status'].upper()}]")
                                elif "error" in chunk_data:
                                    print(f"\n[ERROR: {chunk_data['error']}]")
                                    
                            except json.JSONDecodeError as e:
                                print(f"\n[JSON Parse Error: {e}]")
                    
                    print("\n" + "-" * 50)
                    print(f"Total chunks received: {len(collected_chunks)}")
                    print(f"Full text: {''.join(collected_chunks)}")
                    
                else:
                    print(f"Error: {response.status_code}")
                    print(await response.atext())
                    
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()


async def main():
    """Run the test"""
    print("Testing OCR LLM Streaming Implementation")
    print("=" * 50)
    
    await test_app_streaming()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())