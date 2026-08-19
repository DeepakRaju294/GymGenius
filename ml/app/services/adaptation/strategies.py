from __future__ import annotations

from typing import Tuple


def rep_adjust(base_reps: int, base_weight: float) -> Tuple[int, float]:
    """REP_ADJUST prescription: lower reps, higher weight (docs/SPEC.md §4.2)."""
    reps = max(1, base_reps - 2)
    weight = round(base_weight * 1.075, 1)  # +7.5%, midpoint of the spec's +5-10% range
    return reps, weight


def reverse(base_reps: int, base_weight: float) -> Tuple[int, float]:
    """REVERSE prescription: the opposite adjustment - higher reps, weight back
    down toward the pre-REP_ADJUST baseline."""
    reps = base_reps + 3
    weight = round(base_weight * 0.85, 1)
    return reps, weight
