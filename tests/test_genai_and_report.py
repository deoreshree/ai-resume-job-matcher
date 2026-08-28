"""Offline GenAI fallback, interview generation, and report output tests."""

from genai.interview_generator import generate_interview_pack
from genai.resume_advisor import advise_resume
from utils.report_builder import build_html_report, report_filename


def _analysis_data():
    resume = {
        "name": "Candidate Example",
        "skills": ["Python", "Pandas"],
        "years_experience": 1,
        "projects": [{"title": "Forecasting tool"}],
        "raw_text": "Python Pandas forecasting tool",
    }
    profile = {"title": "Data Scientist", "required_skills": ["Python", "SQL"], "minimum_experience": 1}
    match = {
        "overall_score": 70,
        "components": {"skills": 50, "semantic": 80, "experience": 100, "education": 100, "keywords": 60},
        "weights": {"skills": .4, "semantic": .25, "experience": .15, "education": .1, "keywords": .1},
        "skill_match": {"matching_skills": ["Python"], "missing_skills": ["SQL"], "missing_required": ["SQL"], "skill_gaps": [{"skill": "SQL", "importance": "High"}]},
        "keyword_match": {"missing_keywords": ["data analysis"]},
    }
    ats = {"score": 82, "recommendations": ["Use concise headings."], "components": {}}
    return resume, profile, match, ats


def test_rule_advisor_and_interview_pack_work_without_llm(monkeypatch):
    monkeypatch.setattr("genai.resume_advisor.is_configured", lambda: False)
    resume, profile, match, _ = _analysis_data()
    advisor = advise_resume(resume, profile, match)
    questions = generate_interview_pack(resume, profile, match)
    assert advisor["source"] == "Rule-based guidance"
    assert any("Consider learning SQL" in item for item in advisor["improvements"])
    assert len(questions["technical_questions"]) >= 5
    assert len(questions["project_questions"]) == 5


def test_html_report_is_generated_in_memory_and_escapes_candidate_content():
    resume, profile, match, ats = _analysis_data()
    interview = generate_interview_pack(resume, profile, match)
    html = build_html_report({"resume": {**resume, "name": "<Candidate>"}, "job_profile": profile, "match": match, "ats": ats, "insights": {"strengths": ["Python"], "improvements": ["Learn SQL"], "project_suggestions": ["Explain scope"]}, "interview": interview})
    assert "&lt;Candidate&gt;" in html
    assert "Overall match: 70.0%" in html
    assert report_filename("A B/<>C") == "resume-match-report-ABC.html"
