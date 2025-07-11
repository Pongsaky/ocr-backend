"""
Configuration for testing against remote deployed instances.

Usage:
    Set the environment variable REMOTE_API_URL to your deployed instance:
    export REMOTE_API_URL="https://your-deployed-api.com"
    
    Then run tests with:
    pytest tests/ --remote
"""

import os
from typing import Optional


class RemoteTestConfig:
    """Configuration for remote testing."""
    
    @staticmethod
    def get_remote_url() -> Optional[str]:
        """Get the remote API URL from environment variable."""
        return os.environ.get("REMOTE_API_URL")
    
    @staticmethod
    def is_remote_testing() -> bool:
        """Check if we're testing against a remote instance."""
        return bool(RemoteTestConfig.get_remote_url())
    
    @staticmethod
    def get_base_url() -> str:
        """Get the base URL for testing (remote or local)."""
        remote_url = RemoteTestConfig.get_remote_url()
        if remote_url:
            # Remove trailing slash if present
            return remote_url.rstrip("/")
        return "http://localhost:8000"
    
    @staticmethod
    def get_headers() -> dict:
        """Get headers for remote API calls (e.g., API keys if needed)."""
        headers = {}
        
        # Add API key if provided
        api_key = os.environ.get("REMOTE_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Add any other custom headers
        custom_headers = os.environ.get("REMOTE_API_HEADERS")
        if custom_headers:
            # Format: "Header1:Value1,Header2:Value2"
            for header_pair in custom_headers.split(","):
                if ":" in header_pair:
                    key, value = header_pair.split(":", 1)
                    headers[key.strip()] = value.strip()
        
        return headers
    
    @staticmethod
    def get_timeout() -> float:
        """Get timeout for remote API calls."""
        return float(os.environ.get("REMOTE_API_TIMEOUT", "30.0"))