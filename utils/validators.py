"""Input validation for uploads and (later) job input."""

from __future__ import annotations

from pathlib import Path

from config import ALLOWED_RESUME_EXTENSIONS, MAX_UPLOAD_MB


class ResumeValidationError(ValueError):
    """User-facing validation error for resume files."""


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def validate_resume_file(filename: str, file_bytes: bytes) -> None:
    """Raise ResumeValidationError for unsupported type, empty, or oversized files."""
    if not filename or not str(filename).strip():
        raise ResumeValidationError("Please upload a resume file.")

    ext = _extension(filename)
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        allowed = ", ".join(ALLOWED_RESUME_EXTENSIONS)
        raise ResumeValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. Please upload a {allowed} file."
        )

    if not file_bytes:
        raise ResumeValidationError("The uploaded file is empty. Please upload a valid resume.")

    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ResumeValidationError(
            f"The resume is larger than {MAX_UPLOAD_MB} MB. Please upload a smaller file."
        )


def validate_job_input(role_title: str | None, job_description: str | None) -> None:
    """Ensure a catalog role or a substantive pasted job description is provided."""
    has_role = bool((role_title or "").strip())
    description = (job_description or "").strip()
    if has_role and description:
        raise ValueError("Choose either a predefined role or a custom job description, not both.")
    if not has_role and not description:
        raise ValueError("Choose a target role or paste a job description.")
    if description and len(description) < 40:
        raise ValueError("The job description is too short to analyse reliably.")
