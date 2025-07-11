# Real API Execution Testing Guide

This guide explains the comprehensive real API testing suite that validates your deployed OCR backend with **actual API execution and real results**.

## What Makes These Tests "Real"

Unlike unit tests that mock services, these tests:

✅ **Make actual HTTP calls** to your deployed API  
✅ **Wait for real OCR completion** with actual results  
✅ **Validate real text extraction** quality and accuracy  
✅ **Test real streaming** with character-by-character updates  
✅ **Verify real workflows** that users actually perform  
✅ **Measure real performance** under load conditions  

## Quick Start

```bash
# Test your deployment
export REMOTE_API_URL='http://203.185.131.205/ocr-backend'

# Run complete test suite
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend

# Run specific test types
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s real-api
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s workflows
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s streaming
```

## Test Suites Overview

### 1. **Real API Execution Tests** (`test_real_api_execution.py`)
**What it does**: Validates actual OCR processing with real completion verification

- ✅ **Real Text Images**: Creates images with readable text and verifies extraction
- ✅ **LLM Enhancement**: Tests LLM-enhanced mode with actual model responses  
- ✅ **Thai Text Support**: Tests multilingual OCR capabilities
- ✅ **Task Lifecycle**: Monitors complete task progression from creation to completion
- ✅ **Error Handling**: Validates proper error responses with invalid inputs

**Example Output**:
```
🔍 Testing REAL basic OCR at: http://203.185.131.205/ocr-backend
📝 Created basic OCR task: 08149bef-0363-4866-bdef-61fcc3e2c053
✅ Task completed successfully
📄 Extracted text length: 245 characters
📄 Sample text: HELLO WORLD This is a test document OCR should extract this text...
✅ Found expected words: ['hello', 'world', 'test', 'document', 'ocr']
✅ Real basic OCR test PASSED
```

### 2. **User Workflow Tests** (`test_workflow_journeys.py`)
**What it does**: Tests complete user journeys from start to finish

- 📄 **Business Document Processing**: Invoice/receipt extraction workflows
- 📚 **PDF Page Selection**: Multi-page document processing
- 📡 **Real-time Streaming**: Character-by-character text streaming
- 🔄 **Error Recovery**: User mistake → error → successful retry
- 📦 **Bulk Processing**: Sequential document processing

**Example Workflow**:
```
📄 WORKFLOW: Simple Document OCR
   Scenario: Business user uploads invoice for text extraction

🔹 Step 1: Upload business document
✅ Document uploaded, task created: 2d93e962-21b7-48cf-8231-8946442a14cf

🔹 Step 2: Wait for OCR processing
📊 Status change: None → processing
📈 Progress: 25%
📈 Progress: 75%
✅ Task completed in 8.3s

🔹 Step 3: Validate OCR results
📊 Results Summary:
   Text length: 1,234 characters
   Processing time: 8.1s
   Model used: nectec/Pathumma-vision-ocr-lora-dev
📋 Found business keywords: ['invoice', 'company', 'amount', 'date', 'payment']
✅ Found invoice number
✅ Found currency/amount
✅ WORKFLOW COMPLETED: Simple Document OCR
```

### 3. **Streaming Validation Tests** (`test_streaming_validation.py`)
**What it does**: Comprehensive real-time streaming functionality testing

- 🎛️ **Event Types**: Tests all streaming event types (text, progress, completion)
- 📝 **Text Accumulation**: Validates character-by-character text building
- 🔗 **Connection Stability**: Tests streaming over extended periods
- 🔀 **Concurrent Streams**: Multiple simultaneous streaming connections

**Example Streaming**:
```
📡 Testing REAL streaming with completion at: http://203.185.131.205/ocr-backend
📡 Created streaming task: 072d70d1-7d8f-4a88-ae4a-db3f78ebb53d
📝 Chunk: 'T' (Total: 1 chars)
📝 Chunk: 'h' (Total: 2 chars)
📝 Chunk: 'i' (Total: 3 chars)
📝 Chunk: 's' (Total: 4 chars)
📊 Progress: 25%
📝 Chunk: ' ' (Total: 5 chars)
📝 Chunk: 'i' (Total: 6 chars)
...
🏁 Streaming ended with status: completed

📊 Streaming Results:
   Total updates: 156
   Accumulated text length: 1,045 characters
   Sample text: This is a test document designed to generate multiple streaming chunks...
✅ Received 89 text chunks
✅ Received completion update
✅ Real streaming test PASSED
```

### 4. **Data Quality Tests** (`test_data_quality.py`)
**What it does**: Tests OCR accuracy with real document samples

- 📄 **Invoice Processing**: Business document accuracy validation
- 🧾 **Receipt Analysis**: Retail document text extraction
- 📋 **Form Handling**: Structured data extraction
- ⚖️ **Mode Comparison**: Basic vs LLM-enhanced accuracy comparison

**Example Quality Analysis**:
```
📄 Testing invoice OCR quality at: http://203.185.131.205/ocr-backend
📝 Created invoice OCR task: abc123...
✅ Task completed successfully

📊 Invoice OCR Results:
   Extracted text length: 1,567 characters
   Expected items: 9
   Exact matches: 7
   Partial matches: 1  
   Accuracy: 77.8%
   Partial accuracy: 83.3%
   Sample text: INVOICE ABC CORPORATION INV-2024-001 January 15, 2024 $2,450.00...
   Critical elements found: 4/4
✅ Invoice OCR quality test PASSED
```

