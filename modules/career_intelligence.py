"""AI Career & Company Fit Intelligence Engine.

Provides evidence-based estimation of company matches, suitable job roles,
career level, learning-to-opportunity roadmaps, and company-targeted practice prep.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from config import COMPANIES_PATH
from modules.job_analyzer import load_job_roles
from modules.matcher import match_keywords, match_resume_to_job, match_skills
from modules.recommendation_engine import learning_path
from modules.skill_extractor import normalize_skill


@lru_cache(maxsize=1)
def load_companies() -> list[dict[str, Any]]:
    """Load the curated company dataset once per process."""
    try:
        payload = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not load data/companies.json.") from exc
    companies = payload.get("companies", [])
    if not isinstance(companies, list) or not companies:
        raise RuntimeError("The company catalog has no entries.")
    return companies


def get_company_profile(company_name: str) -> dict[str, Any] | None:
    """Find a company profile by name (case-insensitive)."""
    wanted = (company_name or "").strip().casefold()
    for company in load_companies():
        if str(company.get("name", "")).casefold() == wanted:
            return dict(company)
    return None


def estimate_career_level(resume: dict[str, Any]) -> dict[str, Any]:
    """Estimate candidate career level and confidence based on verified resume facts."""
    years = float(resume.get("years_experience") or 0.0)
    education_entries = resume.get("education", [])
    experience_entries = resume.get("experience", [])
    projects = resume.get("projects", [])
    skills = resume.get("skills", [])

    has_degree = bool(education_entries)
    has_masters_or_phd = any(
        re.search(r"master|m\.?\s*tech|m\.?\s*s|mba|ph\.?\s*d", str(e.get("degree", "") or e.get("raw", "")), re.I)
        for e in education_entries
    )

    evidence: list[str] = []
    if years >= 7.0:
        level_title = "Senior / Lead Professional"
        level_category = "Senior"
        confidence = min(95, int(75 + years * 2))
        evidence.append(f"Demonstrated {years:.1f} years of dated industry work history")
        evidence.append(f"Documented leadership in {len(experience_entries)} professional positions")
    elif years >= 4.0:
        level_title = "Mid-Level Specialist / Engineer"
        level_category = "Mid-Level"
        confidence = min(92, int(70 + years * 4))
        evidence.append(f"Documented {years:.1f} years of industry experience")
        evidence.append(f"Track record across {len(experience_entries)} professional roles")
    elif years >= 1.5:
        level_title = "Junior to Associate Engineer"
        level_category = "Junior"
        confidence = min(88, int(65 + years * 8))
        evidence.append(f"Recorded {years:.1f} years of professional engineering / analytical experience")
        evidence.append(f"Applied technical foundation across {len(experience_entries)} work settings")
    elif years >= 0.5 or (experience_entries and any("intern" in str(e.get("title", "")).lower() for e in experience_entries)):
        level_title = "Entry-Level Practitioner"
        level_category = "Entry-Level"
        confidence = 85
        evidence.append("Internship or initial professional work experience evidenced")
        if projects:
            evidence.append(f"Practical execution demonstrated across {len(projects)} technical projects")
    else:
        level_title = "Student / Fresher Graduate"
        level_category = "Fresher"
        confidence = 82
        if has_degree:
            evidence.append("Academic foundation with verified degree credentials")
        if projects:
            evidence.append(f"Hands-on project evidence across {len(projects)} technical portfolio projects")
        evidence.append(f"Core technical foundation with {len(skills)} verified catalog skills")

    if has_masters_or_phd:
        evidence.append("Advanced postgraduate degree credentials")

    summary = (
        f"Based on {years:.1f} years of documented experience, {len(projects)} portfolio projects, "
        f"and {len(skills)} verified skills, your profile aligns with {level_title} expectations."
    )

    return {
        "level_title": level_title,
        "level_category": level_category,
        "confidence_score": confidence,
        "years_experience": years,
        "evidence": evidence,
        "summary": summary,
    }


def recommend_roles(resume: dict[str, Any], catalog_roles: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Cross-benchmark the candidate against all predefined catalog roles."""
    roles = catalog_roles if catalog_roles is not None else load_job_roles()
    recommendations: list[dict[str, Any]] = []

    for role in roles:
        match_result = match_resume_to_job(resume, role)
        overall_score = round(float(match_result.get("overall_score") or 0.0), 1)
        skill_match = match_result.get("skill_match", {})
        matching_skills = skill_match.get("matching_skills", [])
        missing_required = skill_match.get("missing_required", [])
        missing_preferred = skill_match.get("missing_preferred", [])

        # Build transparent 'why' explanation
        why_points: list[str] = []
        if matching_skills:
            why_points.append(f"Evidences {len(matching_skills)} core skills: {', '.join(matching_skills[:4])}")
        if resume.get("projects"):
            matching_tech = [s for s in matching_skills if any(s.lower() in str(p).lower() for p in resume.get("projects", []))]
            if matching_tech:
                why_points.append(f"Projects demonstrate hands-on application of {', '.join(matching_tech[:3])}")
        if float(resume.get("years_experience") or 0) >= float(role.get("minimum_experience") or 0):
            why_points.append("Meets or exceeds minimum required experience level")
        if not why_points:
            why_points.append("Foundation in complementary technical and problem-solving concepts")

        # Determine fit tier
        if overall_score >= 80.0:
            fit_tier = "High Fit"
            tier_class = "high"
        elif overall_score >= 60.0:
            fit_tier = "Moderate Fit"
            tier_class = "moderate"
        else:
            fit_tier = "Developing Fit"
            tier_class = "developing"

        recommendations.append(
            {
                "title": role.get("title", "Role"),
                "overall_score": overall_score,
                "fit_tier": fit_tier,
                "tier_class": tier_class,
                "components": match_result.get("components", {}),
                "matching_skills": matching_skills,
                "missing_required": missing_required,
                "missing_preferred": missing_preferred,
                "missing_skills": missing_required + missing_preferred,
                "skill_gaps": skill_match.get("skill_gaps", []),
                "why_fit": why_points,
            }
        )

    # Sort descending by overall score
    recommendations.sort(key=lambda r: r["overall_score"], reverse=True)
    for index, rec in enumerate(recommendations, start=1):
        rec["rank"] = index

    return recommendations


