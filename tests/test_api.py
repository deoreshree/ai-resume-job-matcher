"""API route tests (app.py) using the Flask test client."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from app import app
from utils.rate_limit import RateLimiter

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_TEXT = (FIXTURES / "sample_resume.txt").read_text(encoding="utf-8")


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def resume_docx() -> bytes:
    document = Document()
    for line in SAMPLE_TEXT.split("\n"):
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_index_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"AI Resume" in response.data


def test_roles_endpoint(client):
    response = client.get("/api/roles")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["roles"]
    assert {"title": "Data Scientist"} in payload["roles"]


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_analyze_with_role(client, resume_docx):
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "role", "job_role": "Data Scientist"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    analysis = response.get_json()["analysis"]
    assert {"resume", "job_profile", "match", "ats", "insights", "advisor", "interview"} <= set(analysis)
    # Privacy: raw text and section bodies must not be returned to the browser.
    assert "raw_text" not in analysis["resume"]
    assert "sections" not in analysis["resume"]
    assert "raw_text" not in analysis["job_profile"]
    assert 0 <= analysis["match"]["overall_score"] <= 100
    assert analysis["resume"]["name"] == "John Doe"


def test_analyze_with_custom_description(client, resume_docx):
    jd = (
        "Machine Learning Engineer required. Python, SQL, Docker. TensorFlow preferred. "
        "3+ years of experience building predictive models. Bachelor's degree in CS."
    )
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "custom", "job_description": jd},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    profile = response.get_json()["analysis"]["job_profile"]
    assert profile["source"] == "custom"
    assert "Python" in profile["required_skills"]


def test_analyze_custom_jd_without_catalog_skills_warns(client, resume_docx):
    jd = (
        "We are hiring a registered nurse for the night shift at our hospital ward. "
        "Patient care, charting, and medication administration duties. Degree in nursing required."
    )
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "custom", "job_description": jd},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    analysis = response.get_json()["analysis"]
    assert analysis["job_profile"]["warnings"], "expected a warning for a zero-skill job description"
    assert analysis["match"]["skill_match"]["score"] == 50.0


def test_analyze_errors(client, resume_docx):
    # No file at all
    assert client.post("/api/analyze", data={"target_mode": "role", "job_role": "Data Scientist"}).status_code == 400
    # Unsupported extension
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(b"hello"), "resume.txt"), "target_mode": "role", "job_role": "Data Scientist"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    # Corrupt PDF
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(b"%PDF-not-really"), "resume.pdf"), "target_mode": "role", "job_role": "Data Scientist"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()
    # Unknown role
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "role", "job_role": "Astronaut"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    # Too-short custom description
    response = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "custom", "job_description": "short"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_report_round_trip(client, resume_docx):
    analysis = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "role", "job_role": "Data Scientist"},
        content_type="multipart/form-data",
    ).get_json()["analysis"]
    response = client.post("/api/report", json={"analysis": analysis})
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "JohnDoe" in response.headers.get("Content-Disposition", "")
    assert b"Overall match" in response.data


def test_report_rejects_incomplete_payload(client):
    assert client.post("/api/report", json={"analysis": {"resume": {}}}).status_code == 400
    assert client.post("/api/report", json={}).status_code == 400


def test_json_404_and_405(client):
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").is_json
    assert client.post("/api/roles").status_code == 405
    assert client.post("/api/roles").is_json


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_rate_limit_returns_429(client, resume_docx, monkeypatch):
    from app import _analyze_limiter  # noqa: F401  (ensure module state exists)
    import app as app_module

    monkeypatch.setattr(app_module, "_analyze_limiter", RateLimiter(max_requests=2))
    for _ in range(2):
        assert client.post(
            "/api/analyze",
            data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "role", "job_role": "Data Scientist"},
            content_type="multipart/form-data",
        ).status_code == 200
    third = client.post(
        "/api/analyze",
        data={"resume": (BytesIO(resume_docx), "resume.docx"), "target_mode": "role", "job_role": "Data Scientist"},
        content_type="multipart/form-data",
    )
    assert third.status_code == 429
    assert "Retry-After" in third.headers
    assert third.is_json
