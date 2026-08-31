"""Tests for the optional LLM path of the resume advisor (mocked, no network)."""

from __future__ import annotations

import json

import pytest

import genai.resume_advisor as advisor_module
from genai.llm_client import LLMUnavailableError
from genai.resume_advisor import advise_resume


def _inputs():
    resume = {"skills": ["Python"], "years_experience": 1, "projects": [{"title": "Forecasting tool"}]}
    profile = {"title": "Data Scientist", "required_skills": ["Python", "SQL"]}
    match = {
        "skill_match": {"matching_skills": ["Python"], "missing_skills": ["SQL"], "missing_required": ["SQL"], "skill_gaps": []},
        "keyword_match": {"missing_keywords": []},
    }
    return resume, profile, match


_VALID_LLM_JSON = json.dumps(
    {
        "strengths": ["Strong Python evidence."],
        "weaknesses": ["No evidence of SQL was found in the resume."],
        "improvements": ["Consider learning SQL."],
        "missing_keywords": ["data analysis"],
        "skill_recommendations": ["SQL: practice joins."],
        "project_suggestions": ["Quantify the forecasting tool outcome."],
        "ats_suggestions": ["Use standard headings."],
    }
)


def test_llm_valid_response_is_used(monkeypatch):
    monkeypatch.setattr(advisor_module, "is_configured", lambda: True)
    monkeypatch.setattr(advisor_module, "generate_text", lambda system, user: _VALID_LLM_JSON)
    resume, profile, match = _inputs()
    result = advise_resume(resume, profile, match)
    assert result["source"] == "AI-written advice"
    assert result["strengths"] == ["Strong Python evidence."]
    assert result["improvements"] == ["Consider learning SQL."]


def test_llm_invalid_json_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(advisor_module, "is_configured", lambda: True)
    monkeypatch.setattr(advisor_module, "generate_text", lambda system, user: "not json at all")
    resume, profile, match = _inputs()
    result = advise_resume(resume, profile, match)
    assert result["source"] == "Rule-based guidance"
    assert result["improvements"]


def test_llm_partial_json_falls_back_to_rules(monkeypatch):
    """An LLM response missing any required key must be rejected, not half-trusted."""
    monkeypatch.setattr(advisor_module, "is_configured", lambda: True)
    monkeypatch.setattr(advisor_module, "generate_text", lambda system, user: json.dumps({"strengths": ["ok"]}))
    resume, profile, match = _inputs()
    result = advise_resume(resume, profile, match)
    assert result["source"] == "Rule-based guidance"


def test_llm_outage_falls_back_to_rules(monkeypatch):
    def boom(system, user):
        raise LLMUnavailableError("upstream down")

    monkeypatch.setattr(advisor_module, "is_configured", lambda: True)
    monkeypatch.setattr(advisor_module, "generate_text", boom)
    resume, profile, match = _inputs()
    result = advise_resume(resume, profile, match)
    assert result["source"] == "Rule-based guidance"
    assert "unavailable" in result["notice"].casefold()


def test_no_key_uses_rules_with_notice(monkeypatch):
    monkeypatch.setattr(advisor_module, "is_configured", lambda: False)
    resume, profile, match = _inputs()
    result = advise_resume(resume, profile, match)
    assert result["source"] == "Rule-based guidance"
    assert "OPENAI_API_KEY" in result["notice"]
