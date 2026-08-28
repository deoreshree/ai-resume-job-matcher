"""Configurable, explainable weighted score calculations."""

from __future__ import annotations

import re
from typing import Any

from config import MATCH_WEIGHTS

COMPONENT_LABELS = {
    "skills": "Skills Match",
    "semantic": "Semantic Similarity",
    "experience": "Experience Match",
    "education": "Education Match",
    "keywords": "Keyword Match",
}


def _to_percentage(value: object) -> float:
    numeric = float(value or 0)
    if 0 <= numeric <= 1:
        numeric *= 100
    return round(max(0.0, min(100.0, numeric)), 2)


def _validated_weights(weights: dict[str, float] | None) -> dict[str, float]:
    result = dict(MATCH_WEIGHTS.as_dict() if weights is None else weights)
    missing = set(COMPONENT_LABELS) - set(result)
    unexpected = set(result) - set(COMPONENT_LABELS)
    if missing or unexpected:
        raise ValueError(f"Weights must contain exactly: {', '.join(COMPONENT_LABELS)}")
    if any(float(value) < 0 for value in result.values()):
        raise ValueError("Weights cannot be negative.")
    total = sum(float(value) for value in result.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {total}")
    return {name: float(value) for name, value in result.items()}


def compute_match_score(components: dict[str, object], weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Blend five component scores into an overall 0–100 result.

    Component inputs can be decimals (``0.82``) or percentages (``82``). The
    response includes contributions so the UI can state exactly how the total arose.
    """
    calibrated_weights = _validated_weights(weights)
    values = {name: _to_percentage(components.get(name, 0)) for name in COMPONENT_LABELS}
    contributions = {name: round(values[name] * calibrated_weights[name], 2) for name in COMPONENT_LABELS}
    overall = round(sum(contributions.values()), 2)
    return {
        "overall_score": overall,
        "components": values,
        "weights": calibrated_weights,
        "contributions": contributions,
        "explanation": [
            f"{COMPONENT_LABELS[name]}: {values[name]:.1f}% × {calibrated_weights[name] * 100:.0f}% weight = {contributions[name]:.1f} points"
            for name in COMPONENT_LABELS
        ],
    }


def experience_match_score(candidate_years: float, required_years: float) -> float:
    """Score stated/derived experience without penalising roles that require none."""
    required = max(0.0, float(required_years or 0))
    candidate = max(0.0, float(candidate_years or 0))
    if required == 0:
        return 1.0
    return min(1.0, candidate / required)


def education_match_score(education: list[dict[str, Any]], requirements: list[str] | str | None) -> float:
    """Estimate whether a resume shows a degree compatible with a role requirement."""
    if not requirements:
        return 1.0
    entries = education or []
    if not entries:
        return 0.0
    joined = " ".join(
        f"{entry.get('degree', '')} {entry.get('raw', '')}" for entry in entries if isinstance(entry, dict)
    ).casefold()
    if not joined:
        return 0.0
    if re.search(r"ph\.?\s*d|doctorate", joined):
        return 1.0
    if re.search(r"master|m\.?\s*(tech|e|s|sc)|mba|mca", joined):
        return 1.0
    if re.search(r"bachelor|b\.?\s*(tech|e|s|sc|a)|bca|bba", joined):
        return 1.0
    if "diploma" in joined:
        return 0.65
    return 0.5
