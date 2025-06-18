"""
OCR LLM service for enhanced text extraction using Pathumma Vision OCR API.
"""

import time
import base64
from pathlib import Path
from typing import List

import httpx
from PIL import Image

from app.logger_config import get_logger
from config.settings import get_settings
from app.models.ocr_models import (
    OCRLLMRequest, OCRLLMResult, LLMChatRequest, LLMChatResponse,
    ChatMessage, MultimodalContent, ImageURL
)

logger = get_logger(__name__)


class OCRLLMService:
    """Service for performing enhanced OCR operations using LLM API."""
    
    def __init__(self):
        """Initialize OCR LLM service."""
        self.settings = get_settings()
        self.base_url = self.settings.OCR_LLM_BASE_URL
        self.endpoint = self.settings.OCR_LLM_ENDPOINT
        self.timeout = self.settings.OCR_LLM_TIMEOUT
        self.default_model = self.settings.OCR_LLM_MODEL
        self.default_prompt = self.settings.OCR_LLM_DEFAULT_PROMPT
        
        logger.info(f"OCR LLM Service initialized with endpoint: {self.base_url}{self.endpoint}")
    
    async def process_image_with_llm(
        self, 
        processed_image_base64: str,
        original_ocr_text: str,
        ocr_request: OCRLLMRequest,
        image_processing_time: float
    ) -> OCRLLMResult:
        """
        Process an image with LLM for enhanced text extraction.
        
        Args:
            processed_image_base64: Base64 encoded processed image
            original_ocr_text: Original OCR extracted text
            ocr_request: OCR LLM processing parameters
            image_processing_time: Time taken for initial OCR processing
            
        Returns:
            OCRLLMResult: Enhanced OCR processing result
        """
        start_time = time.time()
        
        try:
            logger.info("Starting LLM-enhanced OCR processing")
            
            # Use custom prompt or default
            prompt = ocr_request.prompt or self.default_prompt
            model = ocr_request.model or self.default_model
            
            # Prepare multimodal content for LLM
            multimodal_content = self._prepare_multimodal_content(
                processed_image_base64, prompt
            )
            
            # Create chat request using Pydantic models
            chat_request = LLMChatRequest(
                messages=[
                    ChatMessage(role="system", content=""),
                    ChatMessage(role="user", content=multimodal_content)
                ],
                model=model
            )
            
            # Call LLM API
            llm_start_time = time.time()
            enhanced_text = await self._call_llm_api(chat_request)
            llm_processing_time = time.time() - llm_start_time
            
            total_processing_time = time.time() - start_time + image_processing_time
            
            logger.info(
                f"LLM-enhanced OCR processing completed in {llm_processing_time:.2f}s "
                f"(total: {total_processing_time:.2f}s)"
            )
            
            return OCRLLMResult(
                success=True,
                extracted_text=enhanced_text.strip(),
                original_ocr_text=original_ocr_text.strip(),
                processing_time=total_processing_time,
                image_processing_time=image_processing_time,
                llm_processing_time=llm_processing_time,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level,
                model_used=model,
                prompt_used=prompt
            )
            
        except Exception as e:
            total_processing_time = time.time() - start_time + image_processing_time
            logger.error(f"LLM-enhanced OCR processing failed: {str(e)}")
            
            return OCRLLMResult(
                success=False,
                extracted_text="",
                original_ocr_text=original_ocr_text,
                processing_time=total_processing_time,
                image_processing_time=image_processing_time,
                llm_processing_time=0.0,
                threshold_used=ocr_request.threshold,
                contrast_level_used=ocr_request.contrast_level,
                model_used=model,
                prompt_used=prompt
            )
    
    def _prepare_multimodal_content(self, image_base64: str, prompt: str) -> List[MultimodalContent]:
        """
        Prepare multimodal content for LLM API.
        
        Args:
            image_base64: Base64 encoded image
            prompt: Text prompt for OCR
            
        Returns:
            List[MultimodalContent]: Formatted multimodal content
        """
        return [
            MultimodalContent(
                type="text",
                text=prompt,
                image_url=None  # Explicitly set to None for text content
            ),
            MultimodalContent(
                type="image_url",
                text=None,  # Explicitly set to None for image content
                image_url=ImageURL(url=f"data:image/jpeg;base64,{image_base64}")
            )
        ]
    
    async def _call_llm_api(self, request: LLMChatRequest) -> str:
        """
        Call the LLM API for text extraction.
        
        Args:
            request: LLM chat request
            
        Returns:
            str: Extracted text from LLM
            
        Raises:
            Exception: If API call fails
        """
        url = f"{self.base_url}{self.endpoint}"
        
        try:
            logger.debug(f"Calling LLM API: {url}")
            
            # Serialize request excluding None fields
            request_dict = request.model_dump(exclude_none=True)
            # logger.debug(f"LLM API request: {request_dict}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "accept": "application/json"
                    },
                    json=request_dict
                )
                
                response.raise_for_status()
                
                # Parse response
                response_data = response.json()
                logger.info(f"LLM API response received: {response.status_code}")
                
                # Extract text from response
                llm_response = LLMChatResponse(**response_data)
                if llm_response.choices and len(llm_response.choices) > 0:
                    extracted_text = llm_response.choices[0].message.content
                    logger.debug(f"LLM API response received: {len(extracted_text)} characters")
                    return extracted_text
                else:
                    raise Exception("No choices in LLM response")
                
        except httpx.TimeoutException:
            logger.error(f"Timeout calling LLM API: {url}")
            raise Exception("LLM service timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM API: {e.response.status_code}")
            raise Exception(f"LLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error calling LLM API: {str(e)}")
            raise Exception(f"LLM service unavailable: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            bool: True if service is available
        """
        try:
            # Use a simple health check or test request
            url = f"{self.base_url}/health"  # Assuming there's a health endpoint
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.warning(f"LLM service health check failed: {str(e)}")
            return False


# Global OCR LLM service instance
ocr_llm_service = OCRLLMService() 