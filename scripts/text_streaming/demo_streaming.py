#!/usr/bin/env python3
"""
Demo script showing streaming text output in real-time.
Simple demonstration of the streaming text functionality.
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

async def demo_streaming_text(file_path: str):
    """Demonstrate streaming text with clean output."""
    
    print("🌊 Streaming Text Demo")
    print("=" * 40)
    
    # Check file exists
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📁 File: {Path(file_path).name}")
    print(f"🎯 Mode: LLM Enhanced with Streaming")
    print(f"📝 Prompt: อ่านข้อความในภาพนี้")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create task
        print("\n📤 Creating task...")
        
        files = {"file": (Path(file_path).name, open(file_path, "rb"), "image/png")}
        data = {"request": json.dumps({
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "อ่านข้อความในภาพนี้อย่างชัดเจน"
        })}
        
        response = await client.post("http://localhost:8000/v1/ocr/process-stream", files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return False
        
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Task: {task_id}")
        
        # Connect to stream
        print("\n🌊 Streaming text...")
        print("-" * 40)
        
        stream_url = f"http://localhost:8000/v1/ocr/stream/{task_id}"
        
        async with client.stream("GET", stream_url) as stream_response:
            if stream_response.status_code != 200:
                print(f"❌ Stream failed: {stream_response.status_code}")
                return False
            
            print("Real-time text output:")
            print()
            
            current_text = ""
            
            async for line in stream_response.aiter_lines():
                if line.startswith("data: "):
                    data_content = line[6:]
                    
                    if '"heartbeat"' in data_content:
                        continue
                    
                    try:
                        update = json.loads(data_content)
                        
                        # Show streaming text
                        if "text_chunk" in update and update["text_chunk"]:
                            chunk = update["text_chunk"]
                            current_text += chunk
                            
                            # Clear line and show current text
                            print(f"\r📖 {current_text}", end="", flush=True)
                        
                        # Check completion
                        if update.get("status") in ["completed", "failed", "cancelled"]:
                            print()  # New line
                            
                            if update.get("status") == "completed":
                                print(f"\n✅ Complete! Final text: '{current_text}'")
                                print(f"📏 Length: {len(current_text)} characters")
                                return True
                            else:
                                print(f"\n❌ Failed: {update.get('error_message', 'Unknown error')}")
                                return False
                    
                    except json.JSONDecodeError:
                        continue
            
            print("\n❌ Stream ended unexpectedly")
            return False

async def main():
    """Main demo function."""
    # Default test file
    test_file = "/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/test_image.png"
    
    # Check command line argument
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    print("🚀 Streaming Text Demo")
    print("Shows real-time text output as it streams from the LLM")
    print()
    
    try:
        success = await demo_streaming_text(test_file)
        
        if success:
            print("\n🎉 Demo completed successfully!")
        else:
            print("\n❌ Demo failed!")
            
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())