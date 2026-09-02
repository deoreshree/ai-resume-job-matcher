"""Flask API and static-site host for the AI Resume & Job Match Predictor."""

from __future__ import annotations

import io
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from config import MAX_UPLOAD_MB
from genai.interview_generator import generate_interview_pack
from genai.resume_advisor import advise_resume
from modules.ats_analyzer import analyze_ats
from modules.career_intelligence import (
    analyze_career_intelligence,
    build_company_interview_questions,
)
from modules.job_analyzer import (
    analyze_job_description,
    get_job_profile,
    load_job_roles,
)
from modules.matcher import match_resume_to_job
from modules.recommendation_engine import build_insights
from modules.resume_parser import parse_resume
from utils.report_builder import build_html_report, report_filename
from utils.validators import ResumeValidationError, validate_job_input


# ---------------------------------------------------------------------------
# Paths / Flask configuration
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("ai_resume_matcher")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _run_analysis(
    file_bytes: bytes,
    filename: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Run the complete in-memory workflow."""
    
    logger.info("Starting resume analysis for file: %s", filename)

    # Step 1: Parse resume
    resume = parse_resume(file_bytes, filename)
    logger.info("Resume parsing completed")

    # Step 2: Match resume with job
    match = match_resume_to_job(resume, profile)
    logger.info("Resume/job matching completed")

    # Step 3: ATS analysis
    ats = analyze_ats(resume, profile)
    logger.info("ATS analysis completed")

    # Step 4: General insights
    insights = build_insights(resume, profile, match)

    if not isinstance(insights, dict):
        raise TypeError("build_insights() must return a dictionary.")

    insights["ats_suggestions"] = ats.get("recommendations", [])

    # Step 5: Career intelligence
    career_intel = analyze_career_intelligence(
        resume,
        profile,
        match,
        ats,
    )

    # Step 6: AI advisor
    advisor = advise_resume(
        resume,
        profile,
        match,
    )

    # Step 7: Interview pack
    interview = generate_interview_pack(
        resume,
        profile,
        match,
    )

    logger.info("Full analysis completed successfully")

    return {
        "resume": resume,
        "job_profile": profile,
        "match": match,
        "ats": ats,
        "insights": insights,
        "advisor": advisor,
        "interview": interview,
        "career_intelligence": career_intel,
    }


# ---------------------------------------------------------------------------
# Public response cleanup
# ---------------------------------------------------------------------------

def _public_analysis(
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove large/private raw text fields before sending
    the analysis back to the browser.
    """

    result = deepcopy(analysis)

    resume = result.get("resume")
    if isinstance(resume, dict):
        resume.pop("raw_text", None)
        resume.pop("sections", None)

    job_profile = result.get("job_profile")
    if isinstance(job_profile, dict):
        job_profile.pop("raw_text", None)

    return result


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    """Serve the main frontend."""

    return send_from_directory(
        STATIC_DIR,
        "index.html",
    )


# ---------------------------------------------------------------------------
# Roles API
# ---------------------------------------------------------------------------

@app.get("/api/roles")
def roles():
    """Return predefined job roles."""

    try:
        loaded_roles = load_job_roles()

        return jsonify(
            {
                "roles": [
                    {
                        "title": role.get("title", "")
                    }
                    for role in loaded_roles
                    if isinstance(role, dict)
                ]
            }
        )

    except Exception as exc:
        logger.exception("Failed to load job roles")

        return jsonify(
            {
                "error": "Failed to load job roles.",
                "details": str(exc),
            }
        ), 500


# ---------------------------------------------------------------------------
# Main Analysis API
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
def analyze():
    """
    Analyse an uploaded resume against either:
    - predefined role
    - custom job description
    """

    try:
        # ---------------------------------------------------------------
        # Validate uploaded file
        # ---------------------------------------------------------------

        uploaded = request.files.get("resume")

        if uploaded is None:
            return jsonify(
                {
                    "error": "No resume file was uploaded."
                }
            ), 400

        if not uploaded.filename:
            return jsonify(
                {
                    "error": "Please choose a PDF or DOCX resume."
                }
            ), 400

        filename = uploaded.filename.strip()

        logger.info(
            "Analyze request received | filename=%s",
            filename,
        )

        # ---------------------------------------------------------------
        # Read form values
        # ---------------------------------------------------------------

        mode = request.form.get(
            "target_mode",
            "role",
        ).strip().lower()

        logger.info(
            "Analysis mode: %s",
            mode,
        )

        # ---------------------------------------------------------------
        # Build target job profile
        # ---------------------------------------------------------------

        if mode == "custom":

            description = request.form.get(
                "job_description",
                "",
            ).strip()

            validate_job_input(
                None,
                description,
            )

            profile = analyze_job_description(
                description
            )

        else:

            role_title = request.form.get(
                "job_role",
                "",
            ).strip()

            validate_job_input(
                role_title,
                None,
            )

            profile = get_job_profile(
                role_title
            )

        # ---------------------------------------------------------------
        # Validate profile
        # ---------------------------------------------------------------

        if not isinstance(profile, dict):
            raise TypeError(
                "Job profile must be a dictionary."
            )

        logger.info(
            "Job profile created successfully"
        )

        # ---------------------------------------------------------------
        # Read uploaded file into memory
        # ---------------------------------------------------------------

        file_bytes = uploaded.read()

        if not file_bytes:
            return jsonify(
                {
                    "error": "The uploaded resume is empty."
                }
            ), 400

        logger.info(
            "Resume loaded into memory | bytes=%d",
            len(file_bytes),
        )

        # ---------------------------------------------------------------
        # Run full analysis
        # ---------------------------------------------------------------

        analysis = _run_analysis(
            file_bytes=file_bytes,
            filename=filename,
            profile=profile,
        )

        public_analysis = _public_analysis(
            analysis
        )

        logger.info(
            "Returning successful analysis response"
        )

        return jsonify(
            {
                "analysis": public_analysis
            }
        ), 200

    # -------------------------------------------------------------------
    # Expected validation errors
    # -------------------------------------------------------------------

    except (
        ResumeValidationError,
        ValueError,
    ) as exc:

        logger.warning(
            "Validation error: %s",
            exc,
        )

        return jsonify(
            {
                "error": str(exc)
            }
        ), 400

    # -------------------------------------------------------------------
    # Unexpected backend errors
    # -------------------------------------------------------------------

    except Exception as exc:

        logger.exception(
            "UNEXPECTED ERROR during /api/analyze"
        )

        return jsonify(
            {
                "error": "Resume analysis failed.",
                "details": str(exc),
                "type": type(exc).__name__,
            }
        ), 500


# ---------------------------------------------------------------------------
# Company Interview API
# ---------------------------------------------------------------------------

@app.post("/api/company-interview")
def company_interview():
    """Generate company-specific interview questions."""

    try:

        payload = request.get_json(
            silent=True
        ) or {}

        company_name = payload.get(
            "company",
            "",
        )

        role_title = payload.get(
            "role",
            "",
        )

        resume = payload.get(
            "resume"
        ) or {}

        if not company_name or not role_title:
            return jsonify(
                {
                    "error": "Company name and role title are required."
                }
            ), 400

        questions = build_company_interview_questions(
            resume,
            company_name,
            role_title,
        )

        return jsonify(
            {
                "questions": questions
            }
        ), 200

    except Exception as exc:

        logger.exception(
            "Company interview generation failed"
        )

        return jsonify(
            {
                "error": "Failed to generate company interview questions.",
                "details": str(exc),
                "type": type(exc).__name__,
            }
        ), 500


# ---------------------------------------------------------------------------
# Report API
# ---------------------------------------------------------------------------

@app.post("/api/report")
def report():
    """Create an HTML report from the browser's analysis."""

    try:

        payload = request.get_json(
            silent=True
        ) or {}

        analysis = payload.get(
            "analysis"
        )

        required_keys = {
            "resume",
            "job_profile",
            "match",
            "ats",
            "insights",
            "interview",
        }

        if (
            not isinstance(analysis, dict)
            or not required_keys.issubset(
                analysis.keys()
            )
        ):

            return jsonify(
                {
                    "error": "No complete analysis is available for report generation."
                }
            ), 400

        html = build_html_report(
            analysis
        )

        return send_file(
            io.BytesIO(
                html.encode("utf-8")
            ),
            mimetype="text/html",
            as_attachment=True,
            download_name=report_filename(
                analysis.get("resume", {}).get("name")
            ),
        )

    except Exception as exc:

        logger.exception(
            "Report generation failed"
        )

        return jsonify(
            {
                "error": "Failed to generate report.",
                "details": str(exc),
                "type": type(exc).__name__,
            }
        ), 500


# ---------------------------------------------------------------------------
# Upload too large
# ---------------------------------------------------------------------------

@app.errorhandler(RequestEntityTooLarge)
def file_too_large(
    _: RequestEntityTooLarge,
):
    return jsonify(
        {
            "error": (
                f"The resume is larger than "
                f"{MAX_UPLOAD_MB} MB. "
                "Please upload a smaller file."
            )
        }
    ), 413


# ---------------------------------------------------------------------------
# HTTP errors
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(
    _: Exception,
):
    return jsonify(
        {
            "error": "Route not found."
        }
    ), 404


@app.errorhandler(405)
def method_not_allowed(
    _: Exception,
):
    return jsonify(
        {
            "error": "HTTP method not allowed for this route."
        }
    ), 405


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.errorhandler(Exception)
def handle_unexpected_error(
    exc: Exception,
):
    """
    Make sure Flask ALWAYS returns JSON for API errors
    instead of an HTML error page.
    """

    # Keep normal HTTP exceptions meaningful.
    if isinstance(exc, HTTPException):

        return jsonify(
            {
                "error": exc.description,
                "status": exc.code,
            }
        ), exc.code

    logger.exception(
        "Unhandled application exception"
    )

    return jsonify(
        {
            "error": "Internal server error.",
            "details": str(exc),
            "type": type(exc).__name__,
        }
    ), 500


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000",
        )
    )

    debug = (
        os.getenv(
            "FLASK_ENV",
            ""
        ).lower()
        == "development"
    )

    logger.info(
        "Starting AI Resume Matcher on port %d",
        port,
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )