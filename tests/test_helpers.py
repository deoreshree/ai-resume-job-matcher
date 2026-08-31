"""Tests for utils/helpers.py date and experience estimation logic."""

from __future__ import annotations

from datetime import date

from utils.helpers import (
    estimate_years_of_experience,
    extract_date_ranges,
    find_degree,
    merge_intervals,
    years_from_intervals,
)


def test_extract_date_ranges_months_years_and_present():
    ranges = extract_date_ranges("Jan 2022 - Present\nJun 2021 - Dec 2021")
    assert ranges[0][0] == date(2022, 1, 1)
    assert ranges[0][1] >= date(2026, 1, 1)  # "Present" resolves to today
    assert ranges[1] == (date(2021, 6, 1), date(2021, 12, 1))


def test_extract_date_ranges_year_only_and_invalid_ignored():
    ranges = extract_date_ranges("2019 - 2022 and 2022 - 2019 (reversed)")
    assert (date(2019, 1, 1), date(2022, 1, 1)) in ranges
    assert all(end >= start for start, end in ranges)


def test_merge_intervals_overlaps():
    merged = merge_intervals([(date(2020, 1, 1), date(2021, 1, 1)), (date(2020, 6, 1), date(2022, 1, 1)), (date(2023, 1, 1), date(2023, 6, 1))])
    assert merged == [(date(2020, 1, 1), date(2022, 1, 1)), (date(2023, 1, 1), date(2023, 6, 1))]


def test_years_from_intervals_sums_and_merges():
    assert years_from_intervals([]) == 0.0
    one_year = years_from_intervals([(date(2020, 1, 1), date(2021, 1, 1))])
    assert abs(one_year - 1.0) < 0.01


def test_estimate_years_prefers_largest_signal():
    assert estimate_years_of_experience("5+ years of experience in backend roles") == 5.0
    combined = estimate_years_of_experience("Jan 2020 - Dec 2021\n3+ years of experience")
    assert abs(combined - 3.0) < 1e-9


def test_find_degree_matches_common_forms():
    assert find_degree("B.Tech in Computer Science") is not None
    assert find_degree("Master of Science in Data Analytics") is not None
    assert find_degree("Ph.D. in Physics") is not None
    assert find_degree("High school diploma only") is None or "diploma" in find_degree("High school diploma only").casefold()
