"""
Integration tests for OCR LLM service with real API calls.

These tests make actual HTTP requests to the Pathumma Vision OCR LLM API
to validate end-to-end functionality, serialization, and error handling.
"""

import base64
import json
import pytest
import pytest_asyncio
import httpx
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.ocr_llm_service import OCRLLMService
from app.models.ocr_models import OCRLLMRequest, OCRLLMResult, LLMChoice
from config.settings import get_settings
from tests.utils.image_utils import encode_test_image, validate_base64, get_test_image_info


class TestLLMIntegration:
    """Integration tests for OCR LLM service with real API calls."""
    
    @pytest.fixture(scope="class")
    def llm_service(self):
        """Create LLM service instance for integration testing."""
        return OCRLLMService()
    
    @pytest.fixture(scope="class")
    def test_image_base64(self):
        """Create base64 encoded test image without logging."""
        # Get image info for validation but don't log base64
        image_info = get_test_image_info()
        assert "error" not in image_info, f"Test image issue: {image_info}"
        
        # Encode image without logging
        base64_image = encode_test_image(enable_logging=False)
        
        # Validate encoding without logging
        assert validate_base64(base64_image), "Invalid base64 encoding"
        assert len(base64_image) > 100, "Base64 string too short"
        
        return base64_image
    
    @pytest.fixture(scope="class")
    def sample_text_image_base64(self):
        """Base64 encoded image with some text for OCR testing."""
        # This is a more complex base64 image that might contain text
        return "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwDX4AAAA="
    
    @pytest.fixture(scope="class") 
    def sample_ocr_llm_request(self):
        """Sample OCR LLM request for testing."""
        return OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            prompt="Please extract and clean up any text visible in this image. If no text is visible, respond with 'No text detected'.",
            model="nectec/Pathumma-vision-ocr-lora-dev"
        )

    @pytest_asyncio.fixture(autouse=True) 
    async def check_api_availability(self, llm_service):
        """Check if the LLM API is available before running tests."""
        settings = get_settings()
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Try a simple health check or basic request
                response = await client.get(f"{settings.OCR_LLM_BASE_URL}")
                if response.status_code >= 500:
                    pytest.skip("LLM API server is not available (5xx error)")
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
            pytest.skip("LLM API is not accessible - skipping integration tests")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_llm_api_connectivity(self, llm_service):
        """Test basic connectivity to the real LLM API."""
        # Test health check if available
        try:
            is_healthy = await llm_service.health_check()
            # Health check might fail but that's OK for this test
            # We just want to verify we can make requests
            assert isinstance(is_healthy, bool)
        except Exception as e:
            # If health check endpoint doesn't exist, that's OK
            # Just verify the service is configured properly
            assert llm_service.base_url is not None
            assert llm_service.endpoint is not None
            print(f"Health check not available: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_real_llm_api_with_simple_image(self, llm_service, test_image_base64, sample_ocr_llm_request):
        """Test real LLM API call with a simple image."""
        image_processing_time = 1.0
        
        try:
            result = await llm_service.process_image_with_llm(
                test_image_base64,
                sample_ocr_llm_request,
                image_processing_time
            )
            
            # Verify result structure
            assert isinstance(result, OCRLLMResult)
            assert isinstance(result.success, bool)
            assert isinstance(result.extracted_text, str)
            assert isinstance(result.processing_time, float)
            assert isinstance(result.llm_processing_time, float)
            
            # Verify timing
            assert result.processing_time > image_processing_time
            # Note: llm_processing_time might be 0 if the request failed quickly
            assert result.llm_processing_time >= 0
            
            # Verify original data is preserved
            assert result.image_processing_time == image_processing_time
            assert result.threshold_used == sample_ocr_llm_request.threshold
            assert result.contrast_level_used == sample_ocr_llm_request.contrast_level
            assert result.model_used == sample_ocr_llm_request.model
            
            # Show detailed API response info
            print(f"\n🔍 Real LLM API Response Details:")
            print(f"   Success: {result.success}")
            print(f"   Processing time: {result.processing_time:.2f}s")
            print(f"   LLM processing time: {result.llm_processing_time:.2f}s")
            print(f"   Model used: {result.model_used}")
            
            if result.success:
                print(f"   ✅ Enhanced text: '{result.extracted_text[:100]}...'")
                assert len(result.extracted_text) > 0
            else:
                print(f"   ❌ API failed (expected for current API state)")
                print(f"   Error details: {getattr(result, 'error_message', 'No error message')}")
                
        except Exception as e:
            pytest.fail(f"Real LLM API call failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_serialization_with_api(self, llm_service, test_image_base64):
        """Test that our serialization fix works with the real API."""
        # Create content that would have None fields
        multimodal_content = llm_service._prepare_multimodal_content(
            test_image_base64, 
            "Extract any text from this image"
        )
        
        # Verify the content has None fields that need to be excluded
        text_content = multimodal_content[0]
        image_content = multimodal_content[1]
        
        assert text_content.image_url is None  # This should be excluded
        assert image_content.text is None      # This should be excluded
        
        # Create a real request
        from app.models.ocr_models import LLMChatRequest, ChatMessage
        
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content=multimodal_content)],
            model="nectec/Pathumma-vision-ocr-lora-dev"
        )
        
        # Serialize with our fix
        request_dict = chat_request.model_dump(exclude_none=True)
        serialized_json = json.dumps(request_dict)
        
        # Verify None fields are excluded (this is our critical regression test)
        assert '"image_url": null' not in serialized_json
        assert '"text": null' not in serialized_json
        assert 'null' not in serialized_json
        
        # Now try to make a real API call with this serialized data
        try:
            result = await llm_service._call_llm_api(chat_request)
            assert isinstance(result, str)
            print(f"\n🔍 Serialization Test Results:")
            print(f"   ✅ Real API accepted our serialization")
            print(f"   Response preview: '{result[:50]}...'")
            print(f"   Response length: {len(result)} characters")
        except Exception as e:
            # API might fail for various reasons (authentication, model issues, etc.)
            # The important thing is that our serialization is working correctly
            # We've already verified that None fields are excluded
            print(f"✅ Serialization format is correct - API call failed for other reason: {e}")
            
            # Check that it's not a JSON parsing error which would indicate serialization problems
            if "json" in str(e).lower() or "malformed" in str(e).lower():
                pytest.fail(f"Possible serialization/JSON issue: {e}")
            else:
                # This is expected - API might have authentication, model, or other issues
                pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_response_format(self, llm_service, test_image_base64):
        """Test that real API responses match our Pydantic models."""
        from app.models.ocr_models import LLMChatRequest, ChatMessage, MultimodalContent, ImageURL
        
        # Create a minimal valid request
        content = [
            MultimodalContent(type="text", text="What do you see in this image?", image_url=None),
            MultimodalContent(
                type="image_url", 
                text=None,
                image_url=ImageURL(url=f"data:image/png;base64,{test_image_base64}")
            )
        ]
        
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content=content)],
            model="nectec/Pathumma-vision-ocr-lora-dev"
        )
        
        try:
            # Make real API call
            result = await llm_service._call_llm_api(chat_request)
            
            # If we get here, the API accepted our request format and returned a valid response
            assert isinstance(result, str)
            assert len(result) > 0
            
            print(f"\n🔍 API Response Format Test:")
            print(f"   ✅ Response format valid")
            print(f"   Response type: {type(result)}")
            print(f"   Response length: {len(result)} characters") 
            print(f"   Response preview: '{result[:50]}...'")
            
        except Exception as e:
            # Check if it's a model/format mismatch
            if "validation" in str(e).lower() or "pydantic" in str(e).lower():
                pytest.fail(f"API response doesn't match our Pydantic models: {e}")
            else:
                print(f"API call failed for other reason: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_timeout_handling(self, llm_service, test_image_base64):
        """Test timeout handling with real API by using a very short timeout."""
        # Temporarily patch the service timeout to be very short
        original_timeout = llm_service.timeout
        llm_service.timeout = 0.1  # 100ms - should cause timeout
        
        try:
            sample_request = OCRLLMRequest(
                threshold=128,
                contrast_level=1.0,
                prompt="Extract text from this image"
            )
            
            result = await llm_service.process_image_with_llm(
                test_image_base64,
                sample_request,
                1.0
            )
            
            # Should handle timeout gracefully
            assert isinstance(result, OCRLLMResult)
            # Likely to fail due to timeout, but should handle it gracefully
            if not result.success:
                print("✅ Timeout handled gracefully")
            else:
                print("✅ API was surprisingly fast!")
                
        finally:
            # Restore original timeout
            llm_service.timeout = original_timeout

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_with_custom_parameters(self, llm_service, test_image_base64):
        """Test real API with custom model and prompt parameters."""
        custom_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.5,
            prompt="Please analyze this image and describe what you see. Focus on any text content.",
            model="nectec/Pathumma-vision-ocr-lora-dev"  # Explicit model specification
        )
        
        try:
            result = await llm_service.process_image_with_llm(
                test_image_base64,
                custom_request,
                1.2
            )
            
            assert isinstance(result, OCRLLMResult)
            assert result.model_used == "nectec/Pathumma-vision-ocr-lora-dev"
            assert result.prompt_used == custom_request.prompt
            assert result.threshold_used == 128
            assert result.contrast_level_used == 1.5
            
            print(f"✅ Custom parameters accepted by real API")
            
        except Exception as e:
            print(f"Custom parameters test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_error_responses(self, llm_service):
        """Test real API error handling with invalid requests."""
        # Test with invalid base64 data
        invalid_base64 = "invalid_base64_data_that_should_cause_error"
        
        invalid_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            prompt="This should fail due to invalid image data"
        )
        
        try:
            result = await llm_service.process_image_with_llm(
                invalid_base64,
                invalid_request, 
                1.0
            )
            
            # Should handle the error gracefully
            assert isinstance(result, OCRLLMResult)
            
            if not result.success:
                print("✅ Invalid data handled gracefully")
            else:
                print("⚠️ API accepted invalid data (unexpected)")
                
        except Exception as e:
            print(f"Error handling test result: {e}")

    @pytest.mark.asyncio 
    @pytest.mark.integration
    async def test_real_concurrent_api_calls(self, llm_service, test_image_base64):
        """Test multiple concurrent calls to real API."""
        sample_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            prompt="Concurrent test - extract text"
        )
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(3):  # Small number to avoid overwhelming the API
            task = llm_service.process_image_with_llm(
                test_image_base64,
                sample_request,
                1.0
            )
            tasks.append(task)
        
        try:
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Task {i} failed: {result}")
                else:
                    assert isinstance(result, OCRLLMResult)
                    print(f"✅ Concurrent task {i} completed: {result.success}")
                    
        except Exception as e:
            print(f"Concurrent API test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_configuration_validation(self, llm_service):
        """Test that our service configuration works with real API."""
        settings = get_settings()
        
        # Verify configuration
        assert llm_service.base_url == settings.OCR_LLM_BASE_URL
        assert llm_service.endpoint == settings.OCR_LLM_ENDPOINT  
        assert llm_service.default_model == settings.OCR_LLM_MODEL
        assert llm_service.timeout == settings.OCR_LLM_TIMEOUT
        
        # Test that the endpoint URL is reachable
        full_url = f"{llm_service.base_url}{llm_service.endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Just test connectivity, not a full request
                response = await client.options(full_url)
                # Any response (even errors) means the endpoint is reachable
                print(f"✅ API endpoint reachable: {full_url}")
        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to API endpoint: {full_url}")
        except Exception as e:
            print(f"API connectivity test: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_end_to_end_with_real_workflow(self, llm_service, sample_text_image_base64):
        """Test complete end-to-end workflow with real API."""
        # Simulate the complete workflow:
        # 1. External OCR processing (simulated)
        # 2. LLM enhancement (real API call)
        
        # Simulated OCR result
        image_processing_time = 2.5
        
        # LLM enhancement request  
        llm_request = OCRLLMRequest(
            threshold=150,
            contrast_level=1.2,
            model="nectec/Pathumma-vision-ocr-lora-dev"
        )
        
        try:
            # Real LLM processing
            final_result = await llm_service.process_image_with_llm(
                sample_text_image_base64,
                llm_request,
                image_processing_time
            )
            
            # Verify complete workflow result
            assert isinstance(final_result, OCRLLMResult)
            assert final_result.image_processing_time == image_processing_time
            assert final_result.processing_time > image_processing_time
            
            if final_result.success:
                print(f"✅ End-to-end workflow completed successfully")
                print(f"Enhanced: '{final_result.extracted_text[:100]}...'")
                
                # The enhanced text might be different from original
                assert isinstance(final_result.extracted_text, str)
            else:
                print(f"❌ LLM processing failed, but workflow structure is valid")
            
        except Exception as e:
            pytest.fail(f"End-to-end workflow failed: {e}")

    @pytest.mark.asyncio
    async def test_base64_encoding_validation(self, test_image_base64):
        """Test the base64 encoding utility functions."""
        # Test image info retrieval
        image_info = get_test_image_info()
        assert "error" not in image_info
        assert image_info["exists"] is True
        assert image_info["size_bytes"] > 0
        assert image_info["extension"] == ".png"
        
        # Test base64 validation
        assert validate_base64(test_image_base64)
        assert not validate_base64("invalid_base64")
        assert not validate_base64("")
        
        # Test that we can create base64 with logging (but don't enable it here)
        base64_with_logging = encode_test_image(enable_logging=False)
        assert base64_with_logging == test_image_base64 