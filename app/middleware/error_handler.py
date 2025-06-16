"""
Error handling middleware for OCR Backend API.
"""

import traceback
from typing import Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

from app.logger_config import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """
    Register custom error handlers for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle HTTP exceptions.
        
        Args:
            request: The incoming request
            exc: The HTTP exception
            
        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            f"HTTP {exc.status_code} error at {request.url.path}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, 
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle Starlette HTTP exceptions.
        
        Args:
            request: The incoming request
            exc: The Starlette HTTP exception
            
        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            f"Starlette HTTP {exc.status_code} error at {request.url.path}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": str(exc.detail),
                "status_code": exc.status_code,
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, 
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle request validation errors.
        
        Args:
            request: The incoming request
            exc: The validation error
            
        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            f"Validation error at {request.url.path}: {exc.errors()}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "validation_errors": exc.errors()
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "Validation error",
                "status_code": 422,
                "path": str(request.url.path),
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(
        request: Request, 
        exc: RateLimitExceeded
    ) -> JSONResponse:
        """
        Handle rate limit exceeded errors.
        
        Args:
            request: The incoming request
            exc: The rate limit exception
            
        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            f"Rate limit exceeded at {request.url.path}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=429,
            content={
                "error": True,
                "message": "Rate limit exceeded. Please try again later.",
                "status_code": 429,
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """
        Handle value errors.
        
        Args:
            request: The incoming request
            exc: The value error
            
        Returns:
            JSONResponse: Error response
        """
        logger.error(
            f"Value error at {request.url.path}: {str(exc)}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": f"Invalid value: {str(exc)}",
                "status_code": 400,
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle all other unhandled exceptions.
        
        Args:
            request: The incoming request
            exc: The exception
            
        Returns:
            JSONResponse: Error response
        """
        # Log the full traceback for debugging
        error_traceback = traceback.format_exc()
        logger.error(
            f"Unhandled exception at {request.url.path}: {str(exc)}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "traceback": error_traceback,
                "exception_type": type(exc).__name__
            }
        )
        
        # Don't expose internal error details in production
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error. Please try again later.",
                "status_code": 500,
                "path": str(request.url.path)
            }
        )
    
    logger.info("Error handlers registered successfully") 