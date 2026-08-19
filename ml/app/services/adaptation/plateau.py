from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .policy import ProgressionPolicy

STRATEGIES = ("NORMAL", "REP_ADJUST", "REVERSE", "SWAPPED")


def fresh_state() -> Dict:
    return {
        "currentStrategy": "NORMAL",
        "strategyStartedAt": None,
        "strategySessionCount": 0,
        "consecutiveStallSessions": 0,
        "consecutiveImprovementSessions": 0,
        "baselineEstimated1RM": None,
        "lastEstimated1RM": None,
        "lastEvaluatedAt": None,
        "reason": "",
    }


def advance(
    state: Dict,
    session_1rm: float,
    policy: ProgressionPolicy = ProgressionPolicy(),
    session_ts: Optional[datetime] = None,
) -> Tuple[Dict, List[Dict]]:
    """Evaluate one new logged session against the current progression state and
    return (new_state, events). `events` are progression_events-shaped dicts
    (type + metrics only - the caller fills in username/exerciseId/ts).

    This is the state machine from docs/SPEC.md §4.2:

        NORMAL --plateau--> REP_ADJUST --still stalled--> REVERSE --still stalled--> SWAPPED
          ^                     |                              |
          +--- improvements_before_reset consecutive improvements, from any state ---+

    A single improved session never flips a non-NORMAL strategy back to NORMAL by
    itself - it takes `improvements_before_reset` CONSECUTIVE improved sessions,
    so an intervention actually gets tested before being abandoned. Escalation
    (REP_ADJUST->REVERSE, REVERSE->SWAPPED) is likewise gated on CONSECUTIVE
    stalled sessions within that strategy, not merely total sessions spent in it -
    an improve/stall/improve pattern must not accumulate toward escalation the way
    two genuinely consecutive stalls would.
    """
    state = dict(state)
    events: List[Dict] = []
    prev = state.get("lastEstimated1RM")

    if prev is None:
        # First-ever logged session for this exercise: nothing to compare against yet.
        state["consecutiveStallSessions"] = 0
        state["consecutiveImprovementSessions"] = 0
    elif session_1rm > prev * (1 + policy.improvement_threshold):
        state["consecutiveImprovementSessions"] = state.get("consecutiveImprovementSessions", 0) + 1
        state["consecutiveStallSessions"] = 0
    else:
        state["consecutiveStallSessions"] = state.get("consecutiveStallSessions", 0) + 1
        state["consecutiveImprovementSessions"] = 0

    state["lastEstimated1RM"] = session_1rm
    state["strategySessionCount"] = state.get("strategySessionCount", 0) + 1

    strategy = state.get("currentStrategy", "NORMAL")
    metrics = {"estimated1RM": session_1rm, "priorEstimated1RM": prev}

    if strategy != "NORMAL" and state["consecutiveImprovementSessions"] >= policy.improvements_before_reset:
        events.append({"type": "PROGRESS_RESUMED", "metrics": metrics})
        state.update(
            {
                "currentStrategy": "NORMAL",
                "strategyStartedAt": session_ts,
                "strategySessionCount": 0,
                "consecutiveStallSessions": 0,
                "consecutiveImprovementSessions": 0,
                "reason": "Progress resumed - back to standard progression.",
            }
        )
        return state, events

    if strategy == "NORMAL":
        if state["consecutiveStallSessions"] >= policy.stalls_before_intervention:
            events.append({"type": "PLATEAU_DETECTED", "metrics": metrics})
            events.append({"type": "REP_ADJUST_STARTED", "metrics": metrics})
            state.update(
                {
                    "currentStrategy": "REP_ADJUST",
                    "strategyStartedAt": session_ts,
                    "strategySessionCount": 0,
                    "consecutiveStallSessions": 0,
                    "baselineEstimated1RM": session_1rm,
                    "reason": "Plateaued - lowering reps, raising weight.",
                }
            )
    elif strategy == "REP_ADJUST":
        if state["consecutiveStallSessions"] >= policy.rep_adjust_sessions:
            events.append({"type": "REVERSE_STARTED", "metrics": metrics})
            state.update(
                {
                    "currentStrategy": "REVERSE",
                    "strategyStartedAt": session_ts,
                    "strategySessionCount": 0,
                    "consecutiveStallSessions": 0,
                    "reason": "Still plateaued - reversing to higher reps, lower weight.",
                }
            )
    elif strategy == "REVERSE":
        if state["consecutiveStallSessions"] >= policy.reverse_sessions:
            events.append({"type": "EXERCISE_SWAPPED", "metrics": metrics})
            state.update(
                {
                    "currentStrategy": "SWAPPED",
                    "strategyStartedAt": session_ts,
                    "strategySessionCount": 0,
                    "consecutiveStallSessions": 0,
                    "reason": "Still plateaued after reversing - swapping this exercise out.",
                }
            )
    # SWAPPED: no further auto-transitions except the reset check above.

    return state, events
