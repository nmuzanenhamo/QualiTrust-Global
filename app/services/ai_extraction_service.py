"""AI-powered credential extraction using OpenAI's vision models.

Sends certificate/transcript images directly to GPT-4o-mini, which reads
the document like a human and returns structured fields. This is far more
accurate than regex-on-OCR for varied certificate layouts.

Falls back (returns None) on any failure so the caller can use the
regex-based CredentialExtractionService instead.
"""

import base64
import io
import logging

from app.core.config import settings
from app.services.credential_extraction_service import ExtractedCredential

logger = logging.getLogger(__name__)

# Limit the number of PDF pages sent to the vision model (cost control)
MAX_PDF_PAGES = 3
# Resolution used when rendering PDF pages to images
PDF_RENDER_RESOLUTION = 150

VALID_QUALIFICATION_TYPES = {
    "doctorate",
    "masters_degree",
    "postgraduate_diploma",
    "postgraduate_certificate",
    "undergraduate_degree",
    "diploma",
    "certificate",
    "other",
}

EXTRACTION_PROMPT = """Extract the following fields from this certificate or transcript document.

Return a JSON object with exactly these keys (use null when a field is not present or unreadable):
{
  "holder_name": full name of the person the credential was awarded to,
  "issuing_institution": name of the university/college/exam board that issued it,
  "title": the qualification/programme title as printed (e.g. "Bachelor of Science Honours in Computer Science"),
  "qualification_type": one of "doctorate", "masters_degree", "postgraduate_diploma", "postgraduate_certificate",
    "undergraduate_degree", "diploma", "certificate", "other",
  "grade": the grade or class awarded (e.g. "First Class", "Upper Second Class (2.1)", "Distinction", "A"),
  "serial_number": the serial number printed on the document,
  "registration_number": the student/candidate registration number (not the same as serial),
  "date_issued": the issue/award date in YYYY-MM-DD format
    (use the year alone if the day/month are missing, e.g. "2020-06-15" or "2020-01-01" for just "2020"),
  "holder_id_number": national ID or student number of the holder if printed
}

Notes:
- Distinguish carefully between serial numbers and registration numbers — certificates often print both.
- The holder name is the graduate/candidate, NOT an official or registrar name.
- Only include what is actually printed on the document; do not guess.
- Respond with only the JSON object, no other text."""


