# DOCX Processing Feature Flag

## Overview
The DOCX processing feature is **disabled by default** and can be enabled/disabled using a feature flag. This allows you to control when DOCX functionality is available without removing the code.

## Current Status
- **Status**: 🔴 **DISABLED** (by default)
- **Code**: ✅ **PRESERVED** (all LibreOffice implementation intact)
- **Testing**: ✅ **READY** (when enabled)

## Configuration

### Environment Variable
```bash
# Disable DOCX processing (default)
ENABLE_DOCX_PROCESSING=false

# Enable DOCX processing
ENABLE_DOCX_PROCESSING=true
```

### Local Development
```bash
# In your shell or .env file
export ENABLE_DOCX_PROCESSING=true
```

### Production Deployment
Update your `production.env` file:
```bash
# Enable DOCX in production
ENABLE_DOCX_PROCESSING=true
```

## How It Works

### When DISABLED (Default)
- ❌ DOCX files are rejected with error: `"DOCX processing is currently disabled"`
- ✅ Images and PDFs work normally
- ✅ All DOCX code remains intact but unused

### When ENABLED
- ✅ Full DOCX processing with LibreOffice conversion
- ✅ DOCX → PDF → OCR pipeline
- ✅ Streaming progress updates
- ✅ Both basic and LLM-enhanced modes

## Prerequisites for Enabling

### 1. LibreOffice Service Required
```bash
# Start LibreOffice Docker service
docker run -d --name libreoffice-converter --rm -p 8080:2004 libreofficedocker/libreoffice-unoserver:3.19
```

### 2. Or Use Full Docker Compose
```bash
docker-compose up -d
```

## Testing DOCX Feature

### Test When Disabled
```bash
curl -X POST "http://localhost:8000/v1/ocr/process-stream" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.docx" \
  -F "request={\"mode\": \"basic\"}"

# Expected: 400 error with "DOCX processing is currently disabled"
```

### Test When Enabled
```bash
# 1. Enable the feature
export ENABLE_DOCX_PROCESSING=true

# 2. Start LibreOffice service
docker run -d --name libreoffice-converter --rm -p 8080:2004 libreofficedocker/libreoffice-unoserver:3.19

# 3. Restart OCR backend

# 4. Test DOCX processing
curl -X POST "http://localhost:8000/v1/ocr/process-stream" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.docx" \
  -F "request={\"mode\": \"basic\"}"

# Expected: Success with task_id for streaming
```

## Implementation Details

### Files Modified
- `config/settings.py` - Added `ENABLE_DOCX_PROCESSING` setting
- `production.env.example` - Added feature flag configuration
- `app/services/unified_stream_processor.py` - Added feature flag checks

### Code Preserved
- ✅ `app/services/libreoffice_client.py` - Complete LibreOffice HTTP client
- ✅ `app/services/docx_ocr_service.py` - Full DOCX processing pipeline
- ✅ `docker-compose.yml` - LibreOffice service configuration
- ✅ All LibreOffice settings and configurations

## Future Activation

When you're ready to deploy DOCX processing:

1. **Set environment variable**: `ENABLE_DOCX_PROCESSING=true`
2. **Deploy LibreOffice service**: Ensure LibreOffice container is running
3. **Restart OCR backend**: To pick up new environment variable
4. **Test functionality**: Verify DOCX processing works end-to-end

All the code is ready and waiting! 🚀

## Benefits of This Approach

- ✅ **Code Preservation**: No LibreOffice code deleted
- ✅ **Clean Disable**: Clear error messages when disabled
- ✅ **Easy Enable**: Single environment variable flip
- ✅ **Production Ready**: When LibreOffice infrastructure is ready
- ✅ **Gradual Rollout**: Enable for specific environments first 