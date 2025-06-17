# OCR Backend API

A FastAPI-based backend service for Optical Character Recognition (OCR) using external Vision World API. This service provides both synchronous and asynchronous OCR processing capabilities with comprehensive error handling, rate limiting, and task management.

## 🚀 Features

- **External OCR Integration**: Uses Vision World API for text extraction
- **LLM-Enhanced OCR**: Integration with Pathumma Vision OCR LLM for improved text extraction
- **PDF OCR Processing**: Multi-page PDF processing with batch optimization and memory management
- **Dual Processing Modes**: Synchronous and asynchronous OCR processing for both images and PDFs
- **Task Management**: Track processing status with unique task IDs for all processing types
- **Multi-Format Support**: 
  - **Images**: JPEG, PNG, BMP, TIFF, WebP
  - **PDFs**: Multi-page documents with configurable DPI conversion
- **Advanced PDF Features**:
  - Page-by-page processing with individual results
  - Memory-efficient batch processing
  - Resource cleanup and error recovery
  - Configurable DPI (150-600) for optimal quality/performance balance
- **Rate Limiting**: Configurable request rate limiting
- **Error Handling**: Comprehensive error handling and logging
- **Health Monitoring**: Service health checks and external API monitoring
- **File Validation**: Size and format validation for uploaded files
- **CORS Support**: Cross-origin resource sharing configuration
- **Comprehensive Testing**: Unit and integration tests with high coverage

## 📋 Requirements

- Python 3.11+
- Poetry (for dependency management)  
- Access to Vision World OCR API
- PyMuPDF (for PDF processing)
- PIL/Pillow (for image processing)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ocr-backend
   ```

2. **Install dependencies using Poetry**:
   ```bash
   poetry install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Application Settings
APP_ID=ocr-backend-api
APP_ENV=development
DEBUG=True
PROJECT_NAME=OCR Backend API
LOG_LEVEL=INFO

# Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=True

# CORS Settings
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# External OCR API Settings
EXTERNAL_OCR_BASE_URL=http://203.185.131.205/vision-world
EXTERNAL_OCR_ENDPOINT=/process-image
EXTERNAL_OCR_TIMEOUT=30

# OCR LLM API Settings
OCR_LLM_BASE_URL=http://203.185.131.205/pathumma-vision-ocr
OCR_LLM_ENDPOINT=/v1/chat/completions
OCR_LLM_TIMEOUT=60
OCR_LLM_MODEL=nectec/Pathumma-vision-ocr-lora-dev
OCR_LLM_DEFAULT_PROMPT=ข้อความในภาพนี้

# OCR Processing Settings
DEFAULT_THRESHOLD=128
DEFAULT_CONTRAST_LEVEL=1.0
IMAGE_MAX_SIZE=10485760
ALLOWED_IMAGE_EXTENSIONS=["jpg","jpeg","png","bmp","tiff","webp"]

# PDF Processing Settings
MAX_PDF_SIZE=52428800  # 50MB
MAX_PDF_PAGES=10
PDF_DPI=300
PDF_BATCH_SIZE=3
ALLOWED_PDF_EXTENSIONS=["pdf"]

# File Storage Settings
UPLOAD_DIR=./uploads
RESULTS_DIR=./results
MAX_FILE_SIZE=10485760

# Processing Settings
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT=300
CLEANUP_INTERVAL=3600

