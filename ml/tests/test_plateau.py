"""Synthetic-history unit tests for the plateau state machine (docs/SPEC.md §4.2,
§4.6). No database - `advance()` is a pure function of (state, new session 1RM,
policy), which is exactly what makes it cheap to test exhaustively."""

from datetime import datetime, timedelta

from app.services.adaptation.plateau import advance, fresh_state
from app.services.adaptation.policy import ProgressionPolicy

_T0 = datetime(2026, 1, 1)


def run_sequence(session_1rms, policy=None):
    """Feed each 1RM through advance() in order, starting from a fresh state, one
    session per (fake, monotonically increasing) day. Returns (final_state,
    all_events_seen_in_order)."""
    policy = policy or ProgressionPolicy()
    state = fresh_state()
    all_events = []
    for i, rm in enumerate(session_1rms):
        state, events = advance(state, rm, policy, session_ts=_T0 + timedelta(days=i))
        all_events.extend(events)
    return state, all_events


def event_types(events):
    return [e["type"] for e in events]


# -- NORMAL -> REP_ADJUST -------------------------------------------------------


def test_first_session_has_no_transition_or_events():
    state, events = run_sequence([234.0])
    assert state["currentStrategy"] == "NORMAL"
    assert events == []
    assert state["consecutiveStallSessions"] == 0
    assert state["consecutiveImprovementSessions"] == 0


def test_flat_history_over_plateau_window_triggers_rep_adjust():
    # 185x8 three sessions running: baseline, stall #1, stall #2 -> plateau.
    state, events = run_sequence([234.0, 234.0, 234.0])
    assert state["currentStrategy"] == "REP_ADJUST"
    assert state["consecutiveStallSessions"] == 0  # reset on entering the new strategy
    assert event_types(events) == ["PLATEAU_DETECTED", "REP_ADJUST_STARTED"]


def test_improving_history_stays_normal():
    state, events = run_sequence([200.0, 210.0, 220.0, 230.0, 240.0])
    assert state["currentStrategy"] == "NORMAL"
    assert events == []


def test_single_stall_does_not_trigger_plateau():
    state, events = run_sequence([200.0, 200.0])
    assert state["currentStrategy"] == "NORMAL"
    assert state["consecutiveStallSessions"] == 1
    assert events == []


def test_decreasing_weight_counts_as_stall_not_improvement():
    state, events = run_sequence([240.0, 220.0])
    assert state["consecutiveStallSessions"] == 1
    assert state["consecutiveImprovementSessions"] == 0
    assert events == []


def test_custom_policy_can_trigger_plateau_after_a_single_stall():
    policy = ProgressionPolicy(stalls_before_intervention=1)
    state, events = run_sequence([200.0, 200.0], policy=policy)
    assert state["currentStrategy"] == "REP_ADJUST"
    assert event_types(events) == ["PLATEAU_DETECTED", "REP_ADJUST_STARTED"]


def test_baseline_and_started_at_populate_on_rep_adjust_entry():
    state, _ = run_sequence([234.0, 234.0, 234.0])
    assert state["baselineEstimated1RM"] == 234.0
    assert state["strategyStartedAt"] is not None


# -- improvement-threshold boundary ---------------------------------------------


def test_improvement_exactly_at_threshold_is_not_counted():
    # +2.0% exactly is not > threshold (strict inequality) - should read as a stall.
    state, _ = run_sequence([200.0, 204.0])
    assert state["consecutiveStallSessions"] == 1
    assert state["consecutiveImprovementSessions"] == 0


def test_improvement_just_above_threshold_is_counted():
    state, _ = run_sequence([200.0, 204.01])
    assert state["consecutiveImprovementSessions"] == 1
    assert state["consecutiveStallSessions"] == 0


# -- REP_ADJUST behavior ----------------------------------------------------------


def _in_rep_adjust():
    """Helper: drive state into REP_ADJUST via three flat sessions."""
    state = fresh_state()
    policy = ProgressionPolicy()
    for rm in (234.0, 234.0, 234.0):
        state, _ = advance(state, rm, policy)
    assert state["currentStrategy"] == "REP_ADJUST"
    return state, policy


def test_rep_adjust_single_improvement_remains_rep_adjust():
    state, policy = _in_rep_adjust()
    state, events = advance(state, 240.0, policy)  # one improved session
    assert state["currentStrategy"] == "REP_ADJUST"
    assert state["consecutiveImprovementSessions"] == 1
    assert events == []


def test_rep_adjust_resets_to_normal_after_consecutive_improvements():
    state, policy = _in_rep_adjust()
    state, ev1 = advance(state, 240.0, policy)  # improvement #1
    state, ev2 = advance(state, 250.0, policy)  # improvement #2 -> reset
    assert state["currentStrategy"] == "NORMAL"
    assert event_types(ev2) == ["PROGRESS_RESUMED"]
    assert state["consecutiveImprovementSessions"] == 0
    assert state["consecutiveStallSessions"] == 0


def test_rep_adjust_non_consecutive_improvements_do_not_accumulate():
    state, policy = _in_rep_adjust()
    state, _ = advance(state, 240.0, policy)  # improved
    state, _ = advance(state, 240.0, policy)  # stall (flat vs. 240) - breaks the streak
    state, events = advance(state, 250.0, policy)  # improved again
    assert state["currentStrategy"] == "REP_ADJUST"
    assert state["consecutiveImprovementSessions"] == 1
    assert events == []


