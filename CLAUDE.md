# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based OCR backend service that provides text extraction from images, PDFs, and DOCX files. It integrates with Vision World API and Pathumma Vision OCR LLM for enhanced text recognition, particularly for Thai language documents.

## Essential Commands

### Development
```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests with coverage
poetry run python scripts/run_tests.py --coverage
# Alternative: python scripts/run_tests.py --coverage

# Run unit tests only (fast)
poetry run python scripts/run_tests.py --unit
# Alternative: python scripts/run_tests.py --unit

# Run integration tests
poetry run python scripts/run_tests.py --integration
# Alternative: python scripts/run_tests.py --integration

# Run specific test file
poetry run python scripts/run_tests.py --specific tests/unit/test_ocr_controller.py
# Alternative: python scripts/run_tests.py --specific tests/unit/test_ocr_controller.py

# Code formatting and linting
poetry run black app tests
poetry run isort app tests
poetry run flake8 app tests
poetry run mypy app
```

### Docker Deployment
```bash
# Timestamped deployment (recommended for development)
./scripts/launch_with_timestamp.sh

# Production deployment
./scripts/deploy_production.sh

# Build and push Docker image
./scripts/build_and_push.sh -r registry.com -t v1.0.0
```

## Architecture and Code Organization

### Service-Oriented Architecture
The codebase follows a clean layered architecture:
- **Routers** (`app/routers/`): Define API endpoints, handle HTTP requests/responses
- **Controllers** (`app/controllers/`): Business logic layer, orchestrate services
- **Services** (`app/services/`): External integrations (OCR APIs, PDF/DOCX processing)
- **Models** (`app/models/`): Pydantic models for validation and serialization
- **Utils** (`app/utils/`): Shared utilities (image processing, validators)

### Key Design Patterns
1. **Async-First**: All operations are async using `async/await`
2. **Dependency Injection**: Use FastAPI's `Depends()` for service injection
3. **Task-Based Processing**: Background tasks with status tracking via task IDs
4. **Unified Interface**: New unified API (`/v1/unified/*`) handles all file types

### API Endpoints Structure
Main endpoints:
1. **POST** `/v1/ocr/process-stream` - Create OCR processing task (supports PDF page selection and text streaming)
2. **GET** `/v1/ocr/process-stream/{task_id}` - Get task status and results
3. **GET** `/v1/ocr/stream/{task_id}` - Server-sent events endpoint for real-time streaming updates
4. **POST** `/v1/ocr/tasks/{task_id}/cancel` - Cancel running task

#### PDF Page Selection Feature
The unified API now supports selective PDF page processing:
- **Field**: `pdf_config.page_select` - Array of 1-indexed page numbers
- **Validation**: Pages must exist, no duplicates, automatically sorted
- **Default**: Processes all pages if not specified
- **Examples**: `[1]`, `[1, 3, 5]`, `[2, 4, 6, 8, 10]`

#### Real-time Text Streaming Feature
The API supports character-by-character text streaming for LLM-enhanced OCR:
- **Field**: `stream` - Boolean flag to enable streaming (default: false)
- **Works with**: Both images and PDFs in `llm_enhanced` mode
- **Benefits**: Immediate feedback as text is generated, better UX for long documents
- **Endpoint**: Connect to `/v1/ocr/stream/{task_id}` for Server-Sent Events

### External Service Integration
1. **Vision World API**: Standard OCR processing (`VISION_WORLD_API_URL` env var)
2. **Pathumma Vision LLM**: Enhanced OCR with LLM (`PATHUMMA_*` env vars)
3. **DOCX Processing**: Currently disabled (will return error message when attempting to process DOCX files)

### Error Handling and Logging
- Custom middleware for consistent error responses (`app/middleware/error_handler.py`)
- Request ID tracking for debugging (`app/middleware/request_id.py`)
- Enhanced logging with rotation (`app/logger_config.py`)
- All errors return standardized JSON responses with request IDs

### Testing Strategy
- **Unit Tests**: Test individual components in isolation (controllers, services)
- **Integration Tests**: Test full API endpoints with mocked external services
- Test files mirror source structure: `tests/unit/` and `tests/integration/`
- Use `pytest.mark.asyncio` for async test functions
- Mock external services using `unittest.mock` or `pytest-mock`

### Environment Configuration
Key environment variables (see `.env.example`):
- `VISION_WORLD_API_URL`: OCR service endpoint
- `PATHUMMA_VISION_API_KEY`: LLM service authentication
- `ENABLE_DOCX_PROCESSING`: Feature flag for DOCX support (currently disabled)
- `MAX_IMAGE_SIZE_MB`: Upload size limit
- `RATE_LIMIT_CALLS`/`RATE_LIMIT_PERIOD`: API rate limiting

