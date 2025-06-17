"""
OCR router for API endpoints.
"""

from typing import Dict, List, Any

from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.logger_config import get_logger
from app.models.ocr_models import (
    OCRRequest, OCRResponse, OCRResult, ErrorResponse,
    OCRLLMRequest, OCRLLMResponse, OCRLLMResult
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
        },
        "supported_formats": settings.ALLOWED_IMAGE_EXTENSIONS,
        "max_file_size_bytes": settings.MAX_FILE_SIZE
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