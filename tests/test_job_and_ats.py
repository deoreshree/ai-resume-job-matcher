"""Job-profile, ATS, and input-validation tests."""

import pytest

from modules.ats_analyzer import analyze_ats
from modules.job_analyzer import analyze_job_description, get_job_profile, load_job_roles
from utils.validators import validate_job_input


def test_predefined_roles_are_available():
    roles = load_job_roles()
    assert len(roles) >= 15
    profile = get_job_profile("data scientist")
    assert "Python" in profile["required_skills"]
    assert profile["source"] == "predefined"


def test_custom_job_description_extracts_skills_experience_and_education():
    text = """Machine Learning Engineer
    Required: Python, SQL, scikit-learn and Docker. 2+ years of experience building predictive models.
    TensorFlow is preferred. Bachelor's degree in Computer Science required."""
    profile = analyze_job_description(text)
    assert {"Python", "SQL", "Scikit-learn", "Docker"} <= set(profile["required_skills"])
    assert "TensorFlow" in profile["preferred_skills"]
    assert profile["minimum_experience"] == 2
    assert profile["education"]


def test_job_validation_rejects_ambiguous_or_short_input():
    with pytest.raises(ValueError):
        validate_job_input(None, None)
    with pytest.raises(ValueError):
        validate_job_input("Data Scientist", "A detailed description that is long enough for validation to consider.")
    with pytest.raises(ValueError):
        validate_job_input(None, "too short")


def test_ats_analysis_returns_score_components_and_recommendations(sample_resume_text):
    resume = {
        "raw_text": sample_resume_text,
        "skills": ["Python", "Machine Learning", "Pandas", "NumPy", "Scikit-learn"],
        "sections": {"summary": "x", "experience": "x", "education": "x", "skills": "x", "projects": "x"},
    }
    profile = get_job_profile("Data Scientist")
    result = analyze_ats(resume, profile)
    assert 0 <= result["score"] <= 100
    assert set(result["components"]) == {"keywords", "structure", "skills", "readability", "formatting"}
    assert result["recommendations"]
