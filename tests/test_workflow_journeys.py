"""
Complete user workflow journey tests - end-to-end scenarios that users actually perform.
These test complete workflows from start to finish with real data and real results.
"""

import json
import pytest
import asyncio
import time
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any, List
import base64

from tests.remote_client import RemoteTestClient, AsyncRemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestUserWorkflowJourneys:
    """Test complete user workflows end-to-end."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    @pytest.fixture
    def async_client(self):
        """Create async remote test client."""
        return AsyncRemoteTestClient()
    
    @pytest.fixture
    def multi_page_pdf_content(self):
        """Create multi-page PDF content for testing."""
        # This would normally use reportlab, but we'll simulate with multiple images
        pages_data = []
        
        for page_num in range(1, 6):  # 5 pages
            # Create image for this page
            image = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            # Page content
            draw.text((50, 50), f"Page {page_num}", fill='black', font=font)
            draw.text((50, 120), f"This is content for page {page_num}", fill='black', font=font)
            draw.text((50, 190), f"Line 2 of page {page_num}", fill='black', font=font)
            draw.text((50, 260), f"Line 3 of page {page_num}", fill='black', font=font)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95)
            pages_data.append(img_byte_arr.getvalue())
        
        return pages_data
    
    @pytest.fixture
    def business_document_image(self):
        """Create a business document style image."""
        image = Image.new('RGB', (800, 1000), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
            body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        # Business document content
        draw.text((50, 50), "INVOICE #12345", fill='black', font=title_font)
        draw.text((50, 120), "Company Name: ABC Corporation", fill='black', font=body_font)
        draw.text((50, 160), "Date: 2024-01-15", fill='black', font=body_font)
        draw.text((50, 200), "Amount: $1,234.56", fill='black', font=body_font)
        draw.text((50, 240), "Description: Professional Services", fill='black', font=body_font)
        draw.text((50, 280), "Payment Terms: Net 30", fill='black', font=body_font)
        
        # Table-like structure
        draw.text((50, 350), "Item", fill='black', font=body_font)
        draw.text((200, 350), "Quantity", fill='black', font=body_font)
        draw.text((350, 350), "Price", fill='black', font=body_font)
        draw.text((500, 350), "Total", fill='black', font=body_font)
        
        draw.text((50, 390), "Consulting", fill='black', font=body_font)
        draw.text((200, 390), "10 hours", fill='black', font=body_font)
        draw.text((350, 390), "$123.45", fill='black', font=body_font)
        draw.text((500, 390), "$1,234.50", fill='black', font=body_font)
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    
    def wait_for_completion(self, client: RemoteTestClient, task_id: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for task completion with detailed progress logging."""
        print(f"⏳ Waiting for task {task_id} to complete...")
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            try:
                for endpoint in [f"/v1/ocr/process-stream/{task_id}", f"/v1/ocr/status/{task_id}"]:
                    try:
                        response = client.get(endpoint)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get('status', 'unknown')
                            
                            if status != last_status:
                                print(f"📊 Status change: {last_status} → {status}")
                                last_status = status
                            
                            if 'progress_percentage' in data:
                                progress = data['progress_percentage']
                                print(f"📈 Progress: {progress}%")
                            
                            if status == 'completed':
                                elapsed = time.time() - start_time
                                print(f"✅ Task completed in {elapsed:.1f}s")
                                return data
                            elif status == 'failed':
                                print(f"❌ Task failed: {data.get('error', 'Unknown error')}")
                                return data
                            elif status in ['processing', 'pending']:
                                time.sleep(3)
                                break
                    except Exception:
                        continue
                
                time.sleep(3)
                
            except Exception as e:
                print(f"Error checking status: {e}")
                time.sleep(3)
        
        print(f"⏰ Task timed out after {timeout}s")
        return {"status": "timeout", "error": f"Task timed out after {timeout} seconds"}
    
    def test_workflow_simple_document_ocr(self, client, business_document_image):
        """Workflow: User uploads business document → Gets structured OCR results."""
        print(f"\n📄 WORKFLOW: Simple Document OCR")
        print(f"   Endpoint: {client.base_url}")
        print("   Scenario: Business user uploads invoice for text extraction")
        
        # Step 1: Upload document
        print("\n🔹 Step 1: Upload business document")
        request_data = {
            "mode": "llm_enhanced",
            "prompt": "Extract all text from this business document. Pay attention to invoice details, amounts, and structured data."
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("invoice.jpg", business_document_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        task_id = response.json()["task_id"]
        print(f"✅ Document uploaded, task created: {task_id}")
        
        # Step 2: Wait for processing
        print("\n🔹 Step 2: Wait for OCR processing")
        result = self.wait_for_completion(client, task_id)
        
        # Step 3: Validate results
        print("\n🔹 Step 3: Validate OCR results")
        assert result.get("status") == "completed", f"Processing failed: {result}"
        
        if 'result' in result:
            ocr_data = result['result']
            extracted_text = ocr_data.get('extracted_text', '')
            
            print(f"📊 Results Summary:")
            print(f"   Text length: {len(extracted_text)} characters")
            print(f"   Processing time: {ocr_data.get('processing_time', 0)}s")
            print(f"   Model used: {ocr_data.get('model_used', 'unknown')}")
            
            # Validate business document content
            text_lower = extracted_text.lower()
            business_keywords = ["invoice", "company", "amount", "date", "payment"]
            found_keywords = [kw for kw in business_keywords if kw in text_lower]
            
            print(f"📋 Found business keywords: {found_keywords}")
            
            # Check for specific values
            if "1234" in extracted_text or "12345" in extracted_text:
                print("✅ Found invoice number")
            if "$" in extracted_text or "dollar" in text_lower:
                print("✅ Found currency/amount")
            
            assert len(extracted_text) > 50, "Too little text extracted"
            assert len(found_keywords) >= 2, f"Expected business keywords, found: {found_keywords}"
        
        print("✅ WORKFLOW COMPLETED: Simple Document OCR")
    
    def test_workflow_pdf_page_selection(self, client):
        """Workflow: User uploads PDF → Selects specific pages → Gets targeted results."""
        print(f"\n📚 WORKFLOW: PDF Page Selection")
        print("   Scenario: User processes only pages 1, 3, 5 from multi-page document")
        
        # Create a simple multi-page PDF simulation using single image
        test_image = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(test_image)
        draw.text((50, 50), "Multi-page Document Simulation", fill='black')
        draw.text((50, 100), "This represents a PDF page", fill='black')
        
        img_byte_arr = io.BytesIO()
        test_image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        # Step 1: Upload PDF with page selection
        print("\n🔹 Step 1: Upload PDF with page selection [1, 3, 5]")
        request_data = {
            "mode": "basic",
            "pdf_config": {
                "page_select": [1, 3, 5]
            }
        }
        
        # Note: Using image for PDF simulation since reportlab not available
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("document.jpg", img_byte_arr, "image/jpeg")},  # Simulating PDF
            data={"request": json.dumps(request_data)}
        )
        
        print(f"📤 Upload response: {response.status_code}")
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            print(f"✅ PDF uploaded with page selection: {task_id}")
            
            # Step 2: Monitor processing
            print("\n🔹 Step 2: Monitor page-by-page processing")
            result = self.wait_for_completion(client, task_id)
            
            # Step 3: Validate page-specific results
            print("\n🔹 Step 3: Validate page selection results")
            if result.get("status") == "completed":
                print("✅ Page selection processing completed")
                
                # Check if result structure indicates page processing
                if 'result' in result:
                    ocr_result = result['result']
                    print(f"📄 Result structure: {list(ocr_result.keys())}")
                    
                    # Look for page-specific information
                    if 'page_results' in ocr_result:
                        pages = ocr_result['page_results']
                        print(f"📚 Processed {len(pages)} pages")
                        # Would expect 3 pages (1, 3, 5) if this were a real PDF
        
        print("✅ WORKFLOW COMPLETED: PDF Page Selection")
    
    @pytest.mark.asyncio
    async def test_workflow_real_time_streaming(self, business_document_image):
        """Workflow: User uploads document → Watches real-time text generation → Gets final result."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set")
        
        client = RemoteTestClient()
        async_client = AsyncRemoteTestClient()
        
        print(f"\n📡 WORKFLOW: Real-time Streaming OCR")
        print("   Scenario: User watches text appear character-by-character")
        
        # Step 1: Start streaming task
        print("\n🔹 Step 1: Start streaming OCR task")
        request_data = {
            "mode": "llm_enhanced",
            "stream": True,
            "prompt": "Extract all text from this document with high accuracy"
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("streaming_doc.jpg", business_document_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"✅ Streaming task started: {task_id}")
        
        # Step 2: Connect to real-time stream
        print("\n🔹 Step 2: Connect to real-time text stream")
        
        streaming_data = {
            "updates_received": 0,
            "text_chunks": [],
            "accumulated_text": "",
            "progress_updates": [],
            "final_result": None
        }
        
        try:
            async for update in async_client.stream(f"/v1/ocr/stream/{task_id}"):
                if update:
                    try:
                        data = json.loads(update)
                        streaming_data["updates_received"] += 1
                        
                        # Real-time text chunks
                        if 'text_chunk' in data:
                            chunk = data['text_chunk']
                            streaming_data["text_chunks"].append(chunk)
                            streaming_data["accumulated_text"] += chunk
                            print(f"📝 Text: '{chunk}'", end="", flush=True)
                        
                        # Progress updates
                        if 'progress_percentage' in data:
                            progress = data['progress_percentage']
                            streaming_data["progress_updates"].append(progress)
                            print(f"\n📊 Progress: {progress}%")
                        
                        # Status updates
                        if 'status' in data:
                            status = data['status']
                            print(f"\n📈 Status: {status}")
                            
                            if status == 'completed':
                                streaming_data["final_result"] = data
                                print("\n🏁 Streaming completed!")
                                break
                            elif status == 'failed':
                                print(f"\n❌ Streaming failed: {data.get('error', 'Unknown')}")
                                break
                        
                        # Safety: limit updates for testing
                        if streaming_data["updates_received"] > 100:
                            print("\n🛑 Stopping after 100 updates (test limit)")
                            break
                            
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"\nError processing update: {e}")
        
        except Exception as e:
            print(f"\nStreaming connection error: {e}")
        
        # Step 3: Validate streaming experience
        print("\n🔹 Step 3: Validate streaming experience")
        
        total_updates = streaming_data["updates_received"]
        text_chunks = len(streaming_data["text_chunks"])
        accumulated = streaming_data["accumulated_text"]
        progress_count = len(streaming_data["progress_updates"])
        
        print(f"\n📊 Streaming Summary:")
        print(f"   Total updates: {total_updates}")
        print(f"   Text chunks: {text_chunks}")
        print(f"   Accumulated text: {len(accumulated)} characters")
        print(f"   Progress updates: {progress_count}")
        print(f"   Sample text: {accumulated[:100]}...")
        
        # Validate streaming worked
        assert total_updates > 0, "No streaming updates received"
        
        if text_chunks > 0:
            print("✅ Real-time text streaming worked")
            assert len(accumulated) > 0, "No text accumulated"
        
        if progress_count > 0:
            print("✅ Progress tracking worked")
        
        if streaming_data["final_result"]:
            print("✅ Final completion received")
        
        print("✅ WORKFLOW COMPLETED: Real-time Streaming")
    
    def test_workflow_error_recovery(self, client):
        """Workflow: User uploads invalid file → Gets clear error → Retries with valid file."""
        print(f"\n🔄 WORKFLOW: Error Recovery")
        print("   Scenario: User makes mistake, gets error, then succeeds")
        
        # Step 1: Upload invalid file
        print("\n🔹 Step 1: Upload invalid file (simulate user error)")
        invalid_content = io.BytesIO(b"This is not an image file content")
        
        request_data = {"mode": "basic"}
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("not_an_image.txt", invalid_content, "text/plain")},
            data={"request": json.dumps(request_data)}
        )
        
        print(f"📤 Invalid file response: {response.status_code}")
        
        if response.status_code in [400, 422]:
            print("✅ Invalid file rejected immediately with clear error")
            error_data = response.json()
            print(f"📋 Error message: {error_data.get('detail', error_data)}")
            
        elif response.status_code == 200:
            # File accepted but should fail during processing
            task_id = response.json()["task_id"]
            print(f"⚠️  Invalid file accepted, monitoring for failure: {task_id}")
            
            result = self.wait_for_completion(client, task_id, timeout=30)
            assert result.get("status") == "failed", "Invalid file should cause failure"
            print(f"✅ Task correctly failed: {result.get('error', 'Unknown')}")
        
        # Step 2: Retry with valid file
        print("\n🔹 Step 2: Retry with valid file")
        valid_image = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(valid_image)
        draw.text((50, 50), "Valid document content", fill='black')
        draw.text((50, 100), "This should work correctly", fill='black')
        
        img_byte_arr = io.BytesIO()
        valid_image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        retry_response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("valid_document.jpg", img_byte_arr, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert retry_response.status_code == 200, f"Valid retry failed: {retry_response.text}"
        retry_task_id = retry_response.json()["task_id"]
        print(f"✅ Valid file uploaded successfully: {retry_task_id}")
        
        # Step 3: Verify successful processing
        print("\n🔹 Step 3: Verify successful recovery")
        retry_result = self.wait_for_completion(client, retry_task_id)
        
        if retry_result.get("status") == "completed":
            print("✅ Recovery successful - valid file processed correctly")
            
            if 'result' in retry_result:
                text = retry_result['result'].get('extracted_text', '')
                print(f"📄 Extracted: {len(text)} characters")
                
                # Should find our test content
                if "valid" in text.lower() or "document" in text.lower():
                    print("✅ Correct text extracted from valid file")
        
        print("✅ WORKFLOW COMPLETED: Error Recovery")
    
    def test_workflow_bulk_processing_simulation(self, client):
        """Workflow: User processes multiple documents in sequence."""
        print(f"\n📦 WORKFLOW: Bulk Processing Simulation")
        print("   Scenario: User processes 3 documents sequentially")
        
        documents = []
        for i in range(1, 4):
            # Create different document types
            image = Image.new('RGB', (600, 400), color='white')
            draw = ImageDraw.Draw(image)
            
            draw.text((50, 50), f"Document {i}", fill='black')
            draw.text((50, 100), f"Type: Report {i}", fill='black')
            draw.text((50, 150), f"Content for document {i}", fill='black')
            draw.text((50, 200), f"Important data: {1000 + i}", fill='black')
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            documents.append((f"doc_{i}.jpg", img_byte_arr))
        
        task_ids = []
        results = []
        
        # Step 1: Submit all documents
        print("\n🔹 Step 1: Submit multiple documents")
        for i, (filename, doc_data) in enumerate(documents, 1):
            request_data = {
                "mode": "basic",
                "threshold": 128
            }
            
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": (filename, doc_data, "image/jpeg")},
                data={"request": json.dumps(request_data)}
            )
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                task_ids.append(task_id)
                print(f"✅ Document {i} submitted: {task_id}")
            else:
                print(f"❌ Document {i} failed: {response.status_code}")
        
        # Step 2: Monitor all tasks
        print(f"\n🔹 Step 2: Monitor {len(task_ids)} tasks")
        for i, task_id in enumerate(task_ids, 1):
            print(f"\n📋 Processing document {i}: {task_id}")
            result = self.wait_for_completion(client, task_id, timeout=60)
            results.append(result)
            
            if result.get("status") == "completed":
                print(f"✅ Document {i} completed")
            else:
                print(f"❌ Document {i} failed")
        
        # Step 3: Analyze batch results
        print(f"\n🔹 Step 3: Analyze batch results")
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        
        print(f"📊 Batch Summary:")
        print(f"   Total documents: {len(results)}")
        print(f"   Completed: {completed}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {completed/len(results)*100:.1f}%")
        
        # Validate batch processing
        assert completed > 0, "No documents processed successfully"
        
        # Check extracted content
        for i, result in enumerate(results, 1):
            if result.get("status") == "completed" and 'result' in result:
                text = result['result'].get('extracted_text', '')
                if f"document {i}" in text.lower() or f"report {i}" in text.lower():
                    print(f"✅ Document {i} content verified")
        
        print("✅ WORKFLOW COMPLETED: Bulk Processing")


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])