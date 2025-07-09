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
1. **POST** `/v1/ocr/process-stream` - Create OCR processing task
2. **GET** `/v1/ocr/process-stream/{task_id}` - Get task status and results
3. **POST** `/v1/ocr/tasks/{task_id}/cancel` - Cancel running task

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
- Connection pooling for external APIs
- Async file operations with `aiofiles`
- Server-sent events for real-time status updates