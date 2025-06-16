"""
External OCR service for text extraction using vision-world API.
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Optional
from io import BytesIO

import httpx
from PIL import Image

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, OCRResult, ExternalOCRRequest
)
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class ExternalOCRService:
    """Service for performing OCR operations using external API."""
    
    def __init__(self):
        """Initialize external OCR service."""
        self.settings = settings
        self.base_url = settings.EXTERNAL_OCR_BASE_URL
        self.endpoint = settings.EXTERNAL_OCR_ENDPOINT
        self.timeout = settings.EXTERNAL_OCR_TIMEOUT
        
        logger.info(f"External OCR Service initialized with endpoint: {self.base_url}{self.endpoint}")
    
    async def process_image(
        self, 
        image_path: Path, 
        ocr_request: OCRRequest
    ) -> OCRResult:
        """
        Process an image and extract text using external OCR API.
        
        Args:
            image_path: Path to the image file
            ocr_request: OCR processing parameters
            
        Returns:
            OCRResult: OCR processing result
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting external OCR processing for {image_path}")
            
            # Convert image to base64
            image_base64 = await self._image_to_base64(image_path)
            
            # Prepare request for external API
            external_request = ExternalOCRRequest(
                image=image_base64,
                threshold=ocr_request.threshold,
                contrast_level=ocr_request.contrast_level
            )
            
            # Call external OCR API
            extracted_text = await self._call_external_api(external_request)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"External OCR processing completed in {processing_time:.2f}s"
            )
            
            return OCRResult(
                success=True,
                extracted_text=extracted_text.strip(),
                processing_time=processing_time,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"External OCR processing failed: {str(e)}")
            
            return OCRResult(
                success=False,
                extracted_text="",
                processing_time=processing_time,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level
            )
    
    async def _image_to_base64(self, image_path: Path) -> str:
        """
        Convert image file to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            str: Base64 encoded image data
        """
        try:
            # Load and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Save to BytesIO buffer
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                
                # Encode to base64
                image_bytes = buffer.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                logger.debug(f"Successfully converted {image_path} to base64")
                return image_base64
                
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {str(e)}")
            raise ValueError(f"Could not process image: {str(e)}")
    
    async def _call_external_api(self, request: ExternalOCRRequest) -> str:
        """
        Call the external OCR API.
        
        Args:
            request: External OCR API request
            
        Returns:
            str: Extracted text from the API
        """
        url = f"{self.base_url}{self.endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Calling external OCR API: {url}")

                logger.info(f"Request URL: {url}")
                logger.info(f"Request: {request.dict()}")
                
                response = await client.post(
                    url,
                    json=request.dict(),
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                logger.info(f"External OCR API response: {response.json().keys()}")
                
                # The API returns a simple string response
                extracted_text = response.text.strip('"')  # Remove quotes if present
                
                logger.debug(f"External OCR API response received: {len(extracted_text)} characters")
                return extracted_text
                
        except httpx.TimeoutException:
            logger.error(f"Timeout calling external OCR API: {url}")
            raise Exception("External OCR service timeout")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from external OCR API: {e.response.status_code}")
            raise Exception(f"External OCR service error: {e.response.status_code}")
            
        except Exception as e:
            logger.error(f"Unexpected error calling external OCR API: {str(e)}")
            raise Exception(f"External OCR service unavailable: {str(e)}")
    
    async def validate_image(self, image_path: Path) -> bool:
        """
        Validate image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            bool: True if image is valid
        """
        try:
            # Check file exists
            if not image_path.exists():
                return False
            
            # Check file size
            if image_path.stat().st_size > self.settings.IMAGE_MAX_SIZE:
                logger.warning(f"Image too large: {image_path.stat().st_size}")
                return False
            
            # Check file extension
            extension = image_path.suffix.lower().lstrip('.')
            if extension not in self.settings.ALLOWED_IMAGE_EXTENSIONS:
                logger.warning(f"Unsupported format: {extension}")
                return False
            
            # Try to open with PIL
            with Image.open(image_path) as img:
                img.verify()
            
            return True
            
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            return False
    
    async def health_check(self) -> bool:
        """
        Check if the external OCR service is available.
        
        Returns:
            bool: True if service is available
        """
        try:
            url = f"{self.base_url}/index"  # Use the health endpoint
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.warning(f"External OCR service health check failed: {str(e)}")
            return False


# Global OCR service instance
external_ocr_service = ExternalOCRService() 