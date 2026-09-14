"""Credential extraction service for parsing OCR text into structured qualification data.

Takes raw text extracted from a certificate/transcript (via DocumentService) and
uses regex patterns + heuristics to identify key fields:

- Holder name
- Issuing institution
- Qualification title
- Qualification type
- Grade / class of degree (e.g. First Class, Upper Second (2.1))
- Serial number
- Registration number
- Date issued
- Holder ID number

The patterns are designed to be tolerant of common OCR artifacts such as
merged words (e.g. "Thisis", "Honoursin") and misread characters
(e.g. "Na" instead of "No").
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedCredential:
    """Structured data extracted from a certificate document."""

    holder_name: str | None = None
    issuing_institution: str | None = None
    title: str | None = None
    qualification_type: str | None = None
    grade: str | None = None
    serial_number: str | None = None
    registration_number: str | None = None
    date_issued: str | None = None
    holder_id_number: str | None = None
    raw_text: str = ""
    confidence: dict = field(default_factory=dict)
    extraction_method: str = "regex"


# ── OCR text normalization ───────────────────────────────────────
# Common word merges that OCR produces, and their fixes
WORD_MERGE_FIXES = [
    # "Thisis" -> "This is"
    (re.compile(r"thisis", re.I), "this is"),
    (re.compile(r"tocertify", re.I), "to certify"),
    (re.compile(r"thathaving", re.I), "that having"),
    (re.compile(r"thathas", re.I), "that has"),
    (re.compile(r"thatwas", re.I), "that was"),
    (re.compile(r"thatbeing", re.I), "that being"),
    (re.compile(r"thatsuccessfully", re.I), "that successfully"),
    # "Honoursin" -> "Honours in"
    (re.compile(r"honou?rsin", re.I), "honours in"),
    (re.compile(r"honou?rsdegree", re.I), "honours degree"),
    # "FirstClass" -> "First Class"
    (re.compile(r"firstclass", re.I), "first class"),
    (re.compile(r"secondclass", re.I), "second class"),
    (re.compile(r"thirdclass", re.I), "third class"),
    (re.compile(r"uppersecond", re.I), "upper second"),
    (re.compile(r"lowersecond", re.I), "lower second"),
    # "Bachelorof" -> "Bachelor of"
    (re.compile(r"bachelorof", re.I), "bachelor of"),
    (re.compile(r"masterof", re.I), "master of"),
    (re.compile(r"doctorof", re.I), "doctor of"),
    (re.compile(r"diplomain", re.I), "diploma in"),
    (re.compile(r"certificatein", re.I), "certificate in"),
    # "Serial Na" -> "Serial No"
    (re.compile(r"serial\s*na\b", re.I), "serial no"),
    (re.compile(r"serial\s*n\b", re.I), "serial no"),
    # "Registration" merges
    (re.compile(r"registrationnumber", re.I), "registration number"),
    (re.compile(r"regno", re.I), "reg no"),
    # "Date Issued" merges
    (re.compile(r"dateissued", re.I), "date issued"),
    # "National ID" merges
    (re.compile(r"nationalid", re.I), "national id"),
    # "successfullycompleted" -> "successfully completed"
    (re.compile(r"successfullycompleted", re.I), "successfully completed"),
]


def normalize_ocr_text(text: str) -> str:
    """Fix common OCR word-merge artifacts by inserting missing spaces."""
    for pattern, replacement in WORD_MERGE_FIXES:
        text = pattern.sub(replacement, text)
    return text


# ── Degree classification patterns ──────────────────────────────
GRADE_PATTERNS = [
    # First Class variants
    (re.compile(r"first\s*class\s*(?:honou?rs)?(?:\s*degree)?", re.I), "First Class Honours"),
    (re.compile(r"\bfirst\s*class\b", re.I), "First Class"),
    (re.compile(r"\b1st\s*class\b", re.I), "First Class"),
    # Upper Second (2.1) — with or without "class"
    (re.compile(r"upper\s*second\s*class(?:\s*honou?rs)?", re.I), "Upper Second Class Honours (2.1)"),
    (re.compile(r"second\s*class\s*(?:upper\s*division|division\s*one)", re.I), "Upper Second Class (2.1)"),
    (re.compile(r"\bupper\s*second\b", re.I), "Upper Second Class (2.1)"),
    (re.compile(r"\b2\.1\b"), "Upper Second Class (2.1)"),
    (re.compile(r"\b2:1\b"), "Upper Second Class (2.1)"),
    # Lower Second (2.2) — with or without "class"
    (re.compile(r"lower\s*second\s*class(?:\s*honou?rs)?", re.I), "Lower Second Class Honours (2.2)"),
    (re.compile(r"second\s*class\s*(?:lower\s*division|division\s*two)", re.I), "Lower Second Class (2.2)"),
    (re.compile(r"\blower\s*second\b", re.I), "Lower Second Class (2.2)"),
    (re.compile(r"\b2\.2\b"), "Lower Second Class (2.2)"),
    (re.compile(r"\b2:2\b"), "Lower Second Class (2.2)"),
    # Third class
    (re.compile(r"third\s*class(?:\s*honou?rs)?", re.I), "Third Class Honours"),
    (re.compile(r"\b3rd\s*class\b", re.I), "Third Class"),
    # Pass / Ordinary
    (re.compile(r"\bpass\s*(?:degree|class|with\s*merit)?\b", re.I), "Pass"),
    (re.compile(r"\bordinary\s*degree\b", re.I), "Ordinary (Pass)"),
    # Distinction
    (re.compile(r"\bdistinction\b", re.I), "Distinction"),
    (re.compile(r"with\s*distinction", re.I), "Distinction"),
    # Cum Laude
    (re.compile(r"summa\s*cum\s*laude", re.I), "Summa Cum Laude"),
    (re.compile(r"magna\s*cum\s*laude", re.I), "Magna Cum Laude"),
    (re.compile(r"\bcum\s*laude\b", re.I), "Cum Laude"),
    # Merit
    (re.compile(r"\bmerit\b", re.I), "Merit"),
    (re.compile(r"pass\s*with\s*merit", re.I), "Pass with Merit"),
    # Credit
    (re.compile(r"\bcredit\b", re.I), "Credit"),
]

# ── Qualification type patterns ─────────────────────────────────
TYPE_PATTERNS = [
    (re.compile(r"\b(doctor\s*of\s*philosophy|ph\.?d)\b", re.I), "doctorate"),
    (
        re.compile(
            r"\b(master\s*of\s*(?:science|arts|business|engineering|education)|m\.?sc|m\.?a\b|m\.?ba|m\.?eng|m\.?ed)\b",
            re.I,
        ),
        "masters_degree",
    ),
    (re.compile(r"\b(post\s*graduate\s*diploma|postgraduate\s*diploma|pg\s*dip)\b", re.I), "postgraduate_diploma"),
    (
        re.compile(r"\b(post\s*graduate\s*certificate|postgraduate\s*certificate|pg\s*cert)\b", re.I),
        "postgraduate_certificate",
    ),
    (
        re.compile(
            r"\b(bachelor\s*of\s*(?:science|arts|commerce|business|engineering|education|technology|medicine|surgery)|b\.?sc\b|b\.?a\b|b\.?com\b|b\.?eng\b|b\.?tech\b|b\.?ed\b|mbchb)\b",
            re.I,
        ),
        "undergraduate_degree",
    ),
    (re.compile(r"\b(diploma)\b", re.I), "diploma"),
    (re.compile(r"\b(certificate)\b", re.I), "certificate"),
    (re.compile(r"\b(professional\s*(?:certification|qualification))\b", re.I), "professional_certification"),
]

# ── Institution patterns ────────────────────────────────────────
# Match institution names — both ALL-CAPS and Title Case, with optional "of X" suffix
INSTITUTION_KEYWORDS = re.compile(
    r"((?:[A-Z][a-zA-Z'\-]+\s+){0,5}"
    r"(?:University|Institute|Polytechnic|College|Academy|School)"
    r"(?:\s+of\s+[A-Z][a-zA-Z\s,&\-]+)?)",
    re.I | re.M,
)

# ── Serial / Registration number patterns ───────────────────────
# Tolerant of OCR misreads: "No", "Na", "N°", "N", "Ne", "Nu"
# IMPORTANT: longer alternatives (number) must come before short ones (n[°o.]?)
# to avoid matching just "N" from "Number" and capturing "umber" as the value.
SERIAL_PATTERNS = [
    re.compile(r"serial\s*(?:number|no\.?|na\.?|n[°o.]?|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", re.I),
    re.compile(r"certificate\s*(?:no\.?|na\.?|n[°o.]?|number|#)?\s*[:\-]?\s*(\d{3,}[A-Z0-9\-/]*)", re.I),
    re.compile(r"\bs/?n\b\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", re.I),
]

REG_PATTERNS = [
    # "Registration Number: R211790N" — must NOT match "REGISTRAR"
    re.compile(
        r"reg(?:istration)?\s*(?:number|no\.?|na\.?|n[°o.]?|#)?\s*[:\-]\s*([A-Z0-9][A-Z0-9\-/]{2,})(?!\s*(?:AR|R\b))",
        re.I,
    ),
    re.compile(r"student\s*(?:number|no\.?|na\.?|n[°o.]?|id|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", re.I),
    re.compile(r"candidate\s*(?:number|no\.?|na\.?|n[°o.]?|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", re.I),
]

# ── Date patterns ───────────────────────────────────────────────
DATE_PATTERNS = [
    # "15th June 2023", "15 June 2023", "June 15, 2023"
    re.compile(
        r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        re.I,
    ),
    re.compile(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})",
        re.I,
    ),
    # "Oct 2025", "October 2025" (month + year, no day — common on certificates)
    re.compile(
        r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})",
        re.I,
    ),
    # "2023-06-15", "15/06/2023", "15-06-2023"
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
]

# ── Holder name patterns ────────────────────────────────────────
# Names often end at a newline (name on its own line) or before a stop word
HOLDER_PATTERNS = [
    # "This is to certify that John Doe having..." / "This is to certify that\nJohn Doe\nhaving..."
    re.compile(
        r"this\s+is\s+to\s+certify\s+that\s+(.{2,80}?)"
        r"(?=\s+(?:having|was|has|is|being|successfully|completed|awarded)|\s*\n)",
        re.I,
    ),
    # "We hereby Certify that John Doe having..." (common on Zimbabwean certificates)
    re.compile(
        r"we\s+hereby\s+certify\s+that\s+(.{2,80}?)"
        r"(?=\s+(?:having|was|has|is|being|successfully|completed|awarded)|\s*\n)",
        re.I,
    ),
    # "We hereby Certify that\n<noise lines>\nJOHN DOE\nhaving..." (name on a later line, all caps)
    # This handles OCR noise between "certify that" and the actual name
    re.compile(
        r"(?:this\s+is\s+to|we\s+hereby)\s+certify\s+that\s*\n.*?"
        r"\n([A-Z][A-Z\s]{5,60}?)\s*(?:\n|co\s|having)",
        re.I | re.DOTALL,
    ),
    # All-caps name on its own line (3+ words, common in certificates)
    # Allows OCR noise after the name (e.g. "JOHN DOE co EenrED ~~ oak")
    re.compile(r"\n([A-Z]{3,}\s+[A-Z]{3,}(?:\s+[A-Z]{3,}){1,4})\s+(?:co\s|~~|[a-z]|\n)"),
    # "awarded to John Doe having..."
    re.compile(r"awarded\s+to\s+(.{2,80}?)(?=\s+(?:having|was|has|is|being|successfully|on|upon|for)|\s*\n)", re.I),
    # "Name: John Doe" / "Candidate: John Doe"
    re.compile(r"(?:name|candidate|holder|full\s*name)\s*[:\-]\s*([A-Z][a-zA-Z'\-\s]{2,60})", re.I),
    # "Mr. John Doe" / "Mrs. Jane Smith"
    re.compile(r"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+([A-Z][a-zA-Z'\-\s]{2,60})"),
    # "This certifies that John Doe" (variant)
    re.compile(
        r"certifies?\s+that\s+(.{2,80}?)"
        r"(?=\s+(?:having|was|has|is|being|successfully|completed|awarded)|\s*\n)",
        re.I,
    ),
]

# ── National ID patterns ────────────────────────────────────────
ID_PATTERNS = [
    re.compile(
        r"(?:national\s*id|id\s*(?:no\.?|number|#)|identity\s*(?:no\.?|number|card))\s*[:\-]?\s*([A-Z0-9]{6,15})", re.I
    ),
    re.compile(r"\b(\d{2}[-\s]?\d{6,7}[-\s]?[A-Z]\d{2})\b"),  # Zimbabwean national ID format
]

# ── Degree title patterns ───────────────────────────────────────
# Stop words prevent the title from capturing grade/serial/date text that follows
TITLE_STOP = r"(?:\s+(?:first|second|third|pass|ordinary|distinction|credit|merit|serial|reg(?:istration)?|date|national|candidate|student|awarded|having|successfully|completed|programme|with|upper|lower|division|we|hereby|certify|this|day|admitted|senate|box|satisfied|examiners)\b)"

TITLE_PATTERNS = [
    # "admitted by Senate to the Bachelor of ... in ..." — very common on degree
    # certificates and gives a clean title without OCR noise from the header
    re.compile(
        r"admitted\s+by\s+Senate\s+to\s+the\s+"
        r"((?:Bachelor|Master|Doctor|Diploma|Certificate|Associate)\s+of\s+"
        r"[\w\s,&\-\(\)]+?(?:\s+Honou?rs|\s+\(Hons\)|\s+Hons)?"
        r"(?:\s+Degree)?(?:\s+in\s+[\w\s,&\-\(\)]+?)?)"
        r"(?:\s+in\s+the|\s*[,.;:]|\s*$)",
        re.I,
    ),
    # "Bachelor of Commerce Honours Degree in Data Science and Informatics"
    # Handles "Honours Degree" in the middle (common on Zimbabwean certificates)
    re.compile(
        r"((?:Bachelor|Master|Doctor|Diploma|Certificate|Associate)\s+of\s+"
        r"(?:Science|Arts|Commerce|Business|Engineering|Education|Technology|Medicine|Surgery|Philosophy|Laws|Social)"
        r"(?:\s+Honou?rs)?\s*(?:Degree)?\s*"
        r"(?:in\s+[\w\s,&\-\(\)]+?)?)"
        r"(?:" + TITLE_STOP + r"|\s*[,.;:]|\s*$)",
        re.I,
    ),
    # "Bachelor of Science Honours in Computer Science" (with trailing keyword)
    re.compile(
        r"((?:Bachelor|Master|Doctor|Diploma|Certificate|Associate)\s+of\s+"
        r"[\w\s,&\-\(\)]+?(?:\s+Honou?rs|\s+\(Hons\)|\s+Hons)?"
        r"(?:\s+in\s+[\w\s,&\-\(\)]+?)?)"
        r"(?:" + TITLE_STOP + r"|\s*[,.;:]|\s*$)",
        re.I,
    ),
    # "BSc Honours in Computer Science"
    re.compile(
        r"((?:BSc|BA|BCom|BEng|BTech|BEd|MSc|MA|MBA|MEng|MEd|PhD|MBChB|BDS|BPharm)\s*"
        r"(?:\s+(?:Honou?rs|\(Hons\)|Hons))?\s*(?:in\s+[\w\s,&\-\(\)]+?)?)"
        r"(?:" + TITLE_STOP + r"|\s*[,.;:]|\s*$)",
        re.I,
    ),
]


class CredentialExtractionService:
    """Parses raw OCR text from a certificate into structured qualification data."""

    # Known institutions for fuzzy matching (loaded from institutions.js equivalent)
    KNOWN_INSTITUTIONS = [
        "Midlands State University",
        "University of Zimbabwe",
        "National University of Science and Technology",
        "Chinhoyi University of Technology",
        "Bindura University of Science Education",
        "Great Zimbabwe University",
        "Harare Institute of Technology",
        "Women's University in Africa",
        "Catholic University in Zimbabwe",
        "Africa University",
        "Zimbabwe Open University",
        "Gwanda State University",
        "Marondera University of Agricultural Sciences and Technology",
        "Lupane State University",
        "Zimbabwe National Army",
        "Harare Polytechnic",
        "Bulawayo Polytechnic",
        "Gweru Polytechnic",
        "Kwekwe Polytechnic",
        "Masvingo Polytechnic",
        "Mutare Polytechnic",
    ]

    @staticmethod
    def extract(file_bytes: bytes, filename: str, db=None) -> ExtractedCredential:
        """Extract structured credential data from an uploaded file.

        Tries AI vision extraction first (GPT-4o-mini reads the document
        directly, which is far more accurate than regex on OCR text).
        Falls back to OCR + regex parsing when AI is unavailable (no API
        key, out of credits, or the call fails).

        The OpenAI key is resolved from the DB (admin Settings page) when
        ``db`` is provided, then from the ``OPENAI_API_KEY`` env var.
        """
        from app.services.ai_extraction_service import AIExtractionService

        ai_result = AIExtractionService.extract(file_bytes, filename, db=db)
        if ai_result and (ai_result.serial_number or ai_result.holder_name or ai_result.title):
            return ai_result

        from app.services.document_service import DocumentService

        raw_text = DocumentService.extract_text(file_bytes, filename)
        return CredentialExtractionService.parse_text(raw_text)

    @staticmethod
    def parse_text(raw_text: str) -> ExtractedCredential:
        """Parse raw text into structured credential data."""
        result = ExtractedCredential(raw_text=raw_text)

        if not raw_text or not raw_text.strip():
            logger.warning("No text to parse for credential extraction")
            return result

        # Normalize OCR artifacts (merged words, misread characters)
        normalized = normalize_ocr_text(raw_text)

        result.holder_name = CredentialExtractionService._extract_holder_name(normalized, raw_text)
        result.issuing_institution = CredentialExtractionService._extract_institution(normalized, raw_text)
        result.title = CredentialExtractionService._extract_title(normalized, raw_text)
        result.qualification_type = CredentialExtractionService._extract_type(normalized, result.title)
        result.grade = CredentialExtractionService._extract_grade(normalized, raw_text)
        result.serial_number = CredentialExtractionService._extract_serial(normalized, raw_text)
        result.registration_number = CredentialExtractionService._extract_registration(normalized, raw_text)
        result.date_issued = CredentialExtractionService._extract_date(normalized, raw_text)
        result.holder_id_number = CredentialExtractionService._extract_id(normalized, raw_text)

        # Build confidence report
        result.confidence = CredentialExtractionService._build_confidence(result)

        return result

    @staticmethod
    def _extract_holder_name(normalized: str, raw: str) -> str | None:
        """Extract holder name, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern in HOLDER_PATTERNS:
                m = pattern.search(text)
                if m:
                    name = m.group(1).strip()
                    # Clean up: remove trailing punctuation, collapse whitespace
                    name = re.sub(r"[,.;:].*$", "", name).strip()
                    name = re.sub(r"\s+", " ", name)
                    # Remove common OCR noise words that get appended.
                    # \b ensures we only strip whole noise tokens — without it,
                    # "PER" would match inside "Person" and truncate real names.
                    name = re.sub(
                        r"\s+(?:OG|ERTIES|aela|Co|SNA|L|com|NAL|TRUE|RUE|PCT|TCR|ERR|PRR|RRR|Tey|Terr|PER|ERE|RSPR|REET|eee)\b.*$",
                        "",
                        name,
                        flags=re.I,
                    )
                    name = re.sub(r"\s+", " ", name).strip()
                    # Title-case the name (but preserve already-mixed-case)
                    if name.isupper():
                        name = " ".join(w.capitalize() for w in name.split())
                    if len(name) >= 3 and name.lower() not in {"this", "that", "the", "hereby", "we"}:
                        return name
        return None

    @staticmethod
    def _extract_institution(normalized: str, raw: str) -> str | None:
        """Extract institution name, trying normalized text first then raw.

        Also matches against known institutions using fuzzy matching, since
        OCR on scanned certificates often produces noisy text.
        """
        for text in [normalized, raw]:
            # 1. Try regex pattern matching
            matches = INSTITUTION_KEYWORDS.findall(text)
            seen = set()
            candidates = []
            for m in matches:
                clean = m.strip().rstrip(",.;:")
                # Remove trailing "of" with no continuation
                clean = re.sub(r"\s+of\s*$", "", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                if len(clean) > 5 and clean.lower() not in seen:
                    seen.add(clean.lower())
                    candidates.append(clean)

            if candidates:
                # Prefer the longest match (most specific)
                candidates.sort(key=len, reverse=True)
                # Title-case if all uppercase
                inst = candidates[0]
                if inst.isupper():
                    inst = " ".join(w.capitalize() for w in inst.split())
                # Verify against known institutions (fuzzy)
                matched = CredentialExtractionService._match_known_institution(inst)
                return matched or inst

            # 2. Try fuzzy matching against known institutions
            matched = CredentialExtractionService._fuzzy_match_institution(text)
            if matched:
                return matched

        return None

    @staticmethod
    def _match_known_institution(candidate: str) -> str | None:
        """Match a candidate institution name against known institutions."""
        candidate_lower = candidate.lower()
        for known in CredentialExtractionService.KNOWN_INSTITUTIONS:
            known_lower = known.lower()
            # Exact match (case-insensitive)
            if candidate_lower == known_lower:
                return known
            # Candidate contains the full known name
            if known_lower in candidate_lower:
                return known
            # Known name contains the candidate
            if candidate_lower in known_lower and len(candidate) > 5:
                return known
        return None

    @staticmethod
    def _fuzzy_match_institution(text: str) -> str | None:
        """Fuzzy match text against known institutions using word overlap."""
        text_lower = text.lower()
        text_words = set(re.findall(r"\b\w{3,}\b", text_lower))

        best_match = None
        best_score = 0

        for known in CredentialExtractionService.KNOWN_INSTITUTIONS:
            known_words = set(re.findall(r"\b\w{3,}\b", known.lower()))
            if not known_words:
                continue
            # How many known words appear in the text
            overlap = known_words & text_words
            score = len(overlap) / len(known_words)
            # Require at least 60% word overlap
            if score > best_score and score >= 0.6:
                best_score = score
                best_match = known

        return best_match

    @staticmethod
    def _extract_title(normalized: str, raw: str) -> str | None:
        """Extract qualification title, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern in TITLE_PATTERNS:
                m = pattern.search(text)
                if m:
                    title = m.group(1).strip().rstrip(",.;:")
                    title = re.sub(r"\s+", " ", title)
                    # Normalize "Honours" / "(Hons)"
                    title = re.sub(r"\(Hons\)", "Honours", title, flags=re.I)
                    title = re.sub(r"\bHons\b", "Honours", title, flags=re.I)
                    # Fix common OCR misreads in degree titles
                    title = re.sub(r"Inforinatics", "Informatics", title, flags=re.I)
                    # Strip OCR noise: month names + years, short repeating fragments,
                    # and common certificate phrases that leak through
                    title = re.sub(
                        r"\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
                        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
                        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}",
                        "",
                        title,
                        flags=re.I,
                    )
                    title = re.sub(
                        r"\s+(?:we|hereby|certify|that|this|day|having|satisfied|"
                        r"examiners|admitted|senate|box|successfully|completed|"
                        r"programme|approved)\b.*$",
                        "",
                        title,
                        flags=re.I,
                    )
                    # Strip runs of short all-caps noise tokens (e.g. "SS SS See")
                    title = re.sub(r"\s+(?:[A-Z]{1,3}\s+){2,}[A-Z]{1,3}\b", "", title)
                    # Remove trailing prepositions and short fragments
                    title = re.sub(r"\s+(?:in|of|and|the|for|with)$", "", title, flags=re.I)
                    title = re.sub(r"\s+\w{1,3}$", "", title)
                    title = title.strip()
                    if len(title) > 5:
                        return title
        return None

    @staticmethod
    def _extract_type(text: str, title: str | None) -> str | None:
        # First try patterns on the full text
        for pattern, qual_type in TYPE_PATTERNS:
            if pattern.search(text):
                return qual_type

        # Fall back to inferring from the title
        if title:
            title_lower = title.lower()
            if "doctor" in title_lower or "phd" in title_lower:
                return "doctorate"
            if "master" in title_lower or "msc" in title_lower or "ma " in title_lower or "mba" in title_lower:
                return "masters_degree"
            if "bachelor" in title_lower or "bsc" in title_lower or "ba " in title_lower or "bcom" in title_lower:
                return "undergraduate_degree"
            if "diploma" in title_lower:
                return "diploma"
            if "certificate" in title_lower:
                return "certificate"

        return None

    @staticmethod
    def _extract_grade(normalized: str, raw: str) -> str | None:
        """Extract grade/classification, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern, grade_label in GRADE_PATTERNS:
                if pattern.search(text):
                    return grade_label
        return None

    @staticmethod
    def _extract_serial(normalized: str, raw: str) -> str | None:
        """Extract serial number, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern in SERIAL_PATTERNS:
                m = pattern.search(text)
                if m:
                    val = m.group(1).strip().rstrip(",.;:")
                    if len(val) >= 3:
                        return val
        return None

    @staticmethod
    def _extract_registration(normalized: str, raw: str) -> str | None:
        """Extract registration number, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern in REG_PATTERNS:
                m = pattern.search(text)
                if m:
                    val = m.group(1).strip().rstrip(",.;:")
                    if len(val) >= 3:
                        return val
        return None

    @staticmethod
    def _extract_date(normalized: str, raw: str) -> str | None:
        """Extract date, trying normalized text first then raw.

        Dates are normalized to YYYY-MM-DD so the regex fallback matches
        the AI extraction format and works with downstream date parsing.
        """
        for text in [normalized, raw]:
            for pattern in DATE_PATTERNS:
                m = pattern.search(text)
                if m:
                    return CredentialExtractionService._normalize_date_string(m.group(1).strip())
        return None

    @staticmethod
    def _normalize_date_string(date_str: str) -> str:
        """Normalize a date string to YYYY-MM-DD where possible.

        Handles:
        - "15th June 2023" / "15 June 2023" -> "2023-06-15"
        - "June 15, 2023" -> "2023-06-15"
        - "15/06/2023" / "15-06-2023" -> "2023-06-15" (day-first, common in ZW/UK)
        - "2023-06-15" -> unchanged
        Returns the original string when parsing fails.
        """
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        # ISO format — already normalized
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str)
        if m:
            return date_str

        # "15th June 2023" / "15 June 2023"
        m = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})$", date_str)
        if m and m.group(2).lower() in months:
            return f"{m.group(3)}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"

        # "June 15, 2023" / "June 15 2023"
        m = re.match(r"^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$", date_str)
        if m and m.group(1).lower() in months:
            return f"{m.group(3)}-{months[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"

        # "Oct 2025" / "October 2025" (month + year, no day)
        m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", date_str)
        if m and m.group(1).lower() in months:
            return f"{m.group(2)}-{months[m.group(1).lower()]:02d}-01"

        # "15/06/2023" / "15-06-2023" (day-first)
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", date_str)
        if m:
            return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

        return date_str

    @staticmethod
    def _extract_id(normalized: str, raw: str) -> str | None:
        """Extract national ID, trying normalized text first then raw."""
        for text in [normalized, raw]:
            for pattern in ID_PATTERNS:
                m = pattern.search(text)
                if m:
                    val = m.group(1).strip()
                    if len(val) >= 5:
                        return val
        return None

    @staticmethod
    def _build_confidence(result: ExtractedCredential) -> dict:
        """Build a confidence report showing which fields were extracted."""
        fields = [
            "holder_name",
            "issuing_institution",
            "title",
            "qualification_type",
            "grade",
            "serial_number",
            "registration_number",
            "date_issued",
            "holder_id_number",
        ]
        found = sum(1 for f in fields if getattr(result, f))
        return {
            "fields_extracted": found,
            "fields_total": len(fields),
            "percentage": round(found / len(fields) * 100),
            "extracted": [f for f in fields if getattr(result, f)],
            "missing": [f for f in fields if not getattr(result, f)],
        }
