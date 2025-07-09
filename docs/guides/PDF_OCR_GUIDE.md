# PDF OCR Processing Guide

## Overview

The OCR Backend API provides comprehensive PDF processing capabilities that convert multi-page PDF documents into machine-readable text using advanced OCR technology. This guide covers the technical details, architecture, and best practices for PDF OCR processing.

## Architecture

### Processing Pipeline

```
PDF Upload → Validation → PDF-to-Images → Batch Processing → OCR → Results Aggregation
```

1. **PDF Validation**: File size, page count, and format validation
2. **PDF-to-Images Conversion**: Convert PDF pages to high-resolution images using PyMuPDF
3. **Batch Processing**: Process images in memory-efficient batches
4. **OCR Processing**: Extract text from each page using external OCR service
5. **Results Aggregation**: Combine individual page results into a comprehensive response

### Key Components

- **PDFOCRService**: Core service handling PDF processing pipeline
- **PDFProcessingContext**: Resource management and cleanup
- **Batch Processing**: Memory-efficient processing of multiple pages
- **Error Recovery**: Individual page failures don't stop entire document processing

## API Endpoints

### 1. Synchronous PDF OCR

```http
POST /v1/ocr/process-pdf-sync
Content-Type: multipart/form-data

file: <pdf_file>
request: {
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300
}
```

**Response:**
```json
{
  "success": true,
  "total_pages": 5,
  "processed_pages": 5,
  "results": [
    {
      "page_number": 1,
      "extracted_text": "Page 1 content...",
      "processing_time": 2.34,
      "success": true,
      "error_message": null,
      "threshold_used": 500,
      "contrast_level_used": 1.3
    }
  ],
  "total_processing_time": 15.67,
  "pdf_processing_time": 4.23,
  "image_processing_time": 11.44,
  "dpi_used": 300
}
```

### 2. Asynchronous PDF OCR

```http
POST /v1/ocr/process-pdf
Content-Type: multipart/form-data

file: <pdf_file>
request: {
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300
}
```

**Response:**
```json
{
  "task_id": "uuid-here",
  "status": "processing",
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": null,
  "result": null,
  "error_message": null
}
```

### 3. PDF LLM-Enhanced OCR

```http
POST /v1/ocr/process-pdf-with-llm-sync
Content-Type: multipart/form-data

file: <pdf_file>
request: {
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300,
  "prompt": "อ่านข้อความในเอกสารนี้อย่างถูกต้อง",
  "model": "nectec/Pathumma-vision-ocr-lora-dev"
}
```

### 4. Task Status Checking

```http
GET /v1/ocr/pdf-tasks/{task_id}
```

## Configuration Parameters

### PDF Processing Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `threshold` | integer | 0-1024 | 500 | Threshold for image binarization |
| `contrast_level` | float | 0.1-5.0 | 1.3 | Contrast enhancement level |
| `dpi` | integer | 150-600 | 300 | Resolution for PDF-to-image conversion |

### System Limits

| Setting | Value | Description |
|---------|-------|-------------|
| `MAX_PDF_SIZE` | 50MB | Maximum PDF file size |
| `MAX_PDF_PAGES` | 10 | Maximum pages per PDF |
| `PDF_BATCH_SIZE` | 3 | Pages processed per batch |

### DPI Recommendations

| DPI | Use Case | Quality | Speed | Memory Usage |
|-----|----------|---------|-------|--------------|
| 150 | Fast processing, low-quality scans | Low | Fast | Low |
| 300 | General purpose (recommended) | Good | Balanced | Moderate |
| 450 | High-quality documents | High | Slow | High |
| 600 | Maximum quality, precise text | Very High | Very Slow | Very High |

## Error Handling

### Validation Errors

- **File too large**: PDF exceeds 50MB limit
- **Too many pages**: PDF has more than 10 pages
- **Invalid format**: File is not a valid PDF
- **Corrupted PDF**: PDF cannot be opened or processed

### Processing Errors

- **Page conversion failure**: Individual page cannot be converted to image
- **OCR service error**: External OCR service unavailable or returns error
- **Memory exhaustion**: System runs out of memory during processing
- **Timeout**: Processing takes longer than configured timeout

### Error Response Format

```json
{
  "success": false,
  "total_pages": 5,
  "processed_pages": 3,
  "results": [
    {
      "page_number": 1,
      "success": true,
      "extracted_text": "Page 1 content..."
    },
    {
      "page_number": 2,
      "success": false,
      "error_message": "OCR service unavailable",
      "extracted_text": ""
    }
  ],
  "error_message": "Partial processing failure"
}
```

## Performance Optimization

### Memory Management

1. **Batch Processing**: Pages are processed in configurable batches to prevent memory exhaustion
2. **Resource Cleanup**: Temporary files and memory are automatically cleaned up
3. **Garbage Collection**: Forced garbage collection between batches

### Processing Strategies

```python
# Example batch processing configuration
PDF_BATCH_SIZE = 3  # Process 3 pages at a time

# Memory-efficient processing
async def process_large_pdf():
    # Pages are processed in batches
    # Memory is freed between batches
    # Temporary files are cleaned up automatically
```

### Performance Monitoring

Monitor these metrics for optimization:

- `total_processing_time`: Overall processing duration
- `pdf_processing_time`: Time spent converting PDF to images
- `image_processing_time`: Time spent on OCR processing
- `processing_time` per page: Individual page processing time

## Advanced Usage Patterns

### 1. Batch Document Processing

