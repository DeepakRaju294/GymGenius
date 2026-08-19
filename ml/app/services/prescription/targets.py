from __future__ import annotations

from typing import Dict, Optional, Tuple

GOAL_TO_REP: Dict[str, Tuple[int, int]] = {
    "strength": (3, 5),
    "hypertrophy": (3, 10),
    "endurance": (3, 15),
}
DEFAULT_GOAL = "hypertrophy"


def choose_sets_reps(goal: Optional[str]) -> Tuple[int, int]:
    g = goal or DEFAULT_GOAL
    return GOAL_TO_REP.get(g, GOAL_TO_REP[DEFAULT_GOAL])
