"""
Unit tests for the OCR LLM service.
"""

import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import httpx
from PIL import Image

from app.services.ocr_llm_service import OCRLLMService
from app.models.ocr_models import (
    OCRLLMRequest, 
    OCRLLMResult, 
    LLMChatRequest, 
    LLMChatResponse, 
    ChatMessage, 
    MultimodalContent, 
    ImageURL,
    LLMChoice
)


class TestOCRLLMService:
    """Test cases for OCRLLMService."""
    
    @pytest.fixture
    def llm_service(self):
        """Create an instance of OCRLLMService for testing."""
        return OCRLLMService()
    
    @pytest.fixture
    def sample_base64_image(self):
        """Sample base64 encoded image data."""
        return "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwDX4AAAA="
    
    @pytest.fixture
    def sample_ocr_llm_request(self):
        """Sample OCR LLM request."""
        return OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            prompt="Extract text from this image",
            model="nectec/Pathumma-vision-ocr-lora-dev"
        )
    
    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM API response."""
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1699999999,
            "model": "nectec/Pathumma-vision-ocr-lora-dev",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Enhanced extracted text from image"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }

    @pytest.mark.asyncio
    async def test_process_image_with_llm_success(self, llm_service, sample_base64_image, sample_ocr_llm_request):
        """Test successful LLM-enhanced OCR processing."""
        original_ocr_text = "Original OCR text"
        ocr_processing_time = 1.5
        
        with patch.object(llm_service, '_call_llm_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Enhanced extracted text from image"
            
            result = await llm_service.process_image_with_llm(
                sample_base64_image, 
                original_ocr_text, 
                sample_ocr_llm_request, 
                ocr_processing_time
            )
            
            assert result.success is True
            assert result.extracted_text == "Enhanced extracted text from image"
            assert result.original_ocr_text == "Original OCR text"
            assert result.threshold_used == sample_ocr_llm_request.threshold
            assert result.contrast_level_used == sample_ocr_llm_request.contrast_level
            assert result.model_used == sample_ocr_llm_request.model
            assert result.prompt_used == sample_ocr_llm_request.prompt
            assert result.processing_time > ocr_processing_time
            assert result.ocr_processing_time == ocr_processing_time
            assert result.llm_processing_time > 0
            
            # Verify API was called
            mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_image_with_llm_failure(self, llm_service, sample_base64_image, sample_ocr_llm_request):
        """Test LLM-enhanced OCR processing failure."""
        original_ocr_text = "Original OCR text"
        ocr_processing_time = 1.5
        
        with patch.object(llm_service, '_call_llm_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = Exception("LLM API Error")
            
            result = await llm_service.process_image_with_llm(
                sample_base64_image, 
                original_ocr_text, 
                sample_ocr_llm_request, 
                ocr_processing_time
            )
            
            assert result.success is False
            assert result.extracted_text == ""
            assert result.original_ocr_text == "Original OCR text"
            assert result.processing_time > ocr_processing_time
            assert result.llm_processing_time == 0.0

    def test_prepare_multimodal_content(self, llm_service, sample_base64_image):
        """Test multimodal content preparation."""
        prompt = "Extract text from this image"
        
        content = llm_service._prepare_multimodal_content(sample_base64_image, prompt)
        
        assert isinstance(content, list)
        assert len(content) == 2
        
        # Check text content
        text_content = content[0]
        assert isinstance(text_content, MultimodalContent)
        assert text_content.type == "text"
        assert text_content.text == prompt
        assert text_content.image_url is None
        
        # Check image content
        image_content = content[1]
        assert isinstance(image_content, MultimodalContent)
        assert image_content.type == "image_url"
        assert image_content.text is None
        assert isinstance(image_content.image_url, ImageURL)
        assert image_content.image_url.url == f"data:image/jpeg;base64,{sample_base64_image}"

    @pytest.mark.asyncio
    async def test_call_llm_api_success(self, llm_service, sample_llm_response):
        """Test successful LLM API call."""
        chat_request = LLMChatRequest(
            messages=[
                ChatMessage(role="user", content=[
                    MultimodalContent(type="text", text="Extract text", image_url=None)
                ])
            ],
            model="test-model"
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.json.return_value = sample_llm_response
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            result = await llm_service._call_llm_api(chat_request)
            
            assert result == "Enhanced extracted text from image"
            mock_client.post.assert_called_once()
            
            # Verify the request was serialized properly
            call_args = mock_client.post.call_args
            request_data = call_args[1]['json']
            
            # Check that None fields are excluded
            assert 'image_url' not in str(request_data)  # Should be excluded from text content
            assert 'text' not in str(request_data) or 'null' not in str(request_data)  # Should be excluded from image content

    @pytest.mark.asyncio
    async def test_call_llm_api_timeout(self, llm_service):
        """Test LLM API call timeout."""
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="test-model"
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(Exception, match="LLM service timeout"):
                await llm_service._call_llm_api(chat_request)

    @pytest.mark.asyncio
    async def test_call_llm_api_http_error(self, llm_service):
        """Test LLM API call HTTP error."""
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="test-model"
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=None, response=mock_response
            )
            
            with pytest.raises(Exception, match="LLM service error: 500"):
                await llm_service._call_llm_api(chat_request)

    def test_serialization_excludes_none_fields(self, llm_service, sample_base64_image):
        """Test that serialization properly excludes None fields (regression test)."""
        prompt = "Extract text from this image"
        
        # Prepare multimodal content
        content = llm_service._prepare_multimodal_content(sample_base64_image, prompt)
        
        # Create chat request
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content=content)],
            model="test-model"
        )
        
        # Serialize with exclude_none=True
        serialized = chat_request.model_dump(exclude_none=True)
        serialized_json = json.dumps(serialized)
        
        # Verify None fields are excluded
        assert '"image_url":null' not in serialized_json
        assert '"text":null' not in serialized_json
        assert 'null' not in serialized_json
        
        # Verify expected fields are present (adjust spacing)
        assert '"type": "text"' in serialized_json
        assert '"type": "image_url"' in serialized_json
        assert f'"url": "data:image/jpeg;base64,{sample_base64_image}"' in serialized_json

    def test_multimodal_content_serialization(self, llm_service, sample_base64_image):
        """Test multimodal content serialization structure."""
        prompt = "Extract text from this image"
        content = llm_service._prepare_multimodal_content(sample_base64_image, prompt)
        
        # Serialize each content item
        text_content_dict = content[0].model_dump(exclude_none=True)
        image_content_dict = content[1].model_dump(exclude_none=True)
        
        # Verify text content structure
        assert text_content_dict == {
            "type": "text",
            "text": prompt
        }
        
        # Verify image content structure
        assert image_content_dict == {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{sample_base64_image}"
            }
        }

    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_service):
        """Test successful health check."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            result = await llm_service.health_check()
            
            assert result is True
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_service):
        """Test health check failure."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection error")
            
            result = await llm_service.health_check()
            
            assert result is False

    def test_service_initialization(self, llm_service):
        """Test service initialization."""
        assert llm_service.base_url is not None
        assert llm_service.endpoint is not None
        assert llm_service.timeout > 0
        assert llm_service.default_model is not None
        assert llm_service.default_prompt is not None

    @pytest.mark.asyncio
    async def test_custom_model_parameter(self, llm_service, sample_base64_image):
        """Test custom model parameter handling."""
        custom_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            model="custom-model"
        )
        
        with patch.object(llm_service, '_call_llm_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Custom model response"
            
            result = await llm_service.process_image_with_llm(
                sample_base64_image, "original text", custom_request, 1.0
            )
            
            assert result.model_used == "custom-model"

    @pytest.mark.asyncio
    async def test_custom_prompt_parameter(self, llm_service, sample_base64_image):
        """Test custom prompt parameter handling."""
        custom_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.0,
            prompt="Custom prompt for OCR"
        )
        
        with patch.object(llm_service, '_call_llm_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Custom prompt response"
            
            result = await llm_service.process_image_with_llm(
                sample_base64_image, "original text", custom_request, 1.0
            )
            
            assert result.prompt_used == "Custom prompt for OCR"

    @pytest.mark.asyncio
    async def test_malformed_api_response(self, llm_service):
        """Test handling of malformed API response."""
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="test-model"
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.json.return_value = {"invalid": "response"}
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            with pytest.raises(Exception):
                await llm_service._call_llm_api(chat_request)

    @pytest.mark.asyncio
    async def test_empty_choices_response(self, llm_service):
        """Test handling of API response with no choices."""
        chat_request = LLMChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            model="test-model"
        )
        
        empty_response = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": []
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.json.return_value = empty_response
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            with pytest.raises(Exception, match="No choices in LLM response"):
                await llm_service._call_llm_api(chat_request)

    @pytest.mark.asyncio
    async def test_default_prompt_and_model_usage(self, llm_service, sample_base64_image):
        """Test usage of default prompt and model when not specified."""
        minimal_request = OCRLLMRequest(
            threshold=128,
            contrast_level=1.0
            # No prompt or model specified
        )
        
        with patch.object(llm_service, '_call_llm_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Default configuration response"
            
            result = await llm_service.process_image_with_llm(
                sample_base64_image, "original text", minimal_request, 1.0
            )
            
            assert result.model_used == llm_service.default_model
            assert result.prompt_used == llm_service.default_prompt 