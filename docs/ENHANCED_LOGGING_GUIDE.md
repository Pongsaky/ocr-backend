# Enhanced Logging System Guide

## 🎯 Overview

The OCR Backend API now features a production-grade logging system with advanced capabilities for debugging, monitoring, and performance analysis.

## 🚀 Key Features

### ✅ **Enhanced Log Format**
- **Function names and line numbers** for precise debugging
- **Request ID tracking** across the entire request lifecycle
- **Millisecond timestamps** for precise timing
- **Performance metrics** built-in

### ✅ **Production-Ready Configuration**
- **100MB per file** (vs 10MB previously)
- **30 backup files** (3GB total retention vs 50MB)
- **~30-60 days retention** (vs 1-2 days)
- **Automatic compression** of rotated logs

### ✅ **Performance Optimizations**
- **Async logging** prevents I/O blocking
- **Queue-based processing** (10,000 message buffer)
- **Background thread** for log writes
- **Graceful degradation** under load

### ✅ **Security & Privacy**
- **Sensitive data sanitization** (API keys, tokens, base64 images)
- **Configurable sanitization patterns**
- **PII protection** (email masking)

## 📋 **Log Format Comparison**

### Before:
```
2025-06-18 12:09:01 - app.main - INFO - Application startup initiated...
```

### After:
```
2025-06-18 12:09:01.123 - app.main:startup_event:45 - INFO - [abc-123] Application startup initiated...
│                    │     │              │         │     │        │
│                    │     │              │         │     │        └─ Message
│                    │     │              │         │     └─ Request ID
│                    │     │              │         └─ Log Level  
│                    │     │              └─ Line Number
│                    │     └─ Function Name
│                    └─ Milliseconds
└─ Timestamp
```

## ⚙️ **Configuration Options**

### Environment Variables

```bash
# Basic Settings
LOG_LEVEL=INFO                              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=./logs/ocr-backend.log            # Log file path
LOG_MAX_SIZE=104857600                     # 100MB per file
LOG_BACKUP_COUNT=30                        # 30 backup files (3GB total)

# Enhanced Features
LOG_ENABLE_COMPRESSION=True                # Compress rotated logs (.gz)
LOG_ASYNC_ENABLED=True                     # Enable async logging
LOG_SANITIZE_SENSITIVE=True                # Remove sensitive data
LOG_QUEUE_SIZE=10000                       # Async queue buffer size

# Format Settings
LOG_DATE_FORMAT="%Y-%m-%d %H:%M:%S"       # Date format
LOG_FORMAT="%(asctime)s.%(msecs)03d - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - [%(request_id)s] %(message)s"
```

### Development vs Production

```python
# Development (current defaults)
LOG_LEVEL=DEBUG
LOG_MAX_SIZE=10485760          # 10MB
LOG_BACKUP_COUNT=5             # ~50MB total
LOG_ASYNC_ENABLED=False        # Simpler debugging

# Production (recommended)
LOG_LEVEL=INFO
LOG_MAX_SIZE=104857600         # 100MB  
LOG_BACKUP_COUNT=30            # ~3GB total
LOG_ASYNC_ENABLED=True         # Better performance
```

## 🔧 **Usage Examples**

### Basic Logging
```python
from app.logger_config import get_logger

logger = get_logger(__name__)
logger.info("Processing started")
logger.warning("Image size exceeds recommended limit")
logger.error("External API call failed", exc_info=True)
```

### Request ID Tracking
```python
from app.logger_config import set_request_id, get_request_id

# Set request ID (automatic in middleware)
set_request_id("req-abc-123")

# All subsequent logs will include this ID
logger.info("This log will include [req-abc-123]")

# Get current request ID
current_id = get_request_id()
```

### Performance Logging
```python
from app.logger_config import log_performance
import time

start_time = time.time()
# ... do some work ...
log_performance(logger, "image_processing", start_time, 
                image_size="2MB", scaling_factor=0.75)
# Logs: PERF: image_processing completed in 1.234s image_size=2MB scaling_factor=0.75
```

### Memory Monitoring
```python
from app.logger_config import log_memory_usage

log_memory_usage(logger, "after_image_processing")
# Logs: MEMORY: 156.7MB RSS after_image_processing
```

## 📊 **Log Analysis**

### Request Tracing
Track a complete request lifecycle:
```bash
grep "req-abc-123" logs/ocr-backend.log
# Shows all logs for that specific request across all modules
```

### Performance Analysis
```bash
grep "PERF:" logs/ocr-backend.log | tail -20
# Shows recent performance metrics
```

### Error Investigation
```bash
grep "ERROR\|CRITICAL" logs/ocr-backend.log.1 logs/ocr-backend.log
# Find all errors across current and previous log
```

## 🔍 **Sensitive Data Sanitization**

The system automatically removes/masks:

### Before Sanitization:
```
INFO - Processing image data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA... (500+ chars)
INFO - API key: sk-1234567890abcdef1234567890abcdef
INFO - User email: john.doe@company.com
```

### After Sanitization:
```
INFO - Processing image [BASE64_IMAGE_DATA]
INFO - api_key="[REDACTED]"
INFO - User email: john.doe***@company.com
```

## 📈 **Storage Management**

### Current Storage Usage:
```bash
# Check log directory size
du -h logs/
# 3.2G    logs/

# List log files with sizes
ls -lah logs/
# -rw-r--r-- 1 user staff  45M Jun 18 12:40 ocr-backend.log
# -rw-r--r-- 1 user staff  89M Jun 18 10:30 ocr-backend.log.1.gz
# -rw-r--r-- 1 user staff  92M Jun 18 08:15 ocr-backend.log.2.gz
```

### Automatic Cleanup:
- **Compression**: Old logs compressed to ~10-20% original size
- **Rotation**: When current log reaches 100MB, it's rotated
- **Retention**: Only last 30 files kept (30-60 days typically)

## 🛠 **Troubleshooting**

### High Log Volume
```bash
# Check if async logging is enabled
grep "LOG_ASYNC_ENABLED" config/settings.py

# Monitor queue size (if async enabled)
# Queue drops messages when full to prevent blocking
```

### Missing Request IDs
```bash
# Check if middleware is properly registered
grep "RequestIDMiddleware" app/main.py

# Verify logs show [N/A] for background tasks (expected)
grep "\[N/A\]" logs/ocr-backend.log
```

### Performance Issues
```bash
# Check if compression is causing CPU spikes
LOG_ENABLE_COMPRESSION=False

# Reduce queue size if memory usage is high
LOG_QUEUE_SIZE=5000
```

## 🚀 **Benefits Summary**

| Feature | Before | After | Benefit |
|---------|--------|-------|---------|
| **Retention** | 1-2 days | 30-60 days | Long-term debugging |
| **File Size** | 10MB | 100MB | Fewer rotations |
| **Total Storage** | 50MB | 3GB | Complete history |
| **Function Info** | ❌ | ✅ | Precise debugging |
| **Request Tracing** | ❌ | ✅ | End-to-end tracking |
| **Performance Logs** | ❌ | ✅ | Built-in metrics |
| **Async Processing** | ❌ | ✅ | No I/O blocking |
| **Data Sanitization** | ❌ | ✅ | Security compliance |
| **Compression** | ❌ | ✅ | 80% space savings |

## 🎯 **Next Steps**

The enhanced logging system is now ready for production use with:
- ✅ Better debugging capabilities
- ✅ Long-term log retention
- ✅ Performance monitoring
- ✅ Security compliance
- ✅ Production-ready performance

Monitor the logs directory size and adjust `LOG_BACKUP_COUNT` if needed for your specific retention requirements! 