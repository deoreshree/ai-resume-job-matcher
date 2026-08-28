"""Resume parser: PDF/DOCX extraction plus hybrid NLP/heuristic structuring."""

from __future__ import annotations

import io
import logging
import re
from typing import Any, Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from config import SPACY_MODEL
from modules.skill_extractor import extract_skills
from utils.helpers import estimate_years_of_experience, find_degree
from utils.text_cleaner import clean_text
from utils.validators import ResumeValidationError, validate_resume_file

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:(?:\+?\d{1,3}[\s.-]*)?(?:\(?\d{2,4}\)?[\s.-]*)?\d{3,4}[\s.-]?\d{4})"
)
URL_RE = re.compile(
    r"(https?://[^\s)]+|www\.[^\s)]+|linkedin\.com/in/[^\s)]+|github\.com/[^\s)]+)",
    re.IGNORECASE,
)

_HEADING_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "profile", "objective", "about me", "professional summary"),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "professional experience",
        "work history",
        "internship",
        "internships",
    ),
    "education": ("education", "academic background", "academics", "qualifications"),
    "skills": (
        "skills",
        "technical skills",
        "core competencies",
        "technologies",
        "tech stack",
        "key skills",
    ),
    "projects": ("projects", "personal projects", "academic projects", "key projects"),
    "certifications": ("certifications", "certificates", "licenses"),
    "achievements": ("achievements", "awards", "honors", "accomplishments"),
    "contact": ("contact", "contact information", "personal information"),
}

_HEADING_LOOKUP: dict[str, str] = {}
for _section, _aliases in _HEADING_ALIASES.items():
    for _alias in _aliases:
        _HEADING_LOOKUP[_alias] = _section

_NAME_STOP = re.compile(
    r"resume|curriculum|vitae|contact|email|phone|objective|summary|profile",
    re.IGNORECASE,
)
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "using",
    "used",
    "into",
    "over",
    "your",
    "their",
    "have",
    "has",
    "were",
    "been",
    "also",
    "etc",
}

_nlp = None
_nlp_load_attempted = False


def get_nlp():
    """Load spaCy once. Returns None if the model is unavailable (tests still run)."""
    global _nlp, _nlp_load_attempted
    if _nlp_load_attempted:
        return _nlp
    _nlp_load_attempted = True
    try:
        import spacy

        _nlp = spacy.load(SPACY_MODEL)
    except Exception:
        logger.warning(
            "spaCy model '%s' is not available; using heuristic parsing only.",
            SPACY_MODEL,
        )
        _nlp = None
    return _nlp


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Return raw text from a PDF or DOCX resume."""
    validate_resume_file(filename, file_bytes)
    name = filename.lower()
    try:
        if name.endswith(".pdf"):
            raw = _extract_pdf(file_bytes)
        elif name.endswith(".docx"):
            raw = _extract_docx(file_bytes)
        else:
            raise ResumeValidationError("Unsupported file type. Please upload a PDF or DOCX resume.")
    except ResumeValidationError:
        raise
    except PdfReadError as exc:
        raise ResumeValidationError(
            "The PDF could not be read. It may be damaged, encrypted, or image-only."
        ) from exc
    except Exception as exc:
        if filename.lower().endswith(".docx"):
            raise ResumeValidationError(
                "The DOCX file could not be read. Please export it again and retry."
            ) from exc
        raise ResumeValidationError(
            "The resume could not be read. Please try another PDF or DOCX file."
        ) from exc

    cleaned = clean_text(raw)
    if not cleaned:
        raise ResumeValidationError(
            "No extractable text was found. Scanned or image-only resumes are not supported yet."
        )
    return cleaned


def parse_resume(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Parse a resume file into a structured dictionary."""
    text = extract_text(file_bytes, filename)
    return parse_resume_text(text)


