"""Unit tests for CredentialExtractionService."""

from app.services.credential_extraction_service import (
    CredentialExtractionService,
    ExtractedCredential,
    normalize_ocr_text,
)

SAMPLE_CERTIFICATE_TEXT = """
This is to certify that John Doe
having completed the requirements
was awarded the degree of
Bachelor of Science Honours in Computer Science
by Midlands State University
Serial No: MSU-CS-2020-001
Registration Number: CS2020/001
Date Issued: 15 June 2020
National ID: 63-1234567X12
First Class Honours
"""


class TestNormalizeOcrText:
    """Tests for normalize_ocr_text."""

    def test_fixes_thisis(self):
        assert "this is" in normalize_ocr_text("Thisis a certificate")

    def test_fixes_tocertify(self):
        assert "to certify" in normalize_ocr_text("tocertify that")

    def test_fixes_bachelorof(self):
        assert "bachelor of" in normalize_ocr_text("Bachelorof Science")

    def test_fixes_firstclass(self):
        assert "first class" in normalize_ocr_text("FirstClass Honours")

    def test_fixes_honoursin(self):
        assert "honours in" in normalize_ocr_text("Honoursin Computer Science")

    def test_fixes_serial_na(self):
        assert "serial no" in normalize_ocr_text("Serial Na: 123")

    def test_no_changes_for_clean_text(self):
        text = "This is a clean text"
        assert normalize_ocr_text(text) == text

    def test_fixes_registrationnumber(self):
        assert "registration number" in normalize_ocr_text("RegistrationNumber: 123")


class TestParseText:
    """Tests for parse_text."""

    def test_empty_text_returns_empty_result(self):
        result = CredentialExtractionService.parse_text("")
        assert result.holder_name is None
        assert result.issuing_institution is None
        assert result.title is None

    def test_whitespace_only_returns_empty(self):
        result = CredentialExtractionService.parse_text("   \n  \t  ")
        assert result.holder_name is None

    def test_extracts_holder_name(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.holder_name is not None
        assert "John" in result.holder_name

    def test_extracts_institution(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.issuing_institution is not None
        assert "Midlands" in result.issuing_institution or "State" in result.issuing_institution

    def test_extracts_title(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.title is not None
        assert "Bachelor" in result.title

    def test_extracts_qualification_type(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.qualification_type is not None
        assert result.qualification_type in ("undergraduate_degree", "masters_degree", "doctorate")

    def test_extracts_grade(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.grade is not None
        assert "First" in result.grade

    def test_extracts_serial_number(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.serial_number is not None
        assert "MSU" in result.serial_number or "CS" in result.serial_number

    def test_extracts_registration_number(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.registration_number is not None
        assert "CS" in result.registration_number

    def test_extracts_date(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.date_issued is not None
        assert "2020" in result.date_issued

    def test_extracts_id_number(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.holder_id_number is not None

    def test_confidence_report_built(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert "fields_extracted" in result.confidence
        assert "fields_total" in result.confidence
        assert "percentage" in result.confidence
        assert result.confidence["fields_total"] == 9

    def test_raw_text_preserved(self):
        result = CredentialExtractionService.parse_text(SAMPLE_CERTIFICATE_TEXT)
        assert result.raw_text == SAMPLE_CERTIFICATE_TEXT


class TestExtractHolderName:
    """Tests for _extract_holder_name."""

    def test_certify_that_pattern(self):
        text = "This is to certify that Jane Smith having completed"
        result = CredentialExtractionService._extract_holder_name(text, text)
        assert "Jane" in (result or "")

    def test_hereby_certify_pattern(self):
        text = "We hereby certify that Robert Brown was awarded"
        result = CredentialExtractionService._extract_holder_name(text, text)
        assert "Robert" in (result or "")

    def test_no_match_returns_none(self):
        text = "Random text without name patterns"
        result = CredentialExtractionService._extract_holder_name(text, text)
        assert result is None

    def test_filters_short_noise(self):
        text = "This is to certify that the having completed"
        result = CredentialExtractionService._extract_holder_name(text, text)
        # "the" should be filtered out
        assert result is None or len(result) >= 3


class TestExtractType:
    """Tests for _extract_type."""

    def test_phd(self):
        text = "Doctor of Philosophy in Physics"
        assert CredentialExtractionService._extract_type(text, None) == "doctorate"

    def test_masters(self):
        text = "Master of Science in Data"
        assert CredentialExtractionService._extract_type(text, None) == "masters_degree"

    def test_bachelor(self):
        text = "Bachelor of Science in CS"
        assert CredentialExtractionService._extract_type(text, None) == "undergraduate_degree"

    def test_diploma(self):
        text = "Diploma in Engineering"
        assert CredentialExtractionService._extract_type(text, None) == "diploma"

    def test_certificate(self):
        text = "Certificate in Accounting"
        assert CredentialExtractionService._extract_type(text, None) == "certificate"

    def test_fallback_from_title(self):
        assert CredentialExtractionService._extract_type("", "PhD in AI") == "doctorate"
        assert CredentialExtractionService._extract_type("", "Master of Arts") == "masters_degree"
        assert CredentialExtractionService._extract_type("", "Bachelor of Arts") == "undergraduate_degree"

    def test_no_match_returns_none(self):
        assert CredentialExtractionService._extract_type("random text", None) is None


class TestExtractGrade:
    """Tests for _extract_grade."""

    def test_first_class(self):
        assert "First" in (
            CredentialExtractionService._extract_grade("First Class Honours", "First Class Honours") or ""
        )

    def test_upper_second(self):
        result = CredentialExtractionService._extract_grade("Upper Second Class Honours (2.1)", "Upper Second")
        assert "Upper" in (result or "")

    def test_2_1_notation(self):
        result = CredentialExtractionService._extract_grade("2.1", "2.1")
        assert "Upper" in (result or "")

    def test_distinction(self):
        result = CredentialExtractionService._extract_grade("Distinction", "Distinction")
        assert "Distinction" in (result or "")

    def test_no_grade_returns_none(self):
        assert CredentialExtractionService._extract_grade("no grade here", "no grade here") is None


class TestMatchKnownInstitution:
    """Tests for _match_known_institution."""

    def test_exact_match(self):
        result = CredentialExtractionService._match_known_institution("Midlands State University")
        assert result == "Midlands State University"

    def test_case_insensitive(self):
        result = CredentialExtractionService._match_known_institution("midlands state university")
        assert result == "Midlands State University"

    def test_partial_contained(self):
        result = CredentialExtractionService._match_known_institution("University of Zimbabwe")
        assert result == "University of Zimbabwe"

    def test_no_match(self):
        assert CredentialExtractionService._match_known_institution("Unknown College") is None


class TestExtractedCredential:
    """Tests for the dataclass."""

    def test_defaults(self):
        ec = ExtractedCredential()
        assert ec.holder_name is None
        assert ec.issuing_institution is None
        assert ec.raw_text == ""
        assert ec.confidence == {}

    def test_with_values(self):
        ec = ExtractedCredential(holder_name="John", raw_text="text")
        assert ec.holder_name == "John"
        assert ec.raw_text == "text"
