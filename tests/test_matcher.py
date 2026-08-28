"""Tests for exact evidence matching, scoring, and semantic fallback."""

from modules.matcher import match_keywords, match_resume_to_job, match_skills
from modules.semantic_matcher import semantic_similarity


def test_skill_match_prioritizes_required_gaps():
    result = match_skills(["Python", "Pandas", "sklearn"], ["Python", "SQL", "Scikit-learn"], ["Docker"])
    assert set(result["required_matches"]) == {"Python", "Scikit-learn"}
    assert result["missing_required"] == ["SQL"]
    assert result["missing_preferred"] == ["Docker"]
    assert result["skill_gaps"][0]["importance"] == "High"
    assert result["score"] > 50


def test_keyword_match_uses_phrase_boundaries():
    result = match_keywords("Built predictive models and dashboard reporting.", ["predictive models", "dashboards", "SQL"])
    assert result["matched_keywords"] == ["predictive models"]
    assert set(result["missing_keywords"]) == {"dashboards", "SQL"}


def test_semantic_similarity_handles_empty_and_related_text():
    assert semantic_similarity("", "job text") == 0
    related = semantic_similarity("Built predictive models with Python.", "Develop machine learning predictive models.")
    unrelated = semantic_similarity("Built predictive models with Python.", "Lead restaurant kitchen operations.")
    assert related > unrelated


def test_end_to_end_match_has_five_weighted_components(sample_resume_text):
    resume = {"skills": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-learn"], "raw_text": sample_resume_text, "years_experience": 2, "education": [{"degree": "B.Tech", "raw": "B.Tech in Computer Science"}]}
    profile = {"title": "Data Scientist", "required_skills": ["Python", "SQL", "Pandas", "Machine Learning"], "preferred_skills": ["Scikit-learn"], "keywords": ["predictive models", "data analysis"], "minimum_experience": 1, "education": ["Bachelor's"], "technologies": ["Python"]}
    result = match_resume_to_job(resume, profile)
    assert set(result["components"]) == {"skills", "semantic", "experience", "education", "keywords"}
    assert 0 <= result["overall_score"] <= 100
    assert result["skill_match"]["missing_required"] == ["SQL"]