# Logging Settings
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=./logs/ocr-backend.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
```

## 🚀 Running the Application

### Development Mode

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 📖 Documentation

- **[PDF OCR Processing Guide](docs/PDF_OCR_GUIDE.md)** - Comprehensive guide for PDF OCR features
- **[External OCR Integration](docs/EXTERNAL_OCR_INTEGRATION.md)** - External service integration details
- **[Testing Guide](docs/TESTING.md)** - Complete testing documentation

## 📚 API Endpoints

### Health Check
- `GET /health` - Service health status

### OCR Processing
- `POST /v1/ocr/process` - Asynchronous OCR processing
- `POST /v1/ocr/process-sync` - Synchronous OCR processing

### LLM-Enhanced OCR Processing  
- `POST /v1/ocr/process-with-llm` - Asynchronous LLM-enhanced OCR processing
- `POST /v1/ocr/process-with-llm-sync` - Synchronous LLM-enhanced OCR processing

### PDF OCR Processing
- `POST /v1/ocr/process-pdf` - Asynchronous PDF OCR processing
- `POST /v1/ocr/process-pdf-sync` - Synchronous PDF OCR processing

### PDF LLM-Enhanced OCR Processing
- `POST /v1/ocr/process-pdf-with-llm` - Asynchronous PDF LLM-enhanced OCR processing
- `POST /v1/ocr/process-pdf-with-llm-sync` - Synchronous PDF LLM-enhanced OCR processing

### Task Management
- `GET /v1/ocr/tasks/{task_id}` - Get task status
- `GET /v1/ocr/llm-tasks/{task_id}` - Get LLM task status
- `GET /v1/ocr/pdf-tasks/{task_id}` - Get PDF task status
- `GET /v1/ocr/pdf-llm-tasks/{task_id}` - Get PDF LLM task status
- `GET /v1/ocr/tasks` - List all tasks
- `DELETE /v1/ocr/tasks/cleanup` - Clean up completed tasks

### Information
- `GET /v1/ocr/parameters` - Get OCR parameters info
- `GET /v1/ocr/service-info` - Get external service information

## 🔧 API Usage Examples

### Synchronous OCR Processing

```bash
curl -X POST "http://localhost:8000/v1/ocr/process-sync" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F 'request={"threshold": 128, "contrast_level": 1.0}'
```

### Asynchronous OCR Processing

```bash
# Submit task
curl -X POST "http://localhost:8000/v1/ocr/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F 'request={"threshold": 128, "contrast_level": 1.0}'

# Check task status
curl -X GET "http://localhost:8000/v1/ocr/tasks/{task_id}"
```

### Get OCR Parameters

```bash
curl -X GET "http://localhost:8000/v1/ocr/parameters"

### LLM-Enhanced OCR Processing

```bash
curl -X POST "http://localhost:8000/v1/ocr/process-with-llm-sync" \
  -F "file=@image.jpg" \
  -F 'request={"threshold": 500, "contrast_level": 1.3, "prompt": "อ่านข้อความในภาพนี้", "model": "nectec/Pathumma-vision-ocr-lora-dev"}'
```

### Check LLM Task Status

```bash
curl -X GET "http://localhost:8000/v1/ocr/llm-tasks/{task_id}"
```

## 📄 PDF OCR Usage Examples

### Synchronous PDF OCR Processing

```bash
# Basic PDF processing with default parameters
curl -X POST "http://localhost:8000/v1/ocr/process-pdf-sync" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# PDF processing with custom parameters
curl -X POST "http://localhost:8000/v1/ocr/process-pdf-sync" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F 'request={"threshold": 500, "contrast_level": 1.3, "dpi": 300}'
```

### Asynchronous PDF OCR Processing

```bash
# Submit PDF task
curl -X POST "http://localhost:8000/v1/ocr/process-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F 'request={"threshold": 500, "contrast_level": 1.3, "dpi": 300}'

# Check PDF task status
curl -X GET "http://localhost:8000/v1/ocr/pdf-tasks/{task_id}"
```

### PDF LLM-Enhanced OCR Processing

```bash
# Synchronous PDF + LLM processing
curl -X POST "http://localhost:8000/v1/ocr/process-pdf-with-llm-sync" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F 'request={"threshold": 500, "contrast_level": 1.3, "dpi": 300, "prompt": "อ่านข้อความในเอกสารนี้อย่างถูกต้อง", "model": "nectec/Pathumma-vision-ocr-lora-dev"}'

# Asynchronous PDF + LLM processing
curl -X POST "http://localhost:8000/v1/ocr/process-pdf-with-llm" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F 'request={"threshold": 500, "contrast_level": 1.3, "dpi": 300, "prompt": "อ่านข้อความในเอกสารนี้อย่างถูกต้อง"}'

# Check PDF LLM task status
curl -X GET "http://localhost:8000/v1/ocr/pdf-llm-tasks/{task_id}"
```

### PDF Response Format

```json
{
  "success": true,
  "total_pages": 3,
  "processed_pages": 3,
  "results": [
    {
      "page_number": 1,
      "extracted_text": "Text content from page 1...",
      "processing_time": 2.34,
      "success": true,
      "error_message": null,
      "threshold_used": 500,
      "contrast_level_used": 1.3
    },
    {
      "page_number": 2,
      "extracted_text": "Text content from page 2...",
      "processing_time": 1.87,
      "success": true,
      "error_message": null,
      "threshold_used": 500,
      "contrast_level_used": 1.3
    }
  ],
  "total_processing_time": 12.45,
  "pdf_processing_time": 3.21,
  "ocr_processing_time": 9.24,
  "dpi_used": 300
}
```