```python
import asyncio
import aiohttp

async def process_multiple_pdfs(pdf_files):
    """Process multiple PDFs concurrently"""
    tasks = []
    
    async with aiohttp.ClientSession() as session:
        for pdf_file in pdf_files:
            task = process_single_pdf(session, pdf_file)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

async def process_single_pdf(session, pdf_file):
    """Process a single PDF file"""
    data = aiohttp.FormData()
    data.add_field('file', pdf_file)
    data.add_field('request', '{"dpi": 300, "threshold": 500}')
    
    async with session.post('/v1/ocr/process-pdf', data=data) as response:
        return await response.json()
```

### 2. Quality vs Speed Optimization

```python
# Fast processing for low-quality scans
fast_config = {
    "dpi": 150,
    "threshold": 400,
    "contrast_level": 1.0
}

# Balanced processing (recommended)
balanced_config = {
    "dpi": 300,
    "threshold": 500,
    "contrast_level": 1.3
}

# High-quality processing for precise text
quality_config = {
    "dpi": 600,
    "threshold": 600,
    "contrast_level": 1.5
}
```

### 3. Error Recovery Patterns

```python
async def robust_pdf_processing(pdf_file, max_retries=3):
    """Robust PDF processing with retry logic"""
    
    for attempt in range(max_retries):
        try:
            result = await process_pdf(pdf_file)
            
            if result['success']:
                return result
            
            # Partial success - check if acceptable
            success_rate = result['processed_pages'] / result['total_pages']
            if success_rate >= 0.8:  # 80% success rate acceptable
                return result
                
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            # Wait before retry
            await asyncio.sleep(2 ** attempt)
    
    raise Exception("Failed to process PDF after all retries")
```

## Troubleshooting

### Common Issues

1. **Memory Issues**
   - Reduce DPI setting
   - Decrease batch size
   - Process fewer pages at once

2. **Slow Processing**
   - Use lower DPI for faster processing
   - Use async endpoints for large files
   - Optimize threshold and contrast settings

3. **Poor OCR Quality**
   - Increase DPI setting
   - Adjust contrast level
   - Use LLM-enhanced processing

4. **File Upload Issues**
   - Check file size limits
   - Verify PDF format
   - Ensure PDF is not password-protected

### Debug Information

Enable debug logging to get detailed processing information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Debug logs include:
- PDF validation details
- Page conversion progress
- OCR processing status
- Memory usage information
- Resource cleanup status

## Integration Examples

### Python Client

```python
import requests
import json

class PDFOCRClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def process_pdf_sync(self, pdf_path, config=None):
        """Process PDF synchronously"""
        if config is None:
            config = {"dpi": 300, "threshold": 500, "contrast_level": 1.3}
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {'request': json.dumps(config)}
            
            response = requests.post(
                f"{self.base_url}/v1/ocr/process-pdf-sync",
                files=files,
                data=data
            )
            
            return response.json()
    
    def process_pdf_async(self, pdf_path, config=None):
        """Process PDF asynchronously"""
        if config is None:
            config = {"dpi": 300, "threshold": 500, "contrast_level": 1.3}
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {'request': json.dumps(config)}
            
            response = requests.post(
                f"{self.base_url}/v1/ocr/process-pdf",
                files=files,
                data=data
            )
            
            return response.json()
    
    def get_task_status(self, task_id):
        """Get task status"""
        response = requests.get(f"{self.base_url}/v1/ocr/pdf-tasks/{task_id}")
        return response.json()

# Usage example
client = PDFOCRClient()
result = client.process_pdf_sync("document.pdf", {
    "dpi": 300,
    "threshold": 500,
    "contrast_level": 1.3
})

print(f"Processed {result['processed_pages']}/{result['total_pages']} pages")
for page_result in result['results']:
    print(f"Page {page_result['page_number']}: {len(page_result['extracted_text'])} characters")
```

### JavaScript Client

```javascript
class PDFOCRClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async processPDFSync(file, config = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        const defaultConfig = {
            dpi: 300,
            threshold: 500,
            contrast_level: 1.3
        };
        
        const finalConfig = { ...defaultConfig, ...config };
        formData.append('request', JSON.stringify(finalConfig));
        
        const response = await fetch(`${this.baseUrl}/v1/ocr/process-pdf-sync`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async processPDFAsync(file, config = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        const defaultConfig = {
            dpi: 300,
            threshold: 500,
            contrast_level: 1.3
        };
        
        const finalConfig = { ...defaultConfig, ...config };
        formData.append('request', JSON.stringify(finalConfig));
        
        const response = await fetch(`${this.baseUrl}/v1/ocr/process-pdf`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async getTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/v1/ocr/pdf-tasks/${taskId}`);
        return await response.json();
    }
}

// Usage example
const client = new PDFOCRClient();
const fileInput = document.getElementById('pdfFile');
const file = fileInput.files[0];

try {
    const result = await client.processPDFSync(file, {
        dpi: 300,
        threshold: 500,
        contrast_level: 1.3
    });
    
    console.log(`Processed ${result.processed_pages}/${result.total_pages} pages`);
    result.results.forEach(pageResult => {
        console.log(`Page ${pageResult.page_number}: ${pageResult.extracted_text.length} characters`);
    });
} catch (error) {
    console.error('PDF processing failed:', error);
}
```

## Best Practices Summary

1. **Choose appropriate DPI**: Use 300 DPI for most use cases
2. **Use async endpoints**: For large PDFs to avoid timeouts
3. **Monitor memory usage**: Especially when processing many PDFs
4. **Implement retry logic**: For robust production systems
5. **Validate files**: Check file size and page count before processing
6. **Handle partial failures**: Some pages may fail while others succeed
7. **Clean up resources**: Use cleanup endpoints to manage system resources
8. **Monitor performance**: Track processing times and optimize accordingly

This comprehensive guide should help you effectively use the PDF OCR functionality in your applications. 