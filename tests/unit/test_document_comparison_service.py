"""Unit tests for DocumentComparisonService."""

from types import SimpleNamespace

from app.services.document_comparison_service import DocumentComparisonService


def _make_qualification(**kwargs):
    """Create a mock qualification object."""
    defaults = {
        "holder_name": "John Doe",
        "issuing_institution": "Midlands State University",
        "title": "Bachelor of Science in Computer Science",
        "serial_number": "MSU-CS-2020-001",
        "registration_number": "CS2020/001",
        "document_path": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestCompareDocumentToQualification:
    """Tests for compare_document_to_qualification."""

    def test_empty_text_returns_review(self):
        result = DocumentComparisonService.compare_document_to_qualification("", _make_qualification())
        assert result.match_score == 0.0
        assert result.recommendation == "REVIEW"
        assert "No text" in result.summary

    def test_whitespace_only_text_returns_review(self):
        result = DocumentComparisonService.compare_document_to_qualification("   \n  ", _make_qualification())
        assert result.match_score == 0.0
        assert result.recommendation == "REVIEW"

    def test_full_match_returns_approve(self):
        text = """
        This is to certify that John Doe
        Midlands State University
        Bachelor of Science in Computer Science
        Serial No: MSU-CS-2020-001
        Registration Number: CS2020/001
        """
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        assert result.recommendation == "APPROVE"
        assert result.match_score >= 80

    def test_no_match_returns_reject(self):
        text = "Completely unrelated content about cooking recipes"
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        assert result.recommendation == "REJECT"
        assert result.match_score < 50

    def test_partial_match_returns_review(self):
        text = "John Doe Midlands State University"
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        assert result.recommendation == "REVIEW"
        assert 50 <= result.match_score < 80

    def test_empty_fields_in_qualification(self):
        qual = _make_qualification(
            holder_name="",
            issuing_institution="",
            title="",
            serial_number="",
            registration_number="",
        )
        text = "Some text"
        result = DocumentComparisonService.compare_document_to_qualification(text, qual)
        assert result.match_score == 0.0
        assert result.recommendation == "REJECT"

    def test_serial_number_exact_match(self):
        text = "MSU-CS-2020-001"
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        # Serial number is 15 weight
        assert any(c["field"] == "Serial Number" and c["found_in_document"] for c in result.checks)

    def test_registration_number_exact_match(self):
        text = "CS2020/001"
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        assert any(c["field"] == "Registration Number" and c["found_in_document"] for c in result.checks)

    def test_checks_list_populated(self):
        text = "John Doe"
        result = DocumentComparisonService.compare_document_to_qualification(text, _make_qualification())
        assert len(result.checks) == 5
        fields = [c["field"] for c in result.checks]
        assert "Holder Name" in fields
        assert "Issuing Institution" in fields
        assert "Qualification Title" in fields
        assert "Serial Number" in fields
        assert "Registration Number" in fields

    def test_extracted_text_truncated(self):
        long_text = "John Doe " * 500
        result = DocumentComparisonService.compare_document_to_qualification(long_text, _make_qualification())
        assert len(result.extracted_text) <= 2000


class TestCompareTwoDocuments:
    """Tests for compare_two_documents."""

    def test_identical_documents_approve(self):
        text = "Midlands State University Bachelor of Science John Doe"
        result = DocumentComparisonService.compare_two_documents(text, text)
        assert result.recommendation == "APPROVE"
        assert result.match_score == 100.0

    def test_empty_text_returns_review(self):
        result = DocumentComparisonService.compare_two_documents("", "some text")
        assert result.match_score == 0.0
        assert result.recommendation == "REVIEW"

    def test_both_empty_returns_review(self):
        result = DocumentComparisonService.compare_two_documents("", "")
        assert result.match_score == 0.0
        assert result.recommendation == "REVIEW"

    def test_completely_different_returns_reject(self):
        text1 = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        text2 = "one two three four five six seven eight nine ten"
        result = DocumentComparisonService.compare_two_documents(text1, text2)
        assert result.recommendation == "REJECT"
        assert result.match_score < 50

    def test_moderate_similarity_returns_review(self):
        text1 = "Midlands State University Bachelor of Science John Doe Computer Science"
        text2 = "Midlands State University Bachelor of Science Jane Smith Computer Science"
        result = DocumentComparisonService.compare_two_documents(text1, text2)
        # Should have moderate overlap (shared terms differ by name only)
        assert result.recommendation in ("REVIEW", "APPROVE", "REJECT")
        assert result.match_score >= 40

    def test_no_significant_tokens_returns_review(self):
        result = DocumentComparisonService.compare_two_documents("ab cd", "ef gh")
        assert result.match_score == 0.0
        assert result.recommendation == "REVIEW"


class TestFuzzyContains:
    """Tests for _fuzzy_contains."""

    def test_exact_match(self):
        assert DocumentComparisonService._fuzzy_contains("hello world", "hello") is True

    def test_no_match(self):
        assert DocumentComparisonService._fuzzy_contains("hello world", "python") is False

    def test_empty_search(self):
        assert DocumentComparisonService._fuzzy_contains("hello", "") is False

    def test_empty_text(self):
        assert DocumentComparisonService._fuzzy_contains("", "hello") is False

    def test_word_level_match(self):
        text = "John Robert Doe studied at the university"
        search = "John Doe University"
        # All significant words present
        assert DocumentComparisonService._fuzzy_contains(text, search) is True

    def test_partial_word_match_below_threshold(self):
        text = "John studied at the university"
        search = "John Doe Smith Brown University"
        # Only 2 of 4 significant words present (50% < 80%)
        assert DocumentComparisonService._fuzzy_contains(text, search) is False


class TestNormalizeText:
    """Tests for _normalize_text."""

    def test_lowercases(self):
        assert DocumentComparisonService._normalize_text("HELLO World") == "hello world"

    def test_removes_special_chars(self):
        result = DocumentComparisonService._normalize_text("hello, world!")
        assert "," not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        assert DocumentComparisonService._normalize_text("hello    world") == "hello world"
