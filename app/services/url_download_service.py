"""
URL download service for OCR file processing.
Handles secure downloading of files from URLs with validation and size limits.
Supports Images and PDFs only (DOCX is disabled).
"""

import asyncio
import tempfile
import aiofiles
import httpx
from pathlib import Path
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse, unquote

from app.logger_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class URLDownloadError(Exception):
    """Custom exception for URL download errors."""
    pass


class URLDownloadService:
    """Service for downloading files from URLs with validation and security."""
    
    # Supported MIME types for URL downloads (Images and PDFs only)
    SUPPORTED_MIME_TYPES = {
        # Images
        "image/jpeg", "image/jpg", "image/png", 
        "image/bmp", "image/tiff", "image/webp",
        # PDFs
        "application/pdf"
        # DOCX explicitly excluded
    }
    
    # File size limits based on file type
    SIZE_LIMITS = {
        "image": 10 * 1024 * 1024,  # 10MB for images
        "pdf": 50 * 1024 * 1024,    # 50MB for PDFs
    }
    
    def __init__(self):
        self.client_timeout = httpx.Timeout(
            connect=settings.URL_DOWNLOAD_CONNECT_TIMEOUT,
            read=settings.URL_DOWNLOAD_READ_TIMEOUT,
            write=settings.URL_DOWNLOAD_WRITE_TIMEOUT,
            pool=settings.URL_DOWNLOAD_POOL_TIMEOUT
        )
        
    async def download_file(
        self, 
        url: str, 
        task_id: str
    ) -> Tuple[Path, Dict[str, any]]:
        """
        Download file from URL with validation and security checks.
        
        Args:
            url: URL to download from
            task_id: Unique task identifier for file organization
            
        Returns:
            Tuple[Path, Dict]: Downloaded file path and metadata
            
        Raises:
            URLDownloadError: If download fails or file is not supported
        """
        logger.info(f"🌐 Starting URL download: {url} for task {task_id}")
        
        # Create task-specific temp directory
        temp_dir = Path(settings.TEMP_DIR) / f"url_downloads_{task_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with httpx.AsyncClient(
                timeout=self.client_timeout,
                follow_redirects=True,
                max_redirects=settings.URL_DOWNLOAD_MAX_REDIRECTS,
                headers={
                    "User-Agent": settings.URL_DOWNLOAD_USER_AGENT
                }
            ) as client:
                # First, make a HEAD request to check content type and size
                try:
                    head_response = await client.head(url)
                    content_type = head_response.headers.get("content-type", "").lower()
                    content_length = head_response.headers.get("content-length")
                    
                    logger.debug(f"📋 HEAD response - Content-Type: {content_type}, Length: {content_length}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ HEAD request failed, will try GET: {e}")
                    content_type = None
                    content_length = None
                
                # Validate content type if available
                if content_type:
                    if not self._is_supported_content_type(content_type):
                        raise URLDownloadError(
                            f"Unsupported content type: {content_type}. "
                            f"Supported types: Images (JPEG, PNG, BMP, TIFF, WebP) and PDF only."
                        )
                
                # Validate content length if available
                if content_length:
                    try:
                        size_bytes = int(content_length)
                        self._validate_file_size(size_bytes, content_type)
                    except ValueError:
                        logger.warning(f"⚠️ Invalid content-length header: {content_length}")
                
                # Download the file
                download_response = await client.get(url)
                download_response.raise_for_status()
                
                # Double-check content type from actual response
                actual_content_type = download_response.headers.get("content-type", "").lower()
                if actual_content_type and not self._is_supported_content_type(actual_content_type):
                    raise URLDownloadError(
                        f"Unsupported content type: {actual_content_type}. "
                        f"Supported types: Images (JPEG, PNG, BMP, TIFF, WebP) and PDF only."
                    )
                
                # Validate actual file size
                file_content = download_response.content
                actual_size = len(file_content)
                self._validate_file_size(actual_size, actual_content_type)
                
                # Generate filename from URL
                filename = self._generate_filename(url, actual_content_type)
                file_path = temp_dir / filename
                
                # Save file to disk
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file_content)
                
                # Create metadata
                metadata = {
                    "original_url": url,
                    "downloaded_filename": filename,
                    "file_size_bytes": actual_size,
                    "content_type": actual_content_type,
                    "download_success": True,
                    "temp_directory": str(temp_dir)
                }
                
                logger.info(
                    f"✅ URL download completed: {filename} "
                    f"({actual_size:,} bytes, {actual_content_type})"
                )
                
                return file_path, metadata
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            logger.error(f"❌ URL download failed: {error_msg}")
            raise URLDownloadError(error_msg)
            
        except httpx.TimeoutException:
            error_msg = "Download timeout - file may be too large or server too slow"
            logger.error(f"❌ URL download failed: {error_msg}")
            raise URLDownloadError(error_msg)
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"❌ URL download failed: {error_msg}")
            raise URLDownloadError(error_msg)
    
    def _is_supported_content_type(self, content_type: str) -> bool:
        """Check if content type is supported."""
        # Remove charset and other parameters
        main_type = content_type.split(';')[0].strip().lower()
        return main_type in self.SUPPORTED_MIME_TYPES
    
    def _validate_file_size(self, size_bytes: int, content_type: str) -> None:
        """Validate file size based on content type."""
        if content_type:
            main_type = content_type.split('/')[0].lower()
            if main_type in self.SIZE_LIMITS:
                max_size = self.SIZE_LIMITS[main_type]
                if size_bytes > max_size:
                    raise URLDownloadError(
                        f"File too large: {size_bytes:,} bytes. "
                        f"Maximum allowed for {main_type}: {max_size:,} bytes"
                    )
        
        # Fallback: use the larger PDF limit as maximum
        max_fallback_size = max(self.SIZE_LIMITS.values())
        if size_bytes > max_fallback_size:
            raise URLDownloadError(
                f"File too large: {size_bytes:,} bytes. "
                f"Maximum allowed: {max_fallback_size:,} bytes"
            )
    
    def _generate_filename(self, url: str, content_type: str) -> str:
        """Generate a filename from URL and content type."""
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        
        # Try to get filename from URL path
        if path and path != '/':
            potential_filename = Path(path).name
            if potential_filename and '.' in potential_filename:
                return potential_filename
        
        # Generate filename based on content type
        if content_type:
            main_type = content_type.split('/')[0].lower()
            sub_type = content_type.split('/')[1].split(';')[0].lower()
            
            if main_type == "image":
                if sub_type in ["jpeg", "jpg"]:
                    return "downloaded_image.jpg"
                elif sub_type == "png":
                    return "downloaded_image.png"
                elif sub_type == "bmp":
                    return "downloaded_image.bmp"
                elif sub_type == "tiff":
                    return "downloaded_image.tiff"
                elif sub_type == "webp":
                    return "downloaded_image.webp"
            elif main_type == "application" and sub_type == "pdf":
                return "downloaded_document.pdf"
        
        # Fallback filename
        return "downloaded_file.bin"


# Global service instance
url_download_service = URLDownloadService() 