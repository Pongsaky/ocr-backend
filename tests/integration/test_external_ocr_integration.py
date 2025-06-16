"""
Integration tests for external OCR API integration.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from app.services.external_ocr_service import ExternalOCRService
from app.models.ocr_models import OCRRequest, ExternalOCRRequest


class TestExternalOCRIntegration:
    """Integration tests for external OCR API."""
    
    @pytest.fixture
    def ocr_service(self):
        """Create an instance of ExternalOCRService for testing."""
        return ExternalOCRService()
    
    @pytest.mark.asyncio
    async def test_external_api_call_integration(self, ocr_service):
        """Test actual external API call (mocked for CI/CD)."""
        request = ExternalOCRRequest(
            image="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            threshold=500,
            contrast_level=1.3
        )
        
        # Mock the HTTP client to simulate external API response
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Simulate successful response from vision-world API
            mock_response = MagicMock()
            mock_response.text = '"Sample extracted text from external API"'
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            
            result = await ocr_service._call_external_api(request)
            
            assert result == "Sample extracted text from external API"
            
            # Verify the correct URL and payload were used
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            # Check URL
            expected_url = f"{ocr_service.base_url}{ocr_service.endpoint}"
            assert call_args[0][0] == expected_url
            
            # Check payload
            payload = call_args[1]['json']
            assert payload['image'] == request.image
            assert payload['threshold'] == request.threshold
            assert payload['contrast_level'] == request.contrast_level
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, ocr_service):
        """Test health check integration with external service."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Simulate successful health check
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            
            result = await ocr_service.health_check()
            
            assert result is True
            
            # Verify correct health check URL
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            expected_url = f"{ocr_service.base_url}/index"
            assert call_args[0][0] == expected_url
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self, ocr_service, sample_image_path):
        """Test end-to-end image processing with external API."""
        ocr_request = OCRRequest(threshold=500, contrast_level=1.3)
        
        # Mock the external API call
        with patch.object(ocr_service, '_call_external_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "End-to-end extracted text"
            
            result = await ocr_service.process_image(sample_image_path, ocr_request)
            
            assert result.success is True
            assert result.extracted_text == "End-to-end extracted text"
            assert result.threshold_used == 500
            assert result.contrast_level_used == 1.3
            assert result.processing_time > 0
            
            # Verify API was called with correct parameters
            mock_api.assert_called_once()
            call_args = mock_api.call_args[0][0]
            assert isinstance(call_args, ExternalOCRRequest)
            assert call_args.threshold == 500
            assert call_args.contrast_level == 1.3
            assert len(call_args.image) > 0  # Base64 encoded image
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, ocr_service):
        """Test error handling with external API failures."""
        request = ExternalOCRRequest(
            image="invalid_base64",
            threshold=500,
            contrast_level=1.3
        )
        
        # Test timeout error
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(Exception, match="External OCR service timeout"):
                await ocr_service._call_external_api(request)
        
        # Test HTTP error
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Internal Server Error", request=None, response=mock_response
            )
            
            with pytest.raises(Exception, match="External OCR service error: 500"):
                await ocr_service._call_external_api(request)
    
    @pytest.mark.asyncio
    async def test_image_format_conversion(self, ocr_service, sample_image_path):
        """Test image format conversion for external API."""
        base64_data = await ocr_service._image_to_base64(sample_image_path)
        
        # Verify base64 data is valid
        import base64
        try:
            decoded = base64.b64decode(base64_data)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Invalid base64 data generated")
        
        # Verify it's a JPEG format (as converted by the service)
        assert decoded.startswith(b'\xff\xd8\xff')  # JPEG magic bytes
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, ocr_service, sample_image_path):
        """Test handling of concurrent requests to external API."""
        import asyncio
        
        ocr_request = OCRRequest(threshold=500, contrast_level=1.3)
        
        # Mock the external API call
        with patch.object(ocr_service, '_call_external_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Concurrent test result"
            
            # Create multiple concurrent tasks
            tasks = [
                ocr_service.process_image(sample_image_path, ocr_request)
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all requests completed successfully
            assert len(results) == 5
            for result in results:
                assert result.success is True
                assert result.extracted_text == "Concurrent test result"
            
            # Verify API was called for each request
            assert mock_api.call_count == 5
    
    @pytest.mark.asyncio
    async def test_different_image_formats(self, ocr_service):
        """Test processing different image formats."""
        import tempfile
        from PIL import Image
        
        formats = [
            ('RGB', 'JPEG', '.jpg'),
            ('RGB', 'PNG', '.png'),
            ('RGB', 'BMP', '.bmp'),
        ]
        
        for mode, format_name, extension in formats:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
                # Create test image in different format
                image = Image.new(mode, (100, 50), color='white')
                image.save(temp_file.name, format_name)
                
                image_path = Path(temp_file.name)
                
                try:
                    # Test base64 conversion
                    base64_data = await ocr_service._image_to_base64(image_path)
                    assert len(base64_data) > 0
                    
                    # Test validation
                    is_valid = await ocr_service.validate_image(image_path)
                    assert is_valid is True
                    
                finally:
                    # Cleanup
                    image_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_service_configuration(self, ocr_service):
        """Test service configuration and settings."""
        # Verify service is properly configured
        assert ocr_service.base_url == "http://203.185.131.205/vision-world"
        assert ocr_service.endpoint == "/process-image"
        assert ocr_service.timeout == 30
        
        # Test with custom configuration
        from config.settings import Settings
        
        custom_settings = Settings()
        custom_settings.EXTERNAL_OCR_BASE_URL = "http://custom-ocr-api.com"
        custom_settings.EXTERNAL_OCR_ENDPOINT = "/custom-process"
        custom_settings.EXTERNAL_OCR_TIMEOUT = 60
        
        with patch('app.services.external_ocr_service.settings', custom_settings):
            custom_service = ExternalOCRService()
            
            assert custom_service.base_url == "http://custom-ocr-api.com"
            assert custom_service.endpoint == "/custom-process"
            assert custom_service.timeout == 60 