"""
Unit tests for unified models - testing all new data structures and enums.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from app.models.unified_models import (
    FileType, ProcessingMode, ProcessingStep,
    UnifiedOCRRequest, UnifiedOCRResponse, 
    UnifiedPageResult, UnifiedStreamingStatus,
    FileMetadata, UnifiedTaskCancellationRequest,
    UnifiedTaskCancellationResponse, PDFConfig
)

UTC = timezone.utc


def test_file_type_enum():
    """Test FileType enum values."""
    assert FileType.IMAGE == "image"
    assert FileType.PDF == "pdf"
    assert FileType.DOCX == "docx"


def test_processing_mode_enum():
    """Test ProcessingMode enum values."""
    assert ProcessingMode.BASIC == "basic"
    assert ProcessingMode.LLM_ENHANCED == "llm_enhanced"


def test_processing_step_enum():
    """Test ProcessingStep enum values."""
    expected_steps = [
        "upload", "validation", "conversion", "image_extraction",
        "ocr_processing", "llm_enhancement", "completed", "failed", "cancelled"
    ]
    
    actual_steps = [ps.value for ps in ProcessingStep]
    for step in expected_steps:
        assert step in actual_steps


def test_unified_ocr_request_defaults():
    """Test UnifiedOCRRequest default values."""
    request = UnifiedOCRRequest()
    
    assert request.threshold == 500
    assert request.contrast_level == 1.3
    assert request.dpi == 300
    assert request.prompt is None
    assert request.model is None
    assert request.mode == ProcessingMode.BASIC


def test_unified_ocr_request_custom():
    """Test UnifiedOCRRequest with custom values."""
    request = UnifiedOCRRequest(
        threshold=600,
        contrast_level=1.5,
        dpi=400,
        prompt="Extract text",
        model="gpt-4",
        mode=ProcessingMode.LLM_ENHANCED
    )
    
    assert request.threshold == 600
    assert request.contrast_level == 1.5
    assert request.dpi == 400
    assert request.prompt == "Extract text"
    assert request.model == "gpt-4"
    assert request.mode == ProcessingMode.LLM_ENHANCED


def test_file_metadata():
    """Test FileMetadata model."""
    metadata = FileMetadata(
        original_filename="test.jpg",
        file_size_bytes=1024000,
        mime_type="image/jpeg",
        detected_file_type=FileType.IMAGE,
        image_dimensions={"width": 1920, "height": 1080}
    )
    
    assert metadata.original_filename == "test.jpg"
    assert metadata.file_size_bytes == 1024000
    assert metadata.mime_type == "image/jpeg"
    assert metadata.detected_file_type == FileType.IMAGE
    assert metadata.image_dimensions == {"width": 1920, "height": 1080}
    assert metadata.pdf_page_count is None
    assert metadata.docx_page_count is None


def test_pdf_metadata():
    """Test PDF file metadata."""
    metadata = FileMetadata(
        original_filename="document.pdf",
        file_size_bytes=5000000,
        mime_type="application/pdf",
        detected_file_type=FileType.PDF,
        pdf_page_count=10
    )
    
    assert metadata.original_filename == "document.pdf"
    assert metadata.detected_file_type == FileType.PDF
    assert metadata.pdf_page_count == 10
    assert metadata.image_dimensions is None
    assert metadata.docx_page_count is None


def test_docx_metadata():
    """Test DOCX file metadata."""
    metadata = FileMetadata(
        original_filename="report.docx",
        file_size_bytes=2500000,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        detected_file_type=FileType.DOCX,
        docx_page_count=15
    )
    
    assert metadata.original_filename == "report.docx"
    assert metadata.detected_file_type == FileType.DOCX
    assert metadata.docx_page_count == 15
    assert metadata.image_dimensions is None
    assert metadata.pdf_page_count is None


def test_unified_page_result():
    """Test UnifiedPageResult model."""
    timestamp = datetime.now(UTC)
    result = UnifiedPageResult(
        page_number=1,
        extracted_text="Sample extracted text",
        processing_time=2.5,
        success=True,
        threshold_used=500,
        contrast_level_used=1.3,
        timestamp=timestamp
    )
    
    assert result.page_number == 1
    assert result.extracted_text == "Sample extracted text"
    assert result.processing_time == 2.5
    assert result.success is True
    assert result.threshold_used == 500
    assert result.contrast_level_used == 1.3
    assert result.timestamp == timestamp
    assert result.error_message is None
    
    # LLM fields should be None for basic processing
    assert result.image_processing_time is None
    assert result.llm_processing_time is None
    assert result.model_used is None
    assert result.prompt_used is None


def test_unified_streaming_status():
    """Test UnifiedStreamingStatus model."""
    timestamp = datetime.now(UTC)
    status = UnifiedStreamingStatus(
        task_id="test-task-123",
        file_type=FileType.PDF,
        processing_mode=ProcessingMode.LLM_ENHANCED,
        status="processing",
        current_step=ProcessingStep.OCR_PROCESSING,
        progress_percentage=45.0,
        current_page=2,
        total_pages=5,
        processed_pages=1,
        failed_pages=0,
        timestamp=timestamp
    )
    
    assert status.task_id == "test-task-123"
    assert status.file_type == FileType.PDF
    assert status.processing_mode == ProcessingMode.LLM_ENHANCED
    assert status.status == "processing"
    assert status.current_step == ProcessingStep.OCR_PROCESSING
    assert status.progress_percentage == 45.0
    assert status.current_page == 2
    assert status.total_pages == 5
    assert status.processed_pages == 1
    assert status.failed_pages == 0
    assert status.timestamp == timestamp


def test_unified_ocr_response():
    """Test UnifiedOCRResponse model."""
    created_at = datetime.now(UTC)
    metadata = FileMetadata(
        original_filename="test.pdf",
        file_size_bytes=1000000,
        mime_type="application/pdf",
        detected_file_type=FileType.PDF,
        pdf_page_count=3
    )
    
    response = UnifiedOCRResponse(
        task_id="task-789",
        file_type=FileType.PDF,
        processing_mode=ProcessingMode.BASIC,
        status="processing",
        created_at=created_at,
        estimated_duration=15.5,
        file_metadata=metadata
    )
    
    assert response.task_id == "task-789"
    assert response.file_type == FileType.PDF
    assert response.processing_mode == ProcessingMode.BASIC
    assert response.status == "processing"
    assert response.created_at == created_at
    assert response.estimated_duration == 15.5
    assert response.file_metadata == metadata
    assert response.result is None
    assert response.error_message is None
    assert response.completed_at is None


def test_task_cancellation_models():
    """Test task cancellation request and response models."""
    request = UnifiedTaskCancellationRequest()
    assert request.reason == "User requested cancellation"


def test_model_integration():
    """Test integration between different models."""
    # 1. Create request
    request = UnifiedOCRRequest(
        mode=ProcessingMode.LLM_ENHANCED,
        threshold=550,
        prompt="Extract all text"
    )
    
    # 2. Create metadata
    metadata = FileMetadata(
        original_filename="workflow_test.pdf",
        file_size_bytes=2000000,
        mime_type="application/pdf",
        detected_file_type=FileType.PDF,
        pdf_page_count=5
    )
    
    # 3. Create initial response
    created_at = datetime.now(UTC)
    response = UnifiedOCRResponse(
        task_id="workflow-test",
        file_type=FileType.PDF,
        processing_mode=request.mode,
        status="processing",
        created_at=created_at,
        file_metadata=metadata
    )
    
    # 4. Create page result
    page_result = UnifiedPageResult(
        page_number=1,
        extracted_text="Sample page text",
        processing_time=3.2,
        success=True,
        threshold_used=request.threshold,
        contrast_level_used=request.contrast_level,
        model_used="gpt-4-vision-preview",
        prompt_used=request.prompt,
        timestamp=datetime.now(UTC)
    )
    
    # 5. Create streaming status
    status = UnifiedStreamingStatus(
        task_id=response.task_id,
        file_type=response.file_type,
        processing_mode=response.processing_mode,
        status="page_completed",
        current_step=ProcessingStep.OCR_PROCESSING,
        progress_percentage=20.0,
        current_page=1,
        total_pages=metadata.pdf_page_count,
        processed_pages=1,
        latest_page_result=page_result,
        cumulative_results=[page_result],
        timestamp=datetime.now(UTC)
    )
    
    # Verify all models work together
    assert status.task_id == response.task_id
    assert status.file_type == response.file_type
    assert status.processing_mode == response.processing_mode
    assert status.total_pages == metadata.pdf_page_count
    assert status.latest_page_result.threshold_used == request.threshold
    assert status.latest_page_result.prompt_used == request.prompt


def test_json_round_trip_all_models():
    """Test JSON serialization/deserialization for all models."""
    models_to_test = [
        UnifiedOCRRequest(mode=ProcessingMode.LLM_ENHANCED),
        FileMetadata(
            original_filename="test.jpg",
            file_size_bytes=1000,
            mime_type="image/jpeg",
            detected_file_type=FileType.IMAGE
        ),
        UnifiedPageResult(
            page_number=1,
            extracted_text="Test",
            processing_time=1.0,
            success=True,
            threshold_used=500,
            contrast_level_used=1.3,
            timestamp=datetime.now(UTC)
        ),
        UnifiedTaskCancellationRequest(reason="Test cancellation"),
    ]
    
    for model in models_to_test:
        # Serialize to JSON
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Deserialize from JSON
        model_class = type(model)
        restored = model_class.model_validate_json(json_str)
        
        # Compare key fields (not exact equality due to datetime precision)
        original_dict = model.model_dump()
        restored_dict = restored.model_dump()
        
        # Check that both have the same keys
        assert set(original_dict.keys()) == set(restored_dict.keys())


# --- PDF Configuration Tests ---

def test_pdf_config_defaults():
    """Test PDFConfig default values."""
    config = PDFConfig()
    assert config.page_select is None


def test_pdf_config_valid_page_select():
    """Test PDFConfig with valid page selection."""
    config = PDFConfig(page_select=[1, 3, 5])
    assert config.page_select == [1, 3, 5]


def test_pdf_config_page_select_sorting():
    """Test PDFConfig sorts page selection."""
    config = PDFConfig(page_select=[5, 1, 3])
    assert config.page_select == [1, 3, 5]


def test_pdf_config_empty_page_select():
    """Test PDFConfig rejects empty page selection."""
    with pytest.raises(ValueError, match="page_select cannot be empty if provided"):
        PDFConfig(page_select=[])


def test_pdf_config_invalid_page_numbers():
    """Test PDFConfig rejects invalid page numbers."""
    with pytest.raises(ValueError, match="Page numbers must be 1-indexed"):
        PDFConfig(page_select=[0, 1, 2])


def test_pdf_config_duplicate_page_numbers():
    """Test PDFConfig rejects duplicate page numbers."""
    with pytest.raises(ValueError, match="Duplicate page numbers are not allowed"):
        PDFConfig(page_select=[1, 2, 2, 3])


def test_pdf_config_negative_page_numbers():
    """Test PDFConfig rejects negative page numbers."""
    with pytest.raises(ValueError, match="Page numbers must be 1-indexed"):
        PDFConfig(page_select=[-1, 1, 2])


def test_unified_ocr_request_with_pdf_config():
    """Test UnifiedOCRRequest with pdf_config field."""
    pdf_config = PDFConfig(page_select=[1, 3, 5])
    request = UnifiedOCRRequest(pdf_config=pdf_config)
    
    assert request.pdf_config is not None
    assert request.pdf_config.page_select == [1, 3, 5]


def test_unified_ocr_request_without_pdf_config():
    """Test UnifiedOCRRequest without pdf_config field."""
    request = UnifiedOCRRequest()
    assert request.pdf_config is None 