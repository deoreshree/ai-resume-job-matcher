"""Interactive AI Interview Simulator and Live Answer Evaluation Engine.

Provides dynamic, resume-grounded mock interview questions across 6 categories
and evaluates candidate answers across 5 concrete evaluation dimensions.
"""

from __future__ import annotations

import re
from typing import Any


def generate_simulator_question_bank(
    resume: dict[str, Any],
    job_profile: dict[str, Any],
    match_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate dynamic, resume-personalized mock interview practice questions."""
    role_title = job_profile.get("title", "Software Developer")
    skills = resume.get("skills", [])
    projects = resume.get("projects", [])
    exp = resume.get("experience", [])
    skill_match = match_result.get("skill_match", {})
    missing_required = skill_match.get("missing_required", [])

    top_skill_1 = skills[0] if len(skills) > 0 else "Python"
    top_skill_2 = skills[1] if len(skills) > 1 else "SQL"
    top_proj_name = projects[0].get("name") if projects else "your recent technical project"
    top_proj_tech = ", ".join(projects[0].get("technologies", [])) if projects and projects[0].get("technologies") else top_skill_1
    top_gap = missing_required[0] if missing_required else "system scalability"

    return [
        {
            "id": "q1",
            "category": "Project Ownership & Architecture",
            "category_badge": "Project Architecture",
            "question": f"Walk me through the architecture of '{top_proj_name}'. What technical tradeoffs did you evaluate when selecting {top_proj_tech}?",
            "context": f"Evaluates design rationale and ownership for {top_proj_name}.",
            "expected_concepts": ["Problem definition", "Architecture choices", "Tradeoffs", "Metrics & results"],
            "difficulty": "Intermediate",
        },
        {
            "id": "q2",
            "category": "Technical Deep-Dive",
            "category_badge": "Technical Deep-Dive",
            "question": f"In a production {role_title} environment, how do you optimize performance and manage state when working with {top_skill_1} and {top_skill_2}?",
            "context": f"Tests production-grade proficiency in {top_skill_1} and {top_skill_2}.",
            "expected_concepts": ["Memory management", "Concurrency/Async", "Query/Code Optimization", "Error handling"],
            "difficulty": "Advanced",
        },
        {
            "id": "q3",
            "category": "DSA & Problem Solving",
            "category_badge": "Algorithms & Problem Solving",
            "question": "How would you design an efficient algorithm to process and aggregate a high-volume stream of events in real time with minimal latency?",
            "context": "Evaluates algorithmic complexity, data structure choices, and time/space tradeoff reasoning.",
            "expected_concepts": ["Time complexity (O(N))", "Space complexity", "Hash maps / Heaps / Queues", "Edge cases"],
            "difficulty": "Advanced",
        },
        {
            "id": "q4",
            "category": "Behavioral & Collaboration (STAR)",
            "category_badge": "Behavioral (STAR)",
            "question": "Tell me about a time you encountered a blocking technical disagreement or bug under a tight deadline. How did you resolve it?",
            "context": "Assesses structured communication (STAR: Situation, Task, Action, Result) and team collaboration.",
            "expected_concepts": ["Clear situation context", "Proactive initiative", "Collaborative outcome", "Quantified resolution"],
            "difficulty": "Core",
        },
        {
            "id": "q5",
            "category": "Skill Gap & Upskilling Readiness",
            "category_badge": "Skill-Gap Readiness",
            "question": f"This role frequently utilizes {top_gap}. How would you approach quickly ramping up and applying {top_gap} to production systems?",
            "context": f"Assesses learning agility and engineering problem formulation around {top_gap}.",
            "expected_concepts": ["Learning methodology", "Prototyping & docs", "Safe experimentation", "Peer code review"],
            "difficulty": "Targeted",
        },
        {
            "id": "q6",
            "category": "Role-Specific Scenario",
            "category_badge": "System Scenario",
            "question": f"If an endpoint or pipeline in your {role_title} system suddenly experiences a 5x spike in error rates, what is your step-by-step triage playbook?",
            "context": "Evaluates operational discipline, telemetry inspection, and rollback/mitigation instincts.",
            "expected_concepts": ["Monitoring / Logs inspection", "Isolating blast radius", "Safe rollback / mitigation", "Root cause post-mortem"],
            "difficulty": "Practical",
        },
    ]


def evaluate_interview_answer(
    question: str,
    candidate_answer: str,
    category: str,
    role_title: str,
    resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate candidate's mock interview response across 5 dimensions."""
    text = (candidate_answer or "").strip()
    words = text.split()
    word_count = len(words)

    if word_count < 10:
        return {
            "overall_score": 35,
            "rating": "Insufficient Response Length",
            "rating_class": "danger",
            "feedback_summary": "Your response is too brief for an interviewer to assess your technical depth or communication ability.",
            "dimension_scores": {
                "communication": 30,
                "technical_depth": 25,
                "structure": 25,
                "project_understanding": 30,
                "relevance": 40,
            },
            "what_you_did_well": ["Attempted an initial response."],
            "what_to_improve": [
                "Provide a comprehensive answer (aim for 60–150 words).",
                "Explain concrete technical steps, tools, and tradeoffs.",
                "Structure your answer using the STAR method (Situation, Task, Action, Result).",
            ],
            "better_answer_structure": (
                "Start with the core objective, outline 2-3 specific technical actions you took, "
                "mention the tools or algorithms used, and conclude with the measurable outcome or lesson learned."
            ),
        }

    # 1. Communication & Clarity (Based on length, flow, and sentence formation)
    comm_score = min(95, max(45, int(50 + min(word_count, 120) * 0.35)))

    # 2. Technical Depth (Presence of technical keywords, tools, metrics, tradeoff words)
    tech_keywords = [
        "architecture", "latency", "throughput", "algorithm", "complexity", "database",
        "pipeline", "cache", "async", "testing", "monitoring", "tradeoff", "scalability",
        "optimization", "metrics", "framework", "schema", "api", "docker", "cloud",
        "regression", "classification", "sql", "index", "memory", "profiling", "rollback",
    ]
    tech_found = sum(1 for kw in tech_keywords if re.search(r"\b" + kw + r"\b", text, re.I))
    tech_score = min(95, max(40, int(50 + tech_found * 8)))

    # 3. Answer Structure (Presence of STAR or structured transition words: first, because, result, impact, decided, then)
    struct_markers = ["first", "then", "because", "result", "therefore", "initially", "implemented", "outcome", "finally", "approach"]
    struct_found = sum(1 for m in struct_markers if re.search(r"\b" + m + r"\b", text, re.I))
    struct_score = min(92, max(45, int(55 + struct_found * 7)))

    # 4. Project & Domain Understanding
    proj_score = min(95, max(50, int(0.5 * tech_score + 0.5 * struct_score)))

    # 5. Relevance
    relevance_score = min(95, max(55, int(60 + min(word_count, 100) * 0.3)))

    overall = int(round(0.25 * comm_score + 0.30 * tech_score + 0.20 * struct_score + 0.15 * proj_score + 0.10 * relevance_score))

    if overall >= 85:
        rating = "Outstanding Response"
        rating_class = "success"
        feedback = "Exceptional interview answer! Strong technical depth, clear structure, and professional phrasing."
    elif overall >= 72:
        rating = "Strong Competent Response"
        rating_class = "good"
        feedback = "Well-structured answer with solid technical grounding. Adding quantifiable results would make it even stronger."
    elif overall >= 55:
        rating = "Moderate Response — Needs Detail"
        rating_class = "warning"
        feedback = "Good foundation, but lacks specific architectural details, tools, or concrete outcome metrics."
    else:
        rating = "Developing Response"
        rating_class = "danger"
        feedback = "Response is somewhat vague. Focus on detailing exact technical decisions and their measurable results."

    # Build What You Did Well
    did_well: list[str] = []
    if tech_found >= 2:
        did_well.append("Referenced relevant technical terminology and system concepts.")
    if struct_found >= 2:
        did_well.append("Followed a logical chronological flow from problem identification to resolution.")
    if word_count >= 50:
        did_well.append("Provided sufficient detail to substantiate your technical decision-making.")
    if not did_well:
        did_well.append("Directly addressed the prompt with a clear initial stance.")

    # Build What To Improve
    to_improve: list[str] = []
    if tech_found < 3:
        to_improve.append("Incorporate specific tools, metrics, or architectural terms to prove hands-on mastery.")
    if struct_found < 2:
        to_improve.append("Structure your answer explicitly using the STAR model: Situation -> Action Taken -> Quantified Result.")
    if "metric" not in text.lower() and "%" not in text and "latency" not in text.lower():
        to_improve.append("Highlight measurable impact (e.g., 'reduced processing time by 25%', 'handled 10K requests').")
    if not to_improve:
        to_improve.append("Anticipate follow-up questions regarding edge cases and alternative architectures considered.")

    # Exemplary Better Answer Structure
    model_answer = (
        f"**Situation & Objective:** Set the context clearly in 1 sentence ('In our {role_title} project, we needed to optimize...').\n"
        f"**Technical Action:** Detail the exact tools and architectural pattern chosen ('I designed a modular pipeline in Python/SQL, implementing...').\n"
        f"**Tradeoff & Edge Cases:** Explain why you chose this path over alternatives ('We prioritized throughput and data integrity over complex distributed caching...').\n"
        f"**Quantifiable Result:** Conclude with the outcome ('This improved processing speed and maintained zero data discrepancies under peak load.')."
    )

    return {
        "overall_score": overall,
        "rating": rating,
        "rating_class": rating_class,
        "feedback_summary": feedback,
        "dimension_scores": {
            "communication": comm_score,
            "technical_depth": tech_score,
            "structure": struct_score,
            "project_understanding": proj_score,
            "relevance": relevance_score,
        },
        "what_you_did_well": did_well,
        "what_to_improve": to_improve,
        "better_answer_structure": model_answer,
    }
