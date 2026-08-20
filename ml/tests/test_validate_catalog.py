"""Tests for ml/training/validate_catalog.py (docs/ML_SPEC.md §1 step 6)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from validate_catalog import validate  # noqa: E402


def _valid_row(**overrides):
    row = {
        "exerciseId": "bench_press",
        "name": "Bench Press",
        "primaryMuscle": "chest",
        "equipment": ["barbell"],
        "movementPattern": "horizontal_push",
        "secondaryMovementPatterns": [],
        "mechanics": "compound",
        "utility": "basic",
        "isSelectable": True,
        "source": "test_source",
    }
    row.update(overrides)
    return row


def test_valid_catalog_passes():
    result = validate([_valid_row()], known_sources=["test_source"])
    assert result.ok
    assert result.errors == []


def test_missing_primary_muscle_fails_when_selectable():
    result = validate([_valid_row(primaryMuscle=None)])
    assert not result.ok
    assert any("primaryMuscle" in e for e in result.errors)


def test_missing_primary_muscle_ok_when_not_selectable():
    result = validate([_valid_row(primaryMuscle=None, isSelectable=False)])
    assert result.ok


def test_missing_equipment_fails():
    result = validate([_valid_row(equipment=[])])
    assert not result.ok
    assert any("equipment" in e for e in result.errors)


def test_missing_movement_pattern_fails():
    result = validate([_valid_row(movementPattern=None)])
    assert not result.ok
    assert any("movementPattern" in e for e in result.errors)


def test_invalid_movement_pattern_enum_fails():
    result = validate([_valid_row(movementPattern="not_a_real_pattern")])
    assert not result.ok
    assert any("invalid movementPattern" in e for e in result.errors)


def test_invalid_mechanics_enum_fails():
    result = validate([_valid_row(mechanics="sort-of-compound")])
    assert not result.ok


def test_duplicate_selectable_names_fail():
    rows = [_valid_row(exerciseId="a", name="Bench Press"), _valid_row(exerciseId="b", name="Bench Press")]
    result = validate(rows)
    assert not result.ok
    assert any("duplicate canonical name" in e for e in result.errors)


def test_gif_url_reused_across_exercises_fails():
    rows = [
        _valid_row(exerciseId="a", name="Bench Press", gifUrl="http://x/bench.gif"),
        _valid_row(exerciseId="b", name="Squat", primaryMuscle="quads", movementPattern="squat", gifUrl="http://x/bench.gif"),
    ]
    result = validate(rows)
    assert not result.ok
    assert any("gifUrl" in e for e in result.errors)


def test_unknown_source_fails():
    result = validate([_valid_row(source="a_dataset_never_ingested")], known_sources=["test_source"])
    assert not result.ok
    assert any("does not reference an ingested dataset" in e for e in result.errors)


def test_stats_report_selectable_yield():
    rows = [_valid_row(exerciseId="a", name="A"), _valid_row(exerciseId="b", name="B", isSelectable=False, primaryMuscle=None)]
    result = validate(rows)
    assert result.stats["totalRows"] == 2
    assert result.stats["selectableRows"] == 1
    assert result.stats["selectableYield"] == 0.5
