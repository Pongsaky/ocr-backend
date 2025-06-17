"""
Application configuration settings for OCR Backend API.
"""

import os
import json
from functools import lru_cache
from typing import List, Union

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # --- Application Core Settings ---
    APP_ID: str = os.getenv("APP_ID", "ocr-backend-api")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "OCR Backend API")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- FastAPI/Uvicorn Server Settings ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")

    # --- CORS Settings ---
    CORS_ORIGINS: List[str] = json.loads(
        os.getenv(
            "CORS_ORIGINS",
            '["http://localhost:3000","http://localhost:3001","http://127.0.0.1:3000"]'
        )
    )

    # --- Rate Limiting Settings ---
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

    # --- External OCR API Settings ---
    EXTERNAL_OCR_BASE_URL: str = os.getenv("EXTERNAL_OCR_BASE_URL", "http://203.185.131.205/vision-world")
    EXTERNAL_OCR_ENDPOINT: str = os.getenv("EXTERNAL_OCR_ENDPOINT", "/process-image")
    EXTERNAL_OCR_TIMEOUT: int = int(os.getenv("EXTERNAL_OCR_TIMEOUT", "30"))
    
    # --- OCR LLM API Settings ---
    OCR_LLM_BASE_URL: str = os.getenv("OCR_LLM_BASE_URL", "http://203.185.131.205/pathumma-vision-ocr")
    OCR_LLM_ENDPOINT: str = os.getenv("OCR_LLM_ENDPOINT", "/v1/chat/completions")
    OCR_LLM_TIMEOUT: int = int(os.getenv("OCR_LLM_TIMEOUT", "60"))
    OCR_LLM_MODEL: str = os.getenv("OCR_LLM_MODEL", "nectec/Pathumma-vision-ocr-lora-dev")
    OCR_LLM_DEFAULT_PROMPT: str = os.getenv("OCR_LLM_DEFAULT_PROMPT", "ข้อความในภาพนี้")
    
    # --- OCR Processing Settings ---
    DEFAULT_THRESHOLD: int = int(os.getenv("DEFAULT_THRESHOLD", "500"))
    DEFAULT_CONTRAST_LEVEL: float = float(os.getenv("DEFAULT_CONTRAST_LEVEL", "1.3"))
    IMAGE_MAX_SIZE: int = int(os.getenv("IMAGE_MAX_SIZE", "10485760"))  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = json.loads(
        os.getenv(
            "ALLOWED_IMAGE_EXTENSIONS",
            '["jpg","jpeg","png","bmp","tiff","webp"]'
        )
    )
    
    # --- PDF Processing Settings ---
    MAX_PDF_PAGES: int = int(os.getenv("MAX_PDF_PAGES", "10"))
    MAX_PDF_SIZE: int = int(os.getenv("MAX_PDF_SIZE", "52428800"))  # 50MB
    ALLOWED_PDF_EXTENSIONS: List[str] = json.loads(
        os.getenv(
            "ALLOWED_PDF_EXTENSIONS",
            '["pdf"]'
        )
    )
    PDF_DPI: int = int(os.getenv("PDF_DPI", "300"))  # For PDF to image conversion
    PDF_IMAGE_FORMAT: str = os.getenv("PDF_IMAGE_FORMAT", "PNG")
    PDF_BATCH_SIZE: int = int(os.getenv("PDF_BATCH_SIZE", "3"))  # Process images in batches

    # --- File Storage Settings ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", "./results")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    # --- Processing Settings ---
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 minutes
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hour

    # --- Logging Settings ---
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", 
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/ocr-backend.log")
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    class Config:
        """Pydantic model configuration."""
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    Ensures settings are loaded only once during application lifetime.
    
    Returns:
        Settings: The application settings instance
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings() 