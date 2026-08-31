"""Flask API and static-site host for the AI Resume & Job Match Predictor."""

from __future__ import annotations

import io
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from config import MAX_UPLOAD_MB, RATE_LIMIT_PER_MINUTE
from genai.interview_generator import generate_interview_pack
from genai.resume_advisor import advise_resume
from modules.ats_analyzer import analyze_ats
from modules.job_analyzer import analyze_job_description, get_job_profile, load_job_roles
from modules.matcher import match_resume_to_job
from modules.recommendation_engine import build_insights
from modules.resume_parser import parse_resume
from utils.rate_limit import RateLimiter
from utils.report_builder import build_html_report, report_filename
from utils.validators import ResumeValidationError, validate_job_input

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

_analyze_limiter = RateLimiter(max_requests=RATE_LIMIT_PER_MINUTE)


@app.after_request
def security_headers(response):
    """Attach conservative security headers to every response."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    return response


def _client_key() -> str:
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0]).strip()


def _run_analysis(file_bytes: bytes, filename: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Run the complete in-memory workflow with no resume contents written to disk."""
    resume = parse_resume(file_bytes, filename)
    match = match_resume_to_job(resume, profile)
    ats = analyze_ats(resume, profile)
    insights = build_insights(resume, profile, match)
    insights["ats_suggestions"] = ats["recommendations"]
    return {
        "resume": resume,
        "job_profile": profile,
        "match": match,
        "ats": ats,
        "insights": insights,
        "advisor": advise_resume(resume, profile, match),
        "interview": generate_interview_pack(resume, profile, match),
    }


def _public_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Remove unneeded raw resume/JD text before returning the result to the browser."""
    result = deepcopy(analysis)
    result["resume"].pop("raw_text", None)
    result["resume"].pop("sections", None)
    result["job_profile"].pop("raw_text", None)
    return result


@app.get("/")
def index():
    """Serve the HTML/CSS/JavaScript frontend."""
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/roles")
def roles():
    """Return concise predefined role metadata for the browser selector."""
    return jsonify({"roles": [{"title": role["title"]} for role in load_job_roles()]})


@app.get("/api/health")
def health():
    """Lightweight JSON liveness endpoint for deploy platforms and container healthchecks."""
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
def analyze():
    """Analyse one uploaded resume against a predefined role or pasted job description."""
    if not _analyze_limiter.allow(_client_key()):
        response = jsonify({"error": "Too many analyses from this address. Please wait a minute and try again."})
        response.headers["Retry-After"] = str(_analyze_limiter.retry_after(_client_key()))
        return response, 429
    uploaded = request.files.get("resume")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Please choose a PDF or DOCX resume."}), 400
    mode = request.form.get("target_mode", "role")
    try:
        if mode == "custom":
            description = request.form.get("job_description", "")
            validate_job_input(None, description)
            profile = analyze_job_description(description)
        else:
            role_title = request.form.get("job_role", "")
            validate_job_input(role_title, None)
            profile = get_job_profile(role_title)
        analysis = _run_analysis(uploaded.read(), uploaded.filename, profile)
        return jsonify({"analysis": _public_analysis(analysis)})
    except (ResumeValidationError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Unexpected failure while analysing an uploaded resume.")
        return jsonify({"error": "The analysis could not be completed. Please try again with another resume file."}), 500


@app.post("/api/report")
def report():
    """Create an HTML report from the current browser analysis without server storage."""
    payload = request.get_json(silent=True) or {}
    analysis = payload.get("analysis")
    if not isinstance(analysis, dict) or not {"resume", "job_profile", "match", "ats", "insights", "interview"} <= set(analysis):
        return jsonify({"error": "No complete analysis is available for report generation."}), 400
    html = build_html_report(analysis)
    return send_file(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=report_filename(analysis["resume"].get("name")),
    )


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_: RequestEntityTooLarge):
    return jsonify({"error": f"The resume is larger than {MAX_UPLOAD_MB} MB. Please upload a smaller file."}), 413


@app.errorhandler(404)
def not_found(_: Exception):
    return jsonify({"error": "Route not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_: Exception):
    return jsonify({"error": "Method not allowed for this route."}), 405


@app.errorhandler(500)
def internal_error(error: Exception):
    logger.exception("Unhandled server error: %s", error)
    return jsonify({"error": "An unexpected server error occurred. Please try again."}), 500


if __name__ == "__main__":
    # Local development server configuration
    # For production, use: gunicorn app:app
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    
    app.run(
        host="0.0.0.0",  # Listen on all interfaces for containers/VMs
        port=port,
        debug=debug,
    )
