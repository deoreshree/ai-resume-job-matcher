"""Tests for the deterministic recommendation engine."""

from __future__ import annotations

from modules.recommendation_engine import build_insights, learning_path


def _resume(**overrides):
    base = {
        "skills": ["Python", "Pandas"],
        "years_experience": 2,
        "projects": [{"title": "Churn model"}],
        "experience": [{"title": "Analyst"}],
    }
    base.update(overrides)
    return base


def _profile(**overrides):
    base = {
        "title": "Data Scientist",
        "required_skills": ["Python", "SQL"],
        "preferred_skills": [],
        "keywords": ["data analysis"],
        "minimum_experience": 1,
    }
    base.update(overrides)
    return base


def _match(**overrides):
    base = {
        "skill_match": {
            "matching_skills": ["Python"],
            "missing_required": ["SQL"],
            "missing_skills": ["SQL"],
            "skill_gaps": [{"skill": "SQL", "importance": "High", "reason": "required"}],
        },
        "keyword_match": {"matched_keywords": ["data analysis"], "missing_keywords": []},
    }
    base.update(overrides)
    return base


def test_build_insights_contains_all_expected_keys():
    insights = build_insights(_resume(), _profile(), _match())
    for key in ("strengths", "weaknesses", "improvements", "missing_keywords", "skill_recommendations", "project_suggestions", "ats_suggestions"):
        assert key in insights and isinstance(insights[key], list)
    assert any("SQL" in item for item in insights["improvements"])


def test_build_insights_never_claims_missing_skills_as_held():
    insights = build_insights(_resume(), _profile(), _match())
    assert all("No evidence of" in item for item in insights["weaknesses"])


def test_learning_path_known_and_unknown_skills():
    assert "JOIN" in learning_path("SQL")
    assert "pods" in learning_path("Kubernetes")
    assert "Apache Kafka" in learning_path("Apache Kafka")


def test_build_insights_empty_resume_still_gets_guidance():
    insights = build_insights(_resume(skills=[], projects=[], experience=[], years_experience=0), _profile(minimum_experience=2), _match(skill_match={"matching_skills": [], "missing_required": ["Python", "SQL"], "missing_skills": ["Python", "SQL"], "skill_gaps": []}, keyword_match={"missing_keywords": ["data analysis"]}))
    assert insights["strengths"]
    assert insights["improvements"]
    assert insights["project_suggestions"]
