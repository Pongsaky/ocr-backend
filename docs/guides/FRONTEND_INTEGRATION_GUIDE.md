# Frontend Integration Guide

## 🎯 **Overview**

This guide provides everything frontend developers need to integrate with the OCR Backend API. The API supports **streaming OCR processing** for **Images**, **PDFs**, and **DOCX files** (when enabled).

## 📋 **Quick Reference**

### **Supported File Types**
- ✅ **Images**: JPEG, PNG, BMP, TIFF, WebP (max 10MB)
- ✅ **PDFs**: Multi-page documents (max 50MB, 20 pages)
- 🔴 **DOCX**: Microsoft Word documents (**disabled by default**)

### **Processing Modes**
- `basic` - Standard OCR processing (faster)
- `llm_enhanced` - AI-enhanced text extraction (higher accuracy, slower, supports text streaming)

### **Base URL**
```
http://localhost:8000    # Development
https://your-api.com     # Production
```

## 🚀 **Step-by-Step Integration**

### **Step 1: Upload & Start Processing**

**Endpoint**: `POST /v1/ocr/process-stream`

```javascript
// Upload file and start processing
const uploadFile = async (file, mode = 'basic', enableStreaming = false) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('request', JSON.stringify({ 
    mode,
    stream: enableStreaming && mode === 'llm_enhanced' // Only works with LLM mode
  }));

  const response = await fetch('/v1/ocr/process-stream', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }

  return await response.json();
};
```

**Success Response**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "file_type": "image",
  "processing_mode": "basic",
  "status": "processing",
  "created_at": "2025-01-15T10:30:00Z",
  "estimated_duration": 2.0,
  "file_metadata": {
    "original_filename": "document.png",
    "file_size_bytes": 165513,
    "mime_type": "image/png",
    "detected_file_type": "image",
    "image_dimensions": {"width": 654, "height": 926}
  }
}
```

### **Step 2: Connect to Streaming Results**

**Endpoint**: `GET /v1/ocr/stream/{task_id}` (Server-Sent Events)

```javascript
// Connect to streaming updates
const streamResults = (taskId, onUpdate, onComplete, onError) => {
  const eventSource = new EventSource(`/v1/ocr/stream/${taskId}`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      // Handle heartbeat
      if (data.heartbeat) {
        console.log('Heartbeat received');
        return;
      }

      // Handle real-time text streaming (when stream: true)
      if (data.text_chunk) {
        onUpdate({
          type: 'text_stream',
          text_chunk: data.text_chunk,
          accumulated_text: data.accumulated_text
        });
        return;
      }

      // Handle progress updates
      onUpdate(data);

      // Handle completion
      if (data.status === 'completed') {
        eventSource.close();
        onComplete(data);
      } else if (data.status === 'failed') {
        eventSource.close();
        onError(data);
      }
    } catch (error) {
      console.error('Failed to parse streaming data:', error);
    }
  };

  eventSource.onerror = (error) => {
    console.error('Streaming error:', error);
    eventSource.close();
    onError(error);
  };

  return eventSource; // Return for manual closing if needed
};
```

### **Step 3: Handle Different Types of Streaming Updates**

When streaming is enabled (`stream: true`), you'll receive several different types of updates:

#### **Type 1: Regular Progress Updates**
```json
{
  "task_id": "abc123-def456-ghi789",
  "file_type": "pdf",
  "processing_mode": "llm_enhanced",
  "status": "processing",
  "current_step": "ocr_processing",
  "progress_percentage": 45.5,
  "current_page": 3,
  "total_pages": 5,
  "processed_pages": 2,
  "failed_pages": 0,
  "estimated_time_remaining": 12.5,
  "timestamp": "2025-01-15T10:30:15Z"
}
```

#### **Type 2: Real-time Text Streaming Updates** (when `stream: true`)
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 3,
  "text_chunk": "ข",
  "accumulated_text": "ข้อความในเอกสารนี้คือ ข",
  "timestamp": "2025-01-15T10:30:16Z"
}

{
  "task_id": "abc123-def456-ghi789", 
  "status": "processing",
  "current_step": "llm_enhancement",
  "current_page": 3,
  "text_chunk": "้",
  "accumulated_text": "ข้อความในเอกสารนี้คือ ข้",
  "timestamp": "2025-01-15T10:30:16Z"
}
```

