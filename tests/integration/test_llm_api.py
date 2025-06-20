import pytest
from pathlib import Path
import base64
from app.services.ocr_llm_service import OCRLLMService
from app.models.ocr_models import OCRLLMRequest

@pytest.mark.integration
def test_process_image_with_llm_sync_real_api():
    """
    Integration test for process_image_with_llm_sync that makes a real API call.
    
    This test requires the following environment variables to be set:
    - LLM_API_BASE_URL
    - LLM_API_KEY
    - LLM_DEFAULT_MODEL
    
    To run this test, use the command:
    poetry run pytest -m integration -s
    """
    # 1. Setup
    llm_service = OCRLLMService()
    
    # Check if required settings are configured for a real call
    if not all([llm_service.settings.OCR_LLM_BASE_URL, llm_service.settings.OCR_LLM_API_KEY, llm_service.settings.OCR_LLM_MODEL]):
        pytest.skip("LLM API settings are not configured. Skipping real API test.")

    image_path = Path("test_files/test_image.png")
    if not image_path.exists():
        pytest.fail("Test image 'test_files/test_image.png' not found.")
        
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    image_processing_time = 1.2 
    
    request_data = OCRLLMRequest(
        prompt="Please extract the text from the attached image accurately.",
        # Using default model from settings
    )

    # 2. Execute
    print("\n🚀 Making real API call to LLM service...")
    result = llm_service.process_image_with_llm_sync(
        base64_image,
        request_data,
        image_processing_time
    )
    
    # 3. Assert
    assert result is not None
    assert result.success is True
    assert result.extracted_text is not None
    assert len(result.extracted_text) > 0
    assert result.processing_time > image_processing_time
    assert result.llm_processing_time > 0
    
    print("✅ Real API call successful!")
    print(f"   - Extracted text: '{result.extracted_text[:100]}...'")
    print(f"   - Model used: {result.model_used}")
    print(f"   - Total processing time: {result.processing_time:.2f}s") 