def parse_resume_text(text: str) -> dict[str, Any]:
    """Parse cleaned (or semi-raw) resume text into structured fields."""
    cleaned = clean_text(text)
    if not cleaned:
        raise ResumeValidationError("The resume appears to be empty after text extraction.")

    sections = split_sections(cleaned)
    email = _first_match(EMAIL_RE, cleaned)
    phone = _normalize_phone(_first_match(PHONE_RE, cleaned))
    urls = _unique(URL_RE.findall(cleaned))
    name = extract_name(cleaned, sections)

    education = parse_education(sections.get("education", ""))
    experience = parse_experience_entries(sections.get("experience", ""))
    projects = parse_project_entries(sections.get("projects", ""))
    certifications = _bullet_or_line_items(sections.get("certifications", ""))
    achievements = _bullet_or_line_items(sections.get("achievements", ""))
    section_skills = extract_skill_phrases(sections.get("skills", ""), cleaned)
    skill_details = extract_skills(cleaned)
    skills = skill_details["skills"] or section_skills
    keywords = extract_keywords(cleaned, skills)

    years = estimate_years_of_experience(sections.get("experience", "") or cleaned)

    linkedin = next((url for url in urls if "linkedin.com" in url.casefold()), None)
    github = next((url for url in urls if "github.com" in url.casefold()), None)
    portfolio = next((url for url in urls if url not in {linkedin, github}), None)
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "urls": urls,
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
        "personal_information": {
            "name": name,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "portfolio": portfolio,
        },
        "education": education,
        "skills": skills,
        "skill_details": skill_details,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "achievements": achievements,
        "keywords": keywords,
        "years_experience": years,
        "sections": sections,
        "raw_text": cleaned,
    }


def split_sections(text: str) -> dict[str, str]:
    """Split resume text into known sections using heading detection."""
    lines = text.split("\n")
    buckets: dict[str, list[str]] = {"preamble": []}
    current = "preamble"

    for line in lines:
        heading = _detect_heading(line)
        if heading:
            current = heading
            buckets.setdefault(current, [])
            continue
        buckets.setdefault(current, []).append(line)

    return {key: "\n".join(values).strip() for key, values in buckets.items() if "".join(values).strip()}


def extract_name(text: str, sections: Optional[dict[str, str]] = None) -> Optional[str]:
    """Guess the candidate name from the header and optional NER."""
    header = "\n".join(text.split("\n")[:12])
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(header[:1500])
        persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
        for person in persons:
            if _looks_like_name(person):
                return person

    for line in header.split("\n"):
        candidate = line.strip(" |-")
        if _looks_like_name(candidate):
            return candidate
    return None


def extract_skill_phrases(skills_section: str, full_text: str) -> list[str]:
    """Collect skill-like phrases from the dedicated skills section."""
    source = skills_section or ""
    parts = re.split(r"[,|/•;]|\n| - ", source)
    skills: list[str] = []
    for part in parts:
        item = re.sub(r"^(?:technical|soft|skills?)\s*[:\-]\s*", "", part.strip(), flags=re.I)
        item = item.strip(" -:\t")
        if 1 < len(item) <= 40 and not EMAIL_RE.search(item) and not item.lower().startswith("http"):
            if not re.fullmatch(r"[\W_]+", item):
                skills.append(_title_skill(item))
    return _unique(skills)[:80]


def extract_keywords(text: str, skills: list[str]) -> list[str]:
    """Keywords from noun chunks when spaCy is available, else skills + notable tokens."""
    keywords = list(skills)
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(text[:8000])
        for chunk in doc.noun_chunks:
            phrase = clean_text(chunk.text)
            if _usable_keyword(phrase):
                keywords.append(_title_skill(phrase))
    else:
        for token in re.findall(r"\b[A-Z][A-Za-z0-9+#.]{2,}\b", text):
            if _usable_keyword(token):
                keywords.append(token)
    return _unique(keywords)[:50]


def parse_education(section_text: str) -> list[dict[str, Any]]:
    if not section_text:
        return []
    blocks = _split_blocks(section_text)
    entries: list[dict[str, Any]] = []
    for block in blocks:
        degree = find_degree(block)
        year_match = re.search(r"(?:19|20)\d{2}", block)
        entries.append(
            {
                "raw": block,
                "degree": degree,
                "institution": _guess_institution(block),
                "year": year_match.group(0) if year_match else None,
            }
        )
    return entries


