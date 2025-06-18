"""
Pytest configuration and fixtures for OCR Backend API tests.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.ocr_models import OCRRequest, OCRResult


# Removed custom event_loop fixture to avoid deprecation warnings
# pytest-asyncio provides its own event loop management


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_ocr_request() -> OCRRequest:
    """Create a sample OCR request for testing."""
    return OCRRequest(
        threshold=128,
        contrast_level=1.0
    )


@pytest.fixture
def sample_ocr_result() -> OCRResult:
    """Create a sample OCR result for testing."""
    return OCRResult(
        success=True,
        extracted_text="Sample extracted text from image",
        processing_time=1.23,
        threshold_used=128,
        contrast_level_used=1.0
    )


@pytest.fixture
def sample_image_path() -> Generator[Path, None, None]:
    """Create a temporary sample image for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        # Create a simple test image
        image = Image.new('RGB', (100, 50), color='white')
        image.save(temp_file.name, 'JPEG')
        
        yield Path(temp_file.name)
        
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def mock_external_ocr_service():
    """Mock the external OCR service for testing."""
    mock_service = MagicMock()
    
    # Mock successful processing
    mock_service.process_image = AsyncMock(return_value=OCRResult(
        success=True,
        extracted_text="Mock extracted text",
        processing_time=1.0,
        threshold_used=128,
        contrast_level_used=1.0
    ))
    
    # Mock validation
    mock_service.validate_image = AsyncMock(return_value=True)
    
    # Mock health check
    mock_service.health_check = AsyncMock(return_value=True)
    
    return mock_service


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing external API calls."""
    with httpx.AsyncClient() as client:
        mock_client = AsyncMock(spec=client)
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "Mock extracted text"
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def invalid_image_path() -> Generator[Path, None, None]:
    """Create a temporary invalid image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(b"This is not an image file")
        
        yield Path(temp_file.name)
        
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def large_image_path() -> Generator[Path, None, None]:
    """Create a temporary large image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        # Create a large test image
        image = Image.new('RGB', (5000, 5000), color='white')
        image.save(temp_file.name, 'JPEG')
        
        yield Path(temp_file.name)
        
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True) 