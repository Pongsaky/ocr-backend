"""
External OCR service for image preprocessing using vision-world API.
This service processes and enhances images but does not extract text.
"""

import asyncio
import base64
import time
from pathlib import Path
from typing import Optional
from io import BytesIO
import tempfile

import httpx
from PIL import Image

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, ExternalOCRRequest
)
from app.utils.image_utils import validate_and_scale_image, ImageProcessingError
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class ImageProcessingResult:
    """Result of image processing operation."""
    
    def __init__(self, success: bool, processed_image_base64: str = "", processing_time: float = 0.0, 
                 threshold_used: int = 0, contrast_level_used: float = 0.0, error_message: str = ""):
        self.success = success
        self.processed_image_base64 = processed_image_base64
        self.processing_time = processing_time
        self.threshold_used = threshold_used
        self.contrast_level_used = contrast_level_used
        self.error_message = error_message


class ExternalOCRService:
    """Service for performing image preprocessing using external vision-world API."""
    
    def __init__(self):
        """Initialize external image processing service."""
        self.settings = settings
        self.base_url = settings.EXTERNAL_OCR_BASE_URL
        self.endpoint = settings.EXTERNAL_OCR_ENDPOINT
        self.timeout = settings.EXTERNAL_OCR_TIMEOUT
        
        logger.info(f"External Image Processing Service initialized with endpoint: {self.base_url}{self.endpoint}")
    
    async def process_image(
        self, 
        image_path: Path, 
        ocr_request: OCRRequest
    ) -> ImageProcessingResult:
        """
        Process an image for enhancement/preprocessing using external API with automatic scaling.
        
        Args:
            image_path: Path to the image file
            ocr_request: Image processing parameters
            
        Returns:
            ImageProcessingResult: Image processing result with processed image
        """
        start_time = time.time()
        temp_files = []
        
        try:
            logger.info(f"Starting external image processing for {image_path}")
            
            # Validate and scale image if necessary
            try:
                # Create temp file for scaled image if needed
                import uuid
                temp_dir = Path(settings.TEMP_DIR) / f"ocr_scaling_{uuid.uuid4().hex[:8]}"
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_files.append(temp_dir)
                
                scaled_image_path = temp_dir / f"scaled_{image_path.name}"
                
                final_image_path, scaling_metadata = validate_and_scale_image(
                    image_path, 
                    scaled_image_path
                )
                
                # Log scaling information
                if scaling_metadata.get("scaling_applied", False):
                    original_pixels = scaling_metadata.get("original_pixel_count", 0)
                    scaled_pixels = scaling_metadata.get("scaled_pixel_count", 0)
                    scale_factor = scaling_metadata.get("scale_factor", 1.0)
                    
                    logger.info(
                        f"Image scaled for processing: {original_pixels:,} -> {scaled_pixels:,} pixels "
                        f"(factor: {scale_factor:.3f})"
                    )
                else:
                    logger.debug("Image within limits, no scaling needed")
                
                if final_image_path != image_path:
                    temp_files.append(final_image_path)
                
            except ImageProcessingError as e:
                logger.warning(f"Image scaling failed, using original: {str(e)}")
                final_image_path = image_path
            
            # Convert image to base64
            image_base64 = await self._image_to_base64(final_image_path)
            
            # Prepare request for external API
            external_request = ExternalOCRRequest(
                image=image_base64,
                threshold=ocr_request.threshold,
                contrast_level=ocr_request.contrast_level
            )
            
            # Call external image processing API
            processed_image_base64 = await self._call_external_api(external_request)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"External image processing completed in {processing_time:.2f}s"
            )
            
            return ImageProcessingResult(
                success=True,
                processed_image_base64=processed_image_base64,
                processing_time=processing_time,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"External image processing failed: {str(e)}")
            
            return ImageProcessingResult(
                success=False,
                processed_image_base64="",
                processing_time=processing_time,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level,
                error_message=str(e)
            )
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        if temp_file.is_dir():
                            import shutil
                            shutil.rmtree(temp_file)
                        else:
                            temp_file.unlink()
                except Exception as cleanup_e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_e}")
    
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
        Call the external image processing API.
        
        Args:
            request: External image processing API request
            
        Returns:
            str: Base64 encoded processed image from the API
        """
        url = f"{self.base_url}{self.endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Calling external image processing API: {url}")
                
                response = await client.post(
                    url,
                    json=request.dict(),
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                # Parse JSON response
                response_data = response.json()
                logger.info(f"External image processing API response: {response_data.keys()}")
                
                # Extract processed image from response
                if "image" not in response_data:
                    raise ValueError("No 'image' field in API response")
                
                processed_image_base64 = response_data["image"]
                
                logger.debug(f"External image processing API response received: {len(processed_image_base64)} characters")
                return processed_image_base64
                
        except httpx.TimeoutException:
            logger.error(f"Timeout calling external image processing API: {url}")
            raise Exception("External image processing service timeout")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from external image processing API: {e.response.status_code}")
            raise Exception(f"External image processing service error: {e.response.status_code}")
            
        except Exception as e:
            logger.error(f"Unexpected error calling external image processing API: {str(e)}")
            raise Exception(f"External image processing service unavailable: {str(e)}")
    
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
        Check if the external image processing service is available.
        
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
            logger.warning(f"External image processing service health check failed: {str(e)}")
            return False


# Global image processing service instance
external_ocr_service = ExternalOCRService() 