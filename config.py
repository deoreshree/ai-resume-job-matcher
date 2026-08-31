"""Application configuration. Weights and model names live here so algorithms stay unchanged."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
JOB_ROLES_PATH = DATA_DIR / "job_roles.json"
SKILLS_PATH = DATA_DIR / "skills.json"

MAX_UPLOAD_MB = 8
ALLOWED_RESUME_EXTENSIONS = (".pdf", ".docx")

SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "")).strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

# Best-effort per-IP request limiting for the CPU-bound analysis endpoint (0 disables).
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

# Safety cap for extracted resume text (guards against decompression amplification).
MAX_RESUME_TEXT_CHARS = int(os.getenv("MAX_RESUME_TEXT_CHARS", "400000"))


@dataclass(frozen=True)
class MatchWeights:
    """Must sum to 1.0. Used by the scoring engine."""

    skills: float = 0.40
    semantic: float = 0.25
    experience: float = 0.15
    education: float = 0.10
    keywords: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "skills": self.skills,
            "semantic": self.semantic,
            "experience": self.experience,
            "education": self.education,
            "keywords": self.keywords,
        }

    def validate(self) -> None:
        total = sum(self.as_dict().values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Match weights must sum to 1.0, got {total}")


MATCH_WEIGHTS = MatchWeights()
MATCH_WEIGHTS.validate()

# ATS heuristic component weights.
ATS_WEIGHTS = {
    "keywords": 0.30,
    "structure": 0.25,
    "skills": 0.20,
    "readability": 0.15,
    "formatting": 0.10,
}
