"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def sample_resume_text() -> str:
    return (FIXTURES / "sample_resume.txt").read_text(encoding="utf-8")