class AIExtractionService:
    """Extracts credential fields from documents using OpenAI vision models."""

    @staticmethod
    def extract(file_bytes: bytes, filename: str, db=None) -> ExtractedCredential | None:
        """Extract credential data using GPT-4o-mini vision.

        Returns an ExtractedCredential on success, or None when AI extraction
        is unavailable or fails (caller should fall back to regex extraction).

        The OpenAI key is resolved in order: DB-stored (admin Settings page),
        then the ``OPENAI_API_KEY`` environment variable.
        """
        api_key = AIExtractionService._resolve_api_key(db)
        if not api_key:
            return None

        try:
            images = AIExtractionService._document_to_images(file_bytes, filename)
            if not images:
                return None

            result = AIExtractionService._call_vision_model(images, api_key)
            if result is None:
                return None

            return AIExtractionService._to_extracted_credential(result)
        except Exception as e:
            logger.warning(f"AI vision extraction failed, falling back to regex: {e}")
            return None

    @staticmethod
    def _resolve_api_key(db=None) -> str | None:
        """Resolve the OpenAI API key from the DB (admin settings) or env var."""
        if db is not None:
            try:
                from app.services.settings_service import OPENAI_API_KEY, SettingsService

                key = SettingsService.get_secret(db, OPENAI_API_KEY)
                if key:
                    return key
            except Exception as e:
                logger.warning(f"Failed to read OpenAI key from DB settings: {e}")
        return settings.OPENAI_API_KEY or None

    @staticmethod
    def _document_to_images(file_bytes: bytes, filename: str) -> list[bytes]:
        """Convert a document (PDF or image) to a list of JPEG byte strings.

        Returns an empty list if the document type is unsupported or conversion fails.
        """
        import os

        ext = os.path.splitext(filename or "")[1].lower()

        if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
            image = AIExtractionService._load_image(file_bytes)
            return [AIExtractionService._image_to_jpeg(image)] if image else []
        elif ext == ".pdf":
            return AIExtractionService._pdf_to_jpegs(file_bytes)
        return []

    @staticmethod
    def _load_image(file_bytes: bytes):
        """Load image bytes into a normalized RGB PIL image (handles EXIF rotation)."""
        from PIL import Image, ImageOps

        image = Image.open(io.BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        return image

    @staticmethod
    def _image_to_jpeg(image, quality: int = 85) -> bytes:
        """Serialize a PIL image to compressed JPEG bytes."""
        buffer = io.BytesIO()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()

    @staticmethod
    def _pdf_to_jpegs(file_bytes: bytes) -> list[bytes]:
        """Render the first pages of a PDF to JPEG images for the vision model."""
        import pdfplumber

        jpegs = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:MAX_PDF_PAGES]:
                img = page.to_image(resolution=PDF_RENDER_RESOLUTION).original
                jpegs.append(AIExtractionService._image_to_jpeg(img))
        return jpegs

    @staticmethod
    def _call_vision_model(images: list[bytes], api_key: str) -> dict | None:
        """Send images to GPT-4o-mini and parse the JSON response."""
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        content: list[dict] = [{"type": "text", "text": EXTRACTION_PROMPT}]
        for jpeg_bytes in images:
            b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise document data extraction engine for academic credentials. "
                    "You respond only with valid JSON.",
                },
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=1000,
        )

        message = response.choices[0].message.content
        if not message:
            return None

        import json

        return json.loads(message)

    @staticmethod
    def _to_extracted_credential(data: dict) -> ExtractedCredential:
        """Convert the vision model's JSON response to an ExtractedCredential."""

        def clean(value) -> str | None:
            if value is None:
                return None
            text = str(value).strip()
            return text if text and text.lower() not in ("null", "none", "n/a") else None

        qual_type = clean(data.get("qualification_type"))
        if qual_type and qual_type not in VALID_QUALIFICATION_TYPES:
            qual_type = AIExtractionService._infer_type_from_title(clean(data.get("title")))

        fields = {
            "holder_name": clean(data.get("holder_name")),
            "issuing_institution": clean(data.get("issuing_institution")),
            "title": clean(data.get("title")),
            "qualification_type": qual_type,
            "grade": clean(data.get("grade")),
            "serial_number": clean(data.get("serial_number")),
            "registration_number": clean(data.get("registration_number")),
            "date_issued": clean(data.get("date_issued")),
            "holder_id_number": clean(data.get("holder_id_number")),
        }
        return ExtractedCredential(
            extraction_method="openai_vision",
            confidence={"fields_found": sum(1 for v in fields.values() if v)},
            **fields,
        )

    @staticmethod
    def _infer_type_from_title(title: str | None) -> str | None:
        """Infer the qualification type from the title when the model returns an unrecognized type."""
        if not title:
            return None
        title_lower = title.lower()
        if "doctor" in title_lower or "phd" in title_lower:
            return "doctorate"
        if "master" in title_lower or "msc" in title_lower or "mba" in title_lower or "m.a " in title_lower:
            return "masters_degree"
        if "postgraduate diploma" in title_lower or "pgd" in title_lower:
            return "postgraduate_diploma"
        if "postgraduate certificate" in title_lower or "pgc" in title_lower:
            return "postgraduate_certificate"
        if "bachelor" in title_lower or "bsc" in title_lower or "b.sc" in title_lower or "bcom" in title_lower:
            return "undergraduate_degree"
        if "diploma" in title_lower:
            return "diploma"
        if "certificate" in title_lower:
            return "certificate"
        return "other"
