from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressionPolicy:
    """Tunable thresholds for the plateau state machine (docs/SPEC.md §4.2).
    Kept as constructor parameters, not literals inside the detection logic, so
    they can be tuned - or made per-user/per-goal later - without touching
    adaptation/plateau.py itself."""

    version: str = "v1"
    plateau_window: int = 3
    improvement_threshold: float = 0.02
    stalls_before_intervention: int = 2
    rep_adjust_sessions: int = 2
    reverse_sessions: int = 2
    improvements_before_reset: int = 2
    completion_threshold: float = 0.95


DEFAULT_POLICY = ProgressionPolicy()
