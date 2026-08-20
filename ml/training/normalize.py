"""docs/ML_SPEC.md §1 step 2/3 - normalizes free-text equipment/muscle labels and
assigns movementPattern via the rule tables in ml/artifacts/. Not a model - lookup
tables, same spirit as the synonym maps themselves."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app.*` imports work standalone
from app.utils.artifacts import load_json  # noqa: E402


@lru_cache(maxsize=None)
def _reverse_synonym_map(filename: str) -> dict:
    """{"barbell": ["barbell", "olympic bar"]} -> {"olympic bar": "barbell", "barbell": "barbell"}"""
    raw = load_json(filename)
    reverse = {}
    for canonical, synonyms in raw.items():
        if canonical.startswith("_"):
            continue
        for syn in synonyms:
            reverse[syn.strip().lower()] = canonical
    return reverse


def normalize_equipment(raw: str) -> str:
    key = (raw or "").strip().lower()
    return _reverse_synonym_map("equipment_map.json").get(key, key)


def normalize_muscle(raw: str) -> str:
    key = (raw or "").strip().lower()
    return _reverse_synonym_map("muscle_groups.json").get(key, key)


def assign_movement_pattern(exercise_name: str) -> Tuple[Optional[str], str, List[str]]:
    """Returns (movementPattern, movementPatternSource, secondaryMovementPatterns).
    Hybrid rules are checked first since a hybrid match is more specific than a
    plain single-pattern keyword match (e.g. "thruster" should not fall through to
    a generic squat-only rule if one existed)."""
    name = (exercise_name or "").strip().lower()
    if not name:
        return None, "manual", []

    rules = load_json("movement_pattern_rules.json")

    for rule in rules.get("hybrid_rules", []):
        if any(kw in name for kw in rule["keywords"]):
            return rule["pattern"], "rule", rule.get("secondaryPatterns", [])

    for rule in rules.get("keyword_rules", []):
        if any(kw in name for kw in rule["keywords"]):
            return rule["pattern"], "rule", []

    return None, "manual", []
