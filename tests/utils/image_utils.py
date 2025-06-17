import base64
import os
from pathlib import Path
from typing import Optional


class ImageUtils:
    """Utility class for image processing in tests."""
    
    @staticmethod
    def encode_image_to_base64(image_path: str, enable_logging: bool = False) -> str:
        """
        Encode an image file to base64 string.
        
        Args:
            image_path: Path to the image file
            enable_logging: If True, logs base64 string details
            
        Returns:
            Base64 encoded string of the image
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            Exception: If encoding fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                
                if enable_logging:
                    print(f"Image: {image_path}")
                    print(f"File size: {len(image_data)} bytes")
                    print(f"Base64 length: {len(base64_string)} characters")
                    print(f"Base64 preview: {base64_string[:100]}...")
                    
                return base64_string
                
        except Exception as e:
            raise Exception(f"Failed to encode image {image_path}: {str(e)}")
    
    @staticmethod
    def get_test_image_path() -> str:
        """Get the path to the test image file."""
        project_root = Path(__file__).parent.parent.parent
        test_image_path = project_root / "image" / "test_image.png"
        return str(test_image_path)
    
    @staticmethod
    def create_test_base64_image(enable_logging: bool = False) -> str:
        """
        Create base64 encoded string from the test image.
        
        Args:
            enable_logging: If True, logs encoding details
            
        Returns:
            Base64 encoded string of test_image.png
        """
        test_image_path = ImageUtils.get_test_image_path()
        return ImageUtils.encode_image_to_base64(test_image_path, enable_logging)
    
    @staticmethod
    def validate_base64_encoding(base64_string: str) -> bool:
        """
        Validate that a string is proper base64 encoding.
        
        Args:
            base64_string: The base64 string to validate
            
        Returns:
            True if valid base64, False otherwise
        """
        if not base64_string or not isinstance(base64_string, str):
            return False
            
        try:
            # Try to decode and re-encode
            decoded = base64.b64decode(base64_string)
            re_encoded = base64.b64encode(decoded).decode('utf-8')
            return re_encoded == base64_string and len(base64_string) > 0
        except Exception:
            return False
    
    @staticmethod
    def get_image_info(image_path: str) -> dict:
        """
        Get information about an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with image information
        """
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}
            
        try:
            file_size = os.path.getsize(image_path)
            file_extension = Path(image_path).suffix.lower()
            
            return {
                "path": image_path,
                "size_bytes": file_size,
                "size_kb": round(file_size / 1024, 2),
                "extension": file_extension,
                "exists": True
            }
        except Exception as e:
            return {"error": f"Failed to get info: {str(e)}"}


# Convenience functions for easy import
def encode_test_image(enable_logging: bool = False) -> str:
    """Convenience function to encode the test image."""
    return ImageUtils.create_test_base64_image(enable_logging)


def validate_base64(base64_string: str) -> bool:
    """Convenience function to validate base64 string."""
    return ImageUtils.validate_base64_encoding(base64_string)


def get_test_image_info() -> dict:
    """Convenience function to get test image information."""
    test_image_path = ImageUtils.get_test_image_path()
    return ImageUtils.get_image_info(test_image_path) 