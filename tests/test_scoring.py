"""Scoring tests."""

from config import MATCH_WEIGHTS
from modules.scoring import compute_match_score, education_match_score, experience_match_score


def test_match_weights_sum_to_one():
    MATCH_WEIGHTS.validate()
    assert abs(sum(MATCH_WEIGHTS.as_dict().values()) - 1.0) < 1e-6


def test_compute_score_accepts_decimal_and_percentage_inputs():
    result = compute_match_score({"skills": 1, "semantic": 80, "experience": .5, "education": 100, "keywords": 0})
    assert result["components"]["skills"] == 100
    assert result["components"]["experience"] == 50
    assert result["overall_score"] == 77.5
    assert len(result["explanation"]) == 5


def test_score_helpers_are_bounded_and_education_is_evidence_based():
    assert experience_match_score(3, 2) == 1
    assert experience_match_score(0, 0) == 1
    assert experience_match_score(1, 2) == .5
    assert education_match_score([], ["Bachelor's"]) == 0
    assert education_match_score([{"degree": "B.Tech", "raw": "B.Tech Computer Science"}], ["Bachelor's"]) == 1
