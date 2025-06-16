# External OCR API Integration

This document describes the integration with the Vision World OCR API for text extraction from images.

## Overview

The OCR Backend API has been updated to use an external OCR service instead of local OCR processing. This provides better scalability and removes the dependency on local OCR engines like Tesseract.

## External API Details

### Vision World OCR API
- **Base URL**: `http://203.185.131.205/vision-world`
- **Endpoint**: `/process-image`
- **Method**: POST
- **Content-Type**: `application/json`

### Request Format

```json
{
  "image": "base64_encoded_image_data",
  "threshold": 128,
  "contrast_level": 1.0
}
```

### Response Format

The API returns a simple string containing the extracted text:

```json
"Extracted text from the image"
```

## Implementation

### Service Architecture

```
Client Request → FastAPI Router → OCR Controller → External OCR Service → Vision World API
```

### Key Components

1. **External OCR Service** (`app/services/external_ocr_service.py`)
   - Handles communication with the Vision World API
   - Converts images to base64 format
   - Manages HTTP requests and error handling
   - Provides health check functionality

2. **OCR Controller** (`app/controllers/ocr_controller.py`)
   - Business logic for OCR processing
   - Task management for async operations
   - File validation and cleanup
   - Error handling and logging

3. **API Models** (`app/models/ocr_models.py`)
   - Updated to match external API requirements
   - Simplified parameter structure
   - Removed local OCR-specific options

### Configuration

Environment variables for external OCR service:

```bash
# External OCR API Settings
EXTERNAL_OCR_BASE_URL=http://203.185.131.205/vision-world
EXTERNAL_OCR_ENDPOINT=/process-image
EXTERNAL_OCR_TIMEOUT=30

# OCR Processing Settings
DEFAULT_THRESHOLD=128
DEFAULT_CONTRAST_LEVEL=1.0
```

## API Changes

### Updated Endpoints

All OCR processing endpoints now use the external API:

- `POST /v1/ocr/process` - Async processing
- `POST /v1/ocr/process-sync` - Sync processing

### Request Parameters

The API now accepts two main parameters:

1. **threshold** (integer, 0-255)
   - Controls image binarization
   - Default: 128
   - Lower values for darker images, higher for lighter images

2. **contrast_level** (float, 0.1-5.0)
   - Controls contrast enhancement
   - Default: 1.0
   - Values >1.0 increase contrast, <1.0 decrease contrast

### Example Usage

#### Synchronous Processing

```bash
curl -X POST "http://localhost:8000/v1/ocr/process-sync" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F 'request={"threshold": 128, "contrast_level": 1.0}'
```

#### Asynchronous Processing

```bash
# Submit task
curl -X POST "http://localhost:8000/v1/ocr/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F 'request={"threshold": 128, "contrast_level": 1.0}'

# Response
{
  "task_id": "unique-task-id",
  "status": "processing",
  "created_at": "2024-01-01T12:00:00Z"
}

# Check status
curl -X GET "http://localhost:8000/v1/ocr/tasks/unique-task-id"
```

## Error Handling

The service handles various error scenarios:

### External API Errors

1. **Timeout Errors**
   - HTTP request timeout (default: 30 seconds)
   - Returns 500 with timeout message

2. **HTTP Errors**
   - 4xx/5xx responses from external API
   - Returns 500 with error details

3. **Network Errors**
   - Connection failures
   - DNS resolution issues
   - Returns 500 with network error message

### File Validation Errors

1. **Invalid File Format**
   - Unsupported image formats
   - Returns 400 with format error

2. **File Size Limits**
   - Files exceeding maximum size
   - Returns 413 with size limit message

3. **Corrupted Files**
   - Invalid image data
   - Returns 400 with validation error

## Health Monitoring

### Service Health Check

The external OCR service provides health monitoring:

```bash
curl -X GET "http://localhost:8000/v1/ocr/service-info"
```

Response:
```json
{
  "service_name": "Vision World OCR API",
  "base_url": "http://203.185.131.205/vision-world",
  "endpoint": "/process-image",
  "status": "available",
  "timeout_seconds": 30,
  "description": "External OCR service for text extraction from images"
}
```

### Application Health Check

The main health check endpoint includes external service status:

```bash
curl -X GET "http://localhost:8000/health"
```

Response:
```json
{
  "status": "healthy",
  "environment": "development",
  "service": "OCR Backend API",
  "version": "0.1.0",
  "external_ocr_status": "available"
}
```

## Performance Considerations

### Async Processing

- Use async endpoints for large files or batch processing
- Task-based system allows monitoring of long-running operations
- Prevents request timeouts for slow OCR processing

### Concurrent Requests

- Service supports concurrent requests to external API
- Rate limiting prevents overwhelming the external service
- Connection pooling for efficient HTTP requests

### Caching

- Consider implementing response caching for identical images
- Cache health check results to reduce external API calls
- Implement request deduplication for concurrent identical requests

## Testing

### Unit Tests

- Mock external API responses
- Test error handling scenarios
- Validate request/response transformations

### Integration Tests

- Test actual API integration (with mocking for CI/CD)
- Verify end-to-end processing flow
- Test concurrent request handling

### Example Test

```python
@pytest.mark.asyncio
async def test_external_ocr_integration():
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.text = '"Extracted text"'
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await external_ocr_service.process_image(image_path, ocr_request)
        
        assert result.success is True
        assert result.extracted_text == "Extracted text"
```

## Migration Notes

### Changes from Local OCR

1. **Removed Dependencies**
   - pytesseract
   - opencv-python
   - numpy

2. **Added Dependencies**
   - httpx (for async HTTP requests)
   - requests (for sync HTTP requests)

3. **Configuration Changes**
   - Removed Tesseract-specific settings
   - Added external API configuration
   - Updated parameter validation

4. **API Changes**
   - Simplified parameter structure
   - Removed language and mode options
   - Added threshold and contrast parameters

### Backward Compatibility

- API endpoints remain the same
- Response format is unchanged
- Error handling maintains same HTTP status codes
- Task management system is preserved

## Troubleshooting

### Common Issues

1. **External API Unavailable**
   - Check network connectivity
   - Verify API endpoint URL
   - Check external service status

2. **Timeout Errors**
   - Increase timeout setting
   - Check image size and complexity
   - Monitor external API performance

3. **Authentication Errors**
   - Verify API credentials (if required)
   - Check API key configuration
   - Validate request headers

### Debugging

Enable debug logging to see detailed request/response information:

```bash
LOG_LEVEL=DEBUG
```

This will log:
- HTTP request details
- Response status and content
- Error stack traces
- Processing timing information

## Future Enhancements

### Potential Improvements

1. **Response Caching**
   - Cache results for identical images
   - Implement cache invalidation strategy
   - Use Redis for distributed caching

2. **Load Balancing**
   - Support multiple external API endpoints
   - Implement failover mechanisms
   - Add circuit breaker pattern

3. **Enhanced Monitoring**
   - Metrics collection for external API calls
   - Performance monitoring and alerting
   - Request/response logging for analytics

4. **Batch Processing**
   - Support for multiple image processing
   - Bulk upload and processing
   - Progress tracking for batch operations 