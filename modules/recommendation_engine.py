"""Truthful, deterministic guidance available without an LLM service."""

from __future__ import annotations

from typing import Any

LEARNING_PATHS = {
    "SQL": "Practice SELECT, JOIN, GROUP BY, aggregates, subqueries, and basic query optimisation.",
    "Docker": "Learn images, containers, Dockerfiles, volumes, and how to containerise a small project.",
    "Kubernetes": "Start with pods, deployments, services, and deploying a containerised application locally.",
    "AWS": "Learn IAM, S3, EC2, CloudWatch, and deploy one documented portfolio project.",
    "TensorFlow": "Build a small supervised-learning project, then learn model evaluation and deployment basics.",
    "PyTorch": "Work through tensors, datasets, training loops, evaluation, and one documented model project.",
    "MLOps": "Learn experiment tracking, model packaging, testing, deployment, and model monitoring concepts.",
    "REST APIs": "Build a small CRUD API, document endpoints, validate input, and add automated tests.",
    "React": "Practice components, state, props, hooks, accessibility, and connecting to a simple API.",
    "Statistics": "Study descriptive statistics, probability, hypothesis testing, confidence intervals, and regression basics.",
}


def learning_path(skill: str) -> str:
    """Return a concrete learning route without suggesting the skill is already held."""
    return LEARNING_PATHS.get(
        skill,
        f"Learn the fundamentals of {skill}, complete a small documented project, and be ready to explain the choices you made.",
    )


def build_insights(parsed_resume: dict[str, Any], job_profile: dict[str, Any], match_result: dict[str, Any]) -> dict[str, list[str]]:
    """Build evidence-based strengths, gaps, and next actions from match outputs."""
    skill_match = match_result.get("skill_match", {})
    keywords = match_result.get("keyword_match", {})
    strengths: list[str] = []
    improvements: list[str] = []
    matching_skills = skill_match.get("matching_skills", [])
    if matching_skills:
        strengths.append(f"Your resume evidences {len(matching_skills)} target-role skills: {', '.join(matching_skills[:6])}.")
    if parsed_resume.get("projects"):
        strengths.append("Your resume includes project experience that can be tailored to the target role.")
    if parsed_resume.get("years_experience", 0) >= job_profile.get("minimum_experience", 0):
        strengths.append("Your stated or dated experience meets the role's minimum experience level.")
    if not strengths:
        strengths.append("The analysis found a foundation to build on; add clear, truthful evidence of relevant skills and projects.")

    missing = skill_match.get("missing_required", [])
    for skill in missing:
        improvements.append(f"Consider learning {skill}. {learning_path(skill)}")
    if keywords.get("missing_keywords"):
        improvements.append("Where accurate, connect existing work to role terminology such as " + ", ".join(keywords["missing_keywords"][:4]) + ".")
    if not parsed_resume.get("projects"):
        improvements.append("Add one or two concise project entries that state the problem, your contribution, technologies, and outcome.")
    if not parsed_resume.get("experience"):
        improvements.append("Add experience, internship, volunteer, or project bullets with specific responsibilities and results where truthful.")

    project_suggestions = []
    for project in parsed_resume.get("projects", [])[:3]:
        title = project.get("title", "This project") if isinstance(project, dict) else str(project)
        project_suggestions.append(f"For {title}, explain the problem, your technical decisions, technologies, and measurable outcome if you have one.")
    if not project_suggestions:
        project_suggestions.append("Create a small role-relevant project and document its goal, implementation, and what you learned.")

    return {
        "strengths": strengths,
        "weaknesses": [f"No evidence of {skill} was found in the resume." for skill in missing] or ["No high-priority skill gap was found for the selected profile."],
        "improvements": improvements or ["Keep tailoring your summary and project bullets to the target role using accurate language."],
        "missing_keywords": keywords.get("missing_keywords", []),
        "skill_recommendations": [f"{item['skill']}: {learning_path(item['skill'])}" for item in skill_match.get("skill_gaps", [])],
        "project_suggestions": project_suggestions,
        "ats_suggestions": [],
    }
