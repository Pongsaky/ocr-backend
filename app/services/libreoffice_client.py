"""
LibreOffice HTTP Client for document conversion.

This module provides an HTTP client for communicating with a LibreOffice
headless service to convert DOCX documents to PDF format.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import aiofiles
import aiohttp
from aiohttp import ClientTimeout, ClientError, ClientResponseError

from config.settings import settings

logger = logging.getLogger(__name__)


class LibreOfficeConversionError(Exception):
    """Custom exception for LibreOffice conversion errors."""
    pass


class LibreOfficeClient:
    """
    HTTP client for LibreOffice document conversion service.
    
    Handles communication with a containerized LibreOffice service
    to convert DOCX documents to PDF format.
    """
    
    def __init__(self):
        """Initialize the LibreOffice client with configuration."""
        self.base_url = settings.LIBREOFFICE_BASE_URL.rstrip('/')
        self.convert_endpoint = settings.LIBREOFFICE_CONVERT_ENDPOINT
        self.timeout = settings.LIBREOFFICE_TIMEOUT
        self.max_retries = settings.LIBREOFFICE_MAX_RETRIES
        self.retry_delay = settings.LIBREOFFICE_RETRY_DELAY
        
        logger.info(f"LibreOffice client initialized with endpoint: {self.base_url}")
    
    async def health_check(self) -> bool:
        """
        Check if LibreOffice service is healthy and responsive.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            timeout = ClientTimeout(total=5.0)  # Quick health check
            async with aiohttp.ClientSession(timeout=timeout) as session:
                health_url = f"{self.base_url}/"
                async with session.get(health_url) as response:
                    if response.status == 200:
                        logger.debug("LibreOffice service health check passed")
                        return True
                    else:
                        logger.warning(f"LibreOffice service unhealthy: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"LibreOffice health check failed: {e}")
            return False
    
    async def convert_docx_to_pdf(
        self, 
        docx_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Convert DOCX file to PDF using LibreOffice service.
        
        Args:
            docx_path: Path to the input DOCX file
            output_path: Optional path for output PDF file
            
        Returns:
            Path: Path to the converted PDF file
            
        Raises:
            LibreOfficeConversionError: If conversion fails
            FileNotFoundError: If input file doesn't exist
        """
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")
        
        if output_path is None:
            output_path = docx_path.with_suffix('.pdf')
        
        logger.info(f"Converting DOCX to PDF: {docx_path} -> {output_path}")
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                await self._perform_conversion(docx_path, output_path)
                logger.info(f"✅ DOCX conversion successful: {output_path}")
                return output_path
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Conversion attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    break
        
        # All retries failed
        error_msg = f"DOCX conversion failed after {self.max_retries} attempts"
        if last_exception:
            error_msg += f": {last_exception}"
        
        logger.error(error_msg)
        raise LibreOfficeConversionError(error_msg)
    
    async def _perform_conversion(self, docx_path: Path, output_path: Path) -> None:
        """
        Perform the actual HTTP conversion request.
        
        Args:
            docx_path: Path to input DOCX file
            output_path: Path for output PDF file
            
        Raises:
            LibreOfficeConversionError: If conversion fails
        """
        timeout = ClientTimeout(total=self.timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Prepare multipart form data
            data = aiohttp.FormData()
            
            # Read and add the DOCX file
            async with aiofiles.open(docx_path, 'rb') as f:
                file_content = await f.read()
                data.add_field(
                    'file',
                    file_content,
                    filename=docx_path.name,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            
            # Add conversion parameters for libreofficedocker API
            data.add_field('convert-to', 'pdf')
            
            # Make the conversion request
            convert_url = f"{self.base_url}{self.convert_endpoint}"
            
            try:
                async with session.post(convert_url, data=data) as response:
                    await self._handle_conversion_response(response, output_path)
                    
            except ClientError as e:
                raise LibreOfficeConversionError(f"HTTP client error: {e}")
            except asyncio.TimeoutError:
                raise LibreOfficeConversionError(f"Conversion timeout after {self.timeout}s")
    
    async def _handle_conversion_response(
        self, 
        response: aiohttp.ClientResponse, 
        output_path: Path
    ) -> None:
        """
        Handle the HTTP response from LibreOffice service.
        
        Args:
            response: HTTP response from LibreOffice service
            output_path: Path where to save the converted PDF
            
        Raises:
            LibreOfficeConversionError: If response indicates failure
        """
        if response.status == 200:
            # Successful conversion - save PDF content
            pdf_content = await response.read()
            
            if len(pdf_content) == 0:
                raise LibreOfficeConversionError("Received empty PDF content")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save PDF file
            async with aiofiles.open(output_path, 'wb') as f:
                await f.write(pdf_content)
            
            logger.debug(f"Saved converted PDF: {output_path} ({len(pdf_content)} bytes)")
            
        elif response.status == 400:
            error_text = await response.text()
            raise LibreOfficeConversionError(f"Invalid request: {error_text}")
            
        elif response.status == 422:
            error_text = await response.text()
            raise LibreOfficeConversionError(f"Unsupported file format: {error_text}")
            
        elif response.status == 500:
            error_text = await response.text()
            raise LibreOfficeConversionError(f"LibreOffice service error: {error_text}")
            
        else:
            error_text = await response.text()
            raise LibreOfficeConversionError(
                f"Unexpected response status {response.status}: {error_text}"
            )
    
    async def get_service_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the LibreOffice service.
        
        Returns:
            Dict with service information or None if unavailable
        """
        try:
            timeout = ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                info_url = f"{self.base_url}/info"
                async with session.get(info_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Service info unavailable: {response.status}")
                        return None
                        
        except Exception as e:
            logger.warning(f"Failed to get service info: {e}")
            return None


# Singleton instance for use across the application
libreoffice_client = LibreOfficeClient() 