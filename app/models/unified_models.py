"""
Unified models for all file types OCR processing with streaming support.
"""

import base64
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

# Use timezone.utc instead of UTC for backward compatibility
UTC = timezone.utc


class FileType(str, Enum):
    """Supported file types for OCR processing."""
    IMAGE = "image"
    PDF = "pdf" 
    DOCX = "docx"


class ProcessingMode(str, Enum):
    """Processing enhancement modes."""
    BASIC = "basic"
    LLM_ENHANCED = "llm_enhanced"


class ProcessingStep(str, Enum):
    """Processing steps for progress tracking."""
    UPLOAD = "upload"
    VALIDATION = "validation"
    CONVERSION = "conversion"  # For DOCX -> PDF
    IMAGE_EXTRACTION = "image_extraction"  # For PDF -> Images
    OCR_PROCESSING = "ocr_processing"
    LLM_ENHANCEMENT = "llm_enhancement"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UnifiedOCRRequest(BaseModel):
    """Unified request model for all file types."""
    # Common parameters for all file types
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
    
    # PDF-specific parameters (ignored for images)
    dpi: Optional[int] = Field(
        default=300,
        ge=150,
        le=600,
        description="DPI for PDF to image conversion (150-600, PDF only)"
    )
    
    # LLM-specific parameters (optional for all types)
    prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt for OCR LLM (uses default if not provided)"
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model to use (uses default if not provided)"
    )
    
    # Processing mode
    mode: ProcessingMode = Field(
        default=ProcessingMode.BASIC,
        description="Processing mode: 'basic' or 'llm_enhanced'"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "threshold": 500,
            "contrast_level": 1.3,
            "dpi": 300,
            "mode": "llm_enhanced",
            "prompt": "Extract text from this document accurately",
            "model": "gpt-4-vision-preview"
        }
    })


class FileMetadata(BaseModel):
    """File metadata extracted during processing."""
    original_filename: str = Field(description="Original uploaded filename")
    file_size_bytes: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type of the file")
    detected_file_type: FileType = Field(description="Auto-detected file type")
    
    # Type-specific metadata
    image_dimensions: Optional[Dict[str, int]] = Field(
        default=None,
        description="Image dimensions for image files (width, height)"
    )
    pdf_page_count: Optional[int] = Field(
        default=None,
        description="Number of pages for PDF files"
    )
    docx_page_count: Optional[int] = Field(
        default=None,
        description="Estimated page count for DOCX files"
    )


class UnifiedOCRResponse(BaseModel):
    """Unified response model for all file types."""
    task_id: str = Field(description="Unique task identifier")
    file_type: FileType = Field(description="Detected file type")
    processing_mode: ProcessingMode = Field(description="Processing mode used")
    status: str = Field(description="Processing status: 'processing', 'completed', 'failed', 'cancelled'")
    created_at: datetime = Field(description="Task creation timestamp")
    
    # Estimation and metadata
    estimated_duration: Optional[float] = Field(
        default=None,
        description="Estimated processing time in seconds"
    )
    file_metadata: Optional[FileMetadata] = Field(
        default=None,
        description="File-specific metadata"
    )
    
    # Results (populated when completed)
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Final processing result (when completed)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Task completion timestamp"
    )
    cancelled_at: Optional[datetime] = Field(
        default=None,
        description="Task cancellation timestamp"
    )
    cancellation_reason: Optional[str] = Field(
        default=None,
        description="Reason for task cancellation if cancelled"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "12345678-1234-1234-1234-123456789012",
            "file_type": "pdf",
            "processing_mode": "llm_enhanced",
            "status": "processing",
            "created_at": "2024-01-15T10:30:00Z",
            "estimated_duration": 45.2,
            "file_metadata": {
                "original_filename": "document.pdf",
                "file_size_bytes": 2048576,
                "mime_type": "application/pdf",
                "detected_file_type": "pdf",
                "pdf_page_count": 5
            }
        }
    })


