#!/usr/bin/env python3
"""
Test script for image encoding utilities.
This can be run standalone to test image encoding without cluttering test logs.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.image_utils import (
    encode_test_image, 
    validate_base64, 
    get_test_image_info, 
    ImageUtils
)


def test_image_encoding_without_logging():
    """Test image encoding without logging output."""
    print("Testing image encoding without logging...")
    
    # Get image info
    image_info = get_test_image_info()
    print(f"Image info: {image_info}")
    
    # Encode without logging
    base64_string = encode_test_image(enable_logging=False)
    print(f"Base64 encoding: SUCCESS (length: {len(base64_string)} chars)")
    
    # Validate encoding
    is_valid = validate_base64(base64_string)
    print(f"Base64 validation: {'PASS' if is_valid else 'FAIL'}")
    
    return base64_string


def test_image_encoding_with_logging():
    """Test image encoding with logging output."""
    print("\nTesting image encoding WITH logging...")
    
    # Encode with logging enabled
    base64_string = encode_test_image(enable_logging=True)
    
    return base64_string


def main():
    """Run all image encoding tests."""
    print("=== Image Encoding Utility Test ===\n")
    
    try:
        # Test without logging (clean output)
        base64_no_log = test_image_encoding_without_logging()
        
        # Test with logging (detailed output)
        base64_with_log = test_image_encoding_with_logging()
        
        # Verify they're the same
        if base64_no_log == base64_with_log:
            print(f"\n✅ SUCCESS: Both encoding methods produce identical results")
            print(f"   Image file: {ImageUtils.get_test_image_path()}")
            print(f"   Base64 length: {len(base64_no_log)} characters")
            print(f"   Validation: {'PASS' if validate_base64(base64_no_log) else 'FAIL'}")
        else:
            print(f"\n❌ ERROR: Encoding methods produce different results")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 