#### **Type 3: Page Completion Updates**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "page_completed",
  "current_step": "ocr_processing",
  "progress_percentage": 60.0,
  "current_page": 3,
  "total_pages": 5,
  "processed_pages": 3,
  "failed_pages": 0,
  "latest_page_result": {
    "page_number": 3,
    "extracted_text": "Complete text from page 3...",
    "processing_time": 2.8,
    "success": true,
    "threshold_used": 500,
    "contrast_level_used": 1.3,
    "image_processing_time": 1.1,
    "llm_processing_time": 1.7,
    "model_used": "nectec/Pathumma-vision-ocr-lora-dev"
  },
  "cumulative_results": [
    {
      "page_number": 1,
      "extracted_text": "Page 1 content...",
      "processing_time": 2.1,
      "success": true
    },
    {
      "page_number": 2, 
      "extracted_text": "Page 2 content...",
      "processing_time": 2.3,
      "success": true
    },
    {
      "page_number": 3,
      "extracted_text": "Complete text from page 3...",
      "processing_time": 2.8,
      "success": true
    }
  ],
  "estimated_time_remaining": 8.2,
  "processing_speed": 0.42,
  "timestamp": "2025-01-15T10:30:18Z"
}
```

#### **Type 4: Final Completion**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "completed",
  "current_step": "completed",
  "progress_percentage": 100.0,
  "current_page": 5,
  "total_pages": 5,
  "processed_pages": 5,
  "failed_pages": 0,
  "cumulative_results": [
    // ... all page results
  ],
  "processing_speed": 0.38,
  "timestamp": "2025-01-15T10:30:25Z"
}
```

#### **Type 5: Heartbeat Messages**
```json
{
  "heartbeat": true,
  "timestamp": "2025-01-15T10:30:20Z"
}
```

#### **Type 6: Error Updates**
```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "failed",
  "current_step": "failed",
  "progress_percentage": 40.0,
  "processed_pages": 2,
  "failed_pages": 3,
  "error_message": "LLM processing failed: API timeout",
  "timestamp": "2025-01-15T10:30:22Z"
}
```

## 🔧 **Complete React Integration Example**

