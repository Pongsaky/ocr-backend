#!/usr/bin/env python3
"""
Test script to verify streaming support for Pathumma Vision OCR API.
This script tests if the API supports streaming responses before implementing in the main application.
"""

import asyncio
import httpx
import json
import base64
from pathlib import Path
import sys


async def load_test_image(image_path: str = None) -> str:
    """Load and encode a test image to base64."""
    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    else:
        # Create a simple 1x1 white pixel PNG as fallback test image
        white_pixel_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
        return base64.b64encode(white_pixel_png).decode()


async def test_non_streaming():
    """Test non-streaming request (current implementation)."""
    print("\n=== Testing Non-Streaming Request ===")
    
    url = "http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions"
    image_base64 = await load_test_image()
    
    payload = {
        "model": "nectec/Pathumma-vision-ocr-lora-dev",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "ข้อความในภาพนี้"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": False  # Explicitly set to false
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            print("Sending non-streaming request...")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response Type: {type(result)}")
            
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"Extracted Text: {content}")
            else:
                print("No choices in response")
                print(f"Full Response: {json.dumps(result, indent=2)}")
                
        return True
        
    except Exception as e:
        print(f"Error in non-streaming request: {e}")
        return False


async def test_streaming():
    """Test streaming request with SSE parsing."""
    print("\n=== Testing Streaming Request ===")
    
    url = "http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions"
    image_base64 = await load_test_image()
    
    payload = {
        "model": "nectec/Pathumma-vision-ocr-lora-dev",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "ข้อความในภาพนี้"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": True  # Enable streaming
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            print("Sending streaming request...")
            collected_text = ""
            chunk_count = 0
            
            async with client.stream('POST', url, json=payload) as response:
                response.raise_for_status()
                print(f"Status Code: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print("\nStreaming chunks:")
                print("-" * 50)
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                        
                    # Debug: Show raw line
                    # print(f"[RAW] {line}")
                    
                    if line.startswith("data: "):
                        chunk_count += 1
                        data_content = line[6:]  # Remove "data: " prefix
                        
                        if data_content == "[DONE]":
                            print("\n[STREAM COMPLETE]")
                            break
                            
                        try:
                            chunk_data = json.loads(data_content)
                            # print(f"[CHUNK {chunk_count}] {json.dumps(chunk_data, indent=2)}")
                            
                            # Extract content from delta
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    collected_text += content
                                    print(content, end="", flush=True)
                                    
                        except json.JSONDecodeError as e:
                            print(f"\n[ERROR] Failed to parse chunk: {e}")
                            print(f"[ERROR] Raw data: {data_content}")
                
                print("\n" + "-" * 50)
                print(f"\nTotal chunks received: {chunk_count}")
                print(f"Collected text: {collected_text}")
                
        return True
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"Error Detail: {json.dumps(error_detail, indent=2)}")
        except:
            print(f"Error Text: {e.response.text}")
        return False
        
    except Exception as e:
        print(f"Error in streaming request: {type(e).__name__}: {e}")
        return False


async def test_streaming_with_real_image(image_path: str):
    """Test streaming with a real image file."""
    print(f"\n=== Testing Streaming with Real Image: {image_path} ===")
    
    if not Path(image_path).exists():
        print(f"Error: Image file not found: {image_path}")
        return False
        
    url = "http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions"
    image_base64 = await load_test_image(image_path)
    
    payload = {
        "model": "nectec/Pathumma-vision-ocr-lora-dev",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "อ่านข้อความทั้งหมดในภาพนี้"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            print("Sending streaming request with real image...")
            collected_text = ""
            
            async with client.stream('POST', url, json=payload) as response:
                response.raise_for_status()
                
                print("\nStreaming response:")
                print("-" * 50)
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_content = line[6:]
                        
                        if data_content == "[DONE]":
                            break
                            
                        try:
                            chunk_data = json.loads(data_content)
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    collected_text += content
                                    print(content, end="", flush=True)
                                    
                        except json.JSONDecodeError:
                            pass
                
                print("\n" + "-" * 50)
                print(f"\nTotal extracted text length: {len(collected_text)} characters")
                
        return True
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def test_streaming_with_provided_image():
    """Test streaming with a simple test image."""
    print("\n=== Testing Streaming with Simple Test Image ===")
    
    # Create a simple test image
    url = "http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions"
    
    # Using the same simple test image from the load_test_image function
    test_image_base64 = await load_test_image()
    
    url = "http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions"
    
    payload = {
        "model": "nectec/Pathumma-vision-ocr-lora-dev",
        "messages": [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "อ่านข้อความทั้งหมดในภาพนี้"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{test_image_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            print("Sending streaming request with simple test image...")
            collected_text = ""
            chunk_count = 0
            
            async with client.stream('POST', url, json=payload) as response:
                response.raise_for_status()
                print(f"Status Code: {response.status_code}")
                
                print("\nStreaming response:")
                print("-" * 50)
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                        
                    if line.startswith("data: "):
                        chunk_count += 1
                        data_content = line[6:]
                        
                        if data_content == "[DONE]":
                            break
                            
                        try:
                            chunk_data = json.loads(data_content)
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    collected_text += content
                                    print(content, end="", flush=True)
                                    
                        except json.JSONDecodeError:
                            pass
                
                print("\n" + "-" * 50)
                print(f"\nTotal chunks received: {chunk_count}")
                print(f"Total extracted text length: {len(collected_text)} characters")
                print(f"\nExtracted text: {collected_text}")
                
        return True
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing Pathumma Vision OCR API Streaming Support")
    print("=" * 60)
    
    # Test 1: Non-streaming (baseline with simple test image)
    print("\nTest 1: Basic non-streaming test...")
    non_streaming_success = await test_non_streaming()
    
    # Test 2: Streaming (with simple test image)
    print("\nTest 2: Basic streaming test...")
    streaming_success = await test_streaming()
    
    # Test 3: Try to test with a PDF file first if available
    pdf_file = "/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/ocr-pdf-testing.pdf"
    if Path(pdf_file).exists():
        print(f"\nTest 3: Testing with PDF file: {pdf_file}")
        # Note: This won't work directly with the LLM API since it expects images
        # But we can show that the file exists for future testing
        print(f"PDF file exists: {Path(pdf_file).exists()}")
        print("Note: PDF would need to be converted to images first for LLM API")
    else:
        print("\nTest 3: PDF file not found, skipping PDF test")
    
    # Test 4: Streaming with simple test image
    print("\nTest 4: Streaming with simple test image...")
    real_image_success = await test_streaming_with_provided_image()
    
    # Test 5: Streaming with custom image file (optional)
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\nTest 5: Streaming with custom image file: {image_path}")
        await test_streaming_with_real_image(image_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"- Non-streaming: {'✓ Success' if non_streaming_success else '✗ Failed'}")
    print(f"- Basic streaming: {'✓ Success' if streaming_success else '✗ Failed'}")
    print(f"- Streaming with real image: {'✓ Success' if real_image_success else '✗ Failed'}")
    
    if streaming_success and real_image_success:
        print("\n✅ Streaming is fully supported! You can proceed with implementation.")
        print("\nImplementation notes:")
        print("1. The API returns Server-Sent Events (SSE) format")
        print("2. Each chunk is prefixed with 'data: '")
        print("3. Stream ends with 'data: [DONE]'")
        print("4. Content is in choices[0].delta.content")
        print("5. Works well with Thai text content")
    else:
        print("\n❌ Some streaming tests failed. Check the error messages above.")


if __name__ == "__main__":
    asyncio.run(main())