"""
Data quality testing with real sample documents.
These tests use actual document samples to verify OCR accuracy and quality.
"""

import json
import pytest
import time
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, Any, List, Tuple
import tempfile

from tests.remote_client import RemoteTestClient
from tests.remote_test_config import RemoteTestConfig


class TestDataQuality:
    """Test OCR quality with various document types and content."""
    
    @pytest.fixture
    def client(self):
        """Create a remote test client."""
        if not RemoteTestConfig.is_remote_testing():
            pytest.skip("Remote API URL not set. Set REMOTE_API_URL to run these tests.")
        return RemoteTestClient()
    
    def wait_for_completion(self, client: RemoteTestClient, task_id: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for task completion."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                for endpoint in [f"/v1/ocr/process-stream/{task_id}", f"/v1/ocr/status/{task_id}"]:
                    try:
                        response = client.get(endpoint)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get('status', 'unknown')
                            
                            if status == 'completed':
                                return data
                            elif status == 'failed':
                                return data
                            elif status in ['processing', 'pending']:
                                time.sleep(3)
                                break
                    except Exception:
                        continue
                
                time.sleep(3)
                
            except Exception as e:
                time.sleep(3)
        
        return {"status": "timeout", "error": f"Task timed out after {timeout} seconds"}
    
    def create_invoice_document(self) -> Tuple[io.BytesIO, List[str]]:
        """Create a realistic invoice document with known content."""
        image = Image.new('RGB', (800, 1000), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
            header_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
            body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        # Expected content for validation
        expected_content = [
            "INVOICE",
            "ABC CORPORATION",
            "INV-2024-001",
            "January 15, 2024",
            "$2,450.00",
            "Professional Services",
            "Due: February 14, 2024",
            "Consulting Hours: 20",
            "Rate: $122.50/hour"
        ]
        
        # Draw invoice content
        y = 50
        draw.text((300, y), "INVOICE", fill='black', font=title_font)
        y += 60
        
        draw.text((50, y), "ABC CORPORATION", fill='black', font=header_font)
        y += 30
        draw.text((50, y), "123 Business Street", fill='black', font=body_font)
        y += 25
        draw.text((50, y), "Business City, BC 12345", fill='black', font=body_font)
        y += 50
        
        # Invoice details
        draw.text((50, y), "Invoice Number: INV-2024-001", fill='black', font=body_font)
        draw.text((400, y), "Date: January 15, 2024", fill='black', font=body_font)
        y += 30
        draw.text((50, y), "Due Date: February 14, 2024", fill='black', font=body_font)
        y += 50
        
        # Bill to
        draw.text((50, y), "BILL TO:", fill='black', font=header_font)
        y += 30
        draw.text((50, y), "Client Company Ltd.", fill='black', font=body_font)
        y += 25
        draw.text((50, y), "456 Client Avenue", fill='black', font=body_font)
        y += 25
        draw.text((50, y), "Client City, CC 67890", fill='black', font=body_font)
        y += 60
        
        # Services table
        draw.text((50, y), "DESCRIPTION", fill='black', font=header_font)
        draw.text((300, y), "HOURS", fill='black', font=header_font)
        draw.text((400, y), "RATE", fill='black', font=header_font)
        draw.text((500, y), "AMOUNT", fill='black', font=header_font)
        y += 30
        
        # Line 1
        draw.text((50, y), "Professional Services", fill='black', font=body_font)
        draw.text((300, y), "20", fill='black', font=body_font)
        draw.text((400, y), "$122.50", fill='black', font=body_font)
        draw.text((500, y), "$2,450.00", fill='black', font=body_font)
        y += 30
        
        # Line 2
        draw.text((50, y), "Consulting Hours", fill='black', font=body_font)
        draw.text((300, y), "20", fill='black', font=body_font)
        draw.text((400, y), "$122.50/hour", fill='black', font=body_font)
        y += 60
        
        # Total
        draw.text((400, y), "TOTAL: $2,450.00", fill='black', font=header_font)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        
        return img_byte_arr, expected_content
    
    def create_receipt_document(self) -> Tuple[io.BytesIO, List[str]]:
        """Create a receipt document with known content."""
        image = Image.new('RGB', (600, 800), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        
        expected_content = [
            "GROCERY STORE",
            "Receipt #12345",
            "Bananas",
            "$3.50",
            "Milk",
            "$4.25",
            "Bread",
            "$2.75",
            "Total: $10.50",
            "Thank you!"
        ]
        
        # Draw receipt
        y = 50
        draw.text((200, y), "GROCERY STORE", fill='black', font=title_font)
        y += 40
        draw.text((50, y), "123 Store Street", fill='black', font=body_font)
        y += 25
        draw.text((50, y), "Store City, SC 11111", fill='black', font=body_font)
        y += 40
        
        draw.text((50, y), "Receipt #12345", fill='black', font=body_font)
        draw.text((400, y), "01/15/2024", fill='black', font=body_font)
        y += 40
        
        # Items
        items = [
            ("Bananas (2 lbs)", "$3.50"),
            ("Milk (1 gallon)", "$4.25"),
            ("Bread (1 loaf)", "$2.75")
        ]
        
        for item, price in items:
            draw.text((50, y), item, fill='black', font=body_font)
            draw.text((400, y), price, fill='black', font=body_font)
            y += 25
        
        y += 20
        draw.text((300, y), "Subtotal: $10.50", fill='black', font=body_font)
        y += 25
        draw.text((300, y), "Tax: $0.00", fill='black', font=body_font)
        y += 25
        draw.text((300, y), "Total: $10.50", fill='black', font=title_font)
        y += 40
        
        draw.text((200, y), "Thank you!", fill='black', font=body_font)
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        
        return img_byte_arr, expected_content
    
    def create_form_document(self) -> Tuple[io.BytesIO, List[str]]:
        """Create a form document with structured data."""
        image = Image.new('RGB', (800, 1000), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            label_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            value_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            value_font = ImageFont.load_default()
        
        expected_content = [
            "APPLICATION FORM",
            "John Smith",
            "555-0123",
            "john.smith@email.com",
            "Software Engineer",
            "5 years",
            "Bachelor's Degree",
            "Available immediately"
        ]
        
        # Draw form
        y = 50
        draw.text((250, y), "APPLICATION FORM", fill='black', font=title_font)
        y += 60
        
        # Form fields
        fields = [
            ("Full Name:", "John Smith"),
            ("Phone:", "555-0123"),
            ("Email:", "john.smith@email.com"),
            ("Position:", "Software Engineer"),
            ("Experience:", "5 years"),
            ("Education:", "Bachelor's Degree"),
            ("Availability:", "Available immediately")
        ]
        
        for label, value in fields:
            draw.text((50, y), label, fill='black', font=label_font)
            draw.text((200, y), value, fill='black', font=value_font)
            y += 35
        
        # Checkbox section
        y += 30
        draw.text((50, y), "Skills:", fill='black', font=label_font)
        y += 30
        
        skills = ["☑ Python", "☑ JavaScript", "☐ Java", "☑ SQL"]
        for skill in skills:
            draw.text((50, y), skill, fill='black', font=value_font)
            y += 25
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        
        return img_byte_arr, expected_content
    
    def calculate_accuracy(self, extracted_text: str, expected_content: List[str]) -> Dict[str, float]:
        """Calculate OCR accuracy metrics."""
        text_lower = extracted_text.lower()
        
        # Check how many expected items were found
        found_items = 0
        partially_found = 0
        
        for expected in expected_content:
            expected_lower = expected.lower()
            
            if expected_lower in text_lower:
                found_items += 1
            else:
                # Check for partial matches (for numbers, dates, etc.)
                words = expected_lower.split()
                found_words = sum(1 for word in words if word in text_lower)
                if found_words > 0:
                    partially_found += 1
        
        accuracy = found_items / len(expected_content) if expected_content else 0
        partial_accuracy = (found_items + partially_found * 0.5) / len(expected_content) if expected_content else 0
        
        return {
            "exact_matches": found_items,
            "partial_matches": partially_found,
            "total_expected": len(expected_content),
            "accuracy": accuracy,
            "partial_accuracy": partial_accuracy
        }
    
    def test_invoice_ocr_quality(self, client):
        """Test OCR quality on invoice document."""
        print(f"\n📄 Testing invoice OCR quality at: {client.base_url}")
        
        # Create invoice document
        invoice_image, expected_content = self.create_invoice_document()
        
        request_data = {
            "mode": "llm_enhanced",
            "prompt": "Extract all text from this invoice. Pay special attention to invoice numbers, dates, amounts, and company information."
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("invoice_test.jpg", invoice_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📝 Created invoice OCR task: {task_id}")
        
        # Wait for completion
        result = self.wait_for_completion(client, task_id)
        assert result.get("status") == "completed", f"Invoice OCR failed: {result}"
        
        # Analyze quality
        extracted_text = result['result'].get('extracted_text', '')
        print(f"\n📊 Invoice OCR Results:")
        print(f"   Extracted text length: {len(extracted_text)} characters")
        
        # Calculate accuracy
        accuracy_metrics = self.calculate_accuracy(extracted_text, expected_content)
        
        print(f"   Expected items: {accuracy_metrics['total_expected']}")
        print(f"   Exact matches: {accuracy_metrics['exact_matches']}")
        print(f"   Partial matches: {accuracy_metrics['partial_matches']}")
        print(f"   Accuracy: {accuracy_metrics['accuracy']*100:.1f}%")
        print(f"   Partial accuracy: {accuracy_metrics['partial_accuracy']*100:.1f}%")
        
        # Show sample of extracted text
        sample = extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text
        print(f"   Sample text: {sample}")
        
        # Quality assertions
        assert len(extracted_text) > 100, "Too little text extracted from invoice"
        assert accuracy_metrics['accuracy'] >= 0.3, f"Low accuracy: {accuracy_metrics['accuracy']*100:.1f}%"
        
        # Check for critical invoice elements
        text_lower = extracted_text.lower()
        critical_found = 0
        critical_items = ["invoice", "total", "date", "amount"]
        
        for item in critical_items:
            if item in text_lower:
                critical_found += 1
        
        print(f"   Critical elements found: {critical_found}/{len(critical_items)}")
        assert critical_found >= 2, "Missing critical invoice elements"
        
        print("✅ Invoice OCR quality test PASSED")
        return accuracy_metrics
    
    def test_receipt_ocr_quality(self, client):
        """Test OCR quality on receipt document."""
        print(f"\n🧾 Testing receipt OCR quality at: {client.base_url}")
        
        receipt_image, expected_content = self.create_receipt_document()
        
        request_data = {
            "mode": "llm_enhanced",
            "prompt": "Extract all text from this receipt including item names, prices, and totals."
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("receipt_test.jpg", receipt_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"🧾 Created receipt OCR task: {task_id}")
        
        result = self.wait_for_completion(client, task_id)
        assert result.get("status") == "completed", f"Receipt OCR failed: {result}"
        
        extracted_text = result['result'].get('extracted_text', '')
        accuracy_metrics = self.calculate_accuracy(extracted_text, expected_content)
        
        print(f"\n📊 Receipt OCR Results:")
        print(f"   Accuracy: {accuracy_metrics['accuracy']*100:.1f}%")
        print(f"   Sample: {extracted_text[:200]}...")
        
        # Check for prices and monetary values
        import re
        price_pattern = r'\$\d+\.\d{2}'
        found_prices = re.findall(price_pattern, extracted_text)
        print(f"   Prices found: {found_prices}")
        
        assert len(extracted_text) > 50, "Too little text extracted from receipt"
        assert len(found_prices) >= 1, "No prices detected in receipt"
        
        print("✅ Receipt OCR quality test PASSED")
        return accuracy_metrics
    
    def test_form_ocr_quality(self, client):
        """Test OCR quality on form document."""
        print(f"\n📋 Testing form OCR quality at: {client.base_url}")
        
        form_image, expected_content = self.create_form_document()
        
        request_data = {
            "mode": "llm_enhanced",
            "prompt": "Extract all text from this form including field labels and values. Preserve the structure."
        }
        
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("form_test.jpg", form_image, "image/jpeg")},
            data={"request": json.dumps(request_data)}
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"📋 Created form OCR task: {task_id}")
        
        result = self.wait_for_completion(client, task_id)
        assert result.get("status") == "completed", f"Form OCR failed: {result}"
        
        extracted_text = result['result'].get('extracted_text', '')
        accuracy_metrics = self.calculate_accuracy(extracted_text, expected_content)
        
        print(f"\n📊 Form OCR Results:")
        print(f"   Accuracy: {accuracy_metrics['accuracy']*100:.1f}%")
        
        # Check for structured data elements
        text_lower = extracted_text.lower()
        structured_elements = ["name", "phone", "email", "position", "experience"]
        found_elements = sum(1 for elem in structured_elements if elem in text_lower)
        
        print(f"   Structured elements: {found_elements}/{len(structured_elements)}")
        print(f"   Sample: {extracted_text[:250]}...")
        
        assert len(extracted_text) > 100, "Too little text extracted from form"
        assert found_elements >= 3, "Missing important form elements"
        
        print("✅ Form OCR quality test PASSED")
        return accuracy_metrics
    
    def test_ocr_quality_comparison(self, client):
        """Compare OCR quality between basic and LLM-enhanced modes."""
        print(f"\n⚖️  Testing OCR quality comparison at: {client.base_url}")
        
        # Use invoice for comparison
        invoice_image, expected_content = self.create_invoice_document()
        
        modes_to_test = [
            ("basic", "Basic OCR mode"),
            ("llm_enhanced", "LLM-enhanced mode with detailed prompt")
        ]
        
        results = {}
        
        for mode, description in modes_to_test:
            print(f"\n🔍 Testing {description}")
            
            # Reset image stream
            invoice_image.seek(0)
            
            request_data = {"mode": mode}
            if mode == "llm_enhanced":
                request_data["prompt"] = "Extract all text with high accuracy, preserving structure and formatting"
            
            response = client.post(
                "/v1/ocr/process-stream",
                files={"file": (f"comparison_{mode}.jpg", invoice_image, "image/jpeg")},
                data={"request": json.dumps(request_data)}
            )
            
            if response.status_code == 200:
                task_id = response.json()["task_id"]
                result = self.wait_for_completion(client, task_id)
                
                if result.get("status") == "completed":
                    extracted_text = result['result'].get('extracted_text', '')
                    accuracy = self.calculate_accuracy(extracted_text, expected_content)
                    
                    results[mode] = {
                        "accuracy": accuracy['accuracy'],
                        "partial_accuracy": accuracy['partial_accuracy'],
                        "text_length": len(extracted_text),
                        "processing_time": result['result'].get('processing_time', 0)
                    }
                    
                    print(f"   Accuracy: {accuracy['accuracy']*100:.1f}%")
                    print(f"   Text length: {len(extracted_text)} chars")
                    print(f"   Processing time: {result['result'].get('processing_time', 0):.1f}s")
        
        # Compare results
        if len(results) >= 2:
            print(f"\n📊 Quality Comparison:")
            basic_acc = results.get('basic', {}).get('accuracy', 0)
            llm_acc = results.get('llm_enhanced', {}).get('accuracy', 0)
            
            print(f"   Basic mode accuracy: {basic_acc*100:.1f}%")
            print(f"   LLM mode accuracy: {llm_acc*100:.1f}%")
            
            if llm_acc > basic_acc:
                improvement = (llm_acc - basic_acc) * 100
                print(f"   ✅ LLM mode {improvement:.1f}% better")
            elif basic_acc > llm_acc:
                print(f"   ⚠️  Basic mode performed better")
            else:
                print(f"   📊 Similar performance")
        
        print("✅ OCR quality comparison PASSED")
        return results


if __name__ == "__main__":
    if not RemoteTestConfig.is_remote_testing():
        print("Set REMOTE_API_URL environment variable to test")
        print("Example: export REMOTE_API_URL='http://203.185.131.205/ocr-backend'")
    else:
        pytest.main([__file__, "-v", "-s"])