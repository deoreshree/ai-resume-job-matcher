"""Evidence-based personalised interview questions, usable with no API key."""

from __future__ import annotations

from typing import Any


def _question(question: str, why: str, cover: str) -> dict[str, str]:
    return {"question": question, "why_interviewer_may_ask": why, "strong_answer_should_cover": cover}


def generate_interview_pack(parsed_resume: dict[str, Any], job_profile: dict[str, Any], match_result: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Build technical, project, HR, and scenario prompts from actual analysis facts."""
    title = job_profile.get("title", "this role")
    candidate_skills = parsed_resume.get("skills", [])
    matching = match_result.get("skill_match", {}).get("matching_skills", [])
    required = job_profile.get("required_skills", [])
    primary = (matching or candidate_skills or required)[:6]
    technical = [
        _question(
            f"How have you used {skill} in work, coursework, or a project?",
            f"{skill} is relevant to the {title} role and appears in the analysis.",
            "Describe a real context, your contribution, the approach, and what you learned. Do not claim experience you do not have.",
        )
        for skill in primary
    ]
    while len(technical) < 5:
        technical.append(
            _question(
                "How do you approach debugging an unfamiliar technical problem?",
                "Interviewers evaluate structured problem solving across tools and domains.",
                "Clarify the problem, reproduce it, inspect evidence, form hypotheses, test safely, and communicate the result.",
            )
        )
    projects = parsed_resume.get("projects", [])
    project_questions: list[dict[str, str]] = []
    for project in projects[:5]:
        project_title = project.get("title", "one of your projects") if isinstance(project, dict) else str(project)
        project_questions.append(
            _question(
                f"Walk me through {project_title}: what problem did it address and what did you personally implement?",
                "Projects help confirm that a candidate can explain decisions and ownership.",
                "State the goal, your role, technologies actually used, key trade-offs, testing or evaluation, and the outcome.",
            )
        )
    while len(project_questions) < 5:
        project_questions.append(
            _question(
                "Tell me about a project you would build to strengthen your fit for this role.",
                "This explores initiative when a resume has limited directly related project evidence.",
                "Propose a realistic scope, an honest learning plan, technical choices, and how you would evaluate it.",
            )
        )
    hr = [
        _question(f"Why are you interested in the {title} role?", "Motivation and alignment matter alongside skills.", "Connect your actual interests and experience to the responsibilities without overstating fit."),
        _question("Tell me about a time you collaborated to deliver something.", "Teams need clear collaboration and communication.", "Use a real situation, your contribution, how you coordinated, and the result."),
        _question("What is a skill you are currently developing?", "Interviewers value self-awareness and learning habits.", "Name a genuine gap, your practical learning plan, and evidence of progress if available."),
        _question("How do you prioritise competing tasks?", "The role may involve multiple stakeholders or deadlines.", "Explain how you clarify impact, urgency, dependencies, and communicate trade-offs."),
        _question("What kind of feedback helps you improve?", "This assesses coachability and professional communication.", "Give an honest example of receiving feedback and changing your approach."),
    ]
    scenario = [
        _question("A requirement is ambiguous and the deadline is close. What would you do?", "This tests judgement under uncertainty.", "Clarify the decision needed, identify assumptions, propose a small safe next step, and communicate risks."),
        _question("Your result conflicts with an expected business outcome. How do you respond?", "Interviewers look for analytical integrity.", "Validate the data and method, explain uncertainty, explore alternatives, and present findings transparently."),
        _question("A production issue appears after a release. How would you handle it?", "Reliability and calm incident response are broadly valuable.", "Prioritise user impact, gather evidence, mitigate safely, communicate status, fix, and document prevention."),
        _question("How would you explain a technical choice to a non-technical stakeholder?", "Cross-functional communication is often essential.", "Use plain language, describe trade-offs and impact, invite questions, and avoid unnecessary jargon."),
        _question("You need to learn a tool required by the role quickly. How would you proceed?", "Some job requirements may be skill gaps today.", "Set a focused learning goal, use official material, build a small proof project, seek feedback, and state limits honestly."),
    ]
    return {
        "technical_questions": technical[:10],
        "project_questions": project_questions[:5],
        "hr_questions": hr,
        "scenario_questions": scenario,
    }
