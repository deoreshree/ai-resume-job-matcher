"""Tests for catalog-backed, false-positive-resistant skill extraction."""

from modules.skill_extractor import extract_skills, load_skill_catalog, normalize_skill


def test_catalog_contains_required_categories_and_skills():
    catalog = load_skill_catalog()
    assert {"Programming", "AI/ML", "Data", "Web", "DevOps/Cloud", "Databases", "Soft Skills"} <= set(catalog)
    assert any(item["name"] == "Python" for item in catalog["Programming"])


def test_extract_skills_normalizes_aliases_and_groups_categories():
    result = extract_skills("Built ML models in python using sklearn, pandas, PostgreSQL and Docker. Collaborated in Agile teams.")
    assert {"Python", "Machine Learning", "Scikit-learn", "Pandas", "PostgreSQL", "Docker", "Agile"} <= set(result["skills"])
    assert "Python" in result["by_category"]["Programming"]
    assert result["matched_aliases"]["Scikit-learn"] == "sklearn"


def test_short_aliases_do_not_match_inside_unrelated_words():
    result = extract_skills("The candidate enjoys javascript and has strong communication skills.")
    assert "C" not in result["skills"]
    assert "Java" not in result["skills"]
    assert normalize_skill("sklearn") == "Scikit-learn"
