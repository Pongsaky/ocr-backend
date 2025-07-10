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
1. **POST** `/v1/ocr/process-stream` - Create OCR processing task (supports PDF page selection)
2. **GET** `/v1/ocr/process-stream/{task_id}` - Get task status and results
3. **POST** `/v1/ocr/tasks/{task_id}/cancel` - Cancel running task

#### PDF Page Selection Feature
The unified API now supports selective PDF page processing:
- **Field**: `pdf_config.page_select` - Array of 1-indexed page numbers
- **Validation**: Pages must exist, no duplicates, automatically sorted
- **Default**: Processes all pages if not specified
- **Examples**: `[1]`, `[1, 3, 5]`, `[2, 4, 6, 8, 10]`

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

## API Usage Examples

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
// React/JavaScript example
const processSpecificPages = async (file, pages) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('request', JSON.stringify({
    mode: 'llm_enhanced',
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
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress_percentage + '%');
    console.log('Current page:', data.current_page);
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