```jsx
import React, { useState, useCallback } from 'react';

const OCRProcessor = () => {
  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [streamingText, setStreamingText] = useState('');
  const [enableStreaming, setEnableStreaming] = useState(false);

  // File upload handler
  const handleFileUpload = useCallback(async (selectedFile, mode = 'basic') => {
    try {
      setStatus('uploading');
      setError(null);
      setStreamingText('');
      
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('request', JSON.stringify({ 
        mode,
        stream: enableStreaming && mode === 'llm_enhanced'
      }));

      const response = await fetch('/v1/ocr/process-stream', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `Upload failed: ${response.status}`);
      }

      const data = await response.json();
      setTaskId(data.task_id);
      setStatus('processing');
      
      // Start streaming
      connectToStream(data.task_id);
      
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  }, [enableStreaming]);

  // Streaming connection
  const connectToStream = useCallback((id) => {
    const eventSource = new EventSource(`/v1/ocr/stream/${id}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.heartbeat) return;

        // Handle real-time text streaming
        if (data.text_chunk) {
          setStreamingText(data.accumulated_text || '');
          return;
        }

        // Update progress
        setProgress(data.progress_percentage || 0);
        
        // Update results
        if (data.cumulative_results) {
          setResults(data.cumulative_results);
        }

        // Handle completion
        if (data.status === 'completed') {
          setStatus('completed');
          eventSource.close();
        } else if (data.status === 'failed') {
          setStatus('error');
          setError(data.error_message || 'Processing failed');
          eventSource.close();
        }
      } catch (error) {
        console.error('Streaming parse error:', error);
      }
    };

    eventSource.onerror = () => {
      setStatus('error');
      setError('Connection lost');
      eventSource.close();
    };

    return eventSource;
  }, []);

  // Cancel processing
  const cancelProcessing = useCallback(async () => {
    if (!taskId) return;
    
    try {
      await fetch(`/v1/ocr/tasks/${taskId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User cancelled' })
      });
      setStatus('cancelled');
    } catch (err) {
      console.error('Cancel failed:', err);
    }
  }, [taskId]);

  return (
    <div className="ocr-processor">
      {/* File Input */}
      <input
        type="file"
        accept="image/*,.pdf,.docx"
        onChange={(e) => setFile(e.target.files[0])}
        disabled={status === 'processing'}
      />
      
      {/* Mode Selection */}
      <select id="mode" disabled={status === 'processing'}>
        <option value="basic">Basic OCR</option>
        <option value="llm_enhanced">AI Enhanced</option>
      </select>
      
      {/* Streaming Toggle (only for LLM mode) */}
      <label>
        <input
          type="checkbox"
          checked={enableStreaming}
          onChange={(e) => setEnableStreaming(e.target.checked)}
          disabled={status === 'processing'}
        />
        Enable real-time text streaming (AI mode only)
      </label>
      
      {/* Process Button */}
      <button
        onClick={() => file && handleFileUpload(file, document.getElementById('mode').value)}
        disabled={!file || status === 'processing'}
      >
        {status === 'processing' ? 'Processing...' : 'Start OCR'}
      </button>
      
      {/* Cancel Button */}
      {status === 'processing' && (
        <button onClick={cancelProcessing}>Cancel</button>
      )}
      
      {/* Progress Bar */}
      {status === 'processing' && (
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${progress}%` }}
          ></div>
          <span>{Math.round(progress)}%</span>
        </div>
      )}
      
      {/* Error Display */}
      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}
      
      {/* Streaming Text Display */}
      {streamingText && status === 'processing' && (
        <div className="streaming-text">
          <h3>Live Text Extraction:</h3>
          <pre>{streamingText}<span className="cursor">▊</span></pre>
        </div>
      )}
      
      {/* Results Display */}
      {results.length > 0 && (
        <div className="results">
          <h3>Extracted Text:</h3>
          {results.map((result, index) => (
            <div key={index} className="page-result">
              <h4>Page {result.page_number}</h4>
              <pre>{result.extracted_text}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default OCRProcessor;
```

## ⚠️ **Error Handling**

### **Common Error Responses**

**File Too Large**:
```json
{
  "error": true,
  "message": "File too large. Size: 15,728,640 bytes, Max: 10,485,760 bytes",
  "status_code": 413
}
```

**Unsupported File Type**:
```json
{
  "error": true,
  "message": "Unsupported file type. MIME: text/plain, Filename: document.txt",
  "status_code": 400
}
```

**DOCX Disabled**:
```json
{
  "error": true,
  "message": "DOCX processing is currently disabled. Supported formats: images and PDFs only.",
  "status_code": 400
}
```

**Task Not Found**:
```json
{
  "error": true,
  "message": "Streaming task abc123 not found",
  "status_code": 404
}
```

### **Frontend Error Handling Best Practices**

```javascript
const handleApiError = (error, response) => {
  if (response?.status === 413) {
    return "File is too large. Please choose a smaller file.";
  } else if (response?.status === 400) {
    return error.message || "Invalid file format or request.";
  } else if (response?.status === 404) {
    return "Processing session expired. Please try again.";
  } else if (response?.status >= 500) {
    return "Server error. Please try again later.";
  } else {
    return error.message || "An unexpected error occurred.";
  }
};
```

## 🔄 **Task Management**

### **Cancel Processing**
**Endpoint**: `POST /v1/ocr/tasks/{task_id}/cancel`

```javascript
const cancelTask = async (taskId, reason = 'User cancelled') => {
  const response = await fetch(`/v1/ocr/tasks/${taskId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason })
  });
  
  if (response.ok) {
    return await response.json();
  }
  throw new Error(`Cancel failed: ${response.status}`);
};
```

## 📊 **File Type Specifications**

### **Images**
- **Formats**: JPEG, PNG, BMP, TIFF, WebP
- **Max Size**: 10MB
- **Max Pixels**: 3M pixels (auto-scaled if larger)
- **Processing Time**: 2-4 seconds

### **PDFs**
- **Max Size**: 50MB
- **Max Pages**: 20 pages
- **Processing Time**: 1.5-3 seconds per page
- **Parallel Processing**: Yes (batch optimization)

### **DOCX** (When Enabled)
- **Max Size**: 25MB
- **Processing Steps**: DOCX → PDF → OCR
- **Processing Time**: 3-5 seconds + PDF processing time
- **Requirements**: LibreOffice service must be running

## 🚀 **Performance Tips**

### **For Frontend Developers**

1. **File Validation**: Validate file size/type before upload
```javascript
const validateFile = (file) => {
  const maxSizes = {
    'image': 10 * 1024 * 1024,  // 10MB
    'pdf': 50 * 1024 * 1024,    // 50MB
    'docx': 25 * 1024 * 1024    // 25MB
  };
  
  const fileType = file.type.startsWith('image/') ? 'image' : 
                   file.type === 'application/pdf' ? 'pdf' : 'docx';
  
  if (file.size > maxSizes[fileType]) {
    throw new Error(`File too large for ${fileType}`);
  }
};
```

2. **Connection Management**: Always close EventSource connections
```javascript
useEffect(() => {
  let eventSource;
  
  if (taskId) {
    eventSource = connectToStream(taskId);
  }
  
  return () => {
    if (eventSource) {
      eventSource.close();
    }
  };
}, [taskId]);
```

3. **User Experience**: Show estimated time and progress
```javascript
const formatTimeRemaining = (seconds) => {
  if (seconds < 60) return `${Math.round(seconds)}s remaining`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${Math.round(seconds % 60)}s remaining`;
};
```

## 🔐 **DOCX Feature Flag**

### **Checking if DOCX is Enabled**

```javascript
const checkDocxSupport = async () => {
  try {
    // Test with a small DOCX file or check API docs
    const response = await fetch('/v1/health');
    const health = await response.json();
    
    // You can also test by attempting to upload a DOCX file
    // and checking for the specific error message
    return true; // Implement based on your needs
  } catch {
    return false;
  }
};
```

### **User-Friendly DOCX Handling**

```javascript
const handleDocxFile = (file) => {
  if (file.name.endsWith('.docx')) {
    alert(
      'DOCX processing is currently not available. ' +
      'Please convert your document to PDF or use images instead.'
    );
    return false;
  }
  return true;
};
```

## 📝 **TypeScript Definitions**

```typescript
// API Types
export interface UploadResponse {
  task_id: string;
  file_type: 'image' | 'pdf' | 'docx';
  processing_mode: 'basic' | 'llm_enhanced';
  status: 'processing';
  created_at: string;
  estimated_duration: number;
  file_metadata: FileMetadata;
}

export interface StreamingUpdate {
  task_id: string;
  file_type: 'image' | 'pdf' | 'docx';
  processing_mode: 'basic' | 'llm_enhanced';
  status: 'processing' | 'completed' | 'failed' | 'cancelled';
  current_step: string;
  progress_percentage: number;
  current_page: number;
  total_pages: number;
  processed_pages: number;
  failed_pages: number;
  latest_page_result?: PageResult;
  cumulative_results: PageResult[];
  estimated_time_remaining?: number;
  error_message?: string;
  timestamp: string;
  // Text streaming fields (when stream: true)
  text_chunk?: string;
  accumulated_text?: string;
}

export interface PageResult {
  page_number: number;
  extracted_text: string;
  processing_time: number;
  success: boolean;
  error_message?: string;
}

export interface FileMetadata {
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  detected_file_type: string;
  image_dimensions?: { width: number; height: number };
  pdf_page_count?: number;
  docx_page_count?: number;
}
```

## 🌟 **Real-time Text Streaming Example**

### **Advanced Streaming Implementation**

```javascript
// Enhanced component with real-time text streaming
const StreamingOCRExample = () => {
  const [streamingChunks, setStreamingChunks] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  
  const processWithTextStreaming = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('request', JSON.stringify({
      mode: 'llm_enhanced',
      stream: true,  // Enable character-by-character streaming
      prompt: 'Extract all text accurately'
    }));
    
    const response = await fetch('/v1/ocr/process-stream', {
      method: 'POST',
      body: formData
    });
    
    const { task_id } = await response.json();
    
    // Connect to streaming
    const eventSource = new EventSource(`/v1/ocr/stream/${task_id}`);
    setIsStreaming(true);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.text_chunk) {
        // Animate text appearance
        setStreamingChunks(prev => [...prev, data.text_chunk]);
      }
      
      if (data.status === 'completed') {
        setIsStreaming(false);
        eventSource.close();
      }
    };
  };
  
  return (
    <div>
      {isStreaming && (
        <div className="streaming-container">
          {streamingChunks.map((chunk, i) => (
            <span 
              key={i} 
              className="text-chunk"
              style={{
                animationDelay: `${i * 0.05}s`,
                opacity: 0,
                animation: 'fadeIn 0.3s forwards'
              }}
            >
              {chunk}
            </span>
          ))}
          <span className="typing-cursor">|</span>
        </div>
      )}
    </div>
  );
};
```

### **CSS for Streaming Animation**

```css
@keyframes fadeIn {
  to { opacity: 1; }
}

.typing-cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.streaming-container {
  font-family: monospace;
  line-height: 1.6;
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}
```

## 🎯 **Summary**

This OCR API provides:
- ✅ **Simple Upload**: Single endpoint for all file types
- ✅ **Real-time Progress**: Server-Sent Events streaming
- ✅ **Character-by-Character Text Streaming**: Live text output for LLM mode
- ✅ **Flexible Processing**: Basic and AI-enhanced modes
- ✅ **Error Handling**: Clear error messages and status codes
- ✅ **Task Management**: Cancel processing anytime
- ✅ **Type Safety**: Full TypeScript support

Perfect for building responsive, user-friendly OCR applications with real-time feedback! 🚀 