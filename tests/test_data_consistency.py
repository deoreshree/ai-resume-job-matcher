"""Guards against drift between the job-role catalog and the skill catalog."""

from __future__ import annotations

import json

from config import ATS_WEIGHTS, JOB_ROLES_PATH, SKILLS_PATH
from modules.scoring import COMPONENT_LABELS, _validated_weights


def test_every_role_skill_exists_in_skill_catalog():
    catalog = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    known = set()
    for items in catalog["categories"].values():
        for item in items:
            if isinstance(item, str):
                known.add(item.casefold())
            else:
                known.add(str(item["name"]).casefold())
                known.update(str(alias).casefold() for alias in item.get("aliases", []))

    roles = json.loads(JOB_ROLES_PATH.read_text(encoding="utf-8"))["roles"]
    for role in roles:
        for skill in role.get("required_skills", []) + role.get("preferred_skills", []):
            assert skill.casefold() in known, f"{role['title']}: skill {skill!r} missing from data/skills.json"


def test_every_role_has_required_metadata():
    roles = json.loads(JOB_ROLES_PATH.read_text(encoding="utf-8"))["roles"]
    for role in roles:
        assert role.get("title")
        assert isinstance(role.get("required_skills"), list) and role["required_skills"]
        assert isinstance(role.get("keywords"), list)
        assert isinstance(role.get("minimum_experience"), (int, float))


def test_scoring_and_ats_weights_are_valid():
    assert abs(sum(ATS_WEIGHTS.values()) - 1.0) < 1e-6
    assert set(ATS_WEIGHTS) == {"keywords", "structure", "skills", "readability", "formatting"}
    weights = _validated_weights(None)
    assert set(weights) == set(COMPONENT_LABELS)
