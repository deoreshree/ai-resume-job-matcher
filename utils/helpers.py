"""Shared helpers used by the resume parser and later scoring."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_YEAR = r"(?:19|20)\d{2}"
_PRESENT = r"(?:Present|Current|Now|Ongoing)"

DATE_RANGE_RE = re.compile(
    rf"(?P<start_month>{_MONTH})?[.\s,/]*(?P<start_year>{_YEAR})\s*[-–—to]+\s*"
    rf"(?:(?P<end_month>{_MONTH})?[.\s,/]*)?(?P<end_year>{_YEAR}|{_PRESENT})",
    re.IGNORECASE,
)

EXPLICIT_YEARS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)

DEGREE_RE = re.compile(
    r"\b("
    r"Ph\.?\s*D\.?|Doctorate|MBA|M\.?\s*Tech|M\.?\s*E\.?|M\.?\s*S\.?|M\.?\s*Sc|"
    r"Master(?:'?s)?(?:\s+of\s+(?:Science|Technology|Engineering|Arts|Business))?"
    r"|B\.?\s*Tech|B\.?\s*E\.?|B\.?\s*S\.?|B\.?\s*Sc|B\.?\s*A\.?|"
    r"Bachelor(?:'?s)?(?:\s+of\s+(?:Science|Technology|Engineering|Arts|Commerce))?"
    r"|BCA|MCA|BBA|Diploma"
    r")\b",
    re.IGNORECASE,
)


def _parse_month(token: Optional[str]) -> int:
    if not token:
        return 1
    return MONTH_MAP.get(token.lower().rstrip("."), 1)


def _end_date(month: Optional[str], year_or_present: str) -> date:
    today = date.today()
    if re.fullmatch(_PRESENT, year_or_present, re.IGNORECASE):
        return today
    year = int(year_or_present)
    return date(year, _parse_month(month), 1)


def _start_date(month: Optional[str], year: str) -> date:
    return date(int(year), _parse_month(month), 1)


def extract_date_ranges(text: str) -> list[tuple[date, date]]:
    """Return (start, end) date pairs found in text."""
    ranges: list[tuple[date, date]] = []
    for match in DATE_RANGE_RE.finditer(text or ""):
        start = _start_date(match.group("start_month"), match.group("start_year"))
        end = _end_date(match.group("end_month"), match.group("end_year"))
        if end < start:
            continue
        ranges.append((start, end))
    return ranges


def merge_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda item: item[0])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def years_from_intervals(intervals: list[tuple[date, date]]) -> float:
    total_days = 0
    for start, end in merge_intervals(intervals):
        total_days += (end - start).days
    return round(max(total_days, 0) / 365.25, 1)


def estimate_years_of_experience(text: str) -> float:
    """Estimate years of experience from date ranges, with an explicit-years fallback."""
    from_ranges = years_from_intervals(extract_date_ranges(text))
    explicit: list[float] = [float(m.group(1)) for m in EXPLICIT_YEARS_RE.finditer(text or "")]
    explicit_max = max(explicit) if explicit else 0.0
    return max(from_ranges, explicit_max)


def find_degree(text: str) -> Optional[str]:
    match = DEGREE_RE.search(text or "")
    return match.group(0).strip() if match else None


def find_field_of_study(text: str) -> Optional[str]:
    """Identify specialization or field of study (e.g. Computer Science, AI)."""
    if not text:
        return None
    patterns = [
        r"(?:in|of)\s+([A-Z][A-Za-z\s&,]{3,35})(?=\s*[\n\-,]|\s*(?:19|20)\d{2}|$)",
        r"\b(Computer Science|Software Engineering|Data Science|Artificial Intelligence|Machine Learning|Information Technology|Electrical Engineering|Mechanical Engineering|Business Administration|Cybersecurity|Mathematics|Physics)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            captured = match.group(1 if "(" in pattern else 0).strip(" -,\t")
            if captured and len(captured) > 2 and not re.search(r"University|College|Institute|School", captured, re.IGNORECASE):
                return captured
    return None


def find_cgpa_or_percentage(text: str) -> Optional[str]:
    """Extract CGPA/GPA or percentage without confusing dates or arbitrary numbers."""
    if not text:
        return None
    cgpa_match = re.search(r"\b(?:CGPA|GPA|Score|Grade)?\s*[:\-]?\s*([0-4]\.\d{1,2}|[5-9]\.\d{1,2}|10(?:\.0)?)\s*(?:\/\s*(?:4|10))?\b", text, re.IGNORECASE)
    if cgpa_match:
        return cgpa_match.group(0).strip()
    pct_match = re.search(r"\b([5-9]\d(?:\.\d{1,2})?|100)\s*%\b", text)
    if pct_match:
        return pct_match.group(0).strip()
    return None


def find_location(text: str) -> Optional[str]:
    """Find location phrases such as City, State/Country or Remote."""
    if not text:
        return None
    loc_match = re.search(r"\b([A-Z][A-Za-z\s]{2,20},\s*(?:[A-Z]{2}|[A-Z][A-Za-z\s]{2,20}))\b", text)
    if loc_match:
        return loc_match.group(1).strip()
    if re.search(r"\bRemote\b", text, re.IGNORECASE):
        return "Remote"
    return None


def parse_dates_from_block(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse start date, end date, and overall duration string from a text block."""
    if not text:
        return None, None, None
    match = DATE_RANGE_RE.search(text)
    if match:
        start_m = match.group("start_month") or ""
        start_y = match.group("start_year") or ""
        end_m = match.group("end_month") or ""
        end_y = match.group("end_year") or ""
        
        start_str = f"{start_m} {start_y}".strip() if start_y else None
        end_str = f"{end_m} {end_y}".strip() if end_y else None
        duration_str = match.group(0).strip()
        return start_str, end_str, duration_str
    
    # Fallback to single year or Present
    year_match = re.search(r"\b((?:19|20)\d{2})\b", text)
    if year_match:
        return None, year_match.group(1), year_match.group(1)
    return None, None, None