def parse_experience_entries(section_text: str) -> list[dict[str, Any]]:
    if not section_text:
        return []
    entries: list[dict[str, Any]] = []
    for block in _split_blocks(section_text):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        headline = lines[0]
        bullets = [line.lstrip("- ").strip() for line in lines[1:] if line.strip()]
        dates = re.search(r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.\s,]*\s*(?:19|20)\d{2}\s*[-–—]\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[.\s,]*)?(?:(?:19|20)\d{2}|Present|Current)", block, re.IGNORECASE)
        entries.append(
            {
                "raw": block,
                "title": headline,
                "organization": _guess_organization(headline),
                "bullets": bullets,
                "responsibilities": bullets,
                "duration": dates.group(0) if dates else None,
            }
        )
    return entries


def parse_project_entries(section_text: str) -> list[dict[str, Any]]:
    if not section_text:
        return []
    entries: list[dict[str, Any]] = []
    for block in _split_blocks(section_text):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        entries.append(
            {
                "title": lines[0].lstrip("- ").strip(),
                "description": " ".join(line.lstrip("- ").strip() for line in lines[1:]),
                "technologies": extract_skills(block)["skills"],
                "raw": block,
            }
        )
    return entries


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ResumeValidationError(
                "This PDF is password-protected. Please upload an unlocked copy."
            ) from exc
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        document = Document(io.BytesIO(file_bytes))
    except PackageNotFoundError as exc:
        raise ResumeValidationError(
            "The DOCX file could not be read. Please upload a valid Word document."
        ) from exc

    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text:
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _detect_heading(line: str) -> Optional[str]:
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped) > 48:
        return None
    if stripped.startswith("-"):
        return None
    key = re.sub(r"[^a-zA-Z\s]", "", stripped).lower().strip()
    key = re.sub(r"\s+", " ", key)
    if key in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[key]
    if stripped.isupper() and key in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[key]
    return None


def _looks_like_name(value: str) -> bool:
    if not value or _NAME_STOP.search(value) or EMAIL_RE.search(value) or URL_RE.search(value):
        return False
    if any(ch.isdigit() for ch in value):
        return False
    words = [w for w in re.split(r"\s+", value) if w]
    if not (2 <= len(words) <= 4):
        return False
    if len(value) > 60:
        return False
    return all(re.match(r"^[A-Z][A-Za-z'’.\-]+$", w) for w in words)


def _usable_keyword(phrase: str) -> bool:
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", phrase)]
    if not tokens or len(tokens) > 4:
        return False
    if all(t in _STOPWORDS or len(t) < 3 for t in tokens):
        return False
    return True


def _title_skill(item: str) -> str:
    if item.isupper() and len(item) <= 5:
        return item
    if any(c.islower() for c in item) and any(c.isupper() for c in item) and " " not in item:
        return item
    return item.strip()


def _guess_institution(block: str) -> Optional[str]:
    for line in block.split("\n"):
        if find_degree(line):
            continue
        cleaned = line.strip(" -,")
        if cleaned and not re.search(r"(?:19|20)\d{2}", cleaned):
            return cleaned
    return None


def _guess_organization(headline: str) -> Optional[str]:
    for sep in (" at ", " | ", " - ", " – ", "@"):
        if sep in headline:
            parts = [p.strip() for p in re.split(re.escape(sep), headline, maxsplit=1)]
            if len(parts) == 2 and parts[1]:
                return parts[1]
    return None


def _split_blocks(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n", text.strip())
    blocks = [chunk.strip() for chunk in chunks if chunk.strip()]
    if len(blocks) == 1:
        lines = [line for line in text.split("\n") if line.strip()]
        grouped: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            is_new = bool(re.match(r"^[A-Z].{3,}", line)) and not line.startswith("-")
            if is_new and current and not current[-1].startswith("-"):
                grouped.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            grouped.append(current)
        if len(grouped) > 1:
            return ["\n".join(g) for g in grouped]
    return blocks


def _bullet_or_line_items(text: str) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    for line in text.split("\n"):
        item = line.strip().lstrip("-").strip()
        if item:
            items.append(item)
    return items


def _first_match(pattern: re.Pattern[str], text: str) -> Optional[str]:
    match = pattern.search(text)
    return match.group(0) if match else None


def _normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10 or len(digits) > 15:
        return None
    return value.strip()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out