## 📄 PDF Processing Features & Limitations

### ✅ PDF Features
- **Multi-page processing**: Process up to 10 pages per PDF
- **Batch optimization**: Memory-efficient processing in configurable batches
- **Individual page results**: Get detailed results for each page
- **Resource cleanup**: Automatic cleanup of temporary files and memory
- **Error recovery**: Individual page failures don't stop entire document processing
- **Performance metrics**: Detailed timing information for optimization

### ⚙️ PDF Configuration
- **DPI Range**: 150-600 DPI for PDF-to-image conversion
  - `150 DPI`: Fast processing, lower quality
  - `300 DPI`: Balanced quality and speed (recommended)
  - `600 DPI`: High quality, slower processing
- **Batch Size**: Process pages in batches (default: 3 pages)
- **File Size Limit**: 50MB maximum PDF file size
- **Page Limit**: 10 pages maximum per PDF

### 🚫 PDF Limitations
- **File Size**: Maximum 50MB per PDF file
- **Page Count**: Maximum 10 pages per PDF document
- **Format Support**: Only PDF files (no other document formats)
- **Memory Usage**: Large PDFs with high DPI settings require more memory
- **Processing Time**: Scales with page count and DPI settings

### 💡 PDF Best Practices
1. **DPI Selection**:
   - Use 300 DPI for most documents
   - Use 150 DPI for fast processing of low-quality scans
   - Use 600 DPI only for high-quality documents requiring precise text extraction

2. **Batch Processing**:
   - Default batch size (3 pages) works well for most scenarios
   - Reduce batch size for memory-constrained environments
   - Increase batch size for powerful servers with ample memory

3. **Error Handling**:
   - Check `success` field for overall processing status
   - Review individual page `success` status for partial failures
   - Use `error_message` fields for debugging failed pages

4. **Performance Optimization**:
   - Use async endpoints for large PDFs to avoid timeout issues
   - Monitor `processing_time` metrics to optimize parameters
   - Clean up completed tasks regularly using cleanup endpoint

## 🧪 Testing

We have a comprehensive testing strategy with **87 tests** covering all functionality:

### Quick Start
```bash
# Run all tests
python -m pytest

# Run only fast unit tests (61 tests)
python -m pytest tests/unit/ -v

# Run integration tests with real API calls (26 tests)
python -m pytest tests/integration/ -v

# Generate detailed coverage report
python -m pytest --cov=app --cov-report=term-missing
```

### Test Categories

#### 🔬 Unit Tests (Fast & Isolated)
- **Location**: `tests/unit/`
- **Count**: 61 tests
- **Purpose**: Test individual components in isolation with mocked dependencies
- **Execution Time**: ~0.2-0.5 seconds
- **Coverage**: 100% for LLM service, 80%+ overall

#### 🌐 Integration Tests (Real & End-to-End)
- **Location**: `tests/integration/`
- **Count**: 26 tests
- **Purpose**: Test complete workflows with real external APIs
- **Dependencies**: Live external services
- **Execution Time**: ~0.5-2 seconds (surprisingly fast!)
- **Features**: Auto-skip when APIs unavailable, real image processing

### Advanced Test Commands

```bash
# Run only integration tests
python -m pytest -m integration

# Run everything except integration tests
python -m pytest -m "not integration"

# Run with detailed output and timing
python -m pytest -v --durations=10

# Generate HTML coverage report
python -m pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser

# Run specific test method
python -m pytest tests/unit/test_ocr_llm_service.py::TestOCRLLMService::test_serialization_excludes_none_fields -v
```

### Using the Test Runner Script

```bash
# Run all tests with coverage
python scripts/run_tests.py --coverage

# Run only unit tests
python scripts/run_tests.py --unit

# Run only integration tests
python scripts/run_tests.py --integration

# Run specific test file
python scripts/run_tests.py --specific tests/unit/test_external_ocr_service.py

# Fast run without coverage
python scripts/run_tests.py --fast
```

## 📊 Test Coverage

The project maintains high test coverage across all components:

| Component | Unit Tests | Integration Tests | Coverage |
|-----------|------------|-------------------|----------|
| **OCR LLM Service** | ✅ 16 tests | ✅ 10 tests | **100%** |
| **OCR Controller** | ✅ 15 tests | ✅ Via endpoints | **85%** |
| **External OCR Service** | ✅ 14 tests | ✅ 8 tests | **90%** |
| **API Routes** | ✅ Via controller | ✅ 17 tests | **80%** |

