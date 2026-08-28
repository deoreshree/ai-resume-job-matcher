"""Semantic similarity with an offline TF-IDF fallback."""

from __future__ import annotations

import os
from functools import lru_cache


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


@lru_cache(maxsize=1)
def _embedding_model():
    """Load an already available sentence-transformer model on demand.

    Downloads are deliberately opt-in so the app remains responsive and private by
    default. Set ENABLE_EMBEDDINGS=true after installing/downloading the model to
    use the richer embedding comparison.
    """
    if os.getenv("ENABLE_EMBEDDINGS", "").casefold() not in {"1", "true", "yes"}:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        from config import EMBEDDING_MODEL

        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
    except Exception:
        return None


def _tfidf_similarity(resume_text: str, job_text: str) -> float:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(
            [resume_text, job_text]
        )
        return _clamp(float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]))
    except ValueError:
        return 0.0


def semantic_similarity(resume_text: str, job_text: str) -> float:
    """Return cosine similarity in ``[0, 1]`` using embeddings when available.

    TF-IDF is an intentional local fallback rather than a failure mode, allowing the
    matching pipeline to work without model downloads or network access.
    """
    resume_text, job_text = (resume_text or "").strip(), (job_text or "").strip()
    if not resume_text or not job_text:
        return 0.0

    model = _embedding_model()
    if model is not None:
        try:
            embeddings = model.encode([resume_text[:12000], job_text[:12000]], normalize_embeddings=True)
            return _clamp(float(embeddings[0] @ embeddings[1]))
        except Exception:
            pass
    return _tfidf_similarity(resume_text, job_text)


def semantic_method() -> str:
    """Expose the actual comparison method for transparent UI explanations."""
    return "Sentence-transformer embeddings" if _embedding_model() is not None else "TF-IDF cosine similarity"
