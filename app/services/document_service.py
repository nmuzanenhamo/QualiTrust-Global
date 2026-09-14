"""Document service for extracting text from uploaded certificates and transcripts."""

import io
import logging
import os
import sys

logger = logging.getLogger(__name__)


def _configure_tesseract():
    """Set the Tesseract executable path on Windows if it's not on PATH."""
    if sys.platform == "win32":
        candidate = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(candidate):
            os.environ.setdefault("TESSERACT_CMD", candidate)


_configure_tesseract()


class DocumentService:
    """Extracts text from PDF and image documents for comparison."""

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """Extract text from a PDF or image file.

        For PDFs, uses pdfplumber to extract text directly.
        For images (JPG, PNG, etc.), uses pytesseract OCR.

        Returns the extracted text as a single string, or empty string on failure.
        """
        ext = os.path.splitext(filename or "")[1].lower()

        if ext == ".pdf":
            return DocumentService._extract_from_pdf(file_bytes)
        elif ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
            return DocumentService._extract_from_image(file_bytes)
        elif ext == ".txt":
            return DocumentService._extract_from_text(file_bytes)
        else:
            logger.warning(f"Unsupported file type for text extraction: {ext}")
            return ""

    @staticmethod
    def _extract_from_text(file_bytes: bytes) -> str:
        """Extract text from a plain text file (already digital, no OCR needed)."""
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception as e:
            logger.error(f"Text file extraction failed: {e}")
            return ""

    @staticmethod
    def _extract_from_pdf(file_bytes: bytes) -> str:
        """Extract text from a PDF.

        Tries both direct text extraction (pdfplumber) and OCR on rendered
        page images (for scanned PDFs), then combines the results. This
        ensures we capture text from both the PDF's text layer and the
        scanned image content.
        """
        direct_text = DocumentService._extract_pdf_text_direct(file_bytes)
        ocr_text = DocumentService._extract_pdf_text_ocr(file_bytes)

        # Combine both — OCR may catch things the text layer misses and vice versa
        if direct_text.strip() and ocr_text.strip():
            return f"{direct_text}\n{ocr_text}".strip()
        elif direct_text.strip():
            return direct_text.strip()
        elif ocr_text.strip():
            return ocr_text.strip()
        return ""

    @staticmethod
    def _extract_pdf_text_direct(file_bytes: bytes) -> str:
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
            return "\n".join(text_parts).strip()
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    @staticmethod
    def _extract_pdf_text_ocr(file_bytes: bytes) -> str:
        """Render PDF pages to images and run OCR — handles scanned PDFs.

        Combines PSM 3 (fully automatic) and PSM 6 (uniform block) results,
        since different modes catch different text on certificates with stamps
        and watermarks.
        """
        try:
            import pdfplumber
            import pytesseract

            tess_cmd = os.environ.get("TESSERACT_CMD")
            if tess_cmd:
                pytesseract.pytesseract.tesseract_cmd = tess_cmd

            text_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    img = page.to_image(resolution=400)
                    pil_img = img.original
                    # PSM 3 (fully automatic) — catches grade text, holder name
                    psm3_text = pytesseract.image_to_string(pil_img, config="--psm 3")
                    # PSM 6 (uniform block) — catches institution names
                    psm6_text = pytesseract.image_to_string(pil_img, config="--psm 6")
                    text_parts.append(psm3_text)
                    text_parts.append(psm6_text)
            return "\n".join(text_parts).strip()
        except Exception as e:
            logger.error(f"PDF OCR fallback failed: {e}")
            return ""

    @staticmethod
    def _extract_from_image(file_bytes: bytes) -> str:
        """Extract text from an image using pytesseract OCR.

        Preprocesses the image (upscale small images, convert to grayscale)
        for better accuracy, then runs Tesseract. Falls back gracefully if
        Tesseract is not installed.
        """
        try:
            import pytesseract
            from PIL import Image, ImageOps

            tess_cmd = os.environ.get("TESSERACT_CMD")
            if tess_cmd:
                pytesseract.pytesseract.tesseract_cmd = tess_cmd

            image = Image.open(io.BytesIO(file_bytes))

            # Convert to RGB if needed (handles RGBA, palette, etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Upscale small images for better OCR
            width, height = image.size
            if width < 1500:
                scale = 1500 / width
                image = image.resize(
                    (int(width * scale), int(height * scale)),
                    Image.LANCZOS,
                )

            # Convert to grayscale for better OCR
            gray = ImageOps.grayscale(image)

            # Run OCR with page segmentation mode 6 (uniform block of text)
            text = pytesseract.image_to_string(gray, config="--psm 6")
            return text.strip()
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return ""
