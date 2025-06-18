"""
Request ID middleware for tracking requests across the application.
"""

import uuid
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger_config import set_request_id, get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID tracking and performance logging."""
    
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with ID tracking and performance monitoring.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response with request ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get(self.header_name, str(uuid.uuid4()))
        
        # Set request ID in context for logging
        set_request_id(request_id)
        
        # Log request start
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        logger.info(
            f"REQ START: {request.method} {request.url.path} "
            f"client={client_ip} user_agent={request.headers.get('user-agent', 'N/A')[:100]}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log request completion
            logger.info(
                f"REQ END: {request.method} {request.url.path} "
                f"status={response.status_code} duration={processing_time:.3f}s"
            )
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            return response
            
        except Exception as e:
            # Log request failure
            processing_time = time.time() - start_time
            logger.error(
                f"REQ ERROR: {request.method} {request.url.path} "
                f"error={str(e)} duration={processing_time:.3f}s"
            )
            raise 