def match_companies(
    resume: dict[str, Any],
    companies: list[dict[str, Any]] | None = None,
    role_recommendations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate estimated fit per company and group into Strong, Good, and Developing tiers."""
    company_list = companies if companies is not None else load_companies()
    roles = role_recommendations if role_recommendations is not None else recommend_roles(resume)
    roles_by_title = {r["title"].casefold(): r for r in roles}

    all_matches: list[dict[str, Any]] = []

    for comp in company_list:
        c_name = comp.get("name", "Company")
        c_req = comp.get("required_skills", [])
        c_pref = comp.get("preferred_skills", [])
        c_keywords = comp.get("keywords", [])
        c_roles = comp.get("roles", [])

        # Match skills against company profile
        skill_res = match_skills(resume.get("skills", []), c_req, c_pref)
        kw_res = match_keywords(resume.get("raw_text", ""), c_keywords)

        # Find suitable roles within this company and their best score
        suitable_roles: list[dict[str, Any]] = []
        best_role_score = 0.0
        for r_title in c_roles:
            r_match = roles_by_title.get(r_title.casefold())
            if r_match:
                suitable_roles.append(
                    {
                        "title": r_title,
                        "score": r_match["overall_score"],
                        "matching_skills": r_match["matching_skills"][:4],
                    }
                )
                if r_match["overall_score"] > best_role_score:
                    best_role_score = r_match["overall_score"]

        suitable_roles.sort(key=lambda x: x["score"], reverse=True)

        # Blended Company Fit Score (Skills 35%, Keywords 20%, Best Role Fit 25%, Experience/Edu 20%)
        years = float(resume.get("years_experience") or 0.0)
        exp_score = min(100.0, 50.0 + years * 15.0)
        edu_score = 90.0 if resume.get("education") else 60.0
        exp_edu_blend = 0.6 * exp_score + 0.4 * edu_score

        company_fit = round(
            0.35 * float(skill_res["score"])
            + 0.20 * float(kw_res["score"])
            + 0.25 * float(best_role_score)
            + 0.20 * float(exp_edu_blend),
            1,
        )
        company_fit = max(10.0, min(98.0, company_fit))

        # Build transparent 'why' evidence
        why_matched: list[str] = []
        if skill_res["matching_skills"]:
            why_matched.append(f"Strong foundation in {', '.join(skill_res['matching_skills'][:4])}")
        if suitable_roles and suitable_roles[0]["score"] >= 70:
            why_matched.append(f"High profile alignment with {suitable_roles[0]['title']} expectations")
        if resume.get("projects"):
            why_matched.append("Relevant project portfolio showcasing technical ownership")
        if not why_matched:
            why_matched.append("Complementary background in modern software / analytical methodologies")

        # Group into Fit Tiers
        if company_fit >= 80.0:
            tier_label = "Strong Match"
            tier_code = "strong"
            tier_badge = "🟢 Strong Match"
        elif company_fit >= 65.0:
            tier_label = "Good Match"
            tier_code = "good"
            tier_badge = "🟡 Good Match"
        else:
            tier_label = "Developing Match"
            tier_code = "developing"
            tier_badge = "🟠 Developing Match"

        all_matches.append(
            {
                "name": c_name,
                "industry": comp.get("industry", "Technology"),
                "tier": comp.get("tier", "Enterprise"),
                "description": comp.get("description", ""),
                "fit_score": company_fit,
                "tier_label": tier_label,
                "tier_code": tier_code,
                "tier_badge": tier_badge,
                "suitable_roles": suitable_roles,
                "why_matched": why_matched,
                "matching_skills": skill_res["matching_skills"],
                "missing_skills": skill_res["missing_skills"],
                "skill_gaps": skill_res["missing_required"][:4] or skill_res["missing_preferred"][:4],
                "culture_traits": comp.get("culture_traits", []),
                "interview_focus": comp.get("interview_focus", []),
                "component_breakdown": {
                    "skills_match": round(float(skill_res["score"]), 1),
                    "keyword_match": round(float(kw_res["score"]), 1),
                    "role_alignment": round(float(best_role_score), 1),
                    "experience_education": round(float(exp_edu_blend), 1),
                },
            }
        )

    all_matches.sort(key=lambda c: c["fit_score"], reverse=True)

    return {
        "all_matches": all_matches,
        "strong_matches": [c for c in all_matches if c["tier_code"] == "strong"],
        "good_matches": [c for c in all_matches if c["tier_code"] == "good"],
        "developing_matches": [c for c in all_matches if c["tier_code"] == "developing"],
        "top_company": all_matches[0] if all_matches else None,
    }


def build_company_role_matrix(
    company_matches: list[dict[str, Any]],
    role_recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a searchable, sortable Company x Role combination matrix."""
    matrix: list[dict[str, Any]] = []
    roles_by_title = {r["title"].casefold(): r for r in role_recommendations}

    for comp in company_matches:
        for role_item in comp.get("suitable_roles", []):
            r_title = role_item["title"]
            r_data = roles_by_title.get(r_title.casefold(), {})
            
            # Specific pair fit combines company fit and specific role score
            pair_score = round(0.5 * comp["fit_score"] + 0.5 * role_item["score"], 1)
            
            if pair_score >= 80.0:
                tier = "High"
            elif pair_score >= 65.0:
                tier = "Moderate"
            else:
                tier = "Developing"

            matrix.append(
                {
                    "company": comp["name"],
                    "industry": comp["industry"],
                    "tier": comp["tier"],
                    "role": r_title,
                    "fit_score": pair_score,
                    "fit_tier": tier,
                    "matching_skills": r_data.get("matching_skills", comp.get("matching_skills", []))[:5],
                    "missing_skills": r_data.get("missing_skills", comp.get("missing_skills", []))[:5],
                    "why": comp.get("why_matched", [])[:2],
                    "component_breakdown": {
                        "company_fit": comp["fit_score"],
                        "role_fit": role_item["score"],
                        "skills_coverage": r_data.get("components", {}).get("skills", comp["component_breakdown"]["skills_match"]),
                    },
                }
            )

    matrix.sort(key=lambda m: m["fit_score"], reverse=True)
    return matrix


def build_skill_opportunity_map(
    resume: dict[str, Any],
    role_recommendations: list[dict[str, Any]],
    company_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Connect high-leverage missing skills to concrete unlocked role and company opportunities."""
    skill_impact: dict[str, dict[str, Any]] = {}

    # Count how many top roles miss each skill
    for role in role_recommendations[:8]:
        for skill in role.get("missing_required", []):
            norm = normalize_skill(skill)
            if norm not in skill_impact:
                skill_impact[norm] = {"roles": set(), "companies": set(), "importance": 0}
            skill_impact[norm]["roles"].add(role["title"])
            skill_impact[norm]["importance"] += 3

        for skill in role.get("missing_preferred", []):
            norm = normalize_skill(skill)
            if norm not in skill_impact:
                skill_impact[norm] = {"roles": set(), "companies": set(), "importance": 0}
            skill_impact[norm]["roles"].add(role["title"])
            skill_impact[norm]["importance"] += 1

    # Count how many companies miss each skill
    for comp in company_matches[:10]:
        for skill in comp.get("skill_gaps", []):
            norm = normalize_skill(skill)
            if norm in skill_impact:
                skill_impact[norm]["companies"].add(comp["name"])
                skill_impact[norm]["importance"] += 2

    # Build prioritized list
    sorted_skills = sorted(skill_impact.items(), key=lambda item: item[1]["importance"], reverse=True)

    opportunities: list[dict[str, Any]] = []
    for rank, (skill_name, data) in enumerate(sorted_skills[:6], start=1):
        roles_list = sorted(list(data["roles"]))
        companies_list = sorted(list(data["companies"]))
        
        priority_label = "Priority 1" if rank <= 2 else "Priority 2" if rank <= 4 else "Priority 3"
        priority_class = "high" if rank <= 2 else "medium" if rank <= 4 else "normal"

        opportunities.append(
            {
                "priority_label": priority_label,
                "priority_class": priority_class,
                "skill": skill_name,
                "learning_path": learning_path(skill_name),
                "unlocked_roles": roles_list[:4] or ["General Software & Tech Roles"],
                "boosted_companies": companies_list[:4] or ["Enterprise & Product Tech"],
                "impact_summary": (
                    f"Learning {skill_name} directly improves your fit for "
                    f"{', '.join(roles_list[:3]) or 'target roles'} and enhances compatibility with "
                    f"{', '.join(companies_list[:3]) or 'leading tech firms'}."
                ),
            }
        )

    return opportunities


def build_career_roadmap(
    resume: dict[str, Any],
    target_match: dict[str, Any],
    role_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a structured, 4-phase chronological action plan."""
    top_role = role_recommendations[0]["title"] if role_recommendations else "Target Role"
    missing_core = target_match.get("skill_match", {}).get("missing_required", [])
    missing_secondary = target_match.get("skill_match", {}).get("missing_preferred", [])
    
    gap1 = missing_core[0] if missing_core else (missing_secondary[0] if missing_secondary else "System Design Basics")
    gap2 = missing_core[1] if len(missing_core) > 1 else (missing_secondary[0] if missing_secondary else "Cloud Fundamentals")
    gap3 = missing_secondary[1] if len(missing_secondary) > 1 else "CI/CD & Testing Automation"

    return {
        "phase_1_now": {
            "title": "NOW: Immediate Optimization",
            "timeframe": "Days 1 – 7",
            "goals": [
                f"Highlight proven experience in {', '.join(resume.get('skills', [])[:3]) or 'core skills'}",
                "Ensure standard ATS section headings (Summary, Experience, Education, Skills, Projects)",
                "Quantify measurable results in project and experience bullet points",
            ],
        },
        "phase_2_30_days": {
            "title": "NEXT 30 DAYS: Core Capability",
            "timeframe": "Days 8 – 30",
            "goals": [
                f"Master key required concept: {gap1}",
                "Build and document a focused portfolio project substantiating this skill",
                "Practice core problem-solving and domain coding assessments daily",
            ],
        },
        "phase_3_60_days": {
            "title": "NEXT 60 DAYS: Production Systems",
            "timeframe": "Days 31 – 60",
            "goals": [
                f"Upskill in secondary ecosystem tool: {gap2}",
                f"Containerize projects and implement automated testing ({gap3})",
                "Deploy portfolio projects to live cloud environments with documented READMEs",
            ],
        },
        "phase_4_90_days": {
            "title": "NEXT 90 DAYS: Interview Mastery",
            "timeframe": "Days 61 – 90",
            "goals": [
                f"Practice targeted mock interview questions for {top_role} positions",
                "Study company-specific architecture principles and Leadership / Cultural frameworks",
                "Actively apply to Strong Match companies and track interview conversion rates",
            ],
        },
    }


def build_job_search_strategy(role_recommendations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group target roles into Apply Now, Improve First, and Long-Term Target."""
    apply_now: list[dict[str, Any]] = []
    improve_first: list[dict[str, Any]] = []
    long_term: list[dict[str, Any]] = []

    for role in role_recommendations:
        score = role["overall_score"]
        item = {
            "title": role["title"],
            "score": score,
            "matching_count": len(role["matching_skills"]),
            "gap_count": len(role["missing_skills"]),
            "top_gaps": role["missing_required"][:3] or role["missing_preferred"][:3],
        }
        if score >= 75.0:
            apply_now.append(item)
        elif score >= 55.0:
            improve_first.append(item)
        else:
            long_term.append(item)

    return {
        "apply_now": apply_now,
        "improve_first": improve_first,
        "long_term_target": long_term,
    }


def generate_career_summary(
    resume: dict[str, Any],
    career_level: dict[str, Any],
    role_recommendations: list[dict[str, Any]],
    company_matches: dict[str, Any],
) -> str:
    """Generate a personalized, grounded summary of the candidate's career standing."""
    level = career_level.get("level_title", "Technical Candidate")
    top_role = role_recommendations[0]["title"] if role_recommendations else "Software Development"
    second_role = role_recommendations[1]["title"] if len(role_recommendations) > 1 else "Data Analytics"
    top_company = company_matches.get("top_company", {}).get("name", "leading technology firms")
    
    skills = resume.get("skills", [])
    top_skills = ", ".join(skills[:4]) if skills else "technical problem solving"

    gaps = role_recommendations[0].get("missing_required", []) if role_recommendations else []
    gap_phrase = f" Such as {', '.join(gaps[:3])}" if gaps else ""

    return (
        f"Your profile is currently positioned at the {level} tier, demonstrating strong foundational "
        f"evidence in {top_skills}. Your experience and technical projects align most naturally with "
        f"{top_role} and {second_role} roles, exhibiting high estimated compatibility with organizations "
        f"like {top_company}. Strategic upskilling in high-leverage areas{gap_phrase} will further unlock "
        f"higher-tier engineering and specialist positions across the industry."
    )


def build_company_interview_questions(
    resume: dict[str, Any],
    company_name: str,
    role_title: str,
) -> list[dict[str, str]]:
    """Build company-targeted practice interview questions with answers."""
    comp = get_company_profile(company_name) or {}
    culture_traits = comp.get("culture_traits", ["Problem Solving", "Collaboration"])
    interview_focus = comp.get("interview_focus", ["Technical Fundamentals", "System Architecture"])
    
    skills = resume.get("skills", [])
    top_skill = skills[0] if skills else "Python"
    
    return [
        {
            "question": f"At {company_name}, how would you approach building a reliable {role_title} feature utilizing {top_skill}?",
            "category": "Technical & Role Alignment",
            "why_asked": f"{company_name} evaluates hands-on engineering practices and production readiness in {top_skill}.",
            "strong_answer": "Structure your answer around requirements gathering, modular design, edge case testing, scalability, and monitoring.",
        },
        {
            "question": f"How do your past technical projects demonstrate {company_name}'s cultural focus on '{culture_traits[0]}'?",
            "category": "Company Culture & Values",
            "why_asked": f"Assesses your alignment with {company_name}'s stated cultural values and team working style.",
            "strong_answer": f"Cite a specific situation from your experience or projects that illustrates {culture_traits[0].lower()} and its positive outcome.",
        },
        {
            "question": f"In a {company_name} team environment, how would you troubleshoot an unexpected latency or data inconsistency issue?",
            "category": "System Reliability & Scenarios",
            "why_asked": f"{company_name} values methodical problem-solving and operational resilience under pressure.",
            "strong_answer": "Explain step-by-step telemetry inspection, hypothesis isolation, safe mitigation, rollback readiness, and post-incident root cause documentation.",
        },
        {
            "question": f"What motivates you to contribute as a {role_title} at {company_name} specifically?",
            "category": "Role Motivation",
            "why_asked": f"Interviewer confirms that you understand {company_name}'s products and have realistic career goals.",
            "strong_answer": f"Connect your genuine technical interests and verified skills with {company_name}'s technological domain and engineering challenges.",
        },
    ]


def analyze_career_intelligence(
    resume: dict[str, Any],
    job_profile: dict[str, Any],
    match_result: dict[str, Any],
    ats_result: dict[str, Any],
) -> dict[str, Any]:
    """Master orchestrator generating the full Career & Company Fit Intelligence bundle."""
    career_level = estimate_career_level(resume)
    role_recs = recommend_roles(resume)
    comp_matches = match_companies(resume, None, role_recs)
    matrix = build_company_role_matrix(comp_matches["all_matches"], role_recs)
    skill_opps = build_skill_opportunity_map(resume, role_recs, comp_matches["all_matches"])
    roadmap = build_career_roadmap(resume, match_result, role_recs)
    strategy = build_job_search_strategy(role_recs)
    summary = generate_career_summary(resume, career_level, role_recs, comp_matches)

    top_comp_name = comp_matches["top_company"]["name"] if comp_matches.get("top_company") else "Microsoft"
    target_role_title = job_profile.get("title", "Software Engineer")
    sample_company_interview = build_company_interview_questions(resume, top_comp_name, target_role_title)

    return {
        "disclaimer": "These are AI-generated estimates based on extracted resume facts, skills, and industry standards. They do not guarantee employment or hiring outcomes.",
        "career_level": career_level,
        "career_summary": summary,
        "role_recommendations": role_recs,
        "top_role": role_recs[0] if role_recs else None,
        "company_matches": comp_matches,
        "company_role_matrix": matrix,
        "skill_opportunity_map": skill_opps,
        "career_roadmap": roadmap,
        "job_search_strategy": strategy,
        "company_interview_pack": sample_company_interview,
    }
