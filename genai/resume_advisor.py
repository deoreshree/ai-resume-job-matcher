"""LLM-enhanced resume advice that remains useful without an API key."""

from __future__ import annotations

import json
from typing import Any

from genai.llm_client import LLMUnavailableError, generate_text, is_configured
from modules.recommendation_engine import build_insights


def _context(parsed_resume: dict[str, Any], job_profile: dict[str, Any], match_result: dict[str, Any]) -> str:
    """Limit prompt context to relevant, already extracted facts."""
    return json.dumps(
        {
            "target_role": job_profile.get("title"),
            "target_required_skills": job_profile.get("required_skills", []),
            "candidate_skills": parsed_resume.get("skills", []),
            "candidate_years_experience": parsed_resume.get("years_experience", 0),
            "project_titles": [project.get("title") for project in parsed_resume.get("projects", []) if isinstance(project, dict)],
            "matched_skills": match_result.get("skill_match", {}).get("matching_skills", []),
            "missing_skills": match_result.get("skill_match", {}).get("missing_skills", []),
            "missing_keywords": match_result.get("keyword_match", {}).get("missing_keywords", []),
        },
        ensure_ascii=False,
    )


def _valid_response(value: object) -> dict[str, list[str]] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, list[str]] = {}
    for key in ("strengths", "weaknesses", "improvements", "missing_keywords", "skill_recommendations", "project_suggestions", "ats_suggestions"):
        items = value.get(key)
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            return None
        result[key] = [item.strip() for item in items if item.strip()][:6]
    return result


def advise_resume(parsed_resume: dict[str, Any], job_profile: dict[str, Any], match_result: dict[str, Any]) -> dict[str, Any]:
    """Return tailored advice, falling back to deterministic facts whenever needed."""
    fallback = build_insights(parsed_resume, job_profile, match_result)
    if not is_configured():
        return {**fallback, "source": "Rule-based guidance", "notice": "Add OPENAI_API_KEY to .env to enable optional AI-written advice."}
    system = (
        "You are a careful career advisor. Use only the supplied JSON facts. Never claim the candidate has a missing skill, "
        "invent companies, projects, credentials, numbers, or achievements, or advise false claims. For gaps, say 'consider learning'. "
        "Return valid JSON only with keys strengths, weaknesses, improvements, missing_keywords, skill_recommendations, project_suggestions, ats_suggestions; each value is a list of concise strings."
    )
    try:
        response = _valid_response(json.loads(generate_text(system, _context(parsed_resume, job_profile, match_result))))
        if response is not None:
            return {**response, "source": "AI-written advice", "notice": "Advice is grounded in extracted resume and role facts; verify it before using it."}
    except (LLMUnavailableError, json.JSONDecodeError):
        pass
    return {**fallback, "source": "Rule-based guidance", "notice": "The AI service was unavailable, so evidence-based rule guidance is shown."}
