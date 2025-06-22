"""
Main FastAPI application for OCR Backend API.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# --- Core Application Imports ---
from config.settings import get_settings
from app.logger_config import setup_logger, set_request_id
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_id import RequestIDMiddleware

# --- Router Imports ---
from app.routers import ocr_router
from app.routers import unified_router

# --- Initialize Settings and Logger ---
settings = get_settings()
logger = setup_logger(__name__)

logger.info(f"Starting {settings.PROJECT_NAME} in {settings.APP_ENV} mode...")

# --- Create required directories ---
def create_directories():
    """Create required directories for file storage."""
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)
    logger.info("Required directories created/verified")


# --- Application Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager (replaces deprecated startup/shutdown events).
    """
    # Startup
    logger.info("Application startup initiated...")
    create_directories()
    logger.info("Application startup complete.")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown initiated...")
    # Add cleanup logic here if needed
    await asyncio.sleep(0.1)  # Small delay for tasks to finish
    logger.info("Application shutdown complete.")

# --- Initialize FastAPI App ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="A FastAPI-based backend service for Optical Character Recognition (OCR) processing",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path="/ocr-backend",
    lifespan=lifespan
)

# --- Configure CORS ---
logger.info("Configuring CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Configure Rate Limiter ---
logger.info("Configuring rate limiter...")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}minute"]
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Register Custom Error Handlers and Middleware ---
register_error_handlers(app)

# --- Add Request ID Middleware ---
logger.info("Adding request ID middleware...")
app.add_middleware(RequestIDMiddleware)

# --- Include Routers ---
logger.info("Including API routers...")
app.include_router(unified_router.router, prefix="/v1", tags=["🌟 Unified OCR"])
app.include_router(ocr_router.router, prefix="/v1", tags=["📄 Legacy OCR"])

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing a welcome message."""
    logger.debug("Root endpoint accessed.")
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME}!",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "healthy"
    }

# --- Health Check Endpoint ---
@app.get("/health", tags=["Health"])
async def health_check():
    """Provides basic health status of the API."""
    logger.debug("Health check endpoint accessed.")
    
    # Check external services
    from app.services.external_ocr_service import external_ocr_service
    from app.services.ocr_llm_service import ocr_llm_service
    
    external_ocr_status = "available" if await external_ocr_service.health_check() else "unavailable"
    llm_service_status = "available" if await ocr_llm_service.health_check() else "unavailable"
    
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "external_ocr_status": external_ocr_status,
        "llm_service_status": llm_service_status
    }

# --- Deprecated Event Handlers Removed ---
# Replaced with lifespan context manager above

# --- Direct Run Configuration (for development/debugging) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Running application directly using Uvicorn...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    ) 