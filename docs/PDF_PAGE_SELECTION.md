# PDF Page Selection Feature

## Overview

The PDF Page Selection feature allows users to process specific pages of a PDF document instead of processing all pages. This can significantly reduce processing time and costs when only certain pages are needed.

## Features

- **Selective Processing**: Choose specific pages to process (e.g., pages 1, 3, 5)
- **Smart Validation**: Automatically validates page numbers and prevents errors
- **Auto-sorting**: Pages are processed in ascending order regardless of input order
- **Streaming Support**: Real-time progress updates for selected pages only
- **Backward Compatible**: Default behavior unchanged (processes all pages)

## API Usage

### Unified API Endpoint

**POST** `/v1/ocr/process-stream`

### Request Structure

```json
{
  "mode": "basic" | "llm_enhanced",
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300,
  "prompt": "optional custom prompt",
  "model": "optional model name",
  "pdf_config": {
    "page_select": [1, 3, 5]  // Array of page numbers (1-indexed)
  }
}
```

### Examples

#### 1. Basic OCR with Page Selection

```bash
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@document.pdf" \
  -F "request={
    'mode': 'basic',
    'pdf_config': {
      'page_select': [1, 3, 5]
    }
  }"
```

#### 2. LLM Enhanced OCR with Page Selection

```bash
curl -X POST "/v1/ocr/process-stream" \
  -F "file=@document.pdf" \
  -F "request={
    'mode': 'llm_enhanced',
    'threshold': 500,
    'contrast_level': 1.3,
    'dpi': 300,
    'prompt': 'Extract text accurately',
    'pdf_config': {
      'page_select': [2, 4, 6]
    }
  }"
```

#### 3. URL Download with Page Selection

```bash
curl -X POST "/v1/ocr/process-stream" \
  -F "request={
    'url': 'https://example.com/document.pdf',
    'mode': 'llm_enhanced',
    'pdf_config': {
      'page_select': [1, 10, 20]
    }
  }"
```

#### 4. JavaScript/Frontend Integration

```javascript
async function processSpecificPages(file, pages) {
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
    console.log(`Progress: ${data.progress_percentage}%`);
    console.log(`Processing page: ${data.current_page}`);
    
    if (data.status === 'completed') {
      console.log('All selected pages processed!');
      eventSource.close();
    }
  };
}

// Usage examples
processSpecificPages(fileInput.files[0], [1, 3, 5]);  // Process pages 1, 3, 5
processSpecificPages(fileInput.files[0], [2]);        // Process only page 2
processSpecificPages(fileInput.files[0], [1, 2, 3]);  // Process first 3 pages
```

## Validation Rules

### Valid Page Selection

- **1-indexed**: Pages start from 1 (not 0)
- **Must exist**: Page numbers must exist in the PDF
- **No duplicates**: Each page number can only appear once
- **No empty arrays**: Must provide at least one page number
- **Auto-sorted**: Pages are automatically sorted in ascending order

### Examples

```javascript
// ✅ Valid examples
{ "page_select": [1] }           // Single page
{ "page_select": [1, 3, 5] }     // Multiple pages
{ "page_select": [5, 1, 3] }     // Will be sorted to [1, 3, 5]
{ "page_select": [1, 2, 3, 4, 5] } // Sequential pages

// ❌ Invalid examples
{ "page_select": [] }            // Empty array
{ "page_select": [0, 1, 2] }     // Page 0 doesn't exist
{ "page_select": [1, 1, 2] }     // Duplicate page 1
{ "page_select": [1, 100] }      // Page 100 might not exist
```

## Response Format

### Streaming Response

The streaming response includes progress updates for selected pages only:

```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "page_completed",
  "current_page": 3,
  "total_pages": 3,
  "processed_pages": 2,
  "failed_pages": 0,
  "progress_percentage": 66.7,
  "latest_page_result": {
    "page_number": 3,
    "extracted_text": "Text from page 3...",
    "processing_time": 2.1,
    "success": true
  },
  "cumulative_results": [
    {
      "page_number": 1,
      "extracted_text": "Text from page 1...",
      "processing_time": 1.8,
      "success": true
    },
    {
      "page_number": 3,
      "extracted_text": "Text from page 3...",
      "processing_time": 2.1,
      "success": true
    }
  ]
}
```

### Final Response

When processing is complete:

```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "completed",
  "result": {
    "success": true,
    "total_pages": 2,           // Number of selected pages
    "processed_pages": 2,       // Successfully processed
    "results": [
      {
        "page_number": 1,       // Original page number from PDF
        "extracted_text": "Text from page 1...",
        "processing_time": 1.8,
        "success": true
      },
      {
        "page_number": 3,       // Original page number from PDF
        "extracted_text": "Text from page 3...",
        "processing_time": 2.1,
        "success": true
      }
    ],
    "total_processing_time": 5.2,
    "pdf_processing_time": 1.1,
    "image_processing_time": 4.1
  }
}
```

## Error Handling

### Invalid Page Numbers

```json
{
  "error": true,
  "message": "Invalid page numbers: [15, 20]. PDF only has 10 pages.",
  "status_code": 400
}
```

### Empty Page Selection

```json
{
  "error": true,
  "message": "page_select cannot be empty if provided",
  "status_code": 422
}
```

### Duplicate Pages

```json
{
  "error": true,
  "message": "Duplicate page numbers are not allowed",
  "status_code": 422
}
```

## Performance Benefits

### Processing Time Reduction

- **50% fewer pages = ~50% faster processing**
- Only selected pages are converted to images
- Reduced memory usage and CPU time
- Lower API costs for LLM processing

### Example Scenarios

```javascript
// Scenario 1: Large PDF with 100 pages, only need first and last page
{
  "pdf_config": {
    "page_select": [1, 100]
  }
}
// Processing time: ~2% of full document

// Scenario 2: Extract specific chapters from a book
{
  "pdf_config": {
    "page_select": [5, 15, 25, 35, 45]  // Chapter start pages
  }
}
// Processing time: ~5% of full document

// Scenario 3: Process odd pages only for double-sided scans
{
  "pdf_config": {
    "page_select": [1, 3, 5, 7, 9, 11, 13, 15]
  }
}
// Processing time: ~50% of full document
```

## Legacy API Support

The page selection feature is also available in legacy PDF endpoints:

### PDFOCRRequest

```json
{
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300,
  "page_select": [1, 3, 5]
}
```

### PDFLLMOCRRequest

```json
{
  "threshold": 500,
  "contrast_level": 1.3,
  "dpi": 300,
  "prompt": "Extract text accurately",
  "model": "gpt-4-vision-preview",
  "page_select": [1, 3, 5]
}
```

## Implementation Notes

- Page numbers in results maintain original PDF page numbering
- Streaming progress shows current position within selected pages
- Cancellation works normally and stops processing immediately
- All validation happens before PDF conversion begins
- Memory usage scales with number of selected pages, not total PDF size