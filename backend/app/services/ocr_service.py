"""
PDF Extraction and OCR Service for Sovereign Health Twin.
Supports digital PDFs, scanned/image documents, multi-page page-boundary preservation,
password detection, corruption handling, and pluggable OCR processing.
"""

import io
import os
from typing import Dict, Any, List, Optional, Callable
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from PIL import Image

# Global pluggable OCR hook for tests or custom OCR engines
_CUSTOM_OCR_HANDLER: Optional[Callable[[bytes, str], str]] = None


def register_ocr_handler(handler: Optional[Callable[[bytes, str], str]]):
    """Registers a custom OCR function: handler(file_bytes, filename) -> str."""
    global _CUSTOM_OCR_HANDLER
    _CUSTOM_OCR_HANDLER = handler


def get_ocr_handler() -> Optional[Callable[[bytes, str], str]]:
    return _CUSTOM_OCR_HANDLER


def is_tesseract_available() -> bool:
    """Checks whether pytesseract and the tesseract binary are available."""
    try:
        import pytesseract
        # Quick check if tesseract binary can be executed
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def run_pytesseract_on_image(img: Image.Image) -> str:
    """Invokes pytesseract on a PIL Image if installed."""
    try:
        import pytesseract
        return pytesseract.image_to_string(img)
    except Exception as e:
        return ""


def extract_document_text(file_bytes: bytes, filename: str, ext: str) -> Dict[str, Any]:
    """
    Extracts text from PDF or image documents.
    Detects encryption, corruption, scanned pages, and applies OCR when needed and available.
    Preserves page boundaries and line formatting.
    """
    clean_ext = ext.lower().strip()
    if clean_ext == ".pdf":
        return _extract_pdf_content(file_bytes, filename)
    elif clean_ext in [".png", ".jpg", ".jpeg"]:
        return _extract_image_content(file_bytes, filename, clean_ext)
    else:
        return {
            "text": "",
            "pages": [],
            "total_words": 0,
            "is_scanned": False,
            "ocr_applied": False,
            "ocr_available": False,
            "ocr_message": None,
            "error": f"Unsupported file extension '{clean_ext}'.",
            "is_encrypted": False,
            "is_corrupted": False,
        }