### Coverage Statistics
```
Total Tests: 87
├── Unit Tests: 61 tests
│   ├── OCR LLM Service: 16 tests (100% coverage)
│   ├── OCR Controller: 15 tests
│   └── External OCR Service: 14 tests
└── Integration Tests: 26 tests
    ├── LLM Integration: 10 tests (Real API calls)
    ├── API Endpoints: 17 tests
    └── External OCR: 8 tests
```

**Overall Project Coverage**: 78% (Up from 51% after implementing comprehensive LLM tests)

### What Our Tests Cover

#### Critical Features Tested
- **Serialization Fixes**: Ensures `exclude_none=True` prevents null field bugs
- **Real API Integration**: Actual HTTP requests to Vision World and Pathumma Vision OCR
- **Error Handling**: Timeouts, network issues, malformed responses
- **Concurrent Processing**: Multiple simultaneous API calls
- **Image Processing**: Real image files from `test_files/test_image.png`

#### Why Integration Tests Use Real APIs
Our integration tests make **actual HTTP requests** to:
- **Vision World API**: `http://203.185.131.205/vision-world/process-image`
- **Pathumma Vision OCR LLM**: `http://203.185.131.205/pathumma-vision-ocr/v1/chat/completions`

This detects real issues that unit tests miss:
- API format changes
- Network problems
- Authentication issues
- Serialization bugs in production

For detailed testing documentation, see [`docs/TESTING.md`](docs/TESTING.md).

## 🏗️ Project Structure

```
ocr-backend/
├── app/
│   ├── controllers/          # Business logic controllers
│   ├── middleware/           # Custom middleware
│   ├── models/              # Pydantic models
│   ├── routers/             # API route definitions
│   ├── services/            # External service integrations
│   ├── logger_config.py     # Logging configuration
│   └── main.py              # FastAPI application
├── config/
│   └── settings.py          # Application settings
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Test configuration
├── scripts/
│   └── run_tests.py         # Test runner script
├── docs/                    # Documentation
├── logs/                    # Log files
├── uploads/                 # Temporary file uploads
├── .env.example             # Environment variables template
├── pyproject.toml           # Poetry configuration
└── README.md                # This file
```

## 🔍 External OCR API Integration

This service integrates with the Vision World OCR API:

- **Base URL**: `http://203.185.131.205/vision-world`
- **Endpoint**: `/process-image`
- **Method**: POST
- **Input**: Base64 encoded image with threshold and contrast parameters
- **Output**: Extracted text string

### API Request Format

```json
{
  "image": "base64_encoded_image_data",
  "threshold": 128,
  "contrast_level": 1.0
}
```

### API Response Format

```json
"Extracted text from the image"
```

## 📝 OCR Parameters

### Threshold (0-255)
- **Default**: 128
- **Description**: Threshold value for image binarization
- **Recommendation**: 
  - 128 for general use
  - Lower values for darker images
  - Higher values for lighter images

### Contrast Level (0.1-5.0)
- **Default**: 1.0
- **Description**: Contrast enhancement level
- **Recommendation**:
  - 1.0 for normal contrast
  - >1.0 to increase contrast
  - <1.0 to decrease contrast

## 🚦 Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default**: 100 requests per minute per IP
- **Configurable**: Via environment variables
- **Headers**: Rate limit information in response headers

## 📋 Logging

Comprehensive logging with:

- **Console Output**: Colored logs for development
- **File Output**: Rotating log files
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Structured Logging**: JSON format for production

## 🔒 Error Handling

Robust error handling for:

- **File Validation Errors**: Invalid format, size limits
- **External API Errors**: Timeout, HTTP errors, service unavailable
- **Processing Errors**: OCR failures, task management issues
- **Rate Limiting**: Request throttling

## 🚀 Deployment

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

COPY . .

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment-Specific Configuration

- **Development**: Debug mode, detailed logging
- **Staging**: Production-like settings with debug info
- **Production**: Optimized settings, minimal logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the API documentation at `/docs`
2. Review the test cases for usage examples
3. Check the logs for error details
4. Verify external OCR service availability

## 🔄 Version History

- **v0.1.0**: Initial release with external OCR API integration
  - FastAPI backend with async/sync processing
  - Vision World API integration
  - Comprehensive test suite
  - Rate limiting and error handling
  - Task management system 