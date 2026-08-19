from __future__ import annotations

from typing import Sequence


def epley_1rm(weight: float, reps: int) -> float:
    """Estimated one-rep max via the Epley formula. See docs/SPEC.md §4.2 -
    used so a rep/weight trade-off still registers as progress or stall on one
    comparable number, but it is the Phase 6 plateau signal, not a permanent
    definition of "progress" (best-set 1RM can read flat while a user's other
    working sets are clearly improving)."""
    if reps <= 0 or weight <= 0:
        return 0.0
    if reps == 1:
        return float(weight)
    return float(weight) * (1.0 + reps / 30.0)


def best_set_1rm(sets: Sequence[dict]) -> float:
    best = 0.0
    for s in sets or []:
        weight = s.get("weight")
        reps = s.get("reps")
        if isinstance(weight, (int, float)) and isinstance(reps, (int, float)) and reps > 0:
            best = max(best, epley_1rm(float(weight), int(reps)))
    return best