### Development Workflow
1. Create feature branch from `main`
2. Implement changes following existing patterns
3. Add/update tests for new functionality
4. Run tests and ensure coverage doesn't drop
5. Format code with black/isort before committing
6. Update API documentation if endpoints change

### Performance Considerations
- Image scaling for LLM processing (1024px max dimension)
- Batch processing for multi-page PDFs
- PDF page selection for reduced processing time and costs
- Connection pooling for external APIs
- Async file operations with `aiofiles`
- Server-sent events for real-time status updates
- Character-by-character text streaming reduces perceived wait time

## API Usage Examples

### Text Streaming

#### Enable Streaming for Images
```bash
# Process image with real-time text streaming
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@image.jpg" \
  -F "request={
    'mode': 'llm_enhanced',
    'stream': true,
    'prompt': 'Extract all text from this image'
  }"

# Connect to streaming endpoint for real-time updates
curl -N "http://localhost:8000/v1/ocr/stream/{task_id}"
```

#### Enable Streaming for PDFs
```bash
# Process PDF with text streaming and page selection
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@document.pdf" \
  -F "request={
    'mode': 'llm_enhanced',
    'stream': true,
    'pdf_config': {
      'page_select': [1, 3, 5]
    }
  }"
```

#### Comprehensive Streaming Response Examples

When `stream: true`, the SSE endpoint provides many different types of responses during processing:

##### 1. Initial Processing Updates
```json
// Upload completed, starting processing
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "validation",
  "progress_percentage": 5.0,
  "current_page": 0,
  "total_pages": 3,
  "timestamp": "2024-01-15T10:30:01Z"
}

// Starting OCR on first page
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "ocr_processing",
  "progress_percentage": 15.0,
  "current_page": 1,
  "total_pages": 3,
  "timestamp": "2024-01-15T10:30:03Z"
}
```

##### 2. Real-time Text Streaming (Character-by-Character)
```json
// LLM starts generating text
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 1,
  "text_chunk": "ข",
  "accumulated_text": "ข",
  "timestamp": "2024-01-15T10:30:05Z"
}

data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 1,
  "text_chunk": "้",
  "accumulated_text": "ข้",
  "timestamp": "2024-01-15T10:30:05Z"
}

data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 1,
  "text_chunk": "อ",
  "accumulated_text": "ข้อ",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

##### 3. Page Completion Updates
```json
// First page completed
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "page_completed",
  "current_step": "ocr_processing",
  "progress_percentage": 33.3,
  "current_page": 1,
  "total_pages": 3,
  "processed_pages": 1,
  "failed_pages": 0,
  "latest_page_result": {
    "page_number": 1,
    "extracted_text": "ข้อความจากหน้าที่ 1...",
    "processing_time": 2.5,
    "success": true,
    "threshold_used": 500,
    "contrast_level_used": 1.3,
    "image_processing_time": 1.2,
    "llm_processing_time": 1.3,
    "model_used": "nectec/Pathumma-vision-ocr-lora-dev",
    "timestamp": "2024-01-15T10:30:07Z"
  },
  "cumulative_results": [
    {
      "page_number": 1,
      "extracted_text": "ข้อความจากหน้าที่ 1...",
      "processing_time": 2.5,
      "success": true,
      "threshold_used": 500,
      "contrast_level_used": 1.3
    }
  ],
  "estimated_time_remaining": 12.5,
  "processing_speed": 0.4,
  "timestamp": "2024-01-15T10:30:07Z"
}
```

##### 4. Progress During Multi-Page Processing
```json
// Starting page 2
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "image_extraction", 
  "progress_percentage": 45.0,
  "current_page": 2,
  "total_pages": 3,
  "processed_pages": 1,
  "timestamp": "2024-01-15T10:30:08Z"
}

