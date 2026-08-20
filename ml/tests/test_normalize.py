"""Tests for ml/training/normalize.py - the rule-based movementPattern/equipment/
muscle normalization used during catalog ingestion (docs/ML_SPEC.md §1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from normalize import assign_movement_pattern, normalize_equipment, normalize_muscle  # noqa: E402


def test_normalize_equipment_synonym():
    assert normalize_equipment("DB") == "dumbbell"
    assert normalize_equipment("Olympic Bar") == "barbell"


def test_normalize_equipment_unknown_passthrough():
    assert normalize_equipment("Resistance Band") == "resistance band"


def test_normalize_muscle_synonym():
    assert normalize_muscle("Pecs") == "chest"
    assert normalize_muscle("Latissimus Dorsi") == "lats"


def test_movement_pattern_horizontal_push():
    pattern, source, secondary = assign_movement_pattern("Barbell Bench Press")
    assert pattern == "horizontal_push"
    assert source == "rule"
    assert secondary == []


def test_movement_pattern_vertical_push_not_confused_with_horizontal():
    pattern, _, _ = assign_movement_pattern("Standing Overhead Press")
    assert pattern == "vertical_push"


def test_movement_pattern_squat():
    pattern, _, _ = assign_movement_pattern("Barbell Back Squat")
    assert pattern == "squat"


def test_movement_pattern_hinge():
    pattern, _, _ = assign_movement_pattern("Romanian Deadlift")
    assert pattern == "hinge"


def test_movement_pattern_hybrid_thruster():
    pattern, source, secondary = assign_movement_pattern("Barbell Thruster")
    assert pattern == "squat"
    assert source == "rule"
    assert "vertical_push" in secondary


def test_movement_pattern_hybrid_clean_and_press():
    pattern, _, secondary = assign_movement_pattern("Dumbbell Clean and Press")
    assert pattern == "hinge"
    assert "vertical_push" in secondary


def test_movement_pattern_unknown_falls_to_manual():
    pattern, source, secondary = assign_movement_pattern("Some Completely Novel Exercise Name")
    assert pattern is None
    assert source == "manual"
    assert secondary == []


def test_movement_pattern_empty_name():
    pattern, source, _ = assign_movement_pattern("")
    assert pattern is None
    assert source == "manual"
