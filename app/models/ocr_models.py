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