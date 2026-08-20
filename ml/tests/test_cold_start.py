"""Tests for app.services.ml.cold_start (docs/ML_SPEC.md §3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ml.cold_start import assess_direct, starting_range_for, transfer_weight  # noqa: E402


def test_assess_direct_empty_when_nothing_answered():
    assert assess_direct() == {}


def test_assess_direct_anchor_performance_beats_pushup_proxy():
    result = assess_direct(push_ups_per_set=5, bench_press_known_weight_lb=135, bench_press_known_reps=8)
    assert result["upper_push"]["source"] == "anchor_performance"
    assert result["upper_push"]["confidence"] > 0.6  # anchor is higher-confidence than the proxy question


def test_assess_direct_pushup_proxy_used_when_no_anchor():
    result = assess_direct(push_ups_per_set=20)
    assert result["upper_push"]["source"] == "onboarding_question"
    assert result["upper_push"]["tier"] == "intermediate"


def test_assess_direct_low_pushups_beginner_tier():
    result = assess_direct(push_ups_per_set=3)
    assert result["upper_push"]["tier"] == "beginner"


def test_assess_direct_high_pushups_advanced_tier():
    result = assess_direct(push_ups_per_set=40)
    assert result["upper_push"]["tier"] == "advanced"


def test_assess_direct_squat_comfort_mapped():
    assert assess_direct(squat_comfort="loaded")["squat"]["tier"] == "intermediate"
    assert assess_direct(squat_comfort="none")["squat"]["tier"] == "beginner"


def test_assess_direct_only_answered_families_present():
    result = assess_direct(squat_comfort="loaded")
    assert "squat" in result
    assert "upper_push" not in result
    assert "hinge" not in result


def test_starting_range_dumbbell_fixed():
    r = starting_range_for("horizontal_push", "dumbbell", "beginner", bodyweight_kg=None)
    assert r is not None
    assert 5 <= r["weightLb"] <= 15


def test_starting_range_barbell_needs_bodyweight():
    assert starting_range_for("horizontal_push", "barbell", "beginner", bodyweight_kg=None) is None
    r = starting_range_for("horizontal_push", "barbell", "beginner", bodyweight_kg=80)
    assert r is not None
    assert r["weightLb"] > 0


def test_starting_range_machine_never_predicted():
    assert starting_range_for("horizontal_push", "machine", "beginner", bodyweight_kg=80) is None


def test_starting_range_unknown_pattern():
    assert starting_range_for("not_a_real_pattern", "dumbbell", "beginner", bodyweight_kg=80) is None


def test_transfer_weight_same_equipment_passthrough():
    assert transfer_weight("horizontal_push", "barbell", "barbell", 135) == 135


def test_transfer_weight_barbell_to_dumbbell():
    result = transfer_weight("horizontal_push", "barbell", "dumbbell_per_hand", 135)
    assert result is not None
    assert result < 135  # per-hand dumbbell weight should be well below the barbell total


def test_transfer_weight_unknown_pair_returns_none():
    assert transfer_weight("horizontal_push", "resistance_band", "chain", 50) is None