// Text streaming for page 2
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 2,
  "text_chunk": "เ",
  "accumulated_text": "เ",
  "timestamp": "2024-01-15T10:30:10Z"
}
```

##### 5. Final Completion Response
```json
// All processing completed
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "completed",
  "current_step": "completed",
  "progress_percentage": 100.0,
  "current_page": 3,
  "total_pages": 3,
  "processed_pages": 3,
  "failed_pages": 0,
  "cumulative_results": [
    {
      "page_number": 1,
      "extracted_text": "ข้อความจากหน้าที่ 1...",
      "processing_time": 2.5,
      "success": true
    },
    {
      "page_number": 2,
      "extracted_text": "เนื้อหาจากหน้าที่ 2...",
      "processing_time": 2.8,
      "success": true
    },
    {
      "page_number": 3,
      "extracted_text": "ข้อมูลจากหน้าที่ 3...",
      "processing_time": 2.1,
      "success": true
    }
  ],
  "processing_speed": 0.43,
  "timestamp": "2024-01-15T10:30:15Z"
}
```

##### 6. Error Handling During Streaming
```json
// Page processing failed
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "current_step": "ocr_processing",
  "progress_percentage": 66.7,
  "current_page": 2,
  "total_pages": 3,
  "processed_pages": 1,
  "failed_pages": 1,
  "latest_page_result": {
    "page_number": 2,
    "extracted_text": "",
    "processing_time": 1.2,
    "success": false,
    "error_message": "OCR processing failed for this page",
    "threshold_used": 500,
    "contrast_level_used": 1.3
  },
  "timestamp": "2024-01-15T10:30:12Z"
}

// Complete failure
data: {
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "failed",
  "current_step": "failed",
  "progress_percentage": 66.7,
  "processed_pages": 1,
  "failed_pages": 2,
  "error_message": "Processing failed: Unable to process remaining pages",
  "timestamp": "2024-01-15T10:30:13Z"
}
```

##### 7. Heartbeat Messages (Keep Connection Alive)
```json
// Periodic heartbeat to prevent connection timeout
data: {
  "heartbeat": true,
  "timestamp": "2024-01-15T10:30:10Z"
}
```

##### Key Differences with Streaming Enabled:
- **Text Chunks**: `text_chunk` and `accumulated_text` fields only appear when `stream: true`
- **Granular Updates**: More frequent updates during text generation
- **Character-level Feedback**: Each character appears as it's generated by the LLM
- **Real-time Progress**: Progress updates happen during text streaming, not just between pages
- **Multiple Event Types**: Processing, text streaming, page completion, and final completion events

### PDF Page Selection

#### Basic Usage
```bash
# Process specific pages (1, 3, 5) with basic OCR
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@document.pdf" \
  -F "request={
    'mode': 'basic',
    'pdf_config': {
      'page_select': [1, 3, 5]
    }
  }"
```

#### Advanced Usage with LLM Enhancement
```bash
# Process pages 2, 4, 6 with LLM enhancement
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@document.pdf" \
  -F "request={
    'mode': 'llm_enhanced',
    'threshold': 500,
    'contrast_level': 1.3,
    'dpi': 300,
    'prompt': 'Extract text accurately from this document',
    'pdf_config': {
      'page_select': [2, 4, 6]
    }
  }"
```

#### URL Download with Page Selection
```bash
# Download PDF from URL and process specific pages
curl -X POST "/v1/ocr/process-stream" \
  -F "request={
    'url': 'https://example.com/document.pdf',
    'mode': 'llm_enhanced',
    'pdf_config': {
      'page_select': [1, 10, 20]
    }
  }"
```

#### Frontend Integration
```javascript
// React/JavaScript example with streaming
const processWithStreaming = async (file, pages) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('request', JSON.stringify({
    mode: 'llm_enhanced',
    stream: true,  // Enable text streaming
    pdf_config: {
      page_select: pages  // e.g., [1, 3, 5]
    }
  }));

  const response = await fetch('/v1/ocr/process-stream', {
    method: 'POST',
    body: formData
  });

  const { task_id } = await response.json();
  
  // Connect to streaming updates
  const eventSource = new EventSource(`/v1/ocr/stream/${task_id}`);
  
  let displayedText = '';
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Handle different event types
    if (data.text_chunk) {
      // Real-time text streaming
      displayedText += data.text_chunk;
      updateTextDisplay(displayedText);
    } else if (data.progress_percentage !== undefined) {
      // Progress updates
      updateProgressBar(data.progress_percentage);
    } else if (data.status === 'completed') {
      // Final result
      handleCompletion(data.result);
      eventSource.close();
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('Streaming error:', error);
    eventSource.close();
  };
};
```

### Page Selection Rules
- **Pages are 1-indexed**: First page = 1, second page = 2, etc.
- **Automatic sorting**: Pages processed in ascending order regardless of input order
- **Validation**: 
  - Pages must exist in the PDF
  - No duplicate page numbers allowed
  - Empty arrays are rejected
- **Performance**: Only selected pages are converted to images and processed
- **Streaming**: Real-time updates show progress for selected pages only

### Text Streaming Rules
- **Mode requirement**: Only works with `mode: 'llm_enhanced'`
- **Real-time output**: Characters appear as the LLM generates them
- **Accumulation**: Each chunk includes both the new character and accumulated text
- **Performance**: No impact on processing speed, improves perceived performance
- **Compatibility**: Works with both file uploads and URL downloads