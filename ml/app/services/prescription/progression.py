from __future__ import annotations

from typing import Optional, Sequence

from app.services.history import last_top_weight

LOWER_BODY = {"quads", "hamstrings", "glutes", "calves", "adductors", "abductors"}


def _progression_increment_lbs(primary_muscle: Optional[str]) -> float:
    if isinstance(primary_muscle, str) and primary_muscle in LOWER_BODY:
        return 5.0
    return 2.5


def apply_progression(exercise_id: str, primary_muscle: Optional[str], history: Sequence[dict]) -> Optional[float]:
    """Plain NORMAL-strategy progressive overload: last logged top weight for this
    exercise plus a small increment. Returns None when the user has never logged
    this exercise - there's no meaningful default weight across a beginner and an
    advanced lifter (docs/SPEC.md §3), so the caller must ask the user for a
    starting weight rather than guessing one."""
    last_weight = last_top_weight(history, exercise_id)
    if last_weight is None:
        return None
    inc = _progression_increment_lbs(primary_muscle)
    return max(round(last_weight + inc, 1), 0.0)
