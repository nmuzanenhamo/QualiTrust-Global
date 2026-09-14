"""Unit tests for AIExtractionService (vision-based extraction)."""

import json
from unittest.mock import MagicMock, patch

from app.services.ai_extraction_service import AIExtractionService
from app.services.credential_extraction_service import ExtractedCredential


def _make_openai_response(content: dict | str | None):
    """Build a mock OpenAI chat completion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(content) if isinstance(content, dict) else content
    return resp


SAMPLE_AI_RESPONSE = {
    "holder_name": "Jane Smith",
    "issuing_institution": "Midlands State University",
    "title": "Bachelor of Science Honours in Computer Science",
    "qualification_type": "undergraduate_degree",
    "grade": "First Class",
    "serial_number": "MSU-CS-2021-042",
    "registration_number": "R211790N",
    "date_issued": "2021-06-15",
    "holder_id_number": "63-1234567X12",
}


class TestAIExtractionService:
    """Tests for AIExtractionService (OpenAI vision extraction)."""

    def test_returns_none_without_api_key(self):
        with patch("app.core.config.settings.OPENAI_API_KEY", ""):
            result = AIExtractionService.extract(b"image data", "cert.jpg")
            assert result is None

    def test_returns_none_on_unsupported_file_type(self):
        with (
            patch("app.core.config.settings.OPENAI_API_KEY", "sk-test"),
            patch("app.services.ai_extraction_service.settings.OPENAI_API_KEY", "sk-test"),
        ):
            result = AIExtractionService.extract(b"data", "file.xyz")
            assert result is None

    def test_successful_extraction_from_image(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_openai_response(SAMPLE_AI_RESPONSE)

        with (
            patch("app.core.config.settings.OPENAI_API_KEY", "sk-test"),
            patch("app.services.ai_extraction_service.settings.OPENAI_API_KEY", "sk-test"),
        ):
            # Generate a minimal valid JPEG byte string via PIL
            from PIL import Image

            img = Image.new("RGB", (10, 10), color="white")
            import io

            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            jpeg_bytes = buf.getvalue()

            with patch("openai.OpenAI", return_value=mock_client):
                result = AIExtractionService.extract(jpeg_bytes, "cert.jpg")

        assert result is not None
        assert result.holder_name == "Jane Smith"
        assert result.issuing_institution == "Midlands State University"
        assert result.title == "Bachelor of Science Honours in Computer Science"
        assert result.qualification_type == "undergraduate_degree"
        assert result.grade == "First Class"
        assert result.serial_number == "MSU-CS-2021-042"
        assert result.registration_number == "R211790N"
        assert result.date_issued == "2021-06-15"
        assert result.holder_id_number == "63-1234567X12"
        assert result.extraction_method == "openai_vision"

    def test_openai_failure_returns_none(self):
        with (
            patch("app.core.config.settings.OPENAI_API_KEY", "sk-test"),
            patch("app.services.ai_extraction_service.settings.OPENAI_API_KEY", "sk-test"),
        ):
            with patch("openai.OpenAI", side_effect=Exception("API error")):
                result = AIExtractionService.extract(b"image data", "cert.jpg")
                assert result is None

    def test_null_fields_are_cleaned(self):
        response = {
            "holder_name": "John Doe",
            "issuing_institution": None,
            "title": "Master of Science",
            "qualification_type": None,
            "grade": "null",
            "serial_number": "SN123",
            "registration_number": "n/a",
            "date_issued": "2020-01-01",
            "holder_id_number": "",
        }
        result = AIExtractionService._to_extracted_credential(response)
        assert result.holder_name == "John Doe"
        assert result.issuing_institution is None
        assert result.grade is None  # "null" string cleaned
        assert result.registration_number is None  # "n/a" cleaned
        assert result.holder_id_number is None  # empty cleaned

    def test_invalid_qualification_type_inferred_from_title(self):
        response = dict(SAMPLE_AI_RESPONSE, qualification_type="some_unknown_type")
        result = AIExtractionService._to_extracted_credential(response)
        # Title contains "Bachelor" -> undergraduate_degree
        assert result.qualification_type == "undergraduate_degree"

    def test_infer_type_from_title_variants(self):
        assert AIExtractionService._infer_type_from_title("PhD in Physics") == "doctorate"
        assert AIExtractionService._infer_type_from_title("Master of Business Administration") == "masters_degree"
        assert AIExtractionService._infer_type_from_title("Bachelor of Arts") == "undergraduate_degree"
        assert AIExtractionService._infer_type_from_title("National Diploma in Engineering") == "diploma"
        assert AIExtractionService._infer_type_from_title("Certificate in Accounting") == "certificate"
        assert AIExtractionService._infer_type_from_title("Something Else") == "other"
        assert AIExtractionService._infer_type_from_title(None) is None


class TestCredentialExtractionServiceAIIntegration:
    """Tests for the AI-first extract flow with regex fallback."""

    def test_extract_uses_ai_when_available(self):
        ai_result = ExtractedCredential(
            holder_name="AI Result",
            serial_number="AI-SN-001",
            extraction_method="openai_vision",
        )
        with patch("app.core.config.settings.OPENAI_API_KEY", "sk-test"):
            with patch(
                "app.services.ai_extraction_service.AIExtractionService.extract",
                return_value=ai_result,
            ):
                from app.services.credential_extraction_service import CredentialExtractionService

                result = CredentialExtractionService.extract(b"data", "cert.jpg")
                assert result.holder_name == "AI Result"
                assert result.extraction_method == "openai_vision"

    def test_extract_falls_back_to_regex_when_ai_returns_empty(self):
        """AI returned nothing useful (all fields empty) -> regex fallback."""
        ai_result = ExtractedCredential(extraction_method="openai_vision")
        with patch("app.core.config.settings.OPENAI_API_KEY", "sk-test"):
            with patch(
                "app.services.ai_extraction_service.AIExtractionService.extract",
                return_value=ai_result,
            ):
                from app.services.credential_extraction_service import CredentialExtractionService

                result = CredentialExtractionService.extract(b"data", "cert.xyz")
                assert result.extraction_method == "regex"

    def test_extract_falls_back_when_no_api_key(self):
        with patch("app.core.config.settings.OPENAI_API_KEY", ""):
            from app.services.credential_extraction_service import CredentialExtractionService

            result = CredentialExtractionService.extract(b"data", "cert.xyz")
            assert result.extraction_method == "regex"


class TestDateNormalization:
    """Tests for date normalization in the regex extraction path."""

    def test_normalize_day_month_year(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        assert CredentialExtractionService._normalize_date_string("15th June 2023") == "2023-06-15"
        assert CredentialExtractionService._normalize_date_string("15 June 2023") == "2023-06-15"

    def test_normalize_month_day_year(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        assert CredentialExtractionService._normalize_date_string("June 15, 2023") == "2023-06-15"
        assert CredentialExtractionService._normalize_date_string("June 15 2023") == "2023-06-15"

    def test_normalize_numeric_slash(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        assert CredentialExtractionService._normalize_date_string("15/06/2023") == "2023-06-15"
        assert CredentialExtractionService._normalize_date_string("15-06-2023") == "2023-06-15"

    def test_iso_unchanged(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        assert CredentialExtractionService._normalize_date_string("2023-06-15") == "2023-06-15"

    def test_unparseable_unchanged(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        assert CredentialExtractionService._normalize_date_string("Sommer 2020") == "Sommer 2020"

    def test_extract_date_normalizes_result(self):
        from app.services.credential_extraction_service import CredentialExtractionService

        text = "Date Issued: 15th June 2023"
        result = CredentialExtractionService._extract_date(text, text)
        assert result == "2023-06-15"
