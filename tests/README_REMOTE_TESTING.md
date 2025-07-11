# Remote Deployment Testing Guide

This guide explains how to run your unit tests against a deployed OCR backend instance instead of localhost:8000.

## Quick Start

### 1. Basic Remote Testing

```bash
# Set the remote API URL
export REMOTE_API_URL="https://your-deployed-api.com"

# Run all tests against the remote instance
pytest tests/

# Run specific test file
pytest tests/test_remote_deployment.py

# Run original unit tests against remote
pytest tests/unit/test_pdf_ocr_service.py
```

### 2. With Authentication

```bash
# If your deployed API requires authentication
export REMOTE_API_URL="https://your-deployed-api.com"
export REMOTE_API_KEY="your-api-key"

# Run tests
pytest tests/
```

### 3. With Custom Headers

```bash
# Add custom headers if needed
export REMOTE_API_URL="https://your-deployed-api.com"
export REMOTE_API_HEADERS="X-Custom-Header:value1,X-Another-Header:value2"

# Run tests
pytest tests/
```

### 4. Adjust Timeout for Slower Connections

```bash
# Set custom timeout (in seconds)
export REMOTE_API_URL="https://your-deployed-api.com"
export REMOTE_API_TIMEOUT="60.0"  # 60 seconds

# Run tests
pytest tests/
```

## How It Works

1. **Automatic Client Selection**: When `REMOTE_API_URL` is set, the `client` fixture in `conftest.py` automatically returns a `RemoteTestClient` instead of the local `TestClient`.

2. **Compatibility**: Most existing tests will work without modification because the `RemoteTestClient` implements the same interface as FastAPI's `TestClient`.

3. **Remote-Specific Tests**: Use the `tests/test_remote_deployment.py` file as an example of tests specifically designed for remote testing.

## Writing Tests for Remote Deployment

### Using the Standard Client Fixture

```python
def test_health_check(client):
    """This test works for both local and remote testing."""
    response = client.get("/health")
    assert response.status_code == 200
```

### Using Remote-Specific Fixtures

```python
def test_remote_only_feature(remote_client):
    """This test always uses the remote client."""
    response = remote_client.get("/health")
    assert response.status_code == 200
```

### Async Remote Testing

```python
@pytest.mark.asyncio
async def test_streaming(async_remote_client):
    """Test streaming endpoints."""
    async for update in async_remote_client.stream("/v1/ocr/stream/task-id"):
        print(update)
```

## Limitations and Considerations

1. **File Uploads**: File upload tests work but may be slower due to network latency.

2. **Mocking**: Tests that rely on mocking internal services won't work against remote deployments. Consider creating separate test suites for:
   - Unit tests (run locally with mocks)
   - Integration tests (run against deployed instances)

3. **Database State**: Remote tests run against the actual deployed database. Be careful not to pollute production data.

4. **Rate Limiting**: Deployed instances may have rate limiting. Tests might need to be adjusted to handle rate limit responses.

## Example Test Scenarios

### 1. Test PDF Processing with Page Selection

```python
def test_pdf_with_pages(client):
    """Test PDF processing on remote deployment."""
    with open("test.pdf", "rb") as f:
        response = client.post(
            "/v1/ocr/process-stream",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"request": json.dumps({
                "mode": "basic",
                "pdf_config": {"page_select": [1, 3, 5]}
            })}
        )
    assert response.status_code == 200
```

### 2. Test Different Endpoints

```python
# The client fixture automatically handles local vs remote
def test_multiple_endpoints(client):
    # Health check
    assert client.get("/health").status_code == 200
    
    # API version
    assert client.get("/v1/version").status_code == 200
    
    # Process image
    with open("test.jpg", "rb") as f:
        response = client.post("/v1/ocr/process-stream", files={"file": f})
        assert response.status_code == 200
```

## Troubleshooting

1. **Connection Errors**: Ensure the remote URL is accessible and includes the protocol (https://)

2. **Authentication Failures**: Verify your API key is correct and properly formatted

3. **Timeout Issues**: Increase `REMOTE_API_TIMEOUT` for slow connections or large file uploads

4. **SSL Errors**: For self-signed certificates, you may need to disable SSL verification (not recommended for production)

## CI/CD Integration

```yaml
# Example GitHub Actions workflow
test-remote:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
    - name: Install dependencies
      run: poetry install
    - name: Run remote tests
      env:
        REMOTE_API_URL: ${{ secrets.DEPLOYED_API_URL }}
        REMOTE_API_KEY: ${{ secrets.API_KEY }}
      run: |
        poetry run pytest tests/test_remote_deployment.py -v
```