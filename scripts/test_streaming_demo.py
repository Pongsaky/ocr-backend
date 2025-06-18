#!/usr/bin/env python3
"""
Demo script to test PDF streaming functionality.
This script demonstrates both streaming approaches:
1. Individual page results as they complete
2. Cumulative results containing all completed pages
"""

import asyncio
import json
import time
from pathlib import Path
import sys
import os

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.ocr_models import PDFOCRRequest, PDFLLMOCRRequest
from app.services.pdf_ocr_service import pdf_ocr_service
from app.controllers.ocr_controller import ocr_controller


async def demo_streaming_functionality():
    """Demonstrate PDF streaming functionality."""
    print("🚀 PDF Streaming Demo")
    print("=" * 50)
    
    # Check if test PDF exists
    test_pdf = Path("test_files/ocr-pdf-testing.pdf")
    if not test_pdf.exists():
        print("❌ Test PDF file not found at test_files/ocr-pdf-testing.pdf")
        return
    
    print(f"📄 Test PDF: {test_pdf}")
    print(f"📁 File size: {test_pdf.stat().st_size / 1024:.1f} KB")
    
    # Demo 1: Basic PDF streaming
    await demo_basic_streaming(test_pdf)
    
    # Demo 2: LLM-enhanced streaming  
    await demo_llm_streaming(test_pdf)
    
    # Demo 3: Controller-level streaming (simulated)
    await demo_controller_streaming()


async def demo_basic_streaming(test_pdf: Path):
    """Demo basic PDF OCR streaming."""
    print("\n🔄 Demo 1: Basic PDF OCR Streaming")
    print("-" * 40)
    
    # Create request with lower DPI for faster demo
    request = PDFOCRRequest(
        threshold=500,
        contrast_level=1.3,
        dpi=150  # Lower DPI for demo
    )
    
    # Create streaming queue
    streaming_queue = asyncio.Queue()
    task_id = "demo-basic-streaming"
    
    print(f"📋 Processing PDF with DPI={request.dpi}")
    print("⏳ Starting streaming processing...")
    
    # Track timing
    start_time = time.time()
    
    # Start processing in background
    processing_task = asyncio.create_task(
        pdf_ocr_service.process_pdf_with_streaming(
            test_pdf, request, task_id, streaming_queue
        )
    )
    
    # Monitor streaming updates
    updates_count = 0
    pages_completed = 0
    
    print("\n📊 Streaming Updates:")
    print("Page | Status      | Progress | Cumulative | Timing")
    print("-" * 60)
    
    while True:
        try:
            # Get update with timeout
            update = await asyncio.wait_for(streaming_queue.get(), timeout=2.0)
            
            if update is None:  # End sentinel
                break
            
            updates_count += 1
            
            # Display update
            if hasattr(update, 'current_page'):
                status = update.status[:10].ljust(10)
                progress = f"{update.progress_percentage:5.1f}%"
                cumulative = f"{len(update.cumulative_results):2d} pages"
                
                # Estimate timing
                elapsed = time.time() - start_time
                timing = f"{elapsed:5.1f}s"
                
                print(f"{update.current_page:4d} | {status} | {progress} | {cumulative} | {timing}")
                
                if update.status == "page_completed":
                    pages_completed += 1
                    
                    # Show dual streaming approaches
                    if update.latest_page_result:
                        print(f"     └─ 🔵 Type 1: New page {update.latest_page_result.page_number} completed")
                        print(f"        Text preview: {update.latest_page_result.extracted_text[:50]}...")
                    
                    print(f"     └─ 🟡 Type 2: Total cumulative pages: {len(update.cumulative_results)}")
        
        except asyncio.TimeoutError:
            print("     ⏱️  (waiting for next update...)")
            if processing_task.done():
                break
    
    # Get final result
    try:
        result = await processing_task
        total_time = time.time() - start_time
        
        print(f"\n✅ Basic streaming completed!")
        print(f"📈 Results: {result.processed_pages}/{result.total_pages} pages in {total_time:.2f}s")
        print(f"📊 Updates received: {updates_count}")
        print(f"⚡ Average time per page: {total_time/result.total_pages:.2f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_llm_streaming(test_pdf: Path):
    """Demo LLM-enhanced PDF OCR streaming."""
    print("\n🧠 Demo 2: LLM-Enhanced PDF OCR Streaming")
    print("-" * 40)
    
    # Create LLM request (only process first 2 pages for demo)
    request = PDFLLMOCRRequest(
        threshold=500,
        contrast_level=1.3,
        dpi=150,  # Lower DPI for demo
        prompt="Extract and clean up the text, fix any OCR errors",
        model="gpt-4"
    )
    
    # Create streaming queue
    streaming_queue = asyncio.Queue()
    task_id = "demo-llm-streaming"
    
    print(f"📋 Processing with LLM enhancement (DPI={request.dpi})")
    print(f"🤖 Model: {request.model}")
    print(f"💬 Prompt: {request.prompt}")
    print("⏳ Starting LLM streaming processing...")
    
    start_time = time.time()
    
    # Note: For demo, we'll simulate LLM streaming since it requires external service
    print("\n📊 LLM Streaming Updates (Simulated):")
    print("Page | Status      | OCR Time | LLM Time | Total Time")
    print("-" * 55)
    
    # Create mock LLM streaming updates
    total_pages = 3  # Demo with fewer pages
    
    for page in range(1, total_pages + 1):
        # Simulate page processing
        await asyncio.sleep(0.1)  # Simulate OCR time
        
        ocr_time = 1.2
        llm_time = 2.3
        total_time = ocr_time + llm_time
        
        print(f"{page:4d} | {'processing':<10} | {ocr_time:7.1f}s | {llm_time:7.1f}s | {total_time:9.1f}s")
        print(f"     └─ 🔵 Original OCR: 'Original text from page {page}'")
        print(f"     └─ 🟢 LLM Enhanced: 'Enhanced and cleaned text from page {page}'")
    
    elapsed = time.time() - start_time
    print(f"\n✅ LLM streaming demo completed in {elapsed:.2f}s")
    print("📝 Dual approach benefits:")
    print("   🔵 Type 1: Individual enhanced results per page")  
    print("   🟡 Type 2: Complete cumulative enhanced text")


async def demo_controller_streaming():
    """Demo controller-level streaming simulation."""
    print("\n🎮 Demo 3: Controller-Level Streaming (API Simulation)")
    print("-" * 40)
    
    print("📡 This demonstrates the API endpoints for streaming:")
    print()
    print("1️⃣ Start streaming processing:")
    print("   POST /v1/ocr/process-pdf-stream")
    print("   Returns: {task_id, status, created_at}")
    print()
    print("2️⃣ Connect to streaming updates:")
    print("   GET /v1/ocr/stream/{task_id}")
    print("   Returns: Server-Sent Events (SSE)")
    print()
    print("📊 SSE Stream Format:")
    print("   data: {")
    print('     "task_id": "uuid",')
    print('     "status": "page_completed",')
    print('     "current_page": 3,')
    print('     "total_pages": 9,')
    print('     "processed_pages": 3,')
    print('     "progress_percentage": 33.3,')
    print('     "latest_page_result": {...},  // Type 1: Single page')
    print('     "cumulative_results": [...],  // Type 2: All pages')
    print('     "estimated_time_remaining": 12.5,')
    print('     "processing_speed": 0.3')
    print("   }")
    print()
    print("✨ Both streaming types available for frontend flexibility!")


async def main():
    """Main demo function."""
    try:
        await demo_streaming_functionality()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting PDF Streaming Demo...")
    asyncio.run(main()) 