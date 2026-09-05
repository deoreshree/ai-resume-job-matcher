"""Catalog-backed, boundary-aware skill extraction."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from config import SKILLS_PATH


def _as_skill(item: object) -> dict[str, Any]:
    """Support concise string entries as well as editable rich catalog entries."""
    if isinstance(item, str):
        return {"name": item, "aliases": [item]}
    if isinstance(item, dict) and item.get("name"):
        name = str(item["name"]).strip()
        aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
        return {"name": name, "aliases": [name, *aliases]}
    raise ValueError("Each catalog skill must be a name or an object with a name.")


@lru_cache(maxsize=1)
def load_skill_catalog() -> dict[str, list[dict[str, Any]]]:
    """Load and normalize the editable catalog, once per Python process."""
    try:
        payload = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not load the skill catalog. Check data/skills.json.") from exc

    categories = payload.get("categories")
    if not isinstance(categories, dict) or not categories:
        raise RuntimeError("The skill catalog has no categories.")
    return {
        str(category): [_as_skill(item) for item in items]
        for category, items in categories.items()
        if isinstance(items, list)
    }


@lru_cache(maxsize=1)
def skill_lookup() -> dict[str, str]:
    """Map catalog names and aliases to canonical display names."""
    lookup: dict[str, str] = {}
    for skills in load_skill_catalog().values():
        for skill in skills:
            for term in skill["aliases"]:
                lookup[term.casefold()] = skill["name"]
    return lookup


def normalize_skill(value: str) -> str:
    """Return a catalog canonical name when one is known; otherwise tidy the input."""
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    return skill_lookup().get(cleaned.casefold(), cleaned)


def _find_term(text: str, term: str) -> Optional[str]:
    """Match an alias without turning abbreviations such as SQL into substrings."""
    term = term.strip()
    if not term:
        return None
    if term.lower() == "c":
        match = re.search(r"(?<![A-Za-z0-9+#])c(?![A-Za-z0-9+#])", text, re.IGNORECASE)
        return match.group(0) if match else None
    pattern = r"(?<![A-Za-z0-9+#])" + re.escape(term) + r"(?![A-Za-z0-9+#])"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def _contains_term(text: str, term: str) -> bool:
    return _find_term(text, term) is not None


def extract_skills(text: str) -> dict[str, Any]:
    """Extract canonical skills, grouped categories, and matching catalog aliases.

    The matcher only returns skills evidenced in the supplied text. It never infers a
    tool merely because it is commonly used with another detected skill.
    """
    source = text or ""
    catalog = load_skill_catalog()
    by_category: dict[str, list[str]] = {category: [] for category in catalog}
    matched_aliases: dict[str, str] = {}
    skills: list[str] = []

    for category, catalog_skills in catalog.items():
        found: list[str] = []
        for skill in catalog_skills:
            for alias in sorted(skill["aliases"], key=len, reverse=True):
                matched_str = _find_term(source, alias)
                if matched_str is not None:
                    name = skill["name"]
                    if name not in skills:
                        skills.append(name)
                    if name not in found:
                        found.append(name)
                    matched_aliases[name] = matched_str
                    break
        by_category[category] = found

    # Filter out empty categories for by_category_active, but keep full categorized_skills
    active_by_category = {cat: items for cat, items in by_category.items() if items}

    return {
        "skills": skills,
        "by_category": active_by_category,
        "categorized_skills": by_category,
        "matched_aliases": matched_aliases,
        "catalog_count": sum(len(items) for items in catalog.values()),
    }
