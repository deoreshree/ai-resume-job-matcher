"""Career Readiness Engine and Multi-Role Version Matrix Generator.

Calculates an evidence-grounded Career Readiness Score across 6 distinct dimensions
and generates side-by-side benchmark matrices for multi-role targeting.
"""

from __future__ import annotations

from typing import Any

from modules.job_analyzer import load_job_roles
from modules.matcher import match_resume_to_job


def compute_career_readiness(
    resume: dict[str, Any],
    match_result: dict[str, Any],
    ats_result: dict[str, Any],
    career_intel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute an evidence-grounded Career Readiness Score (0-100) across 6 factors."""
    # 1. Resume Quality (15%) - Evaluates contact, structure, bullet density, length
    contact = resume.get("contact", {})
    contact_points = (
        (25 if contact.get("email") else 0)
        + (25 if contact.get("phone") else 0)
        + (25 if (contact.get("linkedin") or contact.get("github")) else 0)
        + (25 if resume.get("name") else 0)
    )
    sections = ats_result.get("sections_detected", {})
    section_score = (sum(1 for v in sections.values() if v) / max(1, len(sections))) * 100
    bullet_count = sum(len(e.get("bullets", [])) for e in resume.get("experience", [])) + sum(
        len(p.get("bullets", [])) for p in resume.get("projects", [])
    )
    bullet_score = min(100, bullet_count * 15) if bullet_count > 0 else 50
    resume_quality = round(0.4 * contact_points + 0.4 * section_score + 0.2 * bullet_score, 1)

    # 2. ATS Compatibility (20%) - From ATS analyzer heuristic score
    ats_compat = round(float(ats_result.get("score") or 0.0), 1)

    # 3. Technical Skills Depth (25%) - Catalog skills count & variety
    skills = resume.get("skills", [])
    skills_by_cat = resume.get("skills_by_category", {})
    skills_count_score = min(100.0, len(skills) * 10.0)
    breadth_score = min(100.0, len(skills_by_cat) * 25.0)
    tech_skills_score = round(0.6 * skills_count_score + 0.4 * breadth_score, 1)

    # 4. Job Match Alignment (20%) - Weighted match against target / best role
    job_match_score = round(float(match_result.get("overall_score") or 0.0), 1)

    # 5. Projects & Experience (10%) - Proven work history and technical project artifacts
    years = float(resume.get("years_experience") or 0.0)
    projects = resume.get("projects", [])
    exp_points = min(100.0, 50.0 + years * 15.0)
    proj_points = min(100.0, len(projects) * 35.0) if projects else 40.0
    projects_exp_score = round(0.5 * exp_points + 0.5 * proj_points, 1)

    # 6. Interview Readiness (10%) - Evaluates technical coverage, project depth, and role fit
    interview_readiness = round(0.4 * tech_skills_score + 0.4 * job_match_score + 0.2 * resume_quality, 1)

    # Weighted Total Score
    total_readiness = round(
        0.15 * resume_quality
        + 0.20 * ats_compat
        + 0.25 * tech_skills_score
        + 0.20 * job_match_score
        + 0.10 * projects_exp_score
        + 0.10 * interview_readiness,
        1,
    )
    total_readiness = max(10.0, min(99.0, total_readiness))

    # Readiness Tier & Summary
    if total_readiness >= 85.0:
        tier = "Market Ready"
        tier_class = "success"
        summary = "Exceptional profile readiness — strong technical alignment, ATS compliance, and project evidence."
    elif total_readiness >= 70.0:
        tier = "Good Foundation"
        tier_class = "good"
        summary = "Solid foundation — a few targeted improvements can significantly strengthen your candidate profile."
    elif total_readiness >= 55.0:
        tier = "Developing Readiness"
        tier_class = "warning"
        summary = "Growing profile — focus on closing core required skill gaps and expanding project evidence."
    else:
        tier = "Foundational Stage"
        tier_class = "danger"
        summary = "Early career stage — prioritize acquiring foundational catalog skills and building practical portfolio projects."

    factors = {
        "resume_quality": resume_quality,
        "ats_compatibility": ats_compat,
        "technical_skills": tech_skills_score,
        "job_match": job_match_score,
        "projects_experience": projects_exp_score,
        "interview_readiness": interview_readiness,
    }

    # Identify Biggest Opportunity (lowest scoring factor)
    factor_labels = {
        "resume_quality": "Resume Quality & Formatting",
        "ats_compatibility": "ATS Section Compliance",
        "technical_skills": "Technical Skill Breadth",
        "job_match": "Target Role Requirement Fit",
        "projects_experience": "Projects & Experience Depth",
        "interview_readiness": "Interview Preparation Depth",
    }
    lowest_factor_key = min(factors, key=factors.get)
    lowest_score = factors[lowest_factor_key]

    opportunity_recommendations = {
        "resume_quality": [
            "Add verifiable links to GitHub repositories or live project demos in your header.",
            "Ensure standard headings: Summary, Work Experience, Education, Technical Skills, Projects.",
            "Quantify project achievements with measurable impact metrics.",
        ],
        "ats_compatibility": [
            "Use standard ATS-friendly heading keywords rather than stylized graphics or tables.",
            "Ensure core technical keywords appear naturally in context throughout your work history.",
            "Add a clear professional summary highlighting your primary technical stack.",
        ],
        "technical_skills": [
            "Acquire and document high-frequency required catalog skills for your target roles.",
            "Group technical skills cleanly into Languages, Frameworks, Databases, and Developer Tools.",
            "Build hands-on projects directly proving competency in missing required skills.",
        ],
        "job_match": [
            "Tailor your resume bullet points directly to the core responsibilities of your target role.",
            "Highlight required programming languages and domain frameworks in your project summaries.",
            "Review missing required skills in the Skill Gap Roadmap and address high-priority gaps.",
        ],
        "projects_experience": [
            "Build and publish 1-2 production-grade technical projects with clean README documentation.",
            "Describe architecture decisions, database choices, and deployment setups in project bullets.",
            "Demonstrate end-to-end ownership from problem definition to live containerized deployment.",
        ],
        "interview_readiness": [
            "Practice structured STAR-method (Situation, Task, Action, Result) responses for technical scenarios.",
            "Review system architecture and trade-off rationales for all projects listed on your resume.",
            "Use the AI Interview Simulator to practice technical deep-dive and behavioral questions.",
        ],
    }

    return {
        "readiness_score": int(round(total_readiness)),
        "readiness_decimal": total_readiness,
        "readiness_tier": tier,
        "tier_class": tier_class,
        "readiness_summary": summary,
        "factors": factors,
        "biggest_opportunity": {
            "factor_key": lowest_factor_key,
            "factor_name": factor_labels.get(lowest_factor_key, "Interview Readiness"),
            "score": int(round(lowest_score)),
            "impact": "High Leverage",
            "recommendations": opportunity_recommendations.get(lowest_factor_key, []),
        },
    }


def generate_role_versions_matrix(
    resume: dict[str, Any],
    catalog_roles: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Compare candidate profile across top 4 target roles side-by-side."""
    roles = catalog_roles if catalog_roles is not None else load_job_roles()
    matrix_entries: list[dict[str, Any]] = []

    for role in roles[:6]:
        match_res = match_resume_to_job(resume, role)
        comp = match_res.get("components", {})
        skill_match = match_res.get("skill_match", {})
        kw_match = match_res.get("keyword_match", {})

        overall = round(float(match_res.get("overall_score") or 0.0), 1)
        skills_score = round(float(comp.get("skills") or 0.0), 1)
        kw_score = round(float(comp.get("keywords") or 0.0), 1)
        sem_score = round(float(comp.get("semantic") or 0.0), 1)

        matrix_entries.append(
            {
                "role_title": role.get("title", "Role"),
                "overall_fit": overall,
                "skills_score": skills_score,
                "keywords_score": kw_score,
                "semantic_score": sem_score,
                "matched_skills_count": len(skill_match.get("matching_skills", [])),
                "missing_required_count": len(skill_match.get("missing_required", [])),
                "top_matched_skills": skill_match.get("matching_skills", [])[:4],
                "top_gaps": skill_match.get("missing_required", [])[:3] or skill_match.get("missing_preferred", [])[:3],
                "fit_tier": "High Fit" if overall >= 75 else ("Moderate Fit" if overall >= 55 else "Developing"),
            }
        )

    matrix_entries.sort(key=lambda x: x["overall_fit"], reverse=True)
    return matrix_entries[:4]