def test_rep_adjust_continued_stall_escalates_to_reverse():
    state, policy = _in_rep_adjust()
    state, ev1 = advance(state, 234.0, policy)  # stall #1 in REP_ADJUST
    assert state["currentStrategy"] == "REP_ADJUST"
    state, ev2 = advance(state, 234.0, policy)  # stall #2 -> escalate
    assert state["currentStrategy"] == "REVERSE"
    assert event_types(ev2) == ["REVERSE_STARTED"]
    assert state["consecutiveStallSessions"] == 0


def test_rep_adjust_improve_then_stall_does_not_prematurely_escalate():
    # An improved session followed by one stall must NOT count as 2 consecutive
    # stalls - only a genuine second stall should push into REVERSE.
    state, policy = _in_rep_adjust()
    state, _ = advance(state, 240.0, policy)  # improved (breaks any stall streak)
    state, events = advance(state, 240.0, policy)  # single stall vs. 240
    assert state["currentStrategy"] == "REP_ADJUST"
    assert events == []


# -- REVERSE behavior --------------------------------------------------------------


def _in_reverse():
    state, policy = _in_rep_adjust()
    state, _ = advance(state, 234.0, policy)  # stall #1
    state, _ = advance(state, 234.0, policy)  # stall #2 -> REVERSE
    assert state["currentStrategy"] == "REVERSE"
    return state, policy


def test_reverse_single_stall_remains_reverse():
    state, policy = _in_reverse()
    state, events = advance(state, 234.0, policy)
    assert state["currentStrategy"] == "REVERSE"
    assert events == []


def test_reverse_single_improvement_remains_reverse():
    state, policy = _in_reverse()
    state, events = advance(state, 250.0, policy)
    assert state["currentStrategy"] == "REVERSE"
    assert state["consecutiveImprovementSessions"] == 1
    assert events == []


def test_reverse_continued_stall_escalates_to_swapped():
    state, policy = _in_reverse()
    state, _ = advance(state, 234.0, policy)  # stall #1
    state, events = advance(state, 234.0, policy)  # stall #2 -> SWAPPED
    assert state["currentStrategy"] == "SWAPPED"
    assert event_types(events) == ["EXERCISE_SWAPPED"]


def test_reverse_resets_to_normal_after_consecutive_improvements():
    state, policy = _in_reverse()
    state, _ = advance(state, 250.0, policy)  # improvement #1
    state, events = advance(state, 260.0, policy)  # improvement #2 -> reset
    assert state["currentStrategy"] == "NORMAL"
    assert event_types(events) == ["PROGRESS_RESUMED"]


# -- SWAPPED behavior ---------------------------------------------------------------


def _in_swapped():
    state, policy = _in_reverse()
    state, _ = advance(state, 234.0, policy)  # stall #1
    state, _ = advance(state, 234.0, policy)  # stall #2 -> SWAPPED
    assert state["currentStrategy"] == "SWAPPED"
    return state, policy


def test_swapped_stays_swapped_under_continued_stalls():
    state, policy = _in_swapped()
    for _ in range(5):
        state, events = advance(state, 234.0, policy)
        assert state["currentStrategy"] == "SWAPPED"
        assert events == []


def test_swapped_resets_to_normal_after_consecutive_improvements():
    state, policy = _in_swapped()
    state, _ = advance(state, 250.0, policy)  # improvement #1
    state, events = advance(state, 260.0, policy)  # improvement #2 -> reset
    assert state["currentStrategy"] == "NORMAL"
    assert event_types(events) == ["PROGRESS_RESUMED"]


# -- custom policy tuning -----------------------------------------------------------


def test_custom_policy_resets_after_a_single_improvement():
    policy = ProgressionPolicy(improvements_before_reset=1)
    state, _ = _in_rep_adjust()
    # replay with the custom policy from a fresh REP_ADJUST state built under the default policy;
    # only the reset threshold changes, so one improvement should now be enough.
    state, events = advance(state, 240.0, policy)
    assert state["currentStrategy"] == "NORMAL"
    assert event_types(events) == ["PROGRESS_RESUMED"]


def test_custom_policy_escalates_after_a_single_stall():
    policy = ProgressionPolicy(rep_adjust_sessions=1)
    state, _ = _in_rep_adjust()
    state, events = advance(state, 234.0, policy)
    assert state["currentStrategy"] == "REVERSE"
    assert event_types(events) == ["REVERSE_STARTED"]


# -- re-plateau after resuming ------------------------------------------------------


def test_can_re_plateau_after_resuming_normal_progression():
    state, policy = _in_rep_adjust()
    state, _ = advance(state, 240.0, policy)  # improvement #1
    state, resume_events = advance(state, 250.0, policy)  # improvement #2 -> NORMAL
    assert state["currentStrategy"] == "NORMAL"
    assert event_types(resume_events) == ["PROGRESS_RESUMED"]

    # now stall out again from the new baseline (250) and confirm it can re-trigger
    state, _ = advance(state, 250.0, policy)  # stall #1
    state, events = advance(state, 250.0, policy)  # stall #2 -> plateau again
    assert state["currentStrategy"] == "REP_ADJUST"
    assert event_types(events) == ["PLATEAU_DETECTED", "REP_ADJUST_STARTED"]


def test_full_cascade_normal_to_swapped_event_order():
    # 3 flat sessions -> REP_ADJUST, 2 more flat -> REVERSE, 2 more flat -> SWAPPED.
    state, events = run_sequence([234.0] * 7)
    assert state["currentStrategy"] == "SWAPPED"
    assert event_types(events) == [
        "PLATEAU_DETECTED",
        "REP_ADJUST_STARTED",
        "REVERSE_STARTED",
        "EXERCISE_SWAPPED",
    ]