def _extract_pdf_content(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Extracts text from PDF with full error handling and scanned page fallback."""
    if not file_bytes:
        return {
            "text": "",
            "pages": [],
            "total_words": 0,
            "is_scanned": False,
            "ocr_applied": False,
            "ocr_available": False,
            "ocr_message": None,
            "error": "Document is empty (0 bytes).",
            "is_encrypted": False,
            "is_corrupted": True,
        }

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        return {
            "text": "",
            "pages": [],
            "total_words": 0,
            "is_scanned": False,
            "ocr_applied": False,
            "ocr_available": False,
            "ocr_message": None,
            "error": f"Malformed or corrupted PDF document: {str(e)}",
            "is_encrypted": False,
            "is_corrupted": True,
        }

    # 1. Password detection
    if reader.is_encrypted:
        try:
            # Try blank password
            decrypt_res = reader.decrypt("")
            if decrypt_res == 0:  # Decryption failed
                return {
                    "text": "",
                    "pages": [],
                    "total_words": 0,
                    "is_scanned": False,
                    "ocr_applied": False,
                    "ocr_available": False,
                    "ocr_message": None,
                    "error": "Document is password-protected and cannot be extracted without the decryption password.",
                    "is_encrypted": True,
                    "is_corrupted": False,
                }
        except Exception:
            return {
                "text": "",
                "pages": [],
                "total_words": 0,
                "is_scanned": False,
                "ocr_applied": False,
                "ocr_available": False,
                "ocr_message": None,
                "error": "Document is password-protected and cannot be extracted without the decryption password.",
                "is_encrypted": True,
                "is_corrupted": False,
            }

    # 2. Check page count
    total_page_count = len(reader.pages)
    if total_page_count == 0:
        return {
            "text": "",
            "pages": [],
            "total_words": 0,
            "is_scanned": False,
            "ocr_applied": False,
            "ocr_available": False,
            "ocr_message": None,
            "error": "Document contains 0 pages.",
            "is_encrypted": False,
            "is_corrupted": True,
        }

    # 3. Extract digital text per page
    pages_data = []
    extracted_page_texts = []
    scanned_pages_detected = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            page_raw = page.extract_text() or ""
        except Exception:
            page_raw = ""

        page_clean = page_raw.strip()
        word_count = len(page_clean.split())

        # Check if page has insufficient text and might be an image/scanned page
        has_images = bool(getattr(page, "images", []))
        if word_count < 8:
            scanned_pages_detected += 1

        pages_data.append({
            "page_number": page_num,
            "text": page_clean,
            "word_count": word_count,
            "has_images": has_images,
        })
        if page_clean:
            extracted_page_texts.append(f"--- Page {page_num} ---\n{page_clean}")

    total_words = sum(p["word_count"] for p in pages_data)
    is_scanned = (total_words < 12 and scanned_pages_detected >= total_page_count) or (total_words == 0)

    # 4. If scanned or lacking digital text, attempt OCR
    ocr_applied = False
    ocr_available = bool(_CUSTOM_OCR_HANDLER or is_tesseract_available())
    ocr_message = None

    if is_scanned:
        # Check custom OCR handler first (e.g. for testing or configured pipelines)
        if _CUSTOM_OCR_HANDLER is not None:
            try:
                ocr_text = _CUSTOM_OCR_HANDLER(file_bytes, filename)
                if ocr_text and ocr_text.strip():
                    ocr_applied = True
                    pages_data = [{
                        "page_number": 1,
                        "text": ocr_text.strip(),
                        "word_count": len(ocr_text.split()),
                        "has_images": True,
                    }]
                    extracted_page_texts = [f"--- Page 1 (OCR Extracted) ---\n{ocr_text.strip()}"]
                    total_words = len(ocr_text.split())
                    ocr_message = "Document was processed using automated Optical Character Recognition (OCR)."
            except Exception as ocr_err:
                ocr_message = f"OCR execution failed: {str(ocr_err)}"
        elif is_tesseract_available():
            # Try extracting images from pages and running tesseract
            ocr_pages = []
            for idx, page in enumerate(reader.pages):
                page_text_pieces = []
                try:
                    for img_file in getattr(page, "images", []):
                        pil_img = Image.open(io.BytesIO(img_file.data))
                        t_text = run_pytesseract_on_image(pil_img)
                        if t_text.strip():
                            page_text_pieces.append(t_text.strip())
                except Exception:
                    pass
                if page_text_pieces:
                    combined_ocr = "\n".join(page_text_pieces)
                    ocr_pages.append(f"--- Page {idx + 1} (OCR) ---\n{combined_ocr}")
            if ocr_pages:
                ocr_applied = True
                extracted_page_texts = ocr_pages
                total_words = sum(len(p.split()) for p in ocr_pages)
                ocr_message = "Scanned document text was recovered via Tesseract OCR."
            else:
                ocr_message = "Scanned document detected. Tesseract OCR engine was invoked but returned no recognized text."
        else:
            ocr_message = (
                "Scanned or image-based document detected without digital character layer. "
                "Automated OCR engine is not configured on this host. Text extraction could not be completed."
            )

    full_text = "\n\n".join(extracted_page_texts) if extracted_page_texts else ""

    return {
        "text": full_text,
        "pages": pages_data,
        "total_words": total_words,
        "is_scanned": is_scanned,
        "ocr_applied": ocr_applied,
        "ocr_available": ocr_available,
        "ocr_message": ocr_message,
        "error": None,
        "is_encrypted": False,
        "is_corrupted": False,
    }


def _extract_image_content(img_bytes: bytes, filename: str, ext: str) -> Dict[str, Any]:
    """Extracts metadata and attempts OCR for standalone image files."""
    try:
        image = Image.open(io.BytesIO(img_bytes))
        width, height = image.size
        img_format = image.format or ext.replace(".", "").upper()
    except Exception as e:
        return {
            "text": "",
            "pages": [],
            "total_words": 0,
            "is_scanned": True,
            "ocr_applied": False,
            "ocr_available": False,
            "ocr_message": None,
            "error": f"Corrupted or invalid image file: {str(e)}",
            "is_encrypted": False,
            "is_corrupted": True,
        }

    ocr_applied = False
    ocr_available = bool(_CUSTOM_OCR_HANDLER or is_tesseract_available())
    extracted_text = ""
    ocr_message = None

    if _CUSTOM_OCR_HANDLER is not None:
        try:
            extracted_text = _CUSTOM_OCR_HANDLER(img_bytes, filename)
            if extracted_text and extracted_text.strip():
                ocr_applied = True
                ocr_message = "Image text extracted via registered OCR engine."
        except Exception as err:
            ocr_message = f"OCR engine failed: {str(err)}"
    elif is_tesseract_available():
        extracted_text = run_pytesseract_on_image(image)
        if extracted_text and extracted_text.strip():
            ocr_applied = True
            ocr_message = "Image text extracted via Tesseract OCR."
        else:
            ocr_message = "Tesseract OCR was invoked on the image but found no readable characters."
    else:
        ocr_message = (
            "Image document uploaded. Automated OCR engine is not configured on this host. "
            "Please review the image directly or enter clinical findings manually."
        )

    clean_text = extracted_text.strip() if extracted_text else ""
    full_output = f"--- Image Document: {filename} ({img_format}, {width}x{height} px) ---\n"
    if clean_text:
        full_output += clean_text
    else:
        full_output += f"[{ocr_message}]"

    total_words = len(clean_text.split())
    return {
        "text": full_output,
        "pages": [{
            "page_number": 1,
            "text": clean_text,
            "word_count": total_words,
            "has_images": True,
        }],
        "total_words": total_words,
        "is_scanned": True,
        "ocr_applied": ocr_applied,
        "ocr_available": ocr_available,
        "ocr_message": ocr_message,
        "error": None,
        "is_encrypted": False,
        "is_corrupted": False,
    }
