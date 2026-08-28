"""Explainable skill, keyword, and end-to-end resume matching."""

from __future__ import annotations

import re
from typing import Any

from modules.semantic_matcher import semantic_method, semantic_similarity
from modules.skill_extractor import normalize_skill
from modules.scoring import compute_match_score, education_match_score, experience_match_score


def _unique(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = str(value).strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _coverage(found: list[str], expected: list[str]) -> float:
    return len(found) / len(expected) if expected else 1.0


def match_skills(
    resume_skills: list[str], required: list[str], preferred: list[str] | None = None
) -> dict[str, Any]:
    """Compare canonical skills and rank missing requirements by stated importance."""
    candidate = {normalize_skill(skill).casefold(): normalize_skill(skill) for skill in _unique(resume_skills)}
    required = _unique([normalize_skill(skill) for skill in required])
    preferred = _unique([normalize_skill(skill) for skill in preferred])

    required_matches = [skill for skill in required if skill.casefold() in candidate]
    preferred_matches = [skill for skill in preferred if skill.casefold() in candidate]
    missing_required = [skill for skill in required if skill.casefold() not in candidate]
    missing_preferred = [skill for skill in preferred if skill.casefold() not in candidate]

    required_coverage = _coverage(required_matches, required)
    preferred_coverage = _coverage(preferred_matches, preferred)
    # Core requirements dominate, while preferred experience rewards candidates without
    # making a role with no preferred items score lower.
    score = required_coverage if not preferred else (0.8 * required_coverage + 0.2 * preferred_coverage)
    gaps = [
        {"skill": skill, "importance": "High", "reason": "Listed as a required skill for this target role."}
        for skill in missing_required
    ] + [
        {"skill": skill, "importance": "Medium", "reason": "Listed as a preferred skill for this target role."}
        for skill in missing_preferred
    ]

    return {
        "matching_skills": required_matches + [skill for skill in preferred_matches if skill not in required_matches],
        "required_matches": required_matches,
        "preferred_matches": preferred_matches,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
        "missing_skills": missing_required + missing_preferred,
        "skill_gaps": gaps,
        "required_coverage": round(required_coverage, 4),
        "preferred_coverage": round(preferred_coverage, 4),
        "score": round(score * 100, 2),
    }


def _keyword_pattern(keyword: str) -> str:
    return r"(?<![A-Za-z0-9+#])" + re.escape(keyword.strip()) + r"(?![A-Za-z0-9+#])"


def match_keywords(resume_text: str, job_keywords: list[str]) -> dict[str, Any]:
    """Measure job-keyword coverage using case-insensitive phrase boundaries."""
    keywords = _unique(job_keywords)
    text = resume_text or ""
    matched = [keyword for keyword in keywords if re.search(_keyword_pattern(keyword), text, re.IGNORECASE)]
    missing = [keyword for keyword in keywords if keyword not in matched]
    coverage = _coverage(matched, keywords)
    return {
        "matched_keywords": matched,
        "missing_keywords": missing,
        "coverage": round(coverage, 4),
        "score": round(coverage * 100, 2),
    }


def match_resume_to_job(parsed_resume: dict[str, Any], job_profile: dict[str, Any]) -> dict[str, Any]:
    """Run all score components and return an auditable match result."""
    skills = match_skills(
        parsed_resume.get("skills", []),
        job_profile.get("required_skills", []),
        job_profile.get("preferred_skills", []),
    )
    keywords = match_keywords(parsed_resume.get("raw_text", ""), job_profile.get("keywords", []))
    profile_text = job_profile.get("raw_text") or " ".join(
        [
            job_profile.get("title", ""),
            *job_profile.get("required_skills", []),
            *job_profile.get("preferred_skills", []),
            *job_profile.get("keywords", []),
            *job_profile.get("technologies", []),
        ]
    )
    semantic = semantic_similarity(parsed_resume.get("raw_text", ""), profile_text)
    experience = experience_match_score(
        float(parsed_resume.get("years_experience") or 0), float(job_profile.get("minimum_experience") or 0)
    )
    education = education_match_score(parsed_resume.get("education", []), job_profile.get("education", []))
    scoring = compute_match_score(
        {
            "skills": skills["score"],
            "semantic": semantic * 100,
            "experience": experience * 100,
            "education": education * 100,
            "keywords": keywords["score"],
        }
    )
    return {
        **scoring,
        "skill_match": skills,
        "keyword_match": keywords,
        "semantic_similarity": round(semantic * 100, 2),
        "semantic_method": semantic_method(),
        "experience_score": round(experience * 100, 2),
        "education_score": round(education * 100, 2),
    }
