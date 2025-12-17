# Image Support Integration Guide

This guide explains how to integrate the new image extraction and OCR capabilities into your story size estimation workflow.

## Overview

The story size estimator now supports:
- **Image extraction** from PDF and DOCX files
- **OCR (Optical Character Recognition)** to extract text from images
- **Visual complexity analysis** to enhance story point estimates
- **Heuristic-based image type detection** (diagrams, screenshots, forms, etc.)

## Installation

1. Install the required dependencies:
```bash
# Activate virtual environment
venv\Scripts\activate

# Install new dependencies
pip install pymupdf easyocr pillow numpy
```

2. Verify installation:
```bash
python test_image_support_simple.py
```

## Integration Steps

### 1. Update Your Code

Replace the existing imports:

```python
# Old imports
from story_size.core.docs import read_documents_limited
from story_size.core.ai_client import score_factors

# New imports with image support
from story_size.core.docs_enhanced import read_documents_with_images
from story_size.core.ai_client_enhanced import score_factors_with_images
```

### 2. Modify Document Processing

Change from:
```python
doc_text = read_documents_limited(docs_dir, max_content_length=30000)
```

To:
```python
doc_result = read_documents_with_images(docs_dir, max_content_length=30000)
doc_text = doc_result['text_content']
image_analysis = doc_result  # Contains image metadata and analysis
```

### 3. Update AI Scoring

Change from:
```python
factors, score_explanations = score_factors(doc_text, code_analysis_summary, {}, config_data)
```

To:
```python
factors, score_explanations = score_factors_with_images(
    doc_text,
    code_analysis_summary,
    {},
    config_data,
    image_analysis=image_analysis
)
```

## API Reference

### `read_documents_with_images(docs_dir, max_content_length=50000)`

Returns a dictionary with:
- `text_content`: Concatenated text from all documents
- `image_analysis`: List of image analysis results
- `total_images`: Total number of images found
- `images_with_text`: Number of images containing text
- `total_ocr_chars`: Total characters extracted via OCR
- `complexity_indicators`: Summary of visual elements (diagrams, tables, etc.)
- `total_image_complexity`: Aggregate complexity score from all images
- `files_processed`: Number of files processed

### `score_factors_with_images(doc_text, code_summary, metrics, config_data, image_analysis=None)`

Same as `score_factors` but with additional parameter:
- `image_analysis`: Optional image analysis results from `read_documents_with_images`

## Image Analysis Features

### Image Types Detected
- **Diagrams/Charts**: Visual representations of processes or data
- **Tables**: Structured data displays
- **Screenshots**: UI captures or system interfaces
- **Forms**: Input fields and validation layouts
- **Workflows**: Process flow diagrams
- **Icons**: Small UI elements

### Complexity Factors
The system analyzes images to determine:
- **UI Complexity**: Detailed screenshots vs simple interfaces
- **Logic Complexity**: Diagrams and workflows
- **Data Complexity**: Tables and data structures
- **Integration Complexity**: System screenshots
- **Validation Complexity**: Forms with input fields

### OCR Integration
- Extracts text from images when available
- Adds OCR text to document content for AI analysis
- Filters low-confidence OCR results (< 50% confidence)
- Preserves formatting and structure when possible

## Usage Example

```python
from pathlib import Path
from story_size.core.docs_enhanced import read_documents_with_images
from story_size.core.ai_client_enhanced import score_factors_with_images

# Process documents with image support
docs_dir = Path("path/to/your/documents")
doc_result = read_documents_with_images(docs_dir)

# Access results
print(f"Found {doc_result['total_images']} images")
print(f"Complexity indicators: {doc_result['complexity_indicators']}")

# Use in AI scoring
factors, explanations = score_factors_with_images(
    doc_text=doc_result['text_content'],
    code_summary={},
    metrics={},
    config_data=config,
    image_analysis=doc_result
)
```

## Troubleshooting

### OCR Issues
If OCR fails to initialize:
1. Check that all dependencies are installed
2. Ensure you have sufficient disk space (OCR downloads models on first run)
3. Run with `PYTHONIOENCODING=utf-8` on Windows if you see encoding errors

### Performance Considerations
- Image extraction adds processing time
- OCR can be resource-intensive for large documents
- Consider reducing `max_content_length` if experiencing timeouts
- The system gracefully handles OCR failures and continues processing

### Memory Usage
- Large images are automatically resized
- PDF pages are processed individually to manage memory
- OCR results are cached to avoid redundant processing

## Configuration

You can adjust these parameters in your configuration:

```yaml
# Optional: Adjust OCR behavior
image_processing:
  ocr_confidence_threshold: 0.5  # Minimum confidence for OCR results
  max_ocr_chars_per_image: 10000  # Limit OCR text extraction
  max_image_size: [2000, 2000]     # Maximum image dimensions

# Optional: Adjust content limits
document_processing:
  max_content_length: 50000       # Total characters limit
  max_pdf_chars: 10000           # Per-PDF character limit
  max_docx_chars: 15000          # Per-DOCX character limit
```

## Testing

Run the test suite to verify functionality:
```bash
python test_image_support_simple.py
```

This will:
1. Initialize the image processor
2. Test PDF image extraction
3. Test enhanced document reading
4. Verify OCR functionality