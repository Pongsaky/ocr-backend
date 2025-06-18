"""
OCR router for API endpoints.
"""

from typing import Dict, List, Any

from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, OCRResponse, OCRResult, ErrorResponse,
    OCRLLMRequest, OCRLLMResponse, OCRLLMResult,
    PDFOCRRequest, PDFOCRResponse, PDFOCRResult,
    PDFLLMOCRRequest, PDFLLMOCRResponse, PDFLLMOCRResult,
    CancelTaskRequest, CancelTaskResponse
)
from app.controllers.ocr_controller import ocr_controller
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Create router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/ocr/process",
    response_model=OCRResponse,
    summary="Process image for OCR (Async)",
    description="Upload an image file for asynchronous OCR processing. Returns a task ID to check status.",
    responses={
        200: {"description": "Task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_image_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="Image file to process"),
    request: Request = None
):
    """
    Process an uploaded image for OCR asynchronously.
    
    Args:
        request: JSON string containing OCR parameters
        file: Uploaded image file
        
    Returns:
        OCRResponse: Task information with unique ID
    """
    import json
    
    try:
        # Parse OCR request or use defaults if empty
        if request_data:
            ocr_request = OCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            ocr_request = OCRRequest()
        
        logger.info(
            f"Received async OCR request for {file.filename} "
            f"with threshold: {ocr_request.threshold}, contrast: {ocr_request.contrast_level}"
        )
        
        # Process image
        response = await ocr_controller.process_image(file, ocr_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-sync",
    response_model=OCRResult,
    summary="Process image for OCR (Sync)",
    description="Upload an image file for synchronous OCR processing. Returns results immediately.",
    responses={
        200: {"description": "OCR processing completed"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing failed"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_image_sync(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="Image file to process"),
    request: Request = None
):
    """
    Process an uploaded image for OCR synchronously.
    
    Args:
        request: JSON string containing OCR parameters
        file: Uploaded image file
        
    Returns:
        OCRResult: OCR processing result
    """
    import json
    
    try:
        # Parse OCR request or use defaults if empty
        if request_data:
            ocr_request = OCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            ocr_request = OCRRequest()
        
        logger.info(
            f"Received sync OCR request for {file.filename} "
            f"with threshold: {ocr_request.threshold}, contrast: {ocr_request.contrast_level}"
        )
        
        # Process image synchronously
        result = await ocr_controller.process_image_sync(file, ocr_request)
        
        return result
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Sync OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


# --- LLM-Enhanced OCR Endpoints ---

@router.post(
    "/ocr/process-with-llm",
    response_model=OCRLLMResponse,
    summary="Process image for LLM-enhanced OCR (Async)",
    description="Upload an image file for asynchronous LLM-enhanced OCR processing. Returns a task ID to check status.",
    responses={
        200: {"description": "LLM OCR task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_image_with_llm_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="Image file to process"),
    request: Request = None
):
    """
    Process an uploaded image for LLM-enhanced OCR asynchronously.
    
    Args:
        request: JSON string containing OCR LLM parameters
        file: Uploaded image file
        
    Returns:
        OCRLLMResponse: Task information with unique ID
    """
    import json
    
    try:
        # Parse OCR LLM request or use defaults if empty
        if request_data:
            ocr_llm_request = OCRLLMRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            ocr_llm_request = OCRLLMRequest()
        
        logger.info(
            f"Received async LLM OCR request for {file.filename} "
            f"with threshold: {ocr_llm_request.threshold}, contrast: {ocr_llm_request.contrast_level}, "
            f"prompt: {ocr_llm_request.prompt}, model: {ocr_llm_request.model}"
        )
        
        # Process image with LLM
        response = await ocr_controller.process_image_with_llm(file, ocr_llm_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"LLM OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"LLM processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-with-llm-sync",
    response_model=OCRLLMResult,
    summary="Process image for LLM-enhanced OCR (Sync)",
    description="Upload an image file for synchronous LLM-enhanced OCR processing. Returns results immediately.",
    responses={
        200: {"description": "LLM OCR processing completed"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing failed"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_image_with_llm_sync(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="Image file to process"),
    request: Request = None
):
    """
    Process an uploaded image for LLM-enhanced OCR synchronously.
    
    Args:
        request: JSON string containing OCR LLM parameters
        file: Uploaded image file
        
    Returns:
        OCRLLMResult: LLM OCR processing result
    """
    import json
    
    try:
        # Parse OCR LLM request or use defaults if empty
        if request_data:
            ocr_llm_request = OCRLLMRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            ocr_llm_request = OCRLLMRequest()
        
        logger.info(
            f"Received sync LLM OCR request for {file.filename} "
            f"with threshold: {ocr_llm_request.threshold}, contrast: {ocr_llm_request.contrast_level}, "
            f"prompt: {ocr_llm_request.prompt}, model: {ocr_llm_request.model}"
        )
        
        # Process image with LLM synchronously
        result = await ocr_controller.process_image_with_llm_sync(file, ocr_llm_request)
        
        return result
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Sync LLM OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"LLM processing failed: {str(e)}"
        )


@router.get(
    "/ocr/llm-tasks/{task_id}",
    response_model=OCRLLMResponse,
    summary="Get LLM OCR task status",
    description="Get the status and results of an LLM OCR processing task.",
    responses={
        200: {"description": "LLM task status retrieved"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def get_llm_task_status(request: Request, task_id: str):
    """
    Get the status of an LLM OCR processing task.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        OCRLLMResponse: Task status and result
    """
    logger.debug(f"Checking status for LLM task {task_id}")
    
    try:
        response = await ocr_controller.get_llm_task_status(task_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get LLM task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get LLM task status: {str(e)}"
        )


@router.get(
    "/ocr/tasks/{task_id}",
    response_model=OCRResponse,
    summary="Get OCR task status",
    description="Get the status and results of an OCR processing task.",
    responses={
        200: {"description": "Task status retrieved"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def get_task_status(request: Request, task_id: str):
    """
    Get the status of an OCR processing task.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        OCRResponse: Task status and result
    """
    logger.debug(f"Checking status for task {task_id}")
    
    try:
        response = await ocr_controller.get_task_status(task_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get(
    "/ocr/tasks",
    response_model=Dict[str, str],
    summary="List all OCR tasks",
    description="Get a list of all OCR tasks and their current statuses.",
    responses={
        200: {"description": "Task list retrieved"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def list_tasks(request: Request):
    """
    List all OCR tasks and their statuses.
    
    Returns:
        Dict[str, str]: Task IDs and their statuses
    """
    logger.debug("Listing all OCR tasks")
    
    try:
        tasks = await ocr_controller.list_tasks()
        return tasks
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.delete(
    "/ocr/tasks/cleanup",
    summary="Clean up completed tasks",
    description="Remove completed and failed tasks from memory.",
    responses={
        200: {"description": "Tasks cleaned up successfully"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("10/minute")
async def cleanup_tasks(request: Request):
    """
    Clean up completed OCR tasks from memory.
    
    Returns:
        Dict: Number of tasks cleaned up
    """
    logger.info("Cleaning up completed OCR tasks")
    
    try:
        count = await ocr_controller.cleanup_completed_tasks()
        return {"cleaned_up": count, "message": f"Cleaned up {count} completed tasks"}
        
    except Exception as e:
        logger.error(f"Failed to cleanup tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup tasks: {str(e)}"
        )


# --- Task Cancellation Endpoints ---

@router.post(
    "/ocr/tasks/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel OCR Task",
    description="Cancel a running OCR task. This will stop processing and mark the task as cancelled.",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"model": ErrorResponse, "description": "Cannot cancel task (already completed/failed)"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("20/minute")
async def cancel_ocr_task(
    task_id: str,
    cancel_request: CancelTaskRequest = CancelTaskRequest(),
    request: Request = None
):
    """
    Cancel a running OCR task.
    
    Args:
        task_id: Unique task identifier
        cancel_request: Cancellation request details
        
    Returns:
        CancelTaskResponse: Cancellation confirmation
    """
    logger.info(f"Cancelling OCR task {task_id}: {cancel_request.reason}")
    
    try:
        result = await ocr_controller.cancel_ocr_task(task_id, cancel_request.reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel OCR task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post(
    "/ocr/llm-tasks/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel LLM OCR Task",
    description="Cancel a running LLM OCR task. This will stop processing and mark the task as cancelled.",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"model": ErrorResponse, "description": "Cannot cancel task (already completed/failed)"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("20/minute")
async def cancel_llm_task(
    task_id: str,
    cancel_request: CancelTaskRequest = CancelTaskRequest(),
    request: Request = None
):
    """
    Cancel a running LLM OCR task.
    
    Args:
        task_id: Unique task identifier
        cancel_request: Cancellation request details
        
    Returns:
        CancelTaskResponse: Cancellation confirmation
    """
    logger.info(f"Cancelling LLM OCR task {task_id}: {cancel_request.reason}")
    
    try:
        result = await ocr_controller.cancel_llm_task(task_id, cancel_request.reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel LLM OCR task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post(
    "/ocr/pdf-tasks/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel PDF OCR Task",
    description="Cancel a running PDF OCR task. This will stop processing and mark the task as cancelled.",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"model": ErrorResponse, "description": "Cannot cancel task (already completed/failed)"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("20/minute")
async def cancel_pdf_task(
    task_id: str,
    cancel_request: CancelTaskRequest = CancelTaskRequest(),
    request: Request = None
):
    """
    Cancel a running PDF OCR task.
    
    Args:
        task_id: Unique task identifier
        cancel_request: Cancellation request details
        
    Returns:
        CancelTaskResponse: Cancellation confirmation
    """
    logger.info(f"Cancelling PDF OCR task {task_id}: {cancel_request.reason}")
    
    try:
        result = await ocr_controller.cancel_pdf_task(task_id, cancel_request.reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel PDF OCR task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post(
    "/ocr/pdf-llm-tasks/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel PDF LLM OCR Task",
    description="Cancel a running PDF LLM OCR task. This will stop processing and mark the task as cancelled.",
    responses={
        200: {"description": "Task cancelled successfully"},
        400: {"model": ErrorResponse, "description": "Cannot cancel task (already completed/failed)"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("20/minute")
async def cancel_pdf_llm_task(
    task_id: str,
    cancel_request: CancelTaskRequest = CancelTaskRequest(),
    request: Request = None
):
    """
    Cancel a running PDF LLM OCR task.
    
    Args:
        task_id: Unique task identifier
        cancel_request: Cancellation request details
        
    Returns:
        CancelTaskResponse: Cancellation confirmation
    """
    logger.info(f"Cancelling PDF LLM OCR task {task_id}: {cancel_request.reason}")
    
    try:
        result = await ocr_controller.cancel_pdf_llm_task(task_id, cancel_request.reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel PDF LLM OCR task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.post(
    "/ocr/stream/{task_id}/cancel",
    response_model=CancelTaskResponse,
    summary="Cancel Streaming Task",
    description="Cancel a running streaming PDF task (PDF or PDF LLM). This will stop processing and close the stream.",
    responses={
        200: {"description": "Streaming task cancelled successfully"},
        400: {"model": ErrorResponse, "description": "Cannot cancel task (already completed/failed)"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("20/minute")
async def cancel_streaming_task(
    task_id: str,
    cancel_request: CancelTaskRequest = CancelTaskRequest(),
    request: Request = None
):
    """
    Cancel a running streaming task.
    
    Args:
        task_id: Unique task identifier
        cancel_request: Cancellation request details
        
    Returns:
        CancelTaskResponse: Cancellation confirmation
    """
    logger.info(f"Cancelling streaming task {task_id}: {cancel_request.reason}")
    
    try:
        result = await ocr_controller.cancel_streaming_task(task_id, cancel_request.reason)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel streaming task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


# --- PDF OCR Endpoints ---

@router.post(
    "/ocr/process-pdf",
    response_model=PDFOCRResponse,
    summary="Process PDF for OCR (Async)",
    description="Upload a PDF file for asynchronous OCR processing. Maximum 10 pages. Returns a task ID to check status.",
    responses={
        200: {"description": "PDF OCR task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process an uploaded PDF file for OCR asynchronously.
    
    Args:
        request: JSON string containing PDF OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFOCRResponse: Task information with unique ID
    """
    import json
    
    try:
        # Parse PDF OCR request or use defaults if empty
        if request_data:
            pdf_request = PDFOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_request = PDFOCRRequest()
        
        logger.info(
            f"Received async PDF OCR request for {file.filename} "
            f"with threshold: {pdf_request.threshold}, contrast: {pdf_request.contrast_level}, dpi: {pdf_request.dpi}"
        )
        
        # Process PDF
        response = await ocr_controller.process_pdf(file, pdf_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"PDF OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-pdf-sync",
    response_model=PDFOCRResult,
    summary="Process PDF for OCR (Sync)",
    description="Upload a PDF file for synchronous OCR processing. Maximum 10 pages. Returns results immediately.",
    responses={
        200: {"description": "PDF OCR processing completed"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing failed"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_sync(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process an uploaded PDF file for OCR synchronously.
    
    Args:
        request: JSON string containing PDF OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFOCRResult: PDF OCR processing result
    """
    import json
    
    try:
        # Parse PDF OCR request or use defaults if empty
        if request_data:
            pdf_request = PDFOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_request = PDFOCRRequest()
        
        logger.info(
            f"Received sync PDF OCR request for {file.filename} "
            f"with threshold: {pdf_request.threshold}, contrast: {pdf_request.contrast_level}, dpi: {pdf_request.dpi}"
        )
        
        # Process PDF synchronously
        result = await ocr_controller.process_pdf_sync(file, pdf_request)
        
        return result
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Sync PDF OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-pdf-with-llm",
    response_model=PDFLLMOCRResponse,
    summary="Process PDF for LLM-enhanced OCR (Async)",
    description="Upload a PDF file for asynchronous LLM-enhanced OCR processing. Maximum 10 pages. Returns a task ID to check status.",
    responses={
        200: {"description": "PDF LLM OCR task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_with_llm_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process an uploaded PDF file for LLM-enhanced OCR asynchronously.
    
    Args:
        request: JSON string containing PDF LLM OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFLLMOCRResponse: Task information with unique ID
    """
    import json
    
    try:
        # Parse PDF LLM OCR request or use defaults if empty
        if request_data:
            pdf_llm_request = PDFLLMOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_llm_request = PDFLLMOCRRequest()
        
        logger.info(
            f"Received async PDF LLM OCR request for {file.filename} "
            f"with threshold: {pdf_llm_request.threshold}, contrast: {pdf_llm_request.contrast_level}, "
            f"dpi: {pdf_llm_request.dpi}, prompt: {pdf_llm_request.prompt}, model: {pdf_llm_request.model}"
        )
        
        # Process PDF with LLM
        response = await ocr_controller.process_pdf_with_llm(file, pdf_llm_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"PDF LLM OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF LLM processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-pdf-with-llm-sync",
    response_model=PDFLLMOCRResult,
    summary="Process PDF for LLM-enhanced OCR (Sync)",
    description="Upload a PDF file for synchronous LLM-enhanced OCR processing. Maximum 10 pages. Returns results immediately.",
    responses={
        200: {"description": "PDF LLM OCR processing completed"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing failed"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_with_llm_sync(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process an uploaded PDF file for LLM-enhanced OCR synchronously.
    
    Args:
        request: JSON string containing PDF LLM OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFLLMOCRResult: PDF LLM OCR processing result
    """
    import json
    
    try:
        # Parse PDF LLM OCR request or use defaults if empty
        if request_data:
            pdf_llm_request = PDFLLMOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_llm_request = PDFLLMOCRRequest()
        
        logger.info(
            f"Received sync PDF LLM OCR request for {file.filename} "
            f"with threshold: {pdf_llm_request.threshold}, contrast: {pdf_llm_request.contrast_level}, "
            f"dpi: {pdf_llm_request.dpi}, prompt: {pdf_llm_request.prompt}, model: {pdf_llm_request.model}"
        )
        
        # Process PDF with LLM synchronously
        result = await ocr_controller.process_pdf_with_llm_sync(file, pdf_llm_request)
        
        return result
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Sync PDF LLM OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF LLM processing failed: {str(e)}"
        )


@router.get(
    "/ocr/pdf-tasks/{task_id}",
    response_model=PDFOCRResponse,
    summary="Get PDF OCR task status",
    description="Get the status and results of a PDF OCR processing task.",
    responses={
        200: {"description": "PDF task status retrieved"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def get_pdf_task_status(request: Request, task_id: str):
    """
    Get the status of a PDF OCR task.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        PDFOCRResponse: Task status and result
    """
    try:
        result = await ocr_controller.get_pdf_task_status(task_id)
        logger.debug(f"Retrieved PDF task status for {task_id}: {result.status}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve PDF task status: {str(e)}"
        )


@router.get(
    "/ocr/pdf-llm-tasks/{task_id}",
    response_model=PDFLLMOCRResponse,
    summary="Get PDF LLM OCR task status",
    description="Get the status and results of a PDF LLM OCR processing task.",
    responses={
        200: {"description": "PDF LLM task status retrieved"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def get_pdf_llm_task_status(request: Request, task_id: str):
    """
    Get the status of a PDF LLM OCR task.
    
    Args:
        task_id: Unique task identifier
        
    Returns:
        PDFLLMOCRResponse: Task status and result
    """
    try:
        result = await ocr_controller.get_pdf_llm_task_status(task_id)
        logger.debug(f"Retrieved PDF LLM task status for {task_id}: {result.status}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF LLM task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve PDF LLM task status: {str(e)}"
        )


@router.get(
    "/ocr/parameters",
    response_model=Dict[str, Any],
    summary="Get OCR parameters info",
    description="Get information about available OCR processing parameters.",
    responses={
        200: {"description": "Parameter information retrieved"}
    }
)
async def get_ocr_parameters():
    """
    Get information about OCR processing parameters.
    
    Returns:
        Dict[str, Any]: Parameter information and ranges
    """
    from config.settings import get_settings
    settings = get_settings()
    
    parameters = {
        "image_processing": {
            "threshold": {
                "type": "integer",
                "description": "Threshold value for image binarization",
                "min": 0,
                "max": 1024,
                "default": settings.DEFAULT_THRESHOLD,
                "recommended": "500 for general use, lower values for darker images, higher for lighter images"
            },
            "contrast_level": {
                "type": "number",
                "description": "Contrast enhancement level",
                "min": 0.1,
                "max": 5.0,
                "default": settings.DEFAULT_CONTRAST_LEVEL,
                "recommended": "1.3 for enhanced contrast, >1.0 to increase contrast, <1.0 to decrease"
            }
        },
        "pdf_processing": {
            "threshold": {
                "type": "integer",
                "description": "Threshold value for PDF page image binarization",
                "min": 0,
                "max": 1024,
                "default": settings.DEFAULT_THRESHOLD,
                "recommended": "500 for general use, lower values for darker images, higher for lighter images"
            },
            "contrast_level": {
                "type": "number",
                "description": "Contrast enhancement level for PDF pages",
                "min": 0.1,
                "max": 5.0,
                "default": settings.DEFAULT_CONTRAST_LEVEL,
                "recommended": "1.3 for enhanced contrast, >1.0 to increase contrast, <1.0 to decrease"
            },
            "dpi": {
                "type": "integer",
                "description": "DPI for PDF to image conversion",
                "min": 150,
                "max": 600,
                "default": settings.PDF_DPI,
                "recommended": "300 for balanced quality and speed, 600 for high quality, 150 for faster processing"
            },
            "max_pages": settings.MAX_PDF_PAGES,
            "batch_size": settings.PDF_BATCH_SIZE
        },
        "llm_parameters": {
            "prompt": {
                "type": "string",
                "description": "Custom prompt for OCR LLM",
                "default": settings.OCR_LLM_DEFAULT_PROMPT,
                "recommended": "Use custom prompts for specific use cases or languages"
            },
            "model": {
                "type": "string",
                "description": "LLM model to use for OCR enhancement",
                "default": settings.OCR_LLM_MODEL,
                "recommended": "Use default model unless specific requirements exist"
            }
        },
        "file_constraints": {
            "images": {
                "supported_formats": settings.ALLOWED_IMAGE_EXTENSIONS,
                "max_file_size_bytes": settings.IMAGE_MAX_SIZE
            },
            "pdfs": {
                "supported_formats": settings.ALLOWED_PDF_EXTENSIONS,
                "max_file_size_bytes": settings.MAX_PDF_SIZE,
                "max_pages": settings.MAX_PDF_PAGES
            }
        }
    }
    
    return parameters


@router.get(
    "/ocr/service-info",
    response_model=Dict[str, Any],
    summary="Get external service information",
    description="Get information about the external OCR service being used.",
    responses={
        200: {"description": "Service information retrieved"}
    }
)
async def get_service_info():
    """
    Get information about the external OCR services.
    
    Returns:
        Dict[str, Any]: External service information
    """
    from app.services.external_ocr_service import external_ocr_service
    from app.services.ocr_llm_service import ocr_llm_service
    
    # Check service availability
    ocr_available = await external_ocr_service.health_check()
    llm_available = await ocr_llm_service.health_check()
    
    service_info = {
        "ocr_service": {
            "service_name": "Vision World OCR API",
            "base_url": external_ocr_service.base_url,
            "endpoint": external_ocr_service.endpoint,
            "status": "available" if ocr_available else "unavailable",
            "timeout_seconds": external_ocr_service.timeout,
            "description": "External OCR service for text extraction from images"
        },
        "llm_service": {
            "service_name": "Pathumma Vision OCR LLM",
            "base_url": ocr_llm_service.base_url,
            "endpoint": ocr_llm_service.endpoint,
            "status": "available" if llm_available else "unavailable",
            "timeout_seconds": ocr_llm_service.timeout,
            "default_model": ocr_llm_service.default_model,
            "default_prompt": ocr_llm_service.default_prompt,
            "description": "LLM service for enhanced text extraction and correction"
        }
    }
    
    return service_info


# --- STREAMING ENDPOINTS ---

@router.post(
    "/ocr/process-pdf-stream",
    response_model=PDFOCRResponse,
    summary="Process PDF for OCR with Streaming (Async)",
    description="Upload a PDF file for asynchronous OCR processing with real-time streaming updates. Returns a task ID that can be used to connect to the streaming endpoint.",
    responses={
        200: {"description": "PDF OCR streaming task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_stream_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process a PDF file for OCR with streaming support.
    
    Args:
        request: JSON string containing PDF OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFOCRResponse: Task information with unique ID for streaming
    """
    import json
    
    try:
        # Parse PDF OCR request or use defaults if empty
        if request_data:
            pdf_request = PDFOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_request = PDFOCRRequest()
        
        logger.info(
            f"Received streaming PDF OCR request for {file.filename} "
            f"with threshold: {pdf_request.threshold}, contrast: {pdf_request.contrast_level}, "
            f"dpi: {pdf_request.dpi}"
        )
        
        # Process PDF with streaming
        response = await ocr_controller.process_pdf_with_streaming(file, pdf_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Streaming PDF OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Streaming processing failed: {str(e)}"
        )


@router.post(
    "/ocr/process-pdf-with-llm-stream",
    response_model=PDFLLMOCRResponse,
    summary="Process PDF for LLM-enhanced OCR with Streaming (Async)",
    description="Upload a PDF file for asynchronous LLM-enhanced OCR processing with real-time streaming updates. Returns a task ID that can be used to connect to the streaming endpoint.",
    responses={
        200: {"description": "PDF LLM OCR streaming task created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file or parameters"},
        413: {"model": ErrorResponse, "description": "File too large or too many pages"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute")
async def process_pdf_with_llm_stream_async(
    request_data: str = Form(None, alias="request"),
    file: UploadFile = File(..., description="PDF file to process (max 10 pages)"),
    request: Request = None
):
    """
    Process a PDF file for LLM-enhanced OCR with streaming support.
    
    Args:
        request: JSON string containing PDF LLM OCR parameters
        file: Uploaded PDF file
        
    Returns:
        PDFLLMOCRResponse: Task information with unique ID for streaming
    """
    import json
    
    try:
        # Parse PDF LLM OCR request or use defaults if empty
        if request_data:
            pdf_llm_request = PDFLLMOCRRequest.parse_raw(request_data)
        else:
            # Use default values when request is empty
            pdf_llm_request = PDFLLMOCRRequest()
        
        logger.info(
            f"Received streaming PDF LLM OCR request for {file.filename} "
            f"with threshold: {pdf_llm_request.threshold}, contrast: {pdf_llm_request.contrast_level}, "
            f"dpi: {pdf_llm_request.dpi}, prompt: {pdf_llm_request.prompt}, model: {pdf_llm_request.model}"
        )
        
        # Process PDF with LLM and streaming
        response = await ocr_controller.process_pdf_with_llm_streaming(file, pdf_llm_request)
        
        return response
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON in request parameter"
        )
    except Exception as e:
        logger.error(f"Streaming PDF LLM OCR processing request failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Streaming LLM processing failed: {str(e)}"
        )


@router.get(
    "/ocr/stream/{task_id}",
    summary="Stream PDF processing progress",
    description="Connect to real-time streaming updates for PDF processing. Uses Server-Sent Events (SSE) to provide live progress updates.",
    responses={
        200: {"description": "Streaming connection established", "content": {"text/event-stream": {}}},
        404: {"model": ErrorResponse, "description": "Task not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
@limiter.limit("10/minute")  # Lower rate limit for streaming connections
async def stream_pdf_progress(request: Request, task_id: str):
    """
    Stream real-time progress updates for PDF processing.
    
    This endpoint provides Server-Sent Events (SSE) for monitoring PDF processing progress.
    It provides both incremental updates (latest_page_result) and complete state (cumulative_results).
    
    Args:
        task_id: Unique task identifier from the streaming processing request
        
    Returns:
        StreamingResponse: Server-Sent Events stream with progress updates
        
    Example stream data formats:
        ```
        // Type 1: Page completion update
        data: {
            "task_id": "12345...",
            "status": "page_completed",
            "current_page": 2,
            "total_pages": 5,
            "processed_pages": 2,
            "latest_page_result": { ... },      // Single page result
            "cumulative_results": [ ... ],      // All pages processed so far
            "progress_percentage": 40.0,
            "estimated_time_remaining": 6.3,
            "processing_speed": 0.48
        }
        
        // Type 2: Final completion
        data: {
            "task_id": "12345...",
            "status": "completed",
            "current_page": 5,
            "total_pages": 5,
            "processed_pages": 5,
            "cumulative_results": [ ... ],      // All final results
            "progress_percentage": 100.0
        }
        ```
    """
    try:
        logger.debug(f"Starting stream connection for task {task_id}")
        
        # Create streaming response
        return StreamingResponse(
            ocr_controller.stream_pdf_progress(task_id),
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
        logger.error(f"Failed to start stream for task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start streaming connection: {str(e)}"
        ) 