### 5. **Performance Tests** (`test_performance_load.py`)
**What it does**: Validates performance under various load conditions

- ⏱️ **Response Time Baseline**: Measures API response times
- 🔀 **Concurrent Requests**: Tests parallel processing capability
- 📏 **Image Size Impact**: Performance with different document sizes
- ⏳ **Sustained Load**: Extended operation stability
- 📡 **Streaming Performance**: Real-time update efficiency

**Example Performance Results**:
```
⏱️  Testing API response time baseline at: http://203.185.131.205/ocr-backend
   Request 1/5...
   ✅ Response time: 2.34s
   Request 2/5...
   ✅ Response time: 1.98s
   ...

📊 Response Time Baseline:
   Successful requests: 5/5
   Average: 2.15s
   Median: 2.08s
   Min: 1.87s
   Max: 2.45s
✅ Response time baseline test PASSED
```

## Running Individual Test Suites

### Health Check Only
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s health
```

### Real API Execution
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s real-api
```

### Complete User Workflows  
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s workflows
```

### Streaming Validation
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s streaming
```

### Data Quality Testing
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s quality
```

### Performance Testing
```bash
./scripts/run_deployment_tests.sh -u http://203.185.131.205/ocr-backend -s performance
```

## Advanced Usage

### With Authentication
```bash
./scripts/run_deployment_tests.sh \
  -u https://secure-api.example.com \
  -k your-api-key \
  -s all
```

### Verbose Output
```bash
./scripts/run_deployment_tests.sh \
  -u http://203.185.131.205/ocr-backend \
  -v \
  -s real-api
```

### Custom Timeout
```bash
./scripts/run_deployment_tests.sh \
  -u http://203.185.131.205/ocr-backend \
  -t 120 \
  -s performance
```

## Direct pytest Usage

You can also run tests directly with pytest:

```bash
# Set environment
export REMOTE_API_URL='http://203.185.131.205/ocr-backend'

# Run specific test files
pytest tests/test_real_api_execution.py -v -s
pytest tests/test_workflow_journeys.py -v -s  
pytest tests/test_streaming_validation.py -v -s
pytest tests/test_data_quality.py -v -s
pytest tests/test_performance_load.py -v -s

# Run specific tests
pytest tests/test_real_api_execution.py::TestRealAPIExecution::test_real_image_ocr_basic -v -s
```

## Understanding Test Results

### ✅ Success Indicators
- **Task Completion**: Tasks complete with `status: "completed"`
- **Text Extraction**: Actual text extracted from images
- **Accuracy Metrics**: OCR accuracy above defined thresholds
- **Performance Benchmarks**: Response times within acceptable ranges
- **Streaming Functionality**: Real-time updates received

### ❌ Failure Indicators  
- **Connection Issues**: Cannot reach API endpoints
- **Task Failures**: Tasks end with `status: "failed"`
- **Low Accuracy**: OCR extraction below quality thresholds
- **Performance Issues**: Response times too slow
- **Streaming Problems**: No real-time updates received

### ⚠️ Warning Indicators
- **Partial Success**: Some features work, others have issues
- **Performance Degradation**: Slower than expected but functional
- **Quality Variations**: OCR works but with lower accuracy than expected

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   ❌ Cannot connect to API: Connection refused
   ```
   - Check if your deployment URL is correct
   - Verify the service is running and accessible

2. **Authentication Errors**
   ```
   ❌ HTTP 401 Unauthorized
   ```
   - Verify your API key is correct
   - Check if authentication is properly configured

3. **Timeout Issues**
   ```
   ⏰ Task timed out after 60 seconds
   ```
   - Increase timeout with `-t` parameter
   - Check if your deployment has performance issues

4. **Low OCR Accuracy**
   ```
   ❌ Low accuracy: 23.4%
   ```
   - Check if your OCR services are properly configured
   - Verify external OCR/LLM services are accessible

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deployment Tests
on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM
  workflow_dispatch:

jobs:
  test-deployment:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: poetry install
      - name: Test Deployment
        env:
          REMOTE_API_URL: ${{ secrets.DEPLOYED_API_URL }}
          REMOTE_API_KEY: ${{ secrets.API_KEY }}
        run: |
          ./scripts/run_deployment_tests.sh \
            -u $REMOTE_API_URL \
            -k $REMOTE_API_KEY \
            -s all
```

## Benefits of Real API Testing

1. **Production Validation**: Tests actual deployed services, not mocks
2. **End-to-End Confidence**: Validates complete user workflows  
3. **Performance Insights**: Real performance metrics under load
4. **Quality Assurance**: Actual OCR accuracy with real documents
5. **Deployment Verification**: Confirms deployment is working correctly
6. **Regression Detection**: Catches issues in production deployments
7. **User Experience Validation**: Tests what users actually experience

This comprehensive testing approach ensures your OCR backend deployment is not just running, but actually working correctly for real users with real documents!