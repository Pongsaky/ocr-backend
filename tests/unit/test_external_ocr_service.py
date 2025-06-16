"""
Unit tests for the external OCR service.
"""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import httpx
from PIL import Image

from app.services.external_ocr_service import ExternalOCRService
from app.models.ocr_models import OCRRequest, OCRResult, ExternalOCRRequest


class TestExternalOCRService:
    """Test cases for ExternalOCRService."""
    
    @pytest.fixture
    def ocr_service(self):
        """Create an instance of ExternalOCRService for testing."""
        return ExternalOCRService()
    
    @pytest.mark.asyncio
    async def test_process_image_success(self, ocr_service, sample_image_path, sample_ocr_request):
        """Test successful image processing."""
        with patch.object(ocr_service, '_call_external_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Extracted text from image"
            
            result = await ocr_service.process_image(sample_image_path, sample_ocr_request)
            
            assert result.success is True
            assert result.extracted_text == "Extracted text from image"
            assert result.threshold_used == sample_ocr_request.threshold
            assert result.contrast_level_used == sample_ocr_request.contrast_level
            assert result.processing_time > 0
            
            # Verify API was called
            mock_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_failure(self, ocr_service, sample_image_path, sample_ocr_request):
        """Test image processing failure."""
        with patch.object(ocr_service, '_call_external_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = Exception("API Error")
            
            result = await ocr_service.process_image(sample_image_path, sample_ocr_request)
            
            assert result.success is False
            assert result.extracted_text == ""
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_image_to_base64_success(self, ocr_service, sample_image_path):
        """Test successful image to base64 conversion."""
        base64_data = await ocr_service._image_to_base64(sample_image_path)
        
        assert isinstance(base64_data, str)
        assert len(base64_data) > 0
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(base64_data)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Invalid base64 data")
    
    @pytest.mark.asyncio
    async def test_image_to_base64_invalid_file(self, ocr_service, invalid_image_path):
        """Test image to base64 conversion with invalid file."""
        with pytest.raises(ValueError, match="Could not process image"):
            await ocr_service._image_to_base64(invalid_image_path)
    
    @pytest.mark.asyncio
    async def test_call_external_api_success(self, ocr_service):
        """Test successful external API call."""
        request = ExternalOCRRequest(
            image="base64_image_data",
            threshold=128,
            contrast_level=1.0
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.text = '"Extracted text"'
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            result = await ocr_service._call_external_api(request)
            
            assert result == "Extracted text"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_external_api_timeout(self, ocr_service):
        """Test external API call timeout."""
        request = ExternalOCRRequest(
            image="base64_image_data",
            threshold=128,
            contrast_level=1.0
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(Exception, match="External OCR service timeout"):
                await ocr_service._call_external_api(request)
    
    @pytest.mark.asyncio
    async def test_call_external_api_http_error(self, ocr_service):
        """Test external API call HTTP error."""
        request = ExternalOCRRequest(
            image="base64_image_data",
            threshold=128,
            contrast_level=1.0
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=None, response=mock_response
            )
            
            with pytest.raises(Exception, match="External OCR service error: 500"):
                await ocr_service._call_external_api(request)
    
    @pytest.mark.asyncio
    async def test_validate_image_success(self, ocr_service, sample_image_path):
        """Test successful image validation."""
        result = await ocr_service.validate_image(sample_image_path)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_image_not_exists(self, ocr_service):
        """Test image validation with non-existent file."""
        non_existent_path = Path("/non/existent/file.jpg")
        result = await ocr_service.validate_image(non_existent_path)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_image_too_large(self, ocr_service, large_image_path):
        """Test image validation with file too large."""
        # Mock settings to have a very small max size
        with patch.object(ocr_service.settings, 'IMAGE_MAX_SIZE', 1000):
            result = await ocr_service.validate_image(large_image_path)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_image_unsupported_format(self, ocr_service, invalid_image_path):
        """Test image validation with unsupported format."""
        result = await ocr_service.validate_image(invalid_image_path)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, ocr_service):
        """Test successful health check."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            result = await ocr_service.health_check()
            
            assert result is True
            mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, ocr_service):
        """Test health check failure."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection error")
            
            result = await ocr_service.health_check()
            
            assert result is False
    
    def test_service_initialization(self, ocr_service):
        """Test service initialization."""
        assert ocr_service.base_url is not None
        assert ocr_service.endpoint is not None
        assert ocr_service.timeout > 0
        assert isinstance(ocr_service.timeout, int) 