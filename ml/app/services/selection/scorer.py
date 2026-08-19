from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Dict, Optional, Sequence

from app.services.history import days_ago, frequency_28d, last_done_by_exercise, now

DEFAULT_GOAL = "hypertrophy"


def build_user_vector(history: Sequence[dict], catalog: Dict[str, dict]) -> Dict[str, float]:
    """Normalized training volume by muscle group, most recent history first or
    last (order doesn't matter here). Feeds the `balance` term in score_rules so
    candidate selection favors muscle groups the user has trained less, instead of
    only optimizing per-exercise progression."""
    vol: Dict[str, float] = defaultdict(float)
    total = 0.0
    for doc in history:
        for ex in doc.get("exercises", []):
            cat = catalog.get(ex.get("exerciseId"), {})
            mg = cat.get("primaryMuscle") or "other"
            for s in ex.get("sets", []):
                weight = s.get("weight") or 0
                reps = s.get("reps") or 0
                lifted = float(weight) * float(reps)
                vol[mg] += lifted
                total += lifted
    if total <= 0:
        return {}
    return {k: v / total for k, v in vol.items()}


def _goal_alignment(ex_doc: dict, goal: str) -> float:
    goals = ex_doc.get("tags") or []
    if isinstance(goals, list) and goal in goals:
        return 1.0
    return 0.6


def score_rules(
    candidates: Sequence[dict],
    history: Sequence[dict],
    goal: Optional[str],
    catalog: Dict[str, dict],
) -> Dict[str, float]:
    g = goal or DEFAULT_GOAL
    last = last_done_by_exercise(history)
    freq = frequency_28d(history)
    vector = build_user_vector(history, catalog)
    max_share = max(vector.values(), default=0.0) or 1.0

    scores: Dict[str, float] = {}
    for ex in candidates:
        exid = ex["exerciseId"]

        rec_days = days_ago(last.get(exid, now() - timedelta(days=60)))
        rec_norm = min(rec_days / 30.0, 1.0)

        freq_pen = 1.0 / (1.0 + freq.get(exid, 0))

        align = _goal_alignment(ex, g)

        pm = ex.get("primaryMuscle") or "other"
        balance = 1.0 - (vector.get(pm, 0.0) / max_share)

        score = 0.30 * align + 0.25 * rec_norm + 0.20 * freq_pen + 0.25 * balance
        scores[exid] = float(score)

    return scores