class UnifiedPageResult(BaseModel):
    """Unified result for a single page/unit of processing."""
    page_number: int = Field(description="Page number (1-indexed, 1 for single images)")
    extracted_text: str = Field(description="Extracted text from this page/unit")
    processing_time: float = Field(description="Processing time for this page in seconds")
    success: bool = Field(description="Whether page processing was successful")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if page processing failed"
    )
    
    # Processing parameters used
    threshold_used: int = Field(description="Threshold value used for this page")
    contrast_level_used: float = Field(description="Contrast level used for this page")
    
    # LLM-specific fields (when mode is 'llm_enhanced')
    image_processing_time: Optional[float] = Field(
        default=None,
        description="OCR processing time for this page (LLM mode only)"
    )
    llm_processing_time: Optional[float] = Field(
        default=None,
        description="LLM processing time for this page (LLM mode only)"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="LLM model used for this page (LLM mode only)"
    )
    prompt_used: Optional[str] = Field(
        default=None,
        description="Prompt used for LLM on this page (LLM mode only)"
    )
    
    timestamp: datetime = Field(description="Timestamp when page processing completed")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "page_number": 1,
            "extracted_text": "Sample extracted text from page",
            "processing_time": 2.1,
            "success": True,
            "threshold_used": 500,
            "contrast_level_used": 1.3,
            "image_processing_time": 1.2,
            "llm_processing_time": 0.9,
            "model_used": "gpt-4-vision-preview",
            "timestamp": "2024-01-15T10:30:15Z"
        }
    })


class UnifiedStreamingStatus(BaseModel):
    """Unified streaming status for all file types."""
    task_id: str = Field(description="Unique task identifier")
    file_type: FileType = Field(description="File type being processed")
    processing_mode: ProcessingMode = Field(description="Processing mode")
    status: str = Field(
        description="Processing status: 'processing', 'page_completed', 'completed', 'failed', 'cancelled'"
    )
    
    # Progress tracking
    current_step: ProcessingStep = Field(description="Current processing step")
    progress_percentage: float = Field(description="Processing progress percentage (0-100)")
    
    # Page/unit progress (for multi-page files)
    current_page: int = Field(default=0, description="Current page being processed (0 if not started)")
    total_pages: int = Field(default=1, description="Total pages/units to process")
    processed_pages: int = Field(default=0, description="Number of pages successfully processed")
    failed_pages: int = Field(default=0, description="Number of pages that failed processing")
    
    # Results (dual approach for flexibility)
    latest_page_result: Optional[UnifiedPageResult] = Field(
        default=None,
        description="Latest single page result (Type 1: incremental update)"
    )
    cumulative_results: List[UnifiedPageResult] = Field(
        default=[],
        description="All processed page results so far (Type 2: complete state)"
    )
    
    # Performance metrics
    estimated_time_remaining: Optional[float] = Field(
        default=None,
        description="Estimated time remaining in seconds"
    )
    processing_speed: Optional[float] = Field(
        default=None,
        description="Pages per second processing speed"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    
    timestamp: datetime = Field(description="Timestamp of this status update")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "12345678-1234-1234-1234-123456789012",
            "file_type": "pdf",
            "processing_mode": "llm_enhanced",
            "status": "page_completed",
            "current_step": "ocr_processing",
            "progress_percentage": 40.0,
            "current_page": 2,
            "total_pages": 5,
            "processed_pages": 2,
            "failed_pages": 0,
            "latest_page_result": {
                "page_number": 2,
                "extracted_text": "Content from page 2...",
                "processing_time": 2.1,
                "success": True
            },
            "estimated_time_remaining": 15.3,
            "processing_speed": 0.48,
            "timestamp": "2024-01-15T10:30:15Z"
        }
    })


class UnifiedTaskCancellationRequest(BaseModel):
    """Request model for task cancellation."""
    reason: Optional[str] = Field(
        default="User requested cancellation",
        description="Reason for cancellation"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "reason": "User cancelled the operation"
        }
    })


class UnifiedTaskCancellationResponse(BaseModel):
    """Response model for task cancellation."""
    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Updated task status")
    message: str = Field(description="Cancellation confirmation message")
    cancelled_at: datetime = Field(description="Cancellation timestamp")
    cancellation_reason: str = Field(description="Reason for cancellation")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "12345678-1234-1234-1234-123456789012",
            "status": "cancelled",
            "message": "Task cancelled successfully",
            "cancelled_at": "2024-01-15T10:31:00Z",
            "cancellation_reason": "User requested cancellation"
        }
    }) 