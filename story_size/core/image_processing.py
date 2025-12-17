"""
Image processing module for extracting and analyzing images from documents.
Supports PDF and DOCX files with OCR capabilities.
"""

import fitz  # PyMuPDF
import easyocr
import zipfile
from PIL import Image
from pathlib import Path
from typing import List, Dict, Any
import io
import numpy as np
import logging
import os
import sys

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image extraction and analysis from documents."""

    def __init__(self, languages: List[str] = None):
        """
        Initialize the image processor.

        Args:
            languages: List of language codes for OCR (default: ['en'])
        """
        self.languages = languages or ['en']
        self._ocr_reader = None
        self._ocr_initialized = False

    @property
    def ocr_reader(self):
        """Lazy initialization of OCR reader."""
        if not self._ocr_initialized:
            # Completely suppress all output during OCR initialization
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            original_stdout_flush = sys.stdout.flush if hasattr(sys.stdout, 'flush') else lambda: None
            original_stderr_flush = sys.stderr.flush if hasattr(sys.stderr, 'flush') else lambda: None

            try:
                # Redirect all output to devnull
                with open(os.devnull, 'w') as devnull:
                    sys.stdout = devnull
                    sys.stderr = devnull

                    # Also suppress logging temporarily
                    logging.getLogger("easyocr").setLevel(logging.CRITICAL)

                    self._ocr_reader = easyocr.Reader(
                        self.languages,
                        gpu=False,
                        download_enabled=True,
                        verbose=False
                    )

                self._ocr_initialized = True
                logger.info(f"OCR initialized for languages: {self.languages}")

            except Exception as e:
                # Silently handle OCR initialization failure - it's optional for our use case
                self._ocr_reader = None
                self._ocr_initialized = True  # Don't retry

                # Only log at debug level to avoid cluttering output
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"OCR initialization failed (non-critical): {e}")

            finally:
                # Always restore stdout and stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr

                # Restore logging level
                logging.getLogger("easyocr").setLevel(logging.NOTSET)

        return self._ocr_reader

    def extract_pdf_images(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract images from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of dictionaries containing image data and metadata
        """
        images = []

        try:
            doc = fitz.open(pdf_path)
            logger.info(f"Processing PDF: {pdf_path.name} with {len(doc)} pages")

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        # Skip CMYK images (not supported by PIL)
                        if pix.n - pix.alpha < 4:
                            # Convert to PIL Image
                            img_data = pix.tobytes("png")
                            pil_image = Image.open(io.BytesIO(img_data))

                            images.append({
                                'page': page_num,
                                'index': img_index,
                                'image': pil_image,
                                'size': (pix.width, pix.height),
                                'position': img[:4] if len(img) > 4 else None,
                                'format': 'PNG'
                            })

                        pix = None  # Free memory

                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                        continue

            doc.close()
            logger.info(f"Extracted {len(images)} images from {pdf_path.name}")

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")

        return images

    def extract_docx_images(self, docx_path: Path) -> List[Dict[str, Any]]:
        """
        Extract images from a DOCX file.

        Args:
            docx_path: Path to the DOCX file

        Returns:
            List of dictionaries containing image data and metadata
        """
        images = []

        try:
            logger.info(f"Processing DOCX: {docx_path.name}")

            # DOCX is a ZIP file
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                # Look for image files in media folder
                for file_info in docx_zip.filelist:
                    if file_info.filename.startswith('word/media/'):
                        try:
                            # Extract image
                            img_data = docx_zip.read(file_info.filename)
                            pil_image = Image.open(io.BytesIO(img_data))

                            # Extract image format from filename
                            file_ext = Path(file_info.filename).suffix.lower()

                            images.append({
                                'filename': file_info.filename,
                                'image': pil_image,
                                'size': pil_image.size,
                                'format': file_ext.upper().replace('.', '') if file_ext else 'UNKNOWN'
                            })

                        except Exception as e:
                            logger.warning(f"Failed to extract image {file_info.filename}: {e}")
                            continue

            logger.info(f"Extracted {len(images)} images from {docx_path.name}")

        except Exception as e:
            logger.error(f"Failed to process DOCX {docx_path}: {e}")

        return images

    def extract_text_from_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract text from an image using OCR.

        Args:
            image: PIL Image object

        Returns:
            Dictionary with OCR results
        """
        if not self.ocr_reader:
            return {
                'text_blocks': [],
                'full_text': '',
                'has_text': False,
                'error': 'OCR not initialized'
            }

        try:
            # Convert PIL Image to numpy array for EasyOCR
            image_array = np.array(image)

            # Extract text
            results = self.ocr_reader.readtext(image_array)

            # Process results
            text_blocks = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence results
                    text_blocks.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })

            full_text = '\n'.join([block['text'] for block in text_blocks])

            return {
                'text_blocks': text_blocks,
                'full_text': full_text,
                'has_text': len(text_blocks) > 0,
                'block_count': len(text_blocks),
                'total_chars': len(full_text)
            }

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {
                'text_blocks': [],
                'full_text': '',
                'has_text': False,
                'error': str(e)
            }

    def analyze_image_for_story_estimation(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze an image to determine complexity indicators for story estimation.

        Args:
            image: PIL Image object

        Returns:
            Dictionary with analysis results
        """
        width, height = image.size

        # Basic image analysis
        analysis = {
            'size': (width, height),
            'width': width,
            'height': height,
            'aspect_ratio': width / height if height > 0 else 1,
            'is_large': width > 800 or height > 600,  # Large images might be complex
            'is_wide': width / height > 2,  # Wide images might be timelines/diagrams
            'is_tall': height / width > 2,  # Tall images might be forms/flows
            'is_small': width < 200 and height < 200,  # Small images might be icons
        }

        # Try OCR
        ocr_result = self.extract_text_from_image(image)
        analysis.update({
            'has_text': ocr_result.get('has_text', False),
            'text_length': ocr_result.get('total_chars', 0),
            'text_block_count': ocr_result.get('block_count', 0)
        })

        # Heuristics for complexity estimation
        complexity_indicators = {
            'has_diagram': not analysis['has_text'] and (width > 400 and height > 300),
            'has_table': analysis['has_text'] and analysis['text_block_count'] > 5,
            'has_screenshot': analysis['is_large'] and analysis['has_text'],
            'has_form': analysis['is_tall'] and analysis['text_block_count'] > 3,
            'has_workflow': analysis['is_wide'] and analysis['text_block_count'] > 3,
            'has_icon': analysis['is_small'],
            'has_large_text': analysis['text_length'] > 500,
            'has_detailed_ui': analysis['has_text'] and analysis['text_block_count'] > 10
        }

        analysis['complexity_indicators'] = complexity_indicators
        analysis['complexity_score'] = sum(complexity_indicators.values())

        # Determine image type based on characteristics
        image_type = 'unknown'
        if complexity_indicators['has_diagram']:
            image_type = 'diagram'
        elif complexity_indicators['has_workflow']:
            image_type = 'workflow'
        elif complexity_indicators['has_table']:
            image_type = 'table'
        elif complexity_indicators['has_form']:
            image_type = 'form'
        elif complexity_indicators['has_screenshot']:
            image_type = 'screenshot'
        elif complexity_indicators['has_icon']:
            image_type = 'icon'
        elif analysis['has_text']:
            image_type = 'text_document'

        analysis['image_type'] = image_type

        # Estimate complexity factors
        complexity_factors = {
            'ui_complexity': 1 if complexity_indicators['has_detailed_ui'] else 0,
            'logic_complexity': 1 if complexity_indicators['has_workflow'] or complexity_indicators['has_diagram'] else 0,
            'data_complexity': 1 if complexity_indicators['has_table'] else 0,
            'integration_complexity': 1 if complexity_indicators['has_screenshot'] else 0,
            'validation_complexity': 1 if complexity_indicators['has_form'] else 0
        }

        analysis['complexity_factors'] = complexity_factors
        analysis['total_complexity_factor'] = sum(complexity_factors.values())

        return analysis