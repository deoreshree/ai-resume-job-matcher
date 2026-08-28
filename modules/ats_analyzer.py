"""ATS-oriented heuristic analysis with clear, actionable findings."""

from __future__ import annotations

import re
from typing import Any

from config import ATS_WEIGHTS
from modules.matcher import match_keywords, match_skills

RECOMMENDED_SECTIONS = {"summary", "experience", "education", "skills", "projects"}


def _readability_score(text: str) -> float:
    words = re.findall(r"\b\w+\b", text or "")
    if len(words) < 40:
        return 55.0
    sentences = re.split(r"[.!?]+", text)
    average_sentence_length = len(words) / max(1, len([s for s in sentences if s.strip()]))
    # Resumes should be concise; this is a structure signal rather than a judgement of writing quality.
    return round(max(35.0, min(100.0, 100 - max(0, average_sentence_length - 18) * 3)), 2)


def _formatting_score(text: str) -> float:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return 0.0
    bullet_ratio = sum(line.startswith(("-", "•", "*")) for line in lines) / len(lines)
    long_lines = sum(len(line) > 180 for line in lines)
    score = 70 + min(20, bullet_ratio * 60) - min(25, long_lines * 5)
    return round(max(0.0, min(100.0, score)), 2)


def analyze_ats(resume: dict[str, Any], job_profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate an ATS compatibility score and only flag evidence-based issues."""
    text = resume.get("raw_text", "")
    skill_result = match_skills(
        resume.get("skills", []), job_profile.get("required_skills", []), job_profile.get("preferred_skills", [])
    )
    keyword_result = match_keywords(text, job_profile.get("keywords", []))
    present_sections = set(resume.get("sections", {}))
    structure_score = 100 * len(RECOMMENDED_SECTIONS & present_sections) / len(RECOMMENDED_SECTIONS)
    components = {
        "keywords": keyword_result["score"],
        "structure": structure_score,
        "skills": skill_result["score"],
        "readability": _readability_score(text),
        "formatting": _formatting_score(text),
    }
    score = round(sum(components[name] * weight for name, weight in ATS_WEIGHTS.items()), 2)
    issues: list[str] = []
    recommendations: list[str] = []
    missing_sections = sorted(RECOMMENDED_SECTIONS - present_sections)
    if missing_sections:
        issues.append(f"No clearly labelled {', '.join(missing_sections)} section(s) detected.")
        recommendations.append("Use conventional section headings so applicant tracking systems can parse the resume reliably.")
    if skill_result["missing_required"]:
        issues.append("Some required role skills are not evidenced in the resume.")
        recommendations.append("If truthful, describe relevant work or projects using the missing role terminology; otherwise, consider learning those skills.")
    if keyword_result["missing_keywords"]:
        recommendations.append("Use relevant job-description terms naturally when they accurately describe your work; do not add unsupported keywords.")
    if components["readability"] < 70:
        issues.append("Some resume sentences are long for quick ATS/recruiter scanning.")
        recommendations.append("Prefer concise action-oriented bullets with a result or scope where available.")
    if components["formatting"] < 70:
        recommendations.append("Keep formatting simple: standard fonts, short bullets, and no content that exists only in images or text boxes.")
    if not issues:
        recommendations.append("The resume has a readable structure and evidence for the main role requirements. Tailor wording only where it remains accurate.")
    return {
        "score": score,
        "components": {name: round(value, 2) for name, value in components.items()},
        "issues": issues,
        "recommendations": recommendations,
        "detected_sections": sorted(present_sections & RECOMMENDED_SECTIONS),
        "missing_sections": missing_sections,
        "matched_keywords": keyword_result["matched_keywords"],
        "missing_keywords": keyword_result["missing_keywords"],
    }
