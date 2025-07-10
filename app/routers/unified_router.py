"""
Unified OCR streaming router - ONE endpoint for ALL file types + optional specific endpoints.
"""

import uuid
from datetime import datetime, timezone

# Use timezone.utc instead of UTC for backward compatibility
UTC = timezone.utc
from fastapi import APIRouter, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.unified_models import (
    UnifiedOCRRequest, UnifiedOCRResponse, 
    UnifiedTaskCancellationRequest, UnifiedTaskCancellationResponse
)
from app.services.unified_stream_processor import unified_processor
from app.logger_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# =============================================================================
# 🎯 MAIN UNIFIED ENDPOINT - Use this for 95% of cases!
# =============================================================================

@router.post(
    "/ocr/process-stream",
    response_model=UnifiedOCRResponse,
    summary="🌟 Universal OCR Processing with Streaming + URL Support",
    description="""
    ## 🎯 **One Endpoint for ALL File Types + URL Downloads!**
    
    Process files via **file upload** OR **URL download** for streaming OCR with real-time updates.
    
    ### 📁 **Supported File Types:**
    - **🖼️ Images**: JPG, PNG, BMP, TIFF, WebP (max 10MB)
    - **📄 PDFs**: PDF documents (max 10 pages, 50MB) 
    - **🚫 Documents**: DOCX processing is currently disabled
    
    ### 🌐 **Input Methods:**
    - **📁 File Upload**: Traditional file upload (multipart/form-data)
    - **🔗 URL Download**: Provide URL to download file automatically
    
    ### ⚙️ **Processing Features:**
    - **🔍 Auto File Type Detection**: Based on MIME type and extension
    - **🌊 Real-time Streaming**: Live progress updates via Server-Sent Events
    - **🧠 LLM Enhancement**: Optional AI-powered text improvement
    - **📊 Progress Tracking**: Step-by-step processing updates including URL download
    - **⚡ Intelligent Routing**: Optimized processing per file type
    - **🛡️ Secure Downloads**: Validates file types and sizes during download
    - **📄 PDF Page Selection**: Process specific pages only (e.g., pages 1, 3, 5)
    
    ### 🔄 **Processing Modes:**
    - **`basic`**: Fast OCR processing only
    - **`llm_enhanced`**: OCR + AI enhancement for better accuracy
    
    ### 📡 **Streaming Connection:**
    After creating a task, connect to `/v1/ocr/stream/{task_id}` for real-time updates.
    
    ### 📝 **Example Usage:**
    ```bash
    # Upload file (all pages)
    curl -X POST "/v1/ocr/process-stream" \\
      -F "file=@document.pdf" \\
      -F "request={'mode': 'llm_enhanced', 'threshold': 500}"
    
    # Upload file with specific pages
    curl -X POST "/v1/ocr/process-stream" \\
      -F "file=@document.pdf" \\
      -F "request={'mode': 'basic', 'pdf_config': {'page_select': [1, 3, 5]}}"
    
    # Download from URL with page selection
    curl -X POST "/v1/ocr/process-stream" \\
      -F "request={'url': 'https://example.com/document.pdf', 'mode': 'llm_enhanced', 'pdf_config': {'page_select': [2, 4]}}"
    
    # Connect to streaming updates  
    curl -N "/v1/ocr/stream/{task_id}"
    ```
    
    ### ✨ **Frontend Integration:**
    ```javascript
    // File upload with page selection
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('request', JSON.stringify({
        mode: 'llm_enhanced',
        pdf_config: {
            page_select: [1, 3, 5]  // Process pages 1, 3, 5 only
        }
    }));
    
    // URL download with page selection
    const formData = new FormData();
    formData.append('request', JSON.stringify({
        url: 'https://example.com/document.pdf',
        mode: 'basic',
        pdf_config: {
            page_select: [2, 4, 6]  // Process pages 2, 4, 6 only
        }
    }));
    
    const response = await fetch('/v1/ocr/process-stream', {
        method: 'POST',
        body: formData
    });
    
    const {task_id} = await response.json();
    const eventSource = new EventSource(`/v1/ocr/stream/${task_id}`);
    ```
    
    ### 📄 **PDF Page Selection Guide:**
    - **`page_select`**: Array of page numbers (1-indexed)
    - **Validation**: Pages must exist, no duplicates, no empty arrays
    - **Auto-sorting**: Pages processed in ascending order
    - **Default**: If not provided, processes all pages
    - **Examples**: `[1]`, `[1, 3, 5]`, `[2, 4, 6, 8, 10]`
    """,
    responses={
        200: {
            "description": "✅ Streaming task created successfully",
            "content": {
                "application/json": {
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
                            "detected_file_type": "pdf",
                            "pdf_page_count": 5
                        }
                    }
                }
            }
        },
        400: {"description": "❌ Invalid file type or parameters"},
        413: {"description": "📏 File too large for detected type"},
        429: {"description": "⏰ Rate limit exceeded"}
    },
    tags=["🌟 Universal Processing"]
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_any_file_stream(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(None, description="File upload (Image/PDF only) - alternative to URL"),
    request: Request = None
):
    """
    🎯 **Universal OCR Processing Endpoint with URL Support**
    
    Process files via file upload OR URL download with real-time streaming updates.
    The backend automatically:
    1. 📥 Accepts file upload OR URL download
    2. 🔍 Detects file type (Images/PDFs only, DOCX disabled)
    3. ⚙️ Applies appropriate processing pipeline  
    4. 🌊 Provides streaming updates via SSE
    5. 📊 Returns results in unified format
    
    **Perfect for frontend developers** - supports both upload and URL methods!
    """
    task_id = str(uuid.uuid4())
    
    try:
        # Parse unified request parameters
        unified_request = UnifiedOCRRequest()
        if request_data:
            unified_request = UnifiedOCRRequest.model_validate_json(request_data)
        
        # Validate input method (either file upload OR URL, not both)
        has_file = file is not None and file.filename
        has_url = unified_request.url is not None
        
        if not has_file and not has_url:
            raise HTTPException(
                status_code=400,
                detail="Either 'file' upload or 'url' in request data must be provided"
            )
        
        if has_file and has_url:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'file' upload OR 'url', not both"
            )
        
        # Check if URL processing is enabled
        if has_url and not settings.ENABLE_URL_PROCESSING:
            raise HTTPException(
                status_code=400,
                detail="URL processing is currently disabled"
            )
        
        if has_file:
            logger.info(
                f"🚀 Starting UNIFIED streaming task {task_id} for uploaded file: {file.filename} "
                f"(size: {file.size:,} bytes, MIME: {file.content_type})"
            )
        else:
            logger.info(
                f"🚀 Starting UNIFIED streaming task {task_id} for URL: {unified_request.url}"
            )
        
        # Process with unified processor (handles both file upload and URL)
        response = await unified_processor.process_file_stream(
            file=file,
            request=unified_request,
            task_id=task_id
        )
        
        source_type = "uploaded file" if has_file else "URL"
        logger.info(
            f"✅ Created {response.file_type.value} streaming task {task_id} from {source_type} "
            f"(mode: {response.processing_mode.value}, estimated: {response.estimated_duration}s)"
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except Exception as e:
        logger.error(f"❌ Unified streaming failed for {task_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start processing: {str(e)}"
        )


# =============================================================================
# 🌊 UNIVERSAL STREAMING ENDPOINT - Works for ALL file types
# =============================================================================

@router.get(
    "/ocr/stream/{task_id}",
    summary="🌊 Universal Streaming Progress", 
    description="""
    ## 🌊 **Universal Streaming Connection**
    
    Connect to real-time streaming updates for **ANY** file type processing.
    
    ### 📡 **Server-Sent Events (SSE)**
    - **Real-time updates** as processing progresses
    - **Dual result format** for maximum frontend flexibility
    - **Progress tracking** with percentage and time estimates
    - **Error handling** with detailed error messages
    - **Heartbeat messages** to keep connection alive
    
    ### 📊 **Update Types:**
    - **Processing updates**: Step-by-step progress
    - **Page completion**: Individual page/unit results  
    - **Final completion**: Complete results
    - **Error notifications**: Detailed error information
    
    ### 🔄 **Streaming Data Format:**
    ```json
    {
        "task_id": "uuid",
        "file_type": "pdf|image|docx",
        "status": "processing|page_completed|completed|failed",
        "progress_percentage": 45.2,
        "current_step": "ocr_processing",
        "latest_page_result": {...},     // Type 1: Latest result
        "cumulative_results": [...],     // Type 2: All results
        "estimated_time_remaining": 15.3
    }
    ```
    
    ### ✨ **Frontend Example:**
    ```javascript
    const eventSource = new EventSource('/v1/ocr/stream/task-id');
    
    eventSource.onmessage = (event) => {
        const update = JSON.parse(event.data);
        
        // Update progress bar
        updateProgress(update.progress_percentage);
        
        // Handle new results (works for any file type!)
        if (update.latest_page_result) {
            displayNewResult(update.latest_page_result);
        }
        
        // Check completion
        if (update.status === 'completed') {
            displayFinalResults(update.cumulative_results);
            eventSource.close();
        }
    };
    ```
    """,
    responses={
        200: {
            "description": "🌊 Streaming connection established", 
            "content": {"text/event-stream": {
                "example": """data: {"task_id":"uuid","status":"processing","progress_percentage":20.0}

data: {"task_id":"uuid","status":"page_completed","latest_page_result":{...}}

data: {"task_id":"uuid","status":"completed","cumulative_results":[...]}"""
            }}
        },
        404: {"description": "❌ Task not found"},
        429: {"description": "⏰ Rate limit exceeded"}
    },
    tags=["🌊 Streaming"]
)
@limiter.limit("10/minute")  # Lower rate limit for streaming connections
async def stream_universal_progress(task_id: str, request: Request):
    """
    🌊 **Universal streaming endpoint for all file types.**
    
    Provides real-time progress updates via Server-Sent Events (SSE).
    Works seamlessly with any file type processed through the unified endpoint.
    """
    try:
        logger.debug(f"🌊 Starting universal stream for task {task_id}")
        
        return StreamingResponse(
            unified_processor.get_stream_generator(task_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive", 
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start stream for {task_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start streaming connection: {str(e)}"
        )


# =============================================================================
# ⚙️ OPTIONAL SPECIFIC ENDPOINTS - For power users who want explicit control
# =============================================================================

@router.post(
    "/ocr/process-image-stream",
    response_model=UnifiedOCRResponse,
    summary="🖼️ Image-Only Streaming (Power Users)",
    description="""
    ## 🖼️ **Explicit Image Processing**
    
    For power users who want explicit image-only processing with validation.
    
    **Most users should use `/process-stream` instead!**
    
    - **Strict validation**: Only accepts image files
    - **Same streaming**: Uses universal streaming endpoint
    - **Same features**: All unified processing features
    """,
    include_in_schema=False,  # Hide from main docs
    tags=["⚙️ Power User Endpoints"]
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_image_stream_explicit(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="Image file only (JPG, PNG, BMP, TIFF, WebP)"),
    request: Request = None
):
    """Explicit image processing with strict validation."""
    # Strict image validation
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400, 
            detail=f"This endpoint only accepts image files. "
                   f"Received: {file.content_type}. Use /process-stream for auto-detection."
        )
    
    # Delegate to unified endpoint
    return await process_any_file_stream(request_data, file, request)


@router.post(
    "/ocr/process-docx-stream",
    response_model=UnifiedOCRResponse,
    summary="📝 DOCX-Only Streaming (Power Users)",
    description="""
    ## 📝 **Explicit DOCX Processing**
    
    For power users who want explicit DOCX-only processing with validation.
    
    **Most users should use `/process-stream` instead!**
    
    - **Strict validation**: Only accepts DOCX files
    - **DOCX → PDF → OCR**: Complete processing pipeline
    - **Same streaming**: Uses universal streaming endpoint
    """,
    include_in_schema=False,  # Hide from main docs  
    tags=["⚙️ Power User Endpoints"]
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_docx_stream_explicit(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="DOCX file only"),
    request: Request = None
):
    """Explicit DOCX processing with strict validation."""
    # Strict DOCX validation
    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if file.content_type != docx_mime:
        raise HTTPException(
            status_code=400,
            detail=f"This endpoint only accepts DOCX files. "
                   f"Received: {file.content_type}. Use /process-stream for auto-detection."
        )
    
    # Delegate to unified endpoint
    return await process_any_file_stream(request_data, file, request)


# =============================================================================
# 🛑 TASK CANCELLATION - Works for all file types
# =============================================================================

@router.post(
    "/ocr/tasks/{task_id}/cancel",
    response_model=UnifiedTaskCancellationResponse,
    summary="🛑 Cancel Processing Task",
    description="""
    ## 🛑 **Cancel Any Processing Task**
    
    Cancel a running task for **any file type**.
    
    - **Immediate cancellation**: Stops processing and closes streams
    - **Resource cleanup**: Removes temporary files and queues
    - **Status update**: Updates task status to 'cancelled'
    - **Works universally**: Same endpoint for all file types
    """,
    tags=["🛑 Task Management"]
)
@limiter.limit("20/minute")
async def cancel_universal_task(
    task_id: str,
    cancel_request: UnifiedTaskCancellationRequest = UnifiedTaskCancellationRequest(),
    request: Request = None
):
    """Cancel any processing task regardless of file type."""
    try:
        # Check if task exists in streaming queues (actively processing)
        is_actively_processing = task_id in unified_processor.streaming_queues
        
        # Check if task exists in metadata (recently completed or processing)
        task_meta = unified_processor.task_metadata.get(task_id)
        
        if not is_actively_processing and not task_meta:
            # Task truly doesn't exist
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found or already completed"
            )
        
        # If task is actively processing, perform normal cancellation
        if is_actively_processing:
            file_type = task_meta.get("file_type", "unknown") if task_meta else "unknown"
            request_obj = task_meta.get("request", UnifiedOCRRequest()) if task_meta else UnifiedOCRRequest()
            
            # Send cancellation update
            from app.models.unified_models import ProcessingStep
            await unified_processor._send_progress_update(
                task_id=task_id,
                file_type=file_type,
                mode=request_obj.mode if hasattr(request_obj, 'mode') else "basic",
                status="cancelled",
                step=ProcessingStep.CANCELLED,
                progress=0.0,
                message=f"Task cancelled: {cancel_request.reason}"
            )
            
            # Cleanup task
            await unified_processor._cleanup_task(task_id)
            
            response = UnifiedTaskCancellationResponse(
                task_id=task_id,
                status="cancelled",
                message="Task cancelled successfully",
                cancelled_at=datetime.now(UTC),
                cancellation_reason=cancel_request.reason
            )
            
            logger.info(f"🛑 Cancelled active task {task_id}: {cancel_request.reason}")
            return response
        
        # If task recently completed (race condition case)
        elif task_meta and task_meta.get("status") == "completed":
            response = UnifiedTaskCancellationResponse(
                task_id=task_id,
                status="already_completed",
                message="Task was already completed before cancellation request",
                cancelled_at=datetime.now(UTC),
                cancellation_reason="Task completed before cancellation could be processed"
            )
            
            logger.info(f"ℹ️ Attempted to cancel already completed task {task_id}")
            return response
        
        # Fallback for other cases
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} cannot be cancelled in its current state"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


# =============================================================================
# 📊 TASK STATUS - Universal task information
# =============================================================================

@router.get(
    "/ocr/tasks/{task_id}/status",
    response_model=UnifiedOCRResponse,
    summary="📊 Get Task Status",
    description="""
    ## 📊 **Get Universal Task Status**
    
    Get current status and information for any processing task.
    
    - **Universal support**: Works for all file types
    - **Real-time status**: Current processing state
    - **Progress information**: Completion percentage and estimates
    - **Result preview**: Latest results if available
    """,
    tags=["📊 Task Information"]
)
async def get_universal_task_status(task_id: str, request: Request):
    """Get status for any task regardless of file type."""
    try:
        # Check if task exists in our processor
        if task_id not in unified_processor.task_metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        task_meta = unified_processor.task_metadata[task_id]
        
        # Create status response
        response = UnifiedOCRResponse(
            task_id=task_id,
            file_type=task_meta["file_type"],
            processing_mode=task_meta["request"].mode,
            status="processing" if task_id in unified_processor.streaming_queues else "completed",
            created_at=datetime.fromtimestamp(task_meta["start_time"], UTC),
            file_metadata=task_meta["metadata"]
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        ) 