"""Resume parser and file-extraction tests."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from docx import Document

from modules.resume_parser import extract_text, parse_resume, parse_resume_text
from utils.text_cleaner import clean_text
from utils.validators import ResumeValidationError, validate_resume_file

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_TEXT = (FIXTURES / "sample_resume.txt").read_text(encoding="utf-8")


def _minimal_pdf(text: str) -> bytes:
    """Build a tiny one-page PDF whose text pypdf can extract."""
    lines = text.replace("\r\n", "\n").split("\n")
    commands = ["BT", "/F1 10 Tf", "50 750 Td"]
    for index, line in enumerate(lines[:40]):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -14 Td")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands)
    content = f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream"
    pdf = f"""%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj
3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj
4 0 obj{content}endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj
xref
0 6
0000000000 65535 f 
trailer<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""
    return pdf.encode("latin-1", "replace")


def _docx_bytes(text: str) -> bytes:
    document = Document()
    for line in text.split("\n"):
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_clean_text_normalizes_bullets_and_whitespace():
    raw = "Hello\r\n\r\n\r\n• Python\u00a0  and  ML"
    cleaned = clean_text(raw)
    assert "\r" not in cleaned
    assert "Python" in cleaned
    assert "  " not in cleaned.replace("\n\n", "")
    assert cleaned.startswith("Hello")


def test_validate_rejects_unsupported_and_empty():
    with pytest.raises(ResumeValidationError):
        validate_resume_file("resume.txt", b"hello")
    with pytest.raises(ResumeValidationError):
        validate_resume_file("resume.pdf", b"")
    validate_resume_file("resume.pdf", b"%PDF-fake")


def test_parse_resume_text_extracts_identity_and_sections():
    parsed = parse_resume_text(SAMPLE_TEXT)
    assert parsed["name"] == "John Doe"
    assert parsed["email"] == "john.doe@email.com"
    assert parsed["phone"] is not None
    assert "415" in parsed["phone"]
    assert parsed["education"]
    assert any("B.Tech" in (item.get("degree") or "") or "B.Tech" in item["raw"] for item in parsed["education"])
    assert parsed["experience"]
    assert parsed["projects"]
    assert "Python" in parsed["skills"]
    assert "Pandas" in parsed["skills"]
    assert parsed["certifications"]
    assert parsed["achievements"]
    assert parsed["years_experience"] >= 1.0
    assert "experience" in parsed["sections"]
    assert "education" in parsed["sections"]


def test_extract_text_from_docx():
    data = _docx_bytes(SAMPLE_TEXT)
    text = extract_text(data, "resume.docx")
    assert "John Doe" in text
    assert "john.doe@email.com" in text


def test_parse_resume_from_docx():
    parsed = parse_resume(_docx_bytes(SAMPLE_TEXT), "candidate.docx")
    assert parsed["email"] == "john.doe@email.com"
    assert "Machine Learning" in parsed["skills"]


def test_extract_text_from_pdf():
    data = _minimal_pdf("Ada Lovelace\nada@example.com\nSKILLS\nPython, SQL")
    text = extract_text(data, "resume.pdf")
    assert "Ada Lovelace" in text
    assert "ada@example.com" in text


def test_invalid_pdf_raises_friendly_error():
    with pytest.raises(ResumeValidationError, match="PDF"):
        extract_text(b"this is not a pdf", "resume.pdf")


def test_invalid_docx_raises_friendly_error():
    with pytest.raises(ResumeValidationError, match="DOCX"):
        extract_text(b"not-a-docx", "resume.docx")


def test_empty_text_after_clean_is_rejected():
    with pytest.raises(ResumeValidationError, match="empty"):
        parse_resume_text("   \n\n  ")
