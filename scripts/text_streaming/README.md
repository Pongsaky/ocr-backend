# Text Streaming Test Scripts

This directory contains test scripts for validating the streaming text functionality of the OCR backend service.

## Scripts Overview

### Main Test Scripts
- **`test_streaming_text.py`** - Comprehensive test script with colored output, performance comparison, and full testing capabilities
- **`quick_stream_test.py`** - Focused test script showing real-time streaming updates with simple output
- **`demo_streaming.py`** - Clean demo script demonstrating streaming text output in real-time

### Debug and Development Scripts
- **`debug_pdf_streaming.py`** - Debug script specifically for PDF streaming functionality
- **`basic_stream_test.py`** - Basic streaming test without LLM enhancement
- **`test_streaming.py`** - Additional streaming test script
- **`test_app_streaming.py`** - Application-level streaming test
- **`test_unified_streaming.py`** - Unified API streaming test
- **`stream_test.py`** - General stream testing utility

## Usage

All scripts can be run with Poetry from the project root:

```bash
# Comprehensive testing (recommended)
poetry run python scripts/text_streaming/test_streaming_text.py

# Quick test with real-time output
poetry run python scripts/text_streaming/quick_stream_test.py

# Simple demonstration
poetry run python scripts/text_streaming/demo_streaming.py

# Debug PDF streaming specifically
poetry run python scripts/text_streaming/debug_pdf_streaming.py
```

## Test Options

The main test script supports various options:

```bash
# Test specific file types
poetry run python scripts/text_streaming/test_streaming_text.py --test image
poetry run python scripts/text_streaming/test_streaming_text.py --test pdf
poetry run python scripts/text_streaming/test_streaming_text.py --test all

# Custom file paths
poetry run python scripts/text_streaming/test_streaming_text.py --image /path/to/image.png --pdf /path/to/document.pdf

# Custom prompt
poetry run python scripts/text_streaming/test_streaming_text.py --prompt "Custom OCR prompt"
```

## Features Tested

- ✅ Real-time text streaming for images
- ✅ Real-time text streaming for PDFs
- ✅ Performance comparison between streaming and non-streaming modes
- ✅ Progress tracking and status updates
- ✅ Error handling and edge cases
- ✅ Thai language text support