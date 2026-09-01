"""Unit and integration tests for AI Career & Company Fit Intelligence."""

from __future__ import annotations

from typing import Any

from modules.career_intelligence import (
    analyze_career_intelligence,
    build_career_roadmap,
    build_company_interview_questions,
    build_company_role_matrix,
    build_job_search_strategy,
    build_skill_opportunity_map,
    estimate_career_level,
    load_companies,
    match_companies,
    recommend_roles,
)


def _sample_resume() -> dict[str, Any]:
    return {
        "name": "Jane Doe",
        "title": "Data Scientist",
        "raw_text": "Experienced Data Scientist with 3 years in Python, machine learning, SQL, Pandas, Scikit-learn, and statistics.",
        "years_experience": 3.0,
        "education": [{"degree": "B.Tech in Computer Science", "institution": "Tech University", "year": "2020"}],
        "experience": [
            {
                "title": "Machine Learning Engineer",
                "organization": "Data Corp",
                "duration": "2021 - Present",
                "bullets": ["Built Python ML pipelines", "Worked with SQL and Scikit-learn"],
            }
        ],
        "projects": [
            {
                "name": "Churn Predictor",
                "technologies": ["Python", "Scikit-learn", "Pandas"],
                "bullets": ["Trained classification models with 88% precision"],
            }
        ],
        "skills": ["Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Scikit-learn", "Statistics", "Git"],
        "skills_by_category": {
            "Programming": ["Python", "SQL"],
            "Data & AI": ["Machine Learning", "Pandas", "NumPy", "Scikit-learn", "Statistics"],
            "Tools": ["Git"],
        },
    }


def test_companies_catalog_schema_and_integrity():
    companies = load_companies()
    assert len(companies) >= 10, "Company catalog should have at least 10 entries"
    for comp in companies:
        assert comp.get("name"), "Company name is required"
        assert comp.get("industry"), f"Industry missing for {comp['name']}"
        assert isinstance(comp.get("roles"), list) and len(comp["roles"]) > 0
        assert isinstance(comp.get("required_skills"), list) and len(comp["required_skills"]) > 0
        assert isinstance(comp.get("preferred_skills"), list)
        assert isinstance(comp.get("keywords"), list)
        assert isinstance(comp.get("culture_traits"), list)
        assert isinstance(comp.get("interview_focus"), list)


def test_career_level_estimation_thresholds():
    # 1. Test 0 years -> Fresher
    fresher = estimate_career_level({"years_experience": 0.0, "education": [{"degree": "B.S."}], "skills": ["Python"]})
    assert fresher["level_category"] == "Fresher"
    assert fresher["confidence_score"] >= 70

    # 2. Test 3 years -> Junior/Associate
    junior = estimate_career_level(_sample_resume())
    assert junior["level_category"] in {"Junior", "Mid-Level"}
    assert len(junior["evidence"]) >= 2
    assert "3.0" in junior["summary"]

    # 3. Test 8 years -> Senior
    senior = estimate_career_level({"years_experience": 8.5, "education": [{"degree": "M.S."}], "skills": ["Python", "Java", "AWS"]})
    assert senior["level_category"] == "Senior"
    assert senior["confidence_score"] >= 85


def test_role_recommendation_ranking():
    resume = _sample_resume()
    roles = recommend_roles(resume)
    assert len(roles) >= 10, "Should rank all available catalog roles"

    # Verify descending sort
    scores = [r["overall_score"] for r in roles]
    assert scores == sorted(scores, reverse=True), "Roles should be sorted descending by score"

    # Verify Data Scientist or ML role is ranked near the top for our ML resume
    top_titles = [r["title"] for r in roles[:3]]
    assert any("Data" in t or "Machine Learning" in t or "AI" in t for t in top_titles)

    for role in roles:
        assert 0.0 <= role["overall_score"] <= 100.0
        assert "why_fit" in role and len(role["why_fit"]) > 0
        assert "rank" in role


def test_company_matching_and_tiers():
    resume = _sample_resume()
    result = match_companies(resume)
    all_matches = result["all_matches"]
    assert len(all_matches) >= 10

    for comp in all_matches:
        assert 0.0 <= comp["fit_score"] <= 100.0
        assert comp["tier_code"] in {"strong", "good", "developing"}
        assert len(comp["why_matched"]) > 0
        assert "component_breakdown" in comp

    # Verify grouping lists
    assert len(result["strong_matches"]) + len(result["good_matches"]) + len(result["developing_matches"]) == len(all_matches)
    assert result["top_company"] is not None


def test_company_role_matrix_generation():
    resume = _sample_resume()
    roles = recommend_roles(resume)
    comp_result = match_companies(resume, None, roles)
    matrix = build_company_role_matrix(comp_result["all_matches"], roles)
    
    assert len(matrix) >= 10
    for row in matrix:
        assert row["company"] and row["role"]
        assert 0.0 <= row["fit_score"] <= 100.0
        assert "component_breakdown" in row


def test_skill_opportunity_map():
    resume = _sample_resume()
    roles = recommend_roles(resume)
    comp_result = match_companies(resume, None, roles)
    opps = build_skill_opportunity_map(resume, roles, comp_result["all_matches"])

    assert len(opps) > 0
    for opp in opps:
        assert opp["skill"]
        assert opp["priority_label"] in {"Priority 1", "Priority 2", "Priority 3"}
        assert len(opp["unlocked_roles"]) > 0
        assert len(opp["boosted_companies"]) > 0
        assert opp["learning_path"]


def test_career_roadmap_generation():
    resume = _sample_resume()
    roles = recommend_roles(resume)
    target_match = {"skill_match": {"missing_required": ["Docker"], "missing_preferred": ["AWS"]}}
    roadmap = build_career_roadmap(resume, target_match, roles)

    assert "phase_1_now" in roadmap
    assert "phase_2_30_days" in roadmap
    assert "phase_3_60_days" in roadmap
    assert "phase_4_90_days" in roadmap
    assert len(roadmap["phase_1_now"]["goals"]) >= 2


def test_job_search_strategy():
    resume = _sample_resume()
    roles = recommend_roles(resume)
    strategy = build_job_search_strategy(roles)

    assert "apply_now" in strategy
    assert "improve_first" in strategy
    assert "long_term_target" in strategy
    total = len(strategy["apply_now"]) + len(strategy["improve_first"]) + len(strategy["long_term_target"])
    assert total == len(roles)


def test_company_interview_questions():
    resume = _sample_resume()
    questions = build_company_interview_questions(resume, "Microsoft", "Data Scientist")
    assert len(questions) == 4
    for q in questions:
        assert "Microsoft" in q["question"] or "Data Scientist" in q["question"] or "Python" in q["question"]
        assert q.get("why_asked")
        assert q.get("strong_answer")


def test_end_to_end_analyze_career_intelligence_empty_resume():
    # Empty resume should not crash
    empty_resume = {
        "name": None,
        "title": None,
        "raw_text": "",
        "years_experience": 0.0,
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "skills_by_category": {},
    }
    job_profile = {"title": "Software Engineer", "minimum_experience": 1.0}
    match_result = {"overall_score": 30.0, "skill_match": {"matching_skills": [], "missing_required": ["Python"]}}
    ats_result = {"score": 40.0, "recommendations": []}

    result = analyze_career_intelligence(empty_resume, job_profile, match_result, ats_result)
    assert result["career_level"]["level_category"] == "Fresher"
    assert len(result["role_recommendations"]) > 0
    assert len(result["company_matches"]["all_matches"]) > 0
    assert "disclaimer" in result
    assert result["career_summary"]
