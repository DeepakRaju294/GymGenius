from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.utils.db import mongo
from app.services.history import equipment_profile, fetch_user_history, get_exercise_catalog, recent_muscles


def _exercise_matches_focus(ex_doc: dict, focus: Optional[str]) -> bool:
    if not focus:
        return True
    tags = ex_doc.get("tags") or []
    return isinstance(tags, list) and focus in tags


def candidate_pool(username: str, focus: Optional[str]) -> Tuple[List[dict], List[dict]]:
    """Selection stage: which exercises could today's session include. Filters the
    canonical catalog (app.services.history.get_exercise_catalog) by focus tag,
    equipment the user actually has, and muscle groups trained within the rest
    window - it does not rank; that's selection/scorer.py."""
    db = mongo()
    history = fetch_user_history(username)
    catalog = get_exercise_catalog()
    muscles_to_rest = recent_muscles(history, catalog)
    user_eq = equipment_profile(username)

    candidates: List[dict] = []
    for ex in catalog.values():
        if not _exercise_matches_focus(ex, focus):
            continue

        needs = set(ex.get("equipment") or [])
        if needs and not needs.issubset(user_eq):
            continue

        pm = ex.get("primaryMuscle")
        if isinstance(pm, str) and pm in muscles_to_rest:
            continue

        candidates.append(ex)

    return candidates, history
