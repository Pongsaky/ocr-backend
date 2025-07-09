# Image Scaling for LLM Context Limits

## Overview

The OCR Backend API now includes automatic image validation and scaling functionality to ensure images stay within the LLM context length limits (8192 tokens). Images that exceed 4,000,000 pixels (width × height) are automatically scaled down while maintaining their aspect ratio and quality.

## Key Features

### 🎯 **Automatic Scaling**
- Images exceeding 4M pixels are automatically scaled down
- Maintains original aspect ratio
- High-quality scaling using LANCZOS resampling
- Optimized for LLM processing efficiency

### 📊 **Smart Validation**
- Pre-processing pixel count validation
- Calculates optimal scale factors
- Preserves image quality while reducing size

### 🔧 **Configurable Settings**
- Customizable pixel threshold
- Adjustable scaling quality
- Multiple resampling algorithms
- Enable/disable scaling feature

## Configuration

### Environment Variables

```bash
# Image scaling settings
MAX_IMAGE_PIXELS=4000000          # Maximum allowed pixels (4M default)
IMAGE_SCALING_QUALITY=95          # JPEG quality for scaled images (95 default)
IMAGE_SCALING_RESAMPLE=LANCZOS    # Resampling algorithm (LANCZOS default)
ENABLE_IMAGE_SCALING=True         # Enable/disable scaling (True default)
```

### Available Resampling Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| `LANCZOS` | High-quality, slower | Best for photos and detailed images |
| `BICUBIC` | Good quality, medium speed | General purpose |
| `BILINEAR` | Fair quality, fast | Simple images |
| `NEAREST` | Low quality, fastest | Pixel art or simple graphics |

## How It Works

### 1. Image Validation
```python
# Check if image exceeds pixel threshold
pixel_count = width × height
if pixel_count > MAX_IMAGE_PIXELS:
    # Scaling required
```

### 2. Scale Factor Calculation
```python
# Calculate scale factor to achieve target pixels
scale_factor = sqrt(target_pixels / current_pixels)
new_width = int(original_width × scale_factor)
new_height = int(original_height × scale_factor)
```

### 3. Automatic Processing
- **PDF Processing**: Images extracted from PDFs are automatically validated and scaled
- **Single Image OCR**: Uploaded images are scaled before processing
- **LLM OCR**: Images are scaled before sending to LLM APIs

## API Integration

### All OCR Endpoints Support Scaling

#### 1. **Single Image OCR**
```bash
POST /v1/ocr/process
POST /v1/ocr/process/sync
```

#### 2. **PDF OCR**
```bash
POST /v1/pdf/process
POST /v1/pdf/process/sync
```

#### 3. **LLM-Enhanced OCR**
```bash
POST /v1/ocr/process-with-llm
POST /v1/ocr/process-with-llm/sync
POST /v1/pdf/process-with-llm
POST /v1/pdf/process-with-llm/sync
```

### Response Metadata

When scaling is applied, additional metadata is included in logs:

```json
{
  "scaling_applied": true,
  "original_dimensions": [3000, 4000],
  "scaled_dimensions": [2062, 2749],
  "original_pixel_count": 12000000,
  "scaled_pixel_count": 5668438,
  "scale_factor": 0.6875
}
```

## Examples

### Example 1: Large Image Scaling

**Input Image**: 3000×4000 pixels (12M pixels)
- Exceeds 4M pixel limit
- **Scale factor**: 0.577
- **Output**: 1732×2309 pixels (≈4M pixels)
- **Quality**: Maintains visual quality with LANCZOS resampling

### Example 2: PDF Page Processing

**PDF Page**: 2481×3508 pixels (8.7M pixels)
- Automatically scaled during PDF conversion
- **Scale factor**: 0.678
- **Output**: 1682×2378 pixels (≈4M pixels)
- **Result**: Improved LLM processing speed and accuracy

## Benefits

### 🚀 **Performance Improvements**
- **Faster LLM Processing**: Smaller images = faster token processing
- **Memory Efficiency**: Reduced memory usage during processing
- **Better Throughput**: More images processed per second

### 🎯 **Quality Assurance**
- **Maintains Readability**: Text remains clear and legible
- **Preserves Details**: Important visual information retained
- **Consistent Results**: Standardized input sizes for LLM

### 🔒 **Context Limit Compliance**
- **Token Efficiency**: Ensures images fit within 8192 token limit (4M pixel max)
- **Predictable Processing**: Consistent performance across different image sizes
- **Error Prevention**: Avoids context length exceeded errors

## Monitoring and Logging

### Log Messages

```
INFO: Page 1 scaled: 8,703,348 -> 3,997,904 pixels (factor: 0.678)
DEBUG: Image validation: image.png has 2,000,000 pixels (max: 4,000,000) - VALID
INFO: Image scaled for processing: 10,000,000 -> 4,000,000 pixels (factor: 0.632)
```

### Performance Metrics

- Scaling success rate
- Processing time improvements
- Memory usage reduction
- LLM response times

## Troubleshooting

### Common Issues

#### 1. **Scaling Disabled**
```
ERROR: Image scaling is disabled in settings
```
**Solution**: Set `ENABLE_IMAGE_SCALING=True`

#### 2. **Invalid Resampling Method**
```
ERROR: Unknown resampling method: INVALID
```
**Solution**: Use valid methods: LANCZOS, BICUBIC, BILINEAR, NEAREST

#### 3. **Memory Issues**
```
ERROR: Failed to scale image: Out of memory
```
**Solution**: Increase system memory or reduce batch size

### Best Practices

1. **Monitor Scaling Frequency**: Check how often images need scaling  
2. **Adjust Threshold**: Fine-tune `MAX_IMAGE_PIXELS` (current: 4M) based on your use case
3. **Quality vs Speed**: Choose appropriate resampling method
4. **Log Analysis**: Review scaling logs for optimization opportunities

## Technical Implementation

The image scaling functionality is implemented in:
- `app/utils/image_utils.py`: Core scaling functions
- `app/services/pdf_ocr_service.py`: PDF processing integration
- `app/services/external_ocr_service.py`: Single image processing
- `config/settings.py`: Configuration management

For detailed technical information, see the source code documentation. 