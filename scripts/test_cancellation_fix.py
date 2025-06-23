#!/usr/bin/env python3
"""
Test script to verify the cancellation race condition fix.
This script simulates the race condition scenario and tests both cases:
1. Canceling an actively processing task
2. Canceling a recently completed task (race condition case)
"""

import asyncio
import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE_PATH = "test_files/test_image.png"


async def test_cancellation_fix():
    """Test the cancellation fix for race conditions."""
    
    print("🔬 Testing Task Cancellation Race Condition Fix")
    print("=" * 60)
    
    # Test 1: Normal cancellation of active task
    print("\n1️⃣ Testing normal cancellation of active task...")
    await test_normal_cancellation()
    
    # Test 2: Race condition - cancel completed task
    print("\n2️⃣ Testing race condition - cancel completed task...")
    await test_race_condition_cancellation()
    
    print("\n✅ All cancellation tests completed!")


async def test_normal_cancellation():
    """Test normal cancellation of an actively processing task."""
    
    # Check if test image exists
    if not Path(TEST_IMAGE_PATH).exists():
        print(f"⚠️ Test image not found: {TEST_IMAGE_PATH}")
        print("Creating a simple test image...")
        create_test_image()
    
    try:
        # Start processing a task
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'file': ('test.png', f, 'image/png')}
            data = {'mode': 'basic'}
            
            print("📤 Starting image processing...")
            response = requests.post(f"{BASE_URL}/v1/ocr/process-stream", files=files, data=data)
            
            if response.status_code != 200:
                print(f"❌ Failed to start processing: {response.status_code}")
                print(response.text)
                return
            
            task_info = response.json()
            task_id = task_info['task_id']
            print(f"✅ Started task: {task_id}")
            
            # Wait a moment, then cancel
            await asyncio.sleep(0.5)
            
            print("🛑 Attempting to cancel active task...")
            cancel_response = requests.post(
                f"{BASE_URL}/v1/ocr/tasks/{task_id}/cancel",
                json={"reason": "Test cancellation of active task"}
            )
            
            print(f"📋 Cancel response status: {cancel_response.status_code}")
            if cancel_response.status_code == 200:
                cancel_data = cancel_response.json()
                print(f"✅ Cancellation successful: {cancel_data['status']}")
                print(f"📝 Message: {cancel_data['message']}")
            else:
                print(f"❌ Cancellation failed: {cancel_response.text}")
                
    except Exception as e:
        print(f"❌ Error in normal cancellation test: {e}")


async def test_race_condition_cancellation():
    """Test the race condition scenario - cancel a completed task."""
    
    try:
        # Start processing a task and let it complete
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'file': ('test.png', f, 'image/png')}
            data = {'mode': 'basic'}
            
            print("📤 Starting image processing (will let complete)...")
            response = requests.post(f"{BASE_URL}/v1/ocr/process-stream", files=files, data=data)
            
            if response.status_code != 200:
                print(f"❌ Failed to start processing: {response.status_code}")
                return
            
            task_info = response.json()
            task_id = task_info['task_id']
            print(f"✅ Started task: {task_id}")
            
            # Start streaming to trigger completion
            print("🌊 Starting stream to trigger completion...")
            stream_response = requests.get(
                f"{BASE_URL}/v1/ocr/stream/{task_id}",
                stream=True,
                headers={'Accept': 'text/event-stream'}
            )
            
            if stream_response.status_code == 200:
                for line in stream_response.iter_lines(decode_unicode=True):
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: '
                            if data.get('status') in ['completed', 'failed']:
                                print(f"🏁 Task completed with status: {data.get('status')}")
                                break
                        except json.JSONDecodeError:
                            continue
                
                # Now immediately try to cancel (race condition scenario)
                print("🛑 Attempting to cancel completed task (race condition)...")
                cancel_response = requests.post(
                    f"{BASE_URL}/v1/ocr/tasks/{task_id}/cancel",
                    json={"reason": "Test race condition cancellation"}
                )
                
                print(f"📋 Cancel response status: {cancel_response.status_code}")
                if cancel_response.status_code == 200:
                    cancel_data = cancel_response.json()
                    print(f"✅ Handled gracefully: {cancel_data['status']}")
                    print(f"📝 Message: {cancel_data['message']}")
                    
                    # Check if it's the expected "already_completed" status
                    if cancel_data['status'] == 'already_completed':
                        print("🎯 Perfect! Race condition handled correctly.")
                    else:
                        print("⚠️ Unexpected status - may need further investigation.")
                        
                else:
                    print(f"❌ Cancellation failed: {cancel_response.text}")
            else:
                print(f"❌ Failed to start stream: {stream_response.status_code}")
                
    except Exception as e:
        print(f"❌ Error in race condition test: {e}")


def create_test_image():
    """Create a simple test image if none exists."""
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple 200x100 white image with text
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "Test Image", fill='black')
        
        # Ensure directory exists
        Path(TEST_IMAGE_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        # Save the image
        img.save(TEST_IMAGE_PATH)
        print(f"✅ Created test image: {TEST_IMAGE_PATH}")
        
    except ImportError:
        print("❌ PIL not available, cannot create test image")
    except Exception as e:
        print(f"❌ Failed to create test image: {e}")


def check_server_health():
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


async def main():
    """Main test function."""
    print("🚀 OCR Backend Cancellation Fix Test")
    print("=" * 50)
    
    # Check server health
    if not check_server_health():
        print(f"❌ Server not running at {BASE_URL}")
        print("Please start the server first: python -m uvicorn app.main:app --reload")
        return
    
    print(f"✅ Server is running at {BASE_URL}")
    
    # Run tests
    await test_cancellation_fix()


if __name__ == "__main__":
    asyncio.run(main()) 