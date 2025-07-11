"""
Remote HTTP client for testing deployed instances.
"""

import httpx
import json
from typing import Optional, Dict, Any, BinaryIO, Union
import asyncio
from pathlib import Path

from tests.remote_test_config import RemoteTestConfig


class RemoteTestClient:
    """HTTP client for testing remote deployed instances."""
    
    def __init__(self, base_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """Initialize the remote test client."""
        self.base_url = base_url or RemoteTestConfig.get_base_url()
        self.headers = headers or RemoteTestConfig.get_headers()
        self.timeout = RemoteTestConfig.get_timeout()
        
    def _prepare_url(self, path: str) -> str:
        """Prepare the full URL for a request."""
        # Remove leading slash from path if present
        path = path.lstrip("/")
        # Handle base URLs that already have a path (like /ocr-backend)
        if self.base_url.endswith("/"):
            return f"{self.base_url}{path}"
        else:
            return f"{self.base_url}/{path}"
    
    def get(self, path: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        with httpx.Client(timeout=self.timeout) as client:
            return client.get(url, headers=headers, **kwargs)
    
    def post(self, path: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(url, headers=headers, **kwargs)
    
    def put(self, path: str, **kwargs) -> httpx.Response:
        """Make a PUT request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        with httpx.Client(timeout=self.timeout) as client:
            return client.put(url, headers=headers, **kwargs)
    
    def delete(self, path: str, **kwargs) -> httpx.Response:
        """Make a DELETE request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        with httpx.Client(timeout=self.timeout) as client:
            return client.delete(url, headers=headers, **kwargs)
    
    def upload_file(
        self, 
        path: str, 
        file: Union[BinaryIO, Path, str], 
        field_name: str = "file",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Upload a file with optional additional form data."""
        url = self._prepare_url(path)
        headers = {**self.headers}
        
        files = {}
        data = {}
        
        # Handle file input
        if isinstance(file, (Path, str)):
            file_path = Path(file)
            files[field_name] = (file_path.name, open(file_path, "rb"), "application/octet-stream")
        else:
            # Assume it's already a file-like object
            files[field_name] = file
        
        # Add additional data if provided
        if additional_data:
            for key, value in additional_data.items():
                if isinstance(value, dict):
                    # Convert dict to JSON string for form data
                    data[key] = json.dumps(value)
                else:
                    data[key] = value
        
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(url, headers=headers, files=files, data=data)


class AsyncRemoteTestClient:
    """Async HTTP client for testing remote deployed instances."""
    
    def __init__(self, base_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        """Initialize the async remote test client."""
        self.base_url = base_url or RemoteTestConfig.get_base_url()
        self.headers = headers or RemoteTestConfig.get_headers()
        self.timeout = RemoteTestConfig.get_timeout()
        
    def _prepare_url(self, path: str) -> str:
        """Prepare the full URL for a request."""
        path = path.lstrip("/")
        if self.base_url.endswith("/"):
            return f"{self.base_url}{path}"
        else:
            return f"{self.base_url}/{path}"
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Make an async GET request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.get(url, headers=headers, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Make an async POST request."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.post(url, headers=headers, **kwargs)
    
    async def stream(self, path: str, **kwargs):
        """Stream responses from SSE endpoint."""
        url = self._prepare_url(path)
        headers = {**self.headers, **kwargs.get("headers", {})}
        headers["Accept"] = "text/event-stream"
        
        async with httpx.AsyncClient(timeout=None) as client:  # No timeout for streaming
            async with client.stream("GET", url, headers=headers, **kwargs) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line[6:]  # Remove "data: " prefix