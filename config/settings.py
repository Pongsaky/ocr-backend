"""
Application configuration settings for OCR Backend API.
"""

import os
import json
from functools import lru_cache
from typing import List, Union, Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
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
            '["*"]'
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
    OCR_LLM_API_KEY: Optional[str] = os.getenv("OCR_LLM_API_KEY", None)  # Optional API key
    
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
    
    # --- Image Processing & Scaling Settings ---
    MAX_IMAGE_PIXELS: int = int(os.getenv("MAX_IMAGE_PIXELS", "3000000"))  # 4M pixels for LLM context limit
    IMAGE_SCALING_QUALITY: int = int(os.getenv("IMAGE_SCALING_QUALITY", "95"))  # JPEG quality for scaled images
    IMAGE_SCALING_RESAMPLE: str = os.getenv("IMAGE_SCALING_RESAMPLE", "LANCZOS")  # Resampling algorithm
    ENABLE_IMAGE_SCALING: bool = os.getenv("ENABLE_IMAGE_SCALING", "True").lower() in ("true", "1", "t")
    
    # --- PDF Processing Settings ---
    MAX_PDF_PAGES: int = int(os.getenv("MAX_PDF_PAGES", "20"))
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

    # --- DOCX Processing Settings ---
    ENABLE_DOCX_PROCESSING: bool = os.getenv("ENABLE_DOCX_PROCESSING", "False").lower() in ("true", "1", "t")
    MAX_DOCX_SIZE: int = int(os.getenv("MAX_DOCX_SIZE", "26214400"))  # 25MB
    ALLOWED_DOCX_EXTENSIONS: List[str] = json.loads(
        os.getenv(
            "ALLOWED_DOCX_EXTENSIONS",
            '["docx"]'
        )
    )
    
    # --- LibreOffice Service Settings ---
    LIBREOFFICE_BASE_URL: str = os.getenv("LIBREOFFICE_BASE_URL", "http://localhost:8080")
    LIBREOFFICE_CONVERT_ENDPOINT: str = os.getenv("LIBREOFFICE_CONVERT_ENDPOINT", "/request")
    LIBREOFFICE_TIMEOUT: int = int(os.getenv("LIBREOFFICE_TIMEOUT", "30"))
    LIBREOFFICE_MAX_RETRIES: int = int(os.getenv("LIBREOFFICE_MAX_RETRIES", "3"))
    LIBREOFFICE_RETRY_DELAY: float = float(os.getenv("LIBREOFFICE_RETRY_DELAY", "1.0"))
    
    # --- File Storage Settings ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", "./results")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./tmp")  # Project-relative temp directory
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    # --- URL Download Settings ---
    ENABLE_URL_PROCESSING: bool = os.getenv("ENABLE_URL_PROCESSING", "True").lower() in ("true", "1", "t")
    URL_DOWNLOAD_CONNECT_TIMEOUT: int = int(os.getenv("URL_DOWNLOAD_CONNECT_TIMEOUT", "10"))  # 10 seconds
    URL_DOWNLOAD_READ_TIMEOUT: int = int(os.getenv("URL_DOWNLOAD_READ_TIMEOUT", "60"))  # 60 seconds  
    URL_DOWNLOAD_WRITE_TIMEOUT: int = int(os.getenv("URL_DOWNLOAD_WRITE_TIMEOUT", "60"))  # 60 seconds
    URL_DOWNLOAD_POOL_TIMEOUT: int = int(os.getenv("URL_DOWNLOAD_POOL_TIMEOUT", "60"))  # 60 seconds
    URL_DOWNLOAD_MAX_REDIRECTS: int = int(os.getenv("URL_DOWNLOAD_MAX_REDIRECTS", "5"))  # Max redirects
    URL_DOWNLOAD_USER_AGENT: str = os.getenv("URL_DOWNLOAD_USER_AGENT", "OCR-Backend/1.0 (+https://github.com/your-org/ocr-backend)")

    # --- Processing Settings ---
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 minutes
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hour

    # --- Logging Settings ---
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", 
        "%(asctime)s.%(msecs)03d - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - [%(request_id)s] %(message)s"
    )
    LOG_DATE_FORMAT: str = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/ocr-backend.log")
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "104857600"))  # 100MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "30"))  # 30 backups (3GB total)
    
    # Enhanced logging features
    LOG_ENABLE_COMPRESSION: bool = os.getenv("LOG_ENABLE_COMPRESSION", "True").lower() in ("true", "1", "t")
    LOG_ASYNC_ENABLED: bool = os.getenv("LOG_ASYNC_ENABLED", "True").lower() in ("true", "1", "t")
    LOG_SANITIZE_SENSITIVE: bool = os.getenv("LOG_SANITIZE_SENSITIVE", "True").lower() in ("true", "1", "t")
    LOG_QUEUE_SIZE: int = int(os.getenv("LOG_QUEUE_SIZE", "10000"))  # Async log queue size

    model_config = ConfigDict(case_sensitive=True)


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