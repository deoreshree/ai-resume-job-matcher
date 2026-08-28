"""Job-role catalog access and transparent custom job-description analysis."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from config import JOB_ROLES_PATH
from modules.skill_extractor import extract_skills, normalize_skill


def _unique(items: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = str(item).strip()
        if cleaned and cleaned.casefold() not in seen:
            values.append(cleaned)
            seen.add(cleaned.casefold())
    return values


@lru_cache(maxsize=1)
def load_job_roles() -> list[dict[str, Any]]:
    """Load the editable predefined roles once per process."""
    try:
        payload = json.loads(JOB_ROLES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not load data/job_roles.json.") from exc
    roles = payload.get("roles", [])
    if not isinstance(roles, list) or not roles:
        raise RuntimeError("The job-role catalog has no roles.")
    return roles


def get_job_profile(role_title: str) -> dict[str, Any]:
    """Return a copy of a catalog job profile, matched case-insensitively."""
    wanted = (role_title or "").strip().casefold()
    for role in load_job_roles():
        if str(role.get("title", "")).casefold() == wanted:
            return dict(role, source="predefined", raw_text="")
    raise ValueError(f"Unknown job role: {role_title!r}")


def _section_for_skill(text: str, skill: str) -> str:
    """Use nearby JD wording to distinguish must-have from nice-to-have skills."""
    position = text.casefold().find(skill.casefold())
    if position < 0:
        return "required"
    sentence_start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position), text.rfind(";", 0, position)) + 1
    sentence_end_candidates = [point for point in (text.find(".", position), text.find("\n", position), text.find(";", position)) if point >= 0]
    sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)
    context = text[sentence_start:sentence_end].casefold()
    return "preferred" if re.search(r"preferred|nice to have|bonus|plus|desirable", context) else "required"


def _extract_experience(text: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?).{0,35}experience", text, re.IGNORECASE)
    return float(match.group(1)) if match else 0.0


def _extract_education(text: str) -> list[str]:
    matches = re.findall(
        r"(?:bachelor'?s|master'?s|b\.?tech|m\.?tech|b\.?s\.?|m\.?s\.?|mba|diploma).{0,100}",
        text,
        re.IGNORECASE,
    )
    return _unique([re.sub(r"\s+", " ", item).strip(" .;:-") for item in matches])


def _candidate_keywords(text: str, skills: list[str]) -> list[str]:
    phrases = re.findall(r"\b[a-zA-Z][a-zA-Z-]*(?:\s+[a-zA-Z][a-zA-Z-]*){1,2}\b", text)
    blocked = {"the role", "you will", "we are", "this role", "our team", "to the", "and the", "with the"}
    valuable = [phrase for phrase in phrases if phrase.casefold() not in blocked and len(phrase) > 6]
    return _unique([*skills, *valuable])[:25]


def analyze_job_description(text: str) -> dict[str, Any]:
    """Derive a structured profile from pasted job text using the shared skill catalog."""
    raw = re.sub(r"[\t ]+", " ", (text or "")).strip()
    if len(raw) < 40:
        raise ValueError("Please paste a fuller job description (at least 40 characters).")
    extracted = extract_skills(raw)
    required: list[str] = []
    preferred: list[str] = []
    for skill in extracted["skills"]:
        (preferred if _section_for_skill(raw, skill) == "preferred" else required).append(normalize_skill(skill))

    title_match = re.search(r"(?:job title|role|position)\s*[:\-]\s*([^\n.]{3,80})", text or "", re.IGNORECASE)
    first_line = (text or "").strip().splitlines()[0].strip() if text else ""
    title = title_match.group(1).strip() if title_match else first_line[:80]
    if not title or len(title) > 70:
        title = "Custom Job Description"
    technologies = _unique([*required, *preferred])
    return {
        "title": title,
        "required_skills": _unique(required),
        "preferred_skills": _unique(preferred),
        "keywords": _candidate_keywords(raw, technologies),
        "education": _extract_education(raw),
        "minimum_experience": _extract_experience(raw),
        "tools": technologies,
        "technologies": technologies,
        "source": "custom",
        "raw_text": raw,
    }
