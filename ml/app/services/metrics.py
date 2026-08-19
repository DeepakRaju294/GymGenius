from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from app.utils.db import mongo
from .adaptation.policy import DEFAULT_POLICY


def prescribed_volume_completion(actual_sets: Sequence[dict], prescription: Dict) -> float:
    """Fraction of prescribed reps actually completed at-or-above the prescribed
    weight, capped at 1.0. Deliberately not binary (docs/SPEC.md §4.3 rev. 3) -
    "missed the last rep of the last set" and "did half the prescribed volume"
    are very different signals that a binary completed/failed would conflate."""
    prescribed_total_reps = (prescription.get("reps") or 0) * (prescription.get("sets") or 0)
    if prescribed_total_reps <= 0:
        return 0.0
    prescribed_weight = prescription.get("weight") or 0
    completed_reps = sum(
        s.get("reps", 0)
        for s in actual_sets
        if isinstance(s.get("weight"), (int, float)) and s.get("weight", 0) >= prescribed_weight
    )
    return min(completed_reps / prescribed_total_reps, 1.0)


def completion_rate(
    username: str,
    exercise_id: str,
    window: int = 5,
    completion_threshold: float = DEFAULT_POLICY.completion_threshold,
) -> Optional[float]:
    """Fraction of an exercise's last `window` *recommended* sessions (i.e. logged
    with a matching recommendationItemId) that met `completion_threshold`. Answers
    "did the user do what was prescribed" - a different question from
    progression_rate's "is 1RM improving" (docs/SPEC.md §4.3). Returns None when
    there isn't enough recommendation-linked history to compute it."""
    db = mongo()
    recs = list(
        db.recommendations.find({"username": username, "items.exerciseId": exercise_id})
        .sort("createdAt", -1)
        .limit(window * 3)
    )
    if not recs:
        return None

    prescriptions_by_item: Dict[str, Dict] = {}
    for rec in recs:
        for item in rec.get("items", []):
            if item.get("exerciseId") == exercise_id and item.get("recommendationItemId"):
                prescriptions_by_item[item["recommendationItemId"]] = item.get("prescription", {})
    if not prescriptions_by_item:
        return None

    history = list(
        db.histories.find(
            {"username": username, "exercises.recommendationItemId": {"$in": list(prescriptions_by_item.keys())}}
        )
        .sort("workoutDate", -1)
        .limit(window)
    )
    if not history:
        return None

    scores: List[float] = []
    for doc in history:
        for ex in doc.get("exercises", []):
            rid = ex.get("recommendationItemId")
            if rid in prescriptions_by_item:
                scores.append(prescribed_volume_completion(ex.get("sets", []), prescriptions_by_item[rid]))

    if not scores:
        return None
    hits = sum(1 for s in scores if s >= completion_threshold)
    return hits / len(scores)


def progression_rate(
    session_1rms: Sequence[float], improvement_threshold: float = DEFAULT_POLICY.improvement_threshold
) -> Optional[float]:
    """Fraction of consecutive session-pairs where estimated 1RM improved - the
    signal §4.2's plateau trigger actually watches. `session_1rms` must already be
    in chronological order (see app.services.history.sessions_for_exercise)."""
    if len(session_1rms) < 2:
        return None
    compared = 0
    improved = 0
    for prev, curr in zip(session_1rms, session_1rms[1:]):
        compared += 1
        if curr > prev * (1 + improvement_threshold):
            improved += 1
    return improved / compared if compared else None
