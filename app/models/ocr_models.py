"""
Pydantic models for OCR operations using external API.
"""

import base64
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator


class OCRRequest(BaseModel):
    """OCR processing request model for external API."""
    threshold: int = Field(
        default=500,
        ge=0,
        le=1024,
        description="Threshold value for image processing (0-255)"
    )
    contrast_level: float = Field(
        default=1.3,
        ge=0.1,
        le=5.0,
        description="Contrast level for image enhancement (0.1-5.0)"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "threshold": 500,
                "contrast_level": 1.3
            }
        }


class ExternalOCRRequest(BaseModel):
    """Request model for external OCR API."""
    image: str = Field(description="Base64 encoded image data")
    threshold: int = Field(description="Threshold value for processing")
    contrast_level: float = Field(description="Contrast level for enhancement")


class OCRResult(BaseModel):
    """OCR processing result."""
    success: bool = Field(description="Whether OCR processing was successful")
    extracted_text: str = Field(description="Complete extracted text")
    processing_time: float = Field(description="Processing time in seconds")
    threshold_used: int = Field(description="Threshold value used")
    contrast_level_used: float = Field(description="Contrast level used")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "extracted_text": "Sample extracted text from image",
                "processing_time": 1.23,
                "threshold_used": 128,
                "contrast_level_used": 1.0
            }
        }


class OCRResponse(BaseModel):
    """OCR API response model."""
    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Processing status")
    result: Optional[OCRResult] = Field(
        default=None,
        description="OCR processing result"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    created_at: datetime = Field(description="Task creation timestamp")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Task completion timestamp"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "task_id": "12345678-1234-1234-1234-123456789012",
                "status": "completed",
                "result": {
                    "success": True,
                    "extracted_text": "Sample extracted text from image",
                    "processing_time": 1.23,
                    "threshold_used": 128,
                    "contrast_level_used": 1.0
                },
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:01Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: bool = Field(default=True, description="Error flag")
    message: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")
    path: str = Field(description="API endpoint path")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "error": True,
                "message": "File format not supported",
                "status_code": 400,
                "path": "/v1/ocr/process",
                "details": {
                    "supported_formats": ["jpg", "png", "bmp", "tiff"]
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Service status")
    environment: str = Field(description="Environment name")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    external_ocr_status: str = Field(description="External OCR service status")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "status": "healthy",
                "environment": "development",
                "service": "OCR Backend API",
                "version": "0.1.0",
                "external_ocr_status": "available"
            }
        }


# --- OCR LLM Models ---

class ChatMessage(BaseModel):
    """Chat message model for LLM API."""
    role: str = Field(description="Message role (system, user, assistant)")
    content: Any = Field(description="Message content (text or multimodal)")


class ImageURL(BaseModel):
    """Image URL model for multimodal content."""
    url: str = Field(description="Base64 data URL for image")


class MultimodalContent(BaseModel):
    """Multimodal content model for LLM messages."""
    type: str = Field(description="Content type (text or image_url)")
    text: Optional[str] = Field(default=None, description="Text content")
    image_url: Optional[ImageURL] = Field(default=None, description="Image URL content")


class OCRLLMRequest(BaseModel):
    """OCR LLM processing request model."""
    threshold: int = Field(
        default=500,
        ge=0,
        le=1024,
        description="Threshold value for image processing (0-1024)"
    )
    contrast_level: float = Field(
        default=1.3,
        ge=0.1,
        le=5.0,
        description="Contrast level for image enhancement (0.1-5.0)"
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt for OCR LLM (uses default if not provided)"
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model to use (uses default if not provided)"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "threshold": 500,
                "contrast_level": 1.3,
                "prompt": "อ่านข้อความในภาพนี้",
                "model": "nectec/Pathumma-vision-ocr-lora-dev"
            }
        }


class LLMChatRequest(BaseModel):
    """LLM chat request model."""
    messages: List[ChatMessage] = Field(description="Chat messages")
    model: str = Field(description="LLM model name")


class LLMChoice(BaseModel):
    """LLM response choice model."""
    message: ChatMessage = Field(description="Response message")
    index: int = Field(description="Choice index")
    finish_reason: Optional[str] = Field(default=None, description="Finish reason")


class LLMChatResponse(BaseModel):
    """LLM chat response model."""
    choices: List[LLMChoice] = Field(description="Response choices")
    id: Optional[str] = Field(default=None, description="Response ID")
    model: Optional[str] = Field(default=None, description="Model used")
    object: Optional[str] = Field(default=None, description="Object type")


class OCRLLMResult(BaseModel):
    """OCR LLM processing result."""
    success: bool = Field(description="Whether processing was successful")
    extracted_text: str = Field(description="LLM-enhanced extracted text")
    original_ocr_text: str = Field(description="Original OCR extracted text")
    processing_time: float = Field(description="Total processing time in seconds")
    ocr_processing_time: float = Field(description="OCR processing time in seconds")
    llm_processing_time: float = Field(description="LLM processing time in seconds")
    threshold_used: int = Field(description="Threshold value used")
    contrast_level_used: float = Field(description="Contrast level used")
    model_used: str = Field(description="LLM model used")
    prompt_used: str = Field(description="Prompt used for LLM")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "success": True,
                "extracted_text": "Enhanced and corrected text from LLM",
                "original_ocr_text": "Original OCR extracted text",
                "processing_time": 3.45,
                "ocr_processing_time": 1.23,
                "llm_processing_time": 2.22,
                "threshold_used": 500,
                "contrast_level_used": 1.3,
                "model_used": "nectec/Pathumma-vision-ocr-lora-dev",
                "prompt_used": "ข้อความในภาพนี้"
            }
        }


class OCRLLMResponse(BaseModel):
    """OCR LLM API response model."""
    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Processing status")
    result: Optional[OCRLLMResult] = Field(
        default=None,
        description="OCR LLM processing result"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    created_at: datetime = Field(description="Task creation timestamp")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Task completion timestamp"
    )
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "task_id": "12345678-1234-1234-1234-123456789012",
                "status": "completed",
                "result": {
                    "success": True,
                    "extracted_text": "Enhanced and corrected text from LLM",
                    "original_ocr_text": "Original OCR extracted text",
                    "processing_time": 3.45,
                    "ocr_processing_time": 1.23,
                    "llm_processing_time": 2.22,
                    "threshold_used": 500,
                    "contrast_level_used": 1.3,
                    "model_used": "nectec/Pathumma-vision-ocr-lora-dev",
                    "prompt_used": "ข้อความในภาพนี้"
                },
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:03Z"
            }
        } 