"""Unit tests for DocumentService."""

from unittest.mock import MagicMock, patch

from app.services.document_service import DocumentService


class TestExtractText:
    """Tests for extract_text dispatching."""

    def test_unsupported_file_type_returns_empty(self):
        result = DocumentService.extract_text(b"data", "file.xyz")
        assert result == ""

    def test_empty_filename_returns_empty(self):
        result = DocumentService.extract_text(b"data", "")
        assert result == ""

    def test_pdf_dispatches_to_pdf_extractor(self):
        with patch.object(DocumentService, "_extract_from_pdf", return_value="pdf text") as mock:
            result = DocumentService.extract_text(b"data", "doc.pdf")
            mock.assert_called_once_with(b"data")
            assert result == "pdf text"

    def test_image_dispatches_to_image_extractor(self):
        with patch.object(DocumentService, "_extract_from_image", return_value="image text") as mock:
            result = DocumentService.extract_text(b"data", "photo.jpg")
            mock.assert_called_once_with(b"data")
            assert result == "image text"

    def test_png_dispatches_to_image_extractor(self):
        with patch.object(DocumentService, "_extract_from_image", return_value="img") as mock:
            DocumentService.extract_text(b"data", "photo.png")
            mock.assert_called_once()

    def test_jpeg_extension_dispatches_to_image(self):
        with patch.object(DocumentService, "_extract_from_image", return_value="img") as mock:
            DocumentService.extract_text(b"data", "photo.jpeg")
            mock.assert_called_once()

    def test_uppercase_extension_works(self):
        with patch.object(DocumentService, "_extract_from_image", return_value="img") as mock:
            DocumentService.extract_text(b"data", "photo.PNG")
            mock.assert_called_once()


class TestExtractFromPdf:
    """Tests for _extract_from_pdf."""

    def test_both_methods_fail_returns_empty(self):
        with (
            patch.object(DocumentService, "_extract_pdf_text_direct", return_value=""),
            patch.object(DocumentService, "_extract_pdf_text_ocr", return_value=""),
        ):
            result = DocumentService._extract_from_pdf(b"data")
            assert result == ""

    def test_only_direct_text(self):
        with (
            patch.object(DocumentService, "_extract_pdf_text_direct", return_value="direct text"),
            patch.object(DocumentService, "_extract_pdf_text_ocr", return_value=""),
        ):
            result = DocumentService._extract_from_pdf(b"data")
            assert result == "direct text"

    def test_only_ocr_text(self):
        with (
            patch.object(DocumentService, "_extract_pdf_text_direct", return_value=""),
            patch.object(DocumentService, "_extract_pdf_text_ocr", return_value="ocr text"),
        ):
            result = DocumentService._extract_from_pdf(b"data")
            assert result == "ocr text"

    def test_both_texts_combined(self):
        with (
            patch.object(DocumentService, "_extract_pdf_text_direct", return_value="direct"),
            patch.object(DocumentService, "_extract_pdf_text_ocr", return_value="ocr"),
        ):
            result = DocumentService._extract_from_pdf(b"data")
            assert "direct" in result
            assert "ocr" in result


class TestExtractPdfTextDirect:
    """Tests for _extract_pdf_text_direct."""

    def test_exception_returns_empty(self):
        with patch("builtins.__import__", side_effect=Exception("import failed")):
            # The function catches all exceptions and returns ""
            result = DocumentService._extract_pdf_text_direct(b"bad data")
            assert result == ""


class TestExtractFromImage:
    """Tests for _extract_from_image."""

    def test_exception_returns_empty(self):
        result = DocumentService._extract_from_image(b"not an image")
        assert result == ""
