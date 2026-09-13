"""Document comparison service for matching uploaded documents against registered data."""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DocumentMatchResult:
    """Result of comparing an uploaded document against registered qualification data."""

    match_score: float = 0.0
    checks: list[dict] = field(default_factory=list)
    extracted_text: str = ""
    recommendation: str = "REVIEW"
    summary: str = ""


class DocumentComparisonService:
    """Compares text extracted from an uploaded document against registered qualification data.

    This service addresses the scenario where an attacker creates a fake certificate
    with the same serial and registration numbers but different qualification details.
    By extracting text from the uploaded document and comparing key fields against
    the registered data, the system can detect mismatches that blockchain verification
    alone cannot catch.
    """

    @staticmethod
    def compare_document_to_qualification(
        extracted_text: str,
        qualification,
    ) -> DocumentMatchResult:
        """Compare extracted document text against a qualification record.

        Performs fuzzy matching on key fields:
        - Holder name
        - Issuing institution
        - Qualification title
        - Serial number
        - Registration number

        Returns a DocumentMatchResult with a match score (0-100), individual
        check results, and a recommendation.
        """
        if not extracted_text or not extracted_text.strip():
            return DocumentMatchResult(
                match_score=0.0,
                checks=[],
                extracted_text="",
                recommendation="REVIEW",
                summary="No text could be extracted from the document. Manual review required.",
            )

        text_lower = extracted_text.lower()
        checks = []

        # 1. Holder name match
        holder = (qualification.holder_name or "").strip()
        if holder:
            holder_found = DocumentComparisonService._fuzzy_contains(text_lower, holder.lower())
            checks.append(
                {
                    "field": "Holder Name",
                    "registered": holder,
                    "found_in_document": holder_found,
                    "weight": 25,
                }
            )
        else:
            checks.append(
                {
                    "field": "Holder Name",
                    "registered": "(not set)",
                    "found_in_document": False,
                    "weight": 25,
                }
            )

        # 2. Issuing institution match
        institution = (qualification.issuing_institution or "").strip()
        if institution:
            inst_found = DocumentComparisonService._fuzzy_contains(text_lower, institution.lower())
            checks.append(
                {
                    "field": "Issuing Institution",
                    "registered": institution,
                    "found_in_document": inst_found,
                    "weight": 25,
                }
            )
        else:
            checks.append(
                {
                    "field": "Issuing Institution",
                    "registered": "(not set)",
                    "found_in_document": False,
                    "weight": 25,
                }
            )

        # 3. Qualification title match
        title = (qualification.title or "").strip()
        if title:
            title_found = DocumentComparisonService._fuzzy_contains(text_lower, title.lower())
            checks.append(
                {
                    "field": "Qualification Title",
                    "registered": title,
                    "found_in_document": title_found,
                    "weight": 20,
                }
            )
        else:
            checks.append(
                {
                    "field": "Qualification Title",
                    "registered": "(not set)",
                    "found_in_document": False,
                    "weight": 20,
                }
            )

        # 4. Serial number match
        serial = (qualification.serial_number or "").strip()
        if serial:
            serial_found = serial.lower() in text_lower
            checks.append(
                {
                    "field": "Serial Number",
                    "registered": serial,
                    "found_in_document": serial_found,
                    "weight": 15,
                }
            )
        else:
            checks.append(
                {
                    "field": "Serial Number",
                    "registered": "(not set)",
                    "found_in_document": False,
                    "weight": 15,
                }
            )

        # 5. Registration number match
        reg = (qualification.registration_number or "").strip()
        if reg:
            reg_found = reg.lower() in text_lower
            checks.append(
                {
                    "field": "Registration Number",
                    "registered": reg,
                    "found_in_document": reg_found,
                    "weight": 15,
                }
            )
        else:
            checks.append(
                {
                    "field": "Registration Number",
                    "registered": "(not set)",
                    "found_in_document": False,
                    "weight": 15,
                }
            )

        # Calculate weighted score
        total_weight = sum(c["weight"] for c in checks)
        matched_weight = sum(c["weight"] for c in checks if c["found_in_document"])
        match_score = (matched_weight / total_weight * 100) if total_weight > 0 else 0.0

        # Recommendation
        if match_score >= 80:
            recommendation = "APPROVE"
            summary = f"Document matches registered data ({match_score:.0f}% match). All key fields verified."
        elif match_score >= 50:
            recommendation = "REVIEW"
            summary = f"Document partially matches registered data ({match_score:.0f}% match). Some fields could not be verified — manual review recommended."
        else:
            recommendation = "REJECT"
            summary = f"Document does not match registered data ({match_score:.0f}% match). Key fields are missing or different — possible fraud."

        return DocumentMatchResult(
            match_score=round(match_score, 1),
            checks=checks,
            extracted_text=extracted_text[:2000],
            recommendation=recommendation,
            summary=summary,
        )

    @staticmethod
    def compare_two_documents(text1: str, text2: str) -> DocumentMatchResult:
        """Compare two extracted document texts (e.g., registered document vs verifier-uploaded document).

        Uses Jaccard similarity on significant word tokens to determine if the two
        documents are likely the same certificate.
        """
        if not text1.strip() or not text2.strip():
            return DocumentMatchResult(
                match_score=0.0,
                checks=[],
                extracted_text="",
                recommendation="REVIEW",
                summary="One or both documents had no extractable text. Manual review required.",
            )

        # Normalize both texts
        norm1 = DocumentComparisonService._normalize_text(text1)
        norm2 = DocumentComparisonService._normalize_text(text2)

        # Extract key tokens (alphanumeric sequences >= 3 chars)
        tokens1 = set(re.findall(r"\b\w{3,}\b", norm1))
        tokens2 = set(re.findall(r"\b\w{3,}\b", norm2))

        if not tokens1 or not tokens2:
            return DocumentMatchResult(
                match_score=0.0,
                checks=[],
                extracted_text="",
                recommendation="REVIEW",
                summary="Insufficient text content for comparison. Manual review required.",
            )

        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        similarity = (len(intersection) / len(union) * 100) if union else 0.0

        checks = [
            {
                "field": "Document Similarity",
                "registered": f"{len(tokens1)} unique terms in registered document",
                "found_in_document": similarity >= 60,
                "weight": 100,
                "similarity": round(similarity, 1),
            },
        ]

        if similarity >= 80:
            recommendation = "APPROVE"
            summary = f"Documents are highly similar ({similarity:.0f}% token overlap). Likely the same document."
        elif similarity >= 50:
            recommendation = "REVIEW"
            summary = (
                f"Documents show moderate similarity ({similarity:.0f}% token overlap). Manual comparison recommended."
            )
        else:
            recommendation = "REJECT"
            summary = f"Documents are significantly different ({similarity:.0f}% token overlap). The uploaded document may not match the registered certificate."

        return DocumentMatchResult(
            match_score=round(similarity, 1),
            checks=checks,
            extracted_text=text2[:2000],
            recommendation=recommendation,
            summary=summary,
        )

    @staticmethod
    def _fuzzy_contains(text: str, search: str) -> bool:
        """Check if search string is found in text, allowing for minor formatting differences.

        Normalizes whitespace and checks for the presence of the search term
        as a substring, and also checks if all significant words are present.
        """
        if not search or not text:
            return False

        # Direct substring match (normalized)
        norm_text = DocumentComparisonService._normalize_text(text)
        norm_search = DocumentComparisonService._normalize_text(search)

        if norm_search in norm_text:
            return True

        # Word-level match: check if all significant words (>= 3 chars) are present
        search_words = [w for w in norm_search.split() if len(w) >= 3]
        if not search_words:
            return False

        text_words = set(norm_text.split())
        found_words = sum(1 for w in search_words if w in text_words)
        word_match_ratio = found_words / len(search_words)

        return word_match_ratio >= 0.8

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison: lowercase, collapse whitespace, remove special chars."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
