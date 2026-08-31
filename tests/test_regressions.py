"""Regression tests for defects found in the 2026-08 technical audit (see AUDIT.md)."""

from __future__ import annotations

import json

import pytest

from modules.job_analyzer import analyze_job_description
from modules.matcher import match_resume_to_job, match_skills
from modules.resume_parser import extract_text, parse_resume_text
from modules.skill_extractor import extract_skills
from utils.report_builder import build_html_report


def test_education_dates_do_not_inflate_experience():
    """AUDIT §7.1 — degree year ranges must never count as work experience."""
    parsed = parse_resume_text(
        "Jane Smith\njane@example.com\n"
        "EDUCATION\nB.Tech Computer Science, IIT Delhi\n2018 - 2022\n"
        "SKILLS\nPython, SQL\n"
    )
    assert parsed["years_experience"] == 0.0


def test_unrecognised_experience_heading_falls_back_safely():
    """AUDIT §7.1 fallback path — education excluded even without an experience section."""
    parsed = parse_resume_text(
        "Max Payne\nmax@example.com\n"
        "Relevant Experience\nSoftware Engineer at Initech\nJan 2023 - Present\n- Python development\n"
        "EDUCATION\nB.Sc. Physics\n2015 - 2019\n"
    )
    assert "experience" in parsed["sections"]
    assert parsed["years_experience"] > 0  # from the experience section only
    # And education-only again:
    parsed2 = parse_resume_text("Ann B\nann@example.com\nEDUCATION\nM.A. History\n2012 - 2016\n")
    assert parsed2["years_experience"] == 0.0


def test_job_title_header_line_is_not_the_candidate_name():
    """AUDIT §7.2 — 'Data Scientist' above the name must not be detected as the name."""
    parsed = parse_resume_text("Data Scientist\nJohn Doe\njohn@example.com\nSKILLS\nPython")
    assert parsed["name"] == "John Doe"
    parsed2 = parse_resume_text("Senior Full Stack Developer\nJane Roe\njane@example.com\nSKILLS\nReact")
    assert parsed2["name"] == "Jane Roe"


def test_short_skill_aliases_do_not_match_adjacent_punctuation():
    """AUDIT §8.1 — 'R&D' and 'go-to-market' must not register as R / Go skills."""
    result = extract_skills("Led R&D initiatives and go-to-market strategy for a SaaS payroll platform. Compiled C++ binaries.")
    assert "R" not in result["skills"]
    assert "Go" not in result["skills"]
    assert "C++" in result["skills"]

    real = extract_skills("Built statistical models in R, and backend services in Go and Golang.")
    assert "R" in real["skills"]
    assert "Go" in real["skills"]


def test_empty_requirement_lists_score_neutral_not_perfect():
    """AUDIT §8.2 — a JD with no detectable catalog skills must not grant a free 100%."""
    result = match_skills(["Python"], [], [])
    assert result["score"] == 50.0
    profile = analyze_job_description(
        "Night-shift registered nurse for hospital ward. Patient care, medication administration, "
        "and charting. Nursing degree required. 2+ years of experience."
    )
    assert profile["warnings"], "zero-skill JD should carry a visible warning"
    resume = {"skills": ["Python"], "raw_text": "Python developer", "years_experience": 1, "education": []}
    match = match_resume_to_job(resume, profile)
    assert match["skill_match"]["score"] == 50.0


def test_semantic_component_stays_ordered_for_related_roles():
    """AUDIT §8.3 — a data-science resume must rank Data Scientist far above Frontend Developer."""
    text = open("tests/fixtures/sample_resume.txt", encoding="utf-8").read()
    resume = parse_resume_text(text)
    from modules.job_analyzer import get_job_profile

    related = match_resume_to_job(resume, get_job_profile("Data Scientist"))
    unrelated = match_resume_to_job(resume, get_job_profile("Frontend Developer"))
    assert related["semantic_similarity"] > unrelated["semantic_similarity"] + 5
    # Related-role semantic should not be crushed into the floor anymore.
    assert related["semantic_similarity"] >= 20.0


def test_report_builder_survives_tampered_payloads():
    """AUDIT §3.3 — malformed interview entries must not crash report generation."""
    analysis = {
        "resume": {"name": None, "skills": []},
        "job_profile": {"title": "X", "warnings": ["no skills"]},
        "match": {
            "overall_score": "70",
            "components": {"skills": "bad"},
            "weights": {"skills": 0.4},
            "skill_match": {"matching_skills": None, "missing_skills": []},
        },
        "ats": {"score": None, "recommendations": ["Fine."], "components": {}},
        "insights": {"strengths": [], "improvements": ["Learn SQL"], "project_suggestions": []},
        "interview": {"technical_questions": [{"question": None, "why_interviewer_may_ask": 5, "strong_answer_should_cover": []}]},
    }
    html = build_html_report(analysis)
    assert "Learn SQL" in html
    assert "no skills" in html


def test_extracted_text_is_capped(monkeypatch):
    """AUDIT §14 — decompression amplification guard."""
    import modules.resume_parser as parser_module

    monkeypatch.setattr(parser_module, "MAX_RESUME_TEXT_CHARS", 100)
    from io import BytesIO

    from docx import Document

    document = Document()
    document.add_paragraph("word " * 500)
    buffer = BytesIO()
    document.save(buffer)
    text = extract_text(buffer.getvalue(), "resume.docx")
    assert len(text) <= 100


def test_custom_jd_keywords_filter_noise():
    """AUDIT §11.5 — recruitment filler phrases should not become 'missing keywords'."""
    profile = analyze_job_description(
        "Python developer role. We are an equal opportunity employer. Apply now. "
        "Join our team. You will build REST APIs with Python and Docker. Bachelor's degree preferred."
    )
    noise = {"equal opportunity", "opportunity employer", "apply now", "join our", "you will", "we are"}
    for keyword in profile["keywords"]:
        assert keyword.casefold() not in noise
    assert "Python" in profile["keywords"]


@pytest.mark.parametrize(
    "resume_text,expected_name",
    [
        ("John Doe\njohn@x.com\nSKILLS\nPython", "John Doe"),
        ("DATA SCIENTIST\nAmelia Earhart\namelia@x.com", "Amelia Earhart"),
    ],
)
def test_name_detection_cases(resume_text, expected_name):
    assert parse_resume_text(resume_text)["name"] == expected_name
