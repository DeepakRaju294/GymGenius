"""Tests for ml/training/dedup.py - the two-stage catalog dedup (docs/ML_SPEC.md
§1 step 3). Operates on canonical rows directly, no CSV/dataset dependency."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))

from dedup import find_duplicate_groups, merge_group  # noqa: E402


def _row(name, primaryMuscle="chest", equipment=None, movementPattern="horizontal_push", **kw):
    return {
        "name": name,
        "primaryMuscle": primaryMuscle,
        "equipment": equipment or ["dumbbell"],
        "movementPattern": movementPattern,
        "secondaryMuscles": [],
        "sourceDataset": kw.pop("sourceDataset", "test_source"),
        **kw,
    }


def test_near_duplicate_names_same_structure_auto_merge():
    rows = [_row("Dumbbell Bench Press"), _row("DB Bench Press")]
    groups, review = find_duplicate_groups(rows)
    assert len(groups) == 1
    assert set(groups[0]) == {0, 1}
    assert review[0]["decision"] == "AUTO_MERGE"


def test_similar_names_different_muscle_go_to_review():
    rows = [
        _row("Incline Bench Press", primaryMuscle="chest"),
        _row("Incline Row", primaryMuscle="back"),
    ]
    groups, review = find_duplicate_groups(rows)
    # Different muscle -> not merged, and if similar enough to be a candidate at
    # all it should be flagged CONFLICTING_PRIMARY_MUSCLE, not silently dropped.
    assert len(groups) == 2
    if review:
        assert review[0]["decision"] == "REVIEW"
        assert review[0]["reason"] == "CONFLICTING_PRIMARY_MUSCLE"


def test_dissimilar_names_kept_separate_no_review_entry():
    rows = [_row("Dumbbell Bench Press"), _row("Barbell Back Squat", primaryMuscle="quads", movementPattern="squat")]
    groups, review = find_duplicate_groups(rows)
    assert len(groups) == 2
    assert review == []


def test_unknown_movement_pattern_goes_to_review_not_kept_separate():
    rows = [
        _row("Cable Fly Variation A", movementPattern=None),
        _row("Cable Fly Variation B", movementPattern=None),
    ]
    groups, review = find_duplicate_groups(rows)
    if review:
        assert review[0]["reason"] == "UNKNOWN_MOVEMENT_PATTERN"


def test_merge_group_unions_equipment_and_secondary_muscles():
    rows = [
        _row("Dumbbell Bench Press", equipment=["dumbbell"], secondaryMuscles=["triceps"]),
        _row("DB Bench Press", equipment=["bench"], secondaryMuscles=["shoulders"]),
    ]
    merged = merge_group(rows, [0, 1])
    assert set(merged["equipment"]) == {"dumbbell", "bench"}
    assert set(merged["secondaryMuscles"]) == {"triceps", "shoulders"}


def test_merge_group_combines_source_provenance():
    rows = [
        _row("Dumbbell Bench Press", sourceDataset="source_a"),
        _row("DB Bench Press", sourceDataset="source_b"),
    ]
    merged = merge_group(rows, [0, 1])
    assert "source_a" in merged["source"]
    assert "source_b" in merged["source"]


def test_merge_group_fills_gaps_from_later_duplicate():
    rows = [
        _row("Dumbbell Bench Press", gifUrl=None),
        _row("DB Bench Press", gifUrl="http://example.com/db_bench.gif"),
    ]
    merged = merge_group(rows, [0, 1])
    assert merged["gifUrl"] == "http://example.com/db_bench.gif"


def test_single_row_no_duplicates():
    rows = [_row("Unique Exercise")]
    groups, review = find_duplicate_groups(rows)
    assert groups == [[0]]
    assert review == []


def test_empty_rows():
    groups, review = find_duplicate_groups([])
    assert groups == []
    assert review == []
