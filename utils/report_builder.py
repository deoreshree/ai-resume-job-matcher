"""Safe in-memory HTML report generation for completed analyses."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any


def _safe(value: object) -> str:
    """Coerce any value to a display string without raising on None/odd types."""
    if value is None:
        return ""
    return str(value)


def _as_float(value: object) -> float:
    """Coerce numeric-ish values for formatting; never raises on tampered payloads."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _items(values: list[object]) -> str:
    if not values:
        return "<p class='muted'>None identified.</p>"
    return "<ul>" + "".join(f"<li>{escape(_safe(value))}</li>" for value in values) + "</ul>"


def _question_items(groups: dict[str, list[dict[str, str]]]) -> str:
    labels = {
        "technical_questions": "Technical questions",
        "project_questions": "Project questions",
        "hr_questions": "HR questions",
        "scenario_questions": "Scenario questions",
    }
    blocks = []
    for key, label in labels.items():
        entries = groups.get(key, []) or []
        questions = ""
        for question in entries:
            if not isinstance(question, dict):
                continue
            questions += (
                "<li><strong>" + escape(_safe(question.get("question", ""))) + "</strong>"
                + "<br><span>Why: " + escape(_safe(question.get("why_interviewer_may_ask", ""))) + "</span>"
                + "<br><span>Strong answer: " + escape(_safe(question.get("strong_answer_should_cover", ""))) + "</span></li>"
            )
        blocks.append(f"<h3>{escape(label)}</h3><ol>{questions}</ol>")
    return "".join(blocks)


def build_html_report(analysis: dict[str, Any]) -> str:
    """Return a self-contained HTML report without writing personal data to disk."""
    resume = analysis["resume"]
    profile = analysis["job_profile"]
    match = analysis["match"]
    ats = analysis["ats"]
    insights = analysis["insights"]
    interview = analysis["interview"]
    components = match.get("components", {})
    component_rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{_as_float(components.get(key, 0)):.1f}%</td><td>{_as_float(match.get('weights', {}).get(key, 0)) * 100:.0f}%</td></tr>"
        for key, label in {
            "skills": "Skills Match",
            "semantic": "Semantic Similarity",
            "experience": "Experience Match",
            "education": "Education Match",
            "keywords": "Keyword Match",
        }.items()
    )
    generated = datetime.now().strftime("%d %b %Y, %H:%M")
    warnings = profile.get("warnings") or []
    warning_html = (
        "".join(f"<p class='muted'><strong>Note:</strong> {escape(_safe(warning))}</p>" for warning in warnings)
        if warnings else ""
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Resume Match Analysis</title>
<style>body{{font-family:Arial,sans-serif;color:#172033;max-width:960px;margin:32px auto;line-height:1.5}}h1{{color:#123c69}}h2{{border-bottom:2px solid #dce7f4;padding-bottom:5px}}.hero{{background:#edf5ff;padding:18px;border-radius:10px}}.score{{font-size:32px;font-weight:bold;color:#137b5a}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border:1px solid #dbe4ee;text-align:left}}.muted{{color:#637083}}li{{margin:8px 0}}span{{color:#42556f}}</style></head>
<body><h1>AI Resume &amp; Job Match Predictor</h1><p class='muted'>Generated {escape(generated)}. This analysis is advisory and should be reviewed for accuracy.</p>
<section class='hero'><h2>Candidate &amp; target</h2><p><strong>Candidate:</strong> {escape(_safe(resume.get('name')) or 'Not identified')}<br><strong>Target role:</strong> {escape(_safe(profile.get('title')) or 'Custom role')}<br><span class='score'>Overall match: {float(match.get('overall_score', 0) or 0):.1f}%</span><br><strong>ATS score:</strong> {float(ats.get('score', 0) or 0):.1f}/100</p>{warning_html}</section>
<h2>Score breakdown</h2><table><tr><th>Component</th><th>Score</th><th>Weight</th></tr>{component_rows}</table>
<h2>Skills</h2><h3>Evidence found</h3>{_items(match.get('skill_match', {}).get('matching_skills', []))}<h3>Skill gaps</h3>{_items(match.get('skill_match', {}).get('missing_skills', []))}
<h2>ATS analysis</h2><p><strong>Score:</strong> {_as_float(ats.get('score', 0)):.1f}/100</p><h3>Recommendations</h3>{_items(ats.get('recommendations', []))}
<h2>Recommendations</h2><h3>Strengths</h3>{_items(insights.get('strengths', []))}<h3>Improvements</h3>{_items(insights.get('improvements', []))}<h3>Project improvements</h3>{_items(insights.get('project_suggestions', []))}
<h2>Interview preparation</h2>{_question_items(interview)}</body></html>"""


def report_filename(candidate_name: str | None) -> str:
    """Make a safe filename that contains no contact information."""
    cleaned = "".join(char for char in (candidate_name or "candidate") if char.isalnum() or char in {"-", "_"})
    return f"resume-match-report-{cleaned[:40] or 'candidate'}.html"
