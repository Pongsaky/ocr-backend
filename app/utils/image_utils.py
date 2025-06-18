"""
Image processing utilities for OCR operations.
Provides image validation and scaling functionality to ensure compatibility with LLM context length limits.
"""

import math
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image, ImageOps
import io

from app.logger_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """
    Get image dimensions without loading the full image into memory.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple[int, int]: Width and height in pixels
        
    Raises:
        ImageProcessingError: If image cannot be read
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Failed to get image dimensions for {image_path}: {str(e)}")
        raise ImageProcessingError(f"Cannot read image dimensions: {str(e)}")


def get_image_pixel_count(image_path: Path) -> int:
    """
    Get total pixel count (width × height) of an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        int: Total number of pixels
        
    Raises:
        ImageProcessingError: If image cannot be read
    """
    width, height = get_image_dimensions(image_path)
    return width * height


def validate_image_size(image_path: Path, max_pixels: Optional[int] = None) -> bool:
    """
    Validate if image pixel count is within acceptable limits.
    
    Args:
        image_path: Path to the image file
        max_pixels: Maximum allowed pixels (defaults to settings.MAX_IMAGE_PIXELS)
        
    Returns:
        bool: True if image is within limits, False otherwise
        
    Raises:
        ImageProcessingError: If image cannot be read
    """
    if max_pixels is None:
        max_pixels = settings.MAX_IMAGE_PIXELS
    
    pixel_count = get_image_pixel_count(image_path)
    is_valid = pixel_count <= max_pixels
    
    logger.debug(
        f"Image validation: {image_path.name} has {pixel_count:,} pixels "
        f"(max: {max_pixels:,}) - {'VALID' if is_valid else 'EXCEEDS LIMIT'}"
    )
    
    return is_valid


def calculate_scale_factor(current_pixels: int, target_pixels: int) -> float:
    """
    Calculate the scale factor needed to reduce image to target pixel count.
    
    Args:
        current_pixels: Current total pixel count
        target_pixels: Target total pixel count
        
    Returns:
        float: Scale factor (between 0 and 1)
    """
    if current_pixels <= target_pixels:
        return 1.0
    
    # Scale factor is sqrt of pixel ratio to maintain aspect ratio
    scale_factor = math.sqrt(target_pixels / current_pixels)
    
    logger.debug(
        f"Calculated scale factor: {scale_factor:.4f} "
        f"({current_pixels:,} -> {target_pixels:,} pixels)"
    )
    
    return scale_factor


def calculate_new_dimensions(
    current_width: int, 
    current_height: int, 
    target_pixels: int
) -> Tuple[int, int]:
    """
    Calculate new dimensions to achieve target pixel count while maintaining aspect ratio.
    
    Args:
        current_width: Current image width
        current_height: Current image height
        target_pixels: Target total pixel count
        
    Returns:
        Tuple[int, int]: New width and height
    """
    current_pixels = current_width * current_height
    
    if current_pixels <= target_pixels:
        return current_width, current_height
    
    scale_factor = calculate_scale_factor(current_pixels, target_pixels)
    
    new_width = int(current_width * scale_factor)
    new_height = int(current_height * scale_factor)
    
    # Ensure minimum dimensions
    new_width = max(new_width, 1)
    new_height = max(new_height, 1)
    
    actual_pixels = new_width * new_height
    
    logger.debug(
        f"Dimension calculation: {current_width}x{current_height} "
        f"({current_pixels:,} px) -> {new_width}x{new_height} "
        f"({actual_pixels:,} px)"
    )
    
    return new_width, new_height


def scale_image_to_threshold(
    input_path: Path, 
    output_path: Path, 
    max_pixels: Optional[int] = None,
    quality: Optional[int] = None,
    resample_method: Optional[str] = None
) -> Tuple[bool, dict]:
    """
    Scale image to fit within pixel threshold while maintaining aspect ratio.
    
    Args:
        input_path: Path to input image
        output_path: Path where scaled image will be saved
        max_pixels: Maximum allowed pixels (defaults to settings.MAX_IMAGE_PIXELS)
        quality: JPEG quality for output (defaults to settings.IMAGE_SCALING_QUALITY)
        resample_method: Resampling algorithm (defaults to settings.IMAGE_SCALING_RESAMPLE)
        
    Returns:
        Tuple[bool, dict]: (success, metadata)
            - success: Whether scaling was successful
            - metadata: Dictionary with scaling information
            
    Raises:
        ImageProcessingError: If image processing fails
    """
    if max_pixels is None:
        max_pixels = settings.MAX_IMAGE_PIXELS
    if quality is None:
        quality = settings.IMAGE_SCALING_QUALITY
    if resample_method is None:
        resample_method = settings.IMAGE_SCALING_RESAMPLE
    
    # Get resampling filter
    resample_filter = getattr(Image.Resampling, resample_method, Image.Resampling.LANCZOS)
    
    metadata = {
        "original_path": str(input_path),
        "scaled_path": str(output_path),
        "max_pixels_allowed": max_pixels,
        "scaling_applied": False,
        "original_dimensions": None,
        "scaled_dimensions": None,
        "original_pixel_count": 0,
        "scaled_pixel_count": 0,
        "scale_factor": 1.0,
        "quality_used": quality,
        "resample_method": resample_method
    }
    
    try:
        # Get original dimensions
        original_width, original_height = get_image_dimensions(input_path)
        original_pixels = original_width * original_height
        
        metadata.update({
            "original_dimensions": (original_width, original_height),
            "original_pixel_count": original_pixels
        })
        
        # Check if scaling is needed
        if original_pixels <= max_pixels:
            logger.debug(f"Image {input_path.name} is within limits, no scaling needed")
            
            # Copy original to output path
            with Image.open(input_path) as img:
                # Convert to RGB if necessary for JPEG output
                if output_path.suffix.lower() in ['.jpg', '.jpeg'] and img.mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                
                img.save(output_path, quality=quality, optimize=True)
            
            metadata.update({
                "scaled_dimensions": (original_width, original_height),
                "scaled_pixel_count": original_pixels
            })
            
            return True, metadata
        
        # Calculate new dimensions
        new_width, new_height = calculate_new_dimensions(
            original_width, original_height, max_pixels
        )
        new_pixels = new_width * new_height
        scale_factor = new_width / original_width
        
        logger.info(
            f"Scaling image {input_path.name}: "
            f"{original_width}x{original_height} ({original_pixels:,} px) -> "
            f"{new_width}x{new_height} ({new_pixels:,} px) "
            f"[scale: {scale_factor:.4f}]"
        )
        
        # Load and scale image
        with Image.open(input_path) as img:
            # Apply EXIF orientation if present
            img = ImageOps.exif_transpose(img)
            
            # Scale image
            scaled_img = img.resize(
                (new_width, new_height), 
                resample=resample_filter
            )
            
            # Convert to RGB if saving as JPEG
            if output_path.suffix.lower() in ['.jpg', '.jpeg'] and scaled_img.mode in ['RGBA', 'P']:
                scaled_img = scaled_img.convert('RGB')
            
            # Save scaled image
            scaled_img.save(output_path, quality=quality, optimize=True)
        
        metadata.update({
            "scaling_applied": True,
            "scaled_dimensions": (new_width, new_height),
            "scaled_pixel_count": new_pixels,
            "scale_factor": scale_factor
        })
        
        logger.info(f"Successfully scaled image: {input_path.name} -> {output_path.name}")
        return True, metadata
        
    except Exception as e:
        error_msg = f"Failed to scale image {input_path}: {str(e)}"
        logger.error(error_msg)
        metadata["error"] = error_msg
        raise ImageProcessingError(error_msg)


def validate_and_scale_image(
    input_path: Path, 
    output_path: Optional[Path] = None,
    max_pixels: Optional[int] = None
) -> Tuple[Path, dict]:
    """
    Validate image size and scale if necessary.
    
    Args:
        input_path: Path to input image
        output_path: Path for scaled image (defaults to input_path if no scaling needed)
        max_pixels: Maximum allowed pixels (defaults to settings.MAX_IMAGE_PIXELS)
        
    Returns:
        Tuple[Path, dict]: (final_image_path, metadata)
            - final_image_path: Path to the final image (original or scaled)
            - metadata: Dictionary with processing information
            
    Raises:
        ImageProcessingError: If image processing fails
    """
    if max_pixels is None:
        max_pixels = settings.MAX_IMAGE_PIXELS
    
    if not settings.ENABLE_IMAGE_SCALING:
        logger.debug("Image scaling is disabled in settings")
        return input_path, {"scaling_enabled": False}
    
    # Check if scaling is needed
    if validate_image_size(input_path, max_pixels):
        logger.debug(f"Image {input_path.name} is within limits")
        return input_path, {"scaling_applied": False, "within_limits": True}
    
    # Create output path if not provided
    if output_path is None:
        output_path = input_path.parent / f"scaled_{input_path.name}"
    
    # Scale image
    success, metadata = scale_image_to_threshold(input_path, output_path, max_pixels)
    
    if success:
        return output_path, metadata
    else:
        raise ImageProcessingError(f"Failed to scale image: {metadata.get('error', 'Unknown error')}")


def get_resample_method_from_string(method_name: str) -> Image.Resampling:
    """
    Convert string to PIL resampling method.
    
    Args:
        method_name: Name of resampling method
        
    Returns:
        Image.Resampling: PIL resampling method
    """
    method_map = {
        "NEAREST": Image.Resampling.NEAREST,
        "BILINEAR": Image.Resampling.BILINEAR,
        "BICUBIC": Image.Resampling.BICUBIC,
        "LANCZOS": Image.Resampling.LANCZOS,
        "BOX": Image.Resampling.BOX,
        "HAMMING": Image.Resampling.HAMMING
    }
    
    return method_map.get(method_name.upper(), Image.Resampling.LANCZOS) 