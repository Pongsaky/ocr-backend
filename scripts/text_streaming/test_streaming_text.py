#!/usr/bin/env python3
"""
Comprehensive test script for streaming text functionality.
Tests both image and PDF processing with real-time text streaming.
"""

import asyncio
import httpx
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import argparse

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class StreamingTextTester:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 120):
        self.base_url = base_url
        self.timeout = timeout
        self.create_endpoint = f"{base_url}/v1/ocr/process-stream"
        self.stream_endpoint = f"{base_url}/v1/ocr/stream"
        
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    
    def print_info(self, message: str):
        """Print an info message."""
        print(f"{Colors.OKBLUE}ℹ️  {message}{Colors.ENDC}")
    
    def print_success(self, message: str):
        """Print a success message."""
        print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")
    
    def print_error(self, message: str):
        """Print an error message."""
        print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")
    
    def print_streaming_text(self, chunk: str, accumulated: str = None):
        """Print streaming text with special formatting."""
        print(f"{Colors.OKCYAN}📝 Chunk: '{chunk}'{Colors.ENDC}")
        if accumulated:
            print(f"{Colors.BOLD}📚 Accumulated: '{accumulated}'{Colors.ENDC}")
    
    def print_progress(self, progress: float, step: str, status: str):
        """Print progress information."""
        bar_length = 40
        filled_length = int(bar_length * progress // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\r{Colors.OKBLUE}📊 [{bar}] {progress:.1f}% | {step} | {status}{Colors.ENDC}", end='')
        if progress >= 100 or status in ['completed', 'failed', 'cancelled']:
            print()  # New line when complete
    
    async def create_streaming_task(self, file_path: str, request_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a streaming task."""
        try:
            if not Path(file_path).exists():
                self.print_error(f"Test file not found: {file_path}")
                return None
            
            # Determine content type
            file_ext = Path(file_path).suffix.lower()
            content_type = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.pdf': 'application/pdf'
            }.get(file_ext, 'application/octet-stream')
            
            self.print_info(f"Creating streaming task for: {file_path}")
            self.print_info(f"Parameters: {json.dumps(request_params, indent=2)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                files = {"file": (Path(file_path).name, open(file_path, "rb"), content_type)}
                data = {"request": json.dumps(request_params)}
                
                response = await client.post(self.create_endpoint, files=files, data=data)
                
                if response.status_code == 200:
                    task_data = response.json()
                    self.print_success(f"Task created: {task_data['task_id']}")
                    self.print_info(f"File type: {task_data['file_type']}")
                    self.print_info(f"Mode: {task_data['processing_mode']}")
                    self.print_info(f"Estimated duration: {task_data.get('estimated_duration', 'N/A')}s")
                    return task_data
                else:
                    self.print_error(f"Failed to create task: {response.status_code}")
                    self.print_error(f"Response: {response.text}")
                    return None
                    
        except Exception as e:
            self.print_error(f"Error creating task: {str(e)}")
            return None
    
    async def stream_task_progress(self, task_id: str, show_chunks: bool = True) -> Dict[str, Any]:
        """Stream task progress and return final results."""
        try:
            self.print_info(f"Connecting to stream: {task_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                stream_url = f"{self.stream_endpoint}/{task_id}"
                
                async with client.stream("GET", stream_url) as stream_response:
                    if stream_response.status_code != 200:
                        self.print_error(f"Stream connection failed: {stream_response.status_code}")
                        return {"success": False, "error": f"HTTP {stream_response.status_code}"}
                    
                    self.print_success("Connected to stream!")
                    
                    # Track streaming data
                    start_time = time.time()
                    chunk_count = 0
                    total_text = ""
                    updates = []
                    
                    async for line in stream_response.aiter_lines():
                        if line.startswith("data: "):
                            data_content = line[6:]
                            
                            # Skip heartbeat messages
                            if '"heartbeat"' in data_content:
                                continue
                            
                            try:
                                update = json.loads(data_content)
                                updates.append(update)
                                
                                # Extract basic info
                                status = update.get("status", "unknown")
                                step = update.get("current_step", "unknown")
                                progress = update.get("progress_percentage", 0)
                                
                                # Show progress
                                self.print_progress(progress, step, status)
                                
                                # Handle streaming text
                                if show_chunks and "text_chunk" in update and update["text_chunk"]:
                                    chunk = update["text_chunk"]
                                    accumulated = update.get("accumulated_text", "")
                                    self.print_streaming_text(chunk, accumulated)
                                    chunk_count += 1
                                    total_text = accumulated
                                
                                # Handle page results
                                if "latest_page_result" in update and update["latest_page_result"]:
                                    result = update["latest_page_result"]
                                    if not show_chunks:  # Only show if not showing chunks
                                        self.print_success(f"Page {result['page_number']} completed")
                                        text = result.get('extracted_text', '')
                                        if text:
                                            self.print_info(f"Text: {text[:100]}...")
                                
                                # Check completion
                                if status in ["completed", "failed", "cancelled"]:
                                    end_time = time.time()
                                    duration = end_time - start_time
                                    
                                    if status == "completed":
                                        self.print_success(f"Processing completed in {duration:.2f}s")
                                        
                                        # Show final results
                                        if "cumulative_results" in update and update["cumulative_results"]:
                                            results = update["cumulative_results"]
                                            self.print_success(f"Final results: {len(results)} page(s)")
                                            for i, result in enumerate(results[:3]):  # Show first 3
                                                text = result.get('extracted_text', '')
                                                self.print_info(f"Page {i+1}: {text[:100]}...")
                                        
                                        return {
                                            "success": True,
                                            "duration": duration,
                                            "chunk_count": chunk_count,
                                            "total_text": total_text,
                                            "updates": updates
                                        }
                                    else:
                                        self.print_error(f"Processing failed: {status}")
                                        error_msg = update.get("error_message", "Unknown error")
                                        self.print_error(f"Error: {error_msg}")
                                        return {
                                            "success": False,
                                            "error": error_msg,
                                            "duration": duration,
                                            "updates": updates
                                        }
                            
                            except json.JSONDecodeError:
                                self.print_warning(f"Invalid JSON: {data_content}")
                                continue
                    
                    self.print_warning("Stream ended without completion")
                    return {"success": False, "error": "Stream ended unexpectedly"}
                    
        except Exception as e:
            self.print_error(f"Streaming error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_image_streaming(self, file_path: str, prompt: str = None):
        """Test image streaming with custom prompt."""
        self.print_header("🖼️  IMAGE STREAMING TEST")
        
        # Test parameters
        request_params = {
            "mode": "llm_enhanced",
            "stream": True,
            "threshold": 500,
            "contrast_level": 1.3
        }
        
        if prompt:
            request_params["prompt"] = prompt
            
        # Create task
        task_data = await self.create_streaming_task(file_path, request_params)
        if not task_data:
            return False
        
        # Stream results
        results = await self.stream_task_progress(task_data["task_id"], show_chunks=True)
        
        if results["success"]:
            self.print_success("Image streaming test completed successfully!")
            self.print_info(f"Streaming chunks received: {results['chunk_count']}")
            self.print_info(f"Final text: {results['total_text'][:200]}...")
            return True
        else:
            self.print_error("Image streaming test failed!")
            return False
    
    async def test_pdf_streaming(self, file_path: str, prompt: str = None):
        """Test PDF streaming with custom prompt."""
        self.print_header("📄 PDF STREAMING TEST")
        
        # Test parameters
        request_params = {
            "mode": "llm_enhanced",
            "stream": True,
            "threshold": 500,
            "contrast_level": 1.3,
            "dpi": 300
        }
        
        if prompt:
            request_params["prompt"] = prompt
            
        # Create task
        task_data = await self.create_streaming_task(file_path, request_params)
        if not task_data:
            return False
        
        # Stream results
        results = await self.stream_task_progress(task_data["task_id"], show_chunks=True)
        
        if results["success"]:
            self.print_success("PDF streaming test completed successfully!")
            self.print_info(f"Processing duration: {results['duration']:.2f}s")
            return True
        else:
            self.print_error("PDF streaming test failed!")
            return False
    
    async def test_non_streaming_comparison(self, file_path: str):
        """Test non-streaming mode for comparison."""
        self.print_header("🔄 NON-STREAMING COMPARISON")
        
        # Test parameters (no streaming)
        request_params = {
            "mode": "llm_enhanced",
            "stream": False,
            "threshold": 500,
            "contrast_level": 1.3
        }
        
        # Create task
        task_data = await self.create_streaming_task(file_path, request_params)
        if not task_data:
            return False
        
        # Stream results (still uses streaming endpoint, but no text chunks)
        results = await self.stream_task_progress(task_data["task_id"], show_chunks=False)
        
        if results["success"]:
            self.print_success("Non-streaming test completed successfully!")
            self.print_info(f"Processing duration: {results['duration']:.2f}s")
            return True
        else:
            self.print_error("Non-streaming test failed!")
            return False
    
    async def run_performance_comparison(self, file_path: str):
        """Run performance comparison between streaming and non-streaming."""
        self.print_header("⚡ PERFORMANCE COMPARISON")
        
        # Test streaming
        self.print_info("Testing streaming mode...")
        start_time = time.time()
        streaming_success = await self.test_image_streaming(file_path)
        streaming_time = time.time() - start_time
        
        await asyncio.sleep(2)  # Brief pause between tests
        
        # Test non-streaming
        self.print_info("Testing non-streaming mode...")
        start_time = time.time()
        non_streaming_success = await self.test_non_streaming_comparison(file_path)
        non_streaming_time = time.time() - start_time
        
        # Results
        self.print_header("📊 COMPARISON RESULTS")
        print(f"Streaming mode:     {'✅ Success' if streaming_success else '❌ Failed'} ({streaming_time:.2f}s)")
        print(f"Non-streaming mode: {'✅ Success' if non_streaming_success else '❌ Failed'} ({non_streaming_time:.2f}s)")
        
        if streaming_success and non_streaming_success:
            if streaming_time < non_streaming_time:
                self.print_success("Streaming mode was faster!")
            else:
                self.print_info("Non-streaming mode was faster (expected for small files)")

async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test streaming text functionality")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--image", default="/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/test_image.png", help="Path to test image")
    parser.add_argument("--pdf", default="/Users/pongsakon/Study/CEDT/Intern/nstda-intern/ocr-backend/test_files/ocr-pdf-testing.pdf", help="Path to test PDF")
    parser.add_argument("--prompt", help="Custom prompt for LLM")
    parser.add_argument("--test", choices=["image", "pdf", "comparison", "all"], default="all", help="Which test to run")
    parser.add_argument("--timeout", type=int, default=120, help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    # Create tester
    tester = StreamingTextTester(args.base_url, args.timeout)
    
    # Print header
    tester.print_header("🌊 STREAMING TEXT FUNCTIONALITY TESTER")
    tester.print_info(f"Base URL: {args.base_url}")
    tester.print_info(f"Timeout: {args.timeout}s")
    
    # Run tests
    results = []
    
    if args.test in ["image", "all"]:
        tester.print_info(f"Image file: {args.image}")
        success = await tester.test_image_streaming(args.image, args.prompt)
        results.append(("Image Streaming", success))
    
    if args.test in ["pdf", "all"]:
        tester.print_info(f"PDF file: {args.pdf}")
        success = await tester.test_pdf_streaming(args.pdf, args.prompt)
        results.append(("PDF Streaming", success))
    
    if args.test in ["comparison", "all"]:
        success = await tester.run_performance_comparison(args.image)
        results.append(("Performance Comparison", success))
    
    # Final summary
    tester.print_header("📋 FINAL SUMMARY")
    all_passed = True
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{Colors.BOLD}Overall Result: {'🎉 ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}{Colors.ENDC}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}")
        sys.exit(1)