"""Tests for the evidence-priority hierarchy in
app.services.prescription.progression.apply_progression (docs/ML_SPEC.md §3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.prescription.progression import apply_progression  # noqa: E402


def _history_entry(exercise_id, weight, reps, workout_date="2026-01-01"):
    from datetime import datetime

    return {
        "workoutDate": datetime.fromisoformat(workout_date),
        "exercises": [{"exerciseId": exercise_id, "sets": [{"weight": weight, "reps": reps}]}],
    }


CATALOG = {
    "bench_press": {"exerciseId": "bench_press", "primaryMuscle": "chest", "movementPattern": "horizontal_push", "equipment": ["barbell"]},
    "db_bench_press": {"exerciseId": "db_bench_press", "primaryMuscle": "chest", "movementPattern": "horizontal_push", "equipment": ["dumbbell"]},
}


def test_tier1_recent_history_wins_over_everything_else():
    history = [_history_entry("bench_press", 135, 5)]
    result = apply_progression(
        "bench_press", "chest", history, movement_pattern="horizontal_push", equipment=["barbell"], catalog=CATALOG
    )
    assert result is not None
    weight, tier = result
    assert tier == "recent_history"
    assert weight == 137.5  # 135 + 2.5 upper-body increment


def test_tier2_related_exercise_history_via_transfer():
    # No history for bench_press itself, but DB bench press has been logged.
    history = [_history_entry("db_bench_press", 40, 8)]
    result = apply_progression(
        "bench_press", "chest", history, movement_pattern="horizontal_push", equipment=["barbell"], catalog=CATALOG
    )
    assert result is not None
    weight, tier = result
    assert tier == "related_exercise_history"
    assert weight > 40  # barbell total should be well above a single dumbbell's per-hand weight


def test_tier3_anchor_performance_used_when_no_history():
    fitness_assessment = {
        "predictedByFamily": {
            "upper_push": {
                "tier": "intermediate",
                "source": "anchor_performance",
                "anchorEquipment": "barbell",
                "anchorWeightLb": 135,
                "anchorReps": 8,
            }
        }
    }
    result = apply_progression(
        "bench_press",
        "chest",
        [],
        movement_pattern="horizontal_push",
        equipment=["barbell"],
        catalog=CATALOG,
        fitness_assessment=fitness_assessment,
    )
    assert result is not None
    weight, tier = result
    assert tier == "anchor_performance"
    assert weight == 135  # same equipment as anchor - transfer is a passthrough


def test_tier5_population_range_when_nothing_else_known():
    result = apply_progression(
        "bench_press", "chest", [], movement_pattern="horizontal_push", equipment=["dumbbell"], catalog=CATALOG, bodyweight_kg=None
    )
    assert result is not None
    weight, tier = result
    assert tier == "population_range"
    assert 5 <= weight <= 15  # dumbbell beginner range


def test_tier5_machine_never_predicted_falls_to_tier6():
    result = apply_progression(
        "bench_press", "chest", [], movement_pattern="horizontal_push", equipment=["machine"], catalog=CATALOG
    )
    assert result is None


def test_tier6_nothing_available_returns_none():
    result = apply_progression("bench_press", "chest", [], movement_pattern=None, equipment=None, catalog=None)
    assert result is None


def test_evidence_priority_order_tier1_beats_tier2_and_tier3():
    # Both recent history AND an anchor exist - tier 1 must still win.
    history = [_history_entry("bench_press", 100, 5)]
    fitness_assessment = {
        "predictedByFamily": {
            "upper_push": {"source": "anchor_performance", "anchorEquipment": "barbell", "anchorWeightLb": 200, "anchorReps": 5}
        }
    }
    result = apply_progression(
        "bench_press",
        "chest",
        history,
        movement_pattern="horizontal_push",
        equipment=["barbell"],
        catalog=CATALOG,
        fitness_assessment=fitness_assessment,
    )
    weight, tier = result
    assert tier == "recent_history"
    assert weight == 102.5  # from the logged 100, not the anchor's 200
