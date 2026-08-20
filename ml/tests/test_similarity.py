"""Tests for the exercise-similarity pipeline (docs/ML_SPEC.md §2):
similarity_features.build_feature_matrix (pure) and
app.services.ml.similarity.rank_by_similarity (uses a fitted in-memory index,
no Mongo/joblib file needed)."""

import sys
from contextlib import contextmanager
from pathlib import Path

from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from similarity_features import build_feature_matrix  # noqa: E402
import app.services.ml.similarity as sim_module  # noqa: E402


def _exercise(exerciseId, primaryMuscle, equipment, movementPattern, **kw):
    return {
        "exerciseId": exerciseId,
        "primaryMuscle": primaryMuscle,
        "secondaryMuscles": kw.get("secondaryMuscles", []),
        "equipment": equipment,
        "mechanics": kw.get("mechanics"),
        "utility": kw.get("utility"),
        "movementPattern": movementPattern,
    }


CATALOG = [
    _exercise("bench_press", "chest", ["barbell"], "horizontal_push", mechanics="compound", utility="basic"),
    _exercise("db_bench_press", "chest", ["dumbbell"], "horizontal_push", mechanics="compound", utility="basic"),
    _exercise("chest_fly", "chest", ["dumbbell"], "horizontal_push", mechanics="isolation", utility="auxiliary"),
    _exercise("overhead_press", "shoulders", ["barbell"], "vertical_push", mechanics="compound", utility="basic"),
    _exercise("squat", "quads", ["barbell"], "squat", mechanics="compound", utility="basic"),
]


def _build_artifact():
    X, exercise_ids, feature_names = build_feature_matrix(CATALOG)
    index = NearestNeighbors(n_neighbors=len(CATALOG), metric="cosine").fit(X)
    return {
        "index": index,
        "features": X,
        "exerciseIds": exercise_ids,
        "movementPatterns": {ex["exerciseId"]: ex["movementPattern"] for ex in CATALOG},
        "primaryMuscles": {ex["exerciseId"]: ex["primaryMuscle"] for ex in CATALOG},
        "featureNames": feature_names,
        "modelVersion": "test-0.0.1",
    }


@contextmanager
def _patched_model(artifact):
    original = sim_module.get_model
    sim_module.get_model = lambda name: artifact
    try:
        yield
    finally:
        sim_module.get_model = original


def test_build_feature_matrix_shape():
    X, exercise_ids, feature_names = build_feature_matrix(CATALOG)
    assert X.shape[0] == len(CATALOG)
    assert exercise_ids == [ex["exerciseId"] for ex in CATALOG]
    assert X.shape[1] == len(feature_names)


def test_build_feature_matrix_empty():
    X, exercise_ids, feature_names = build_feature_matrix([])
    assert X.shape[0] == 0
    assert exercise_ids == []


def test_rank_by_similarity_prefers_same_movement_pattern():
    with _patched_model(_build_artifact()):
        # bench_press's real candidates: db_bench_press/chest_fly (horizontal_push)
        # vs. overhead_press (vertical_push) and squat (squat) - same pattern
        # should rank first regardless of which is a closer feature match.
        ranked = sim_module.rank_by_similarity("bench_press", ["db_bench_press", "chest_fly", "overhead_press", "squat"], k=4)
    assert set(ranked[:2]) == {"db_bench_press", "chest_fly"}
    assert set(ranked[2:]) == {"overhead_press", "squat"}


def test_rank_by_similarity_excludes_self():
    with _patched_model(_build_artifact()):
        ranked = sim_module.rank_by_similarity("bench_press", ["bench_press", "db_bench_press"], k=5)
    assert "bench_press" not in ranked


def test_rank_by_similarity_respects_candidate_pool_only():
    """Even though chest_fly is a great match for bench_press, if it's not in
    the caller's already-hard-filtered candidate pool, it must never appear -
    ranking only reorders what Selection already allowed through."""
    with _patched_model(_build_artifact()):
        ranked = sim_module.rank_by_similarity("bench_press", ["overhead_press"], k=5)
    assert ranked == ["overhead_press"]
    assert "chest_fly" not in ranked


def test_rank_by_similarity_falls_back_when_model_missing():
    with _patched_model(None):
        ranked = sim_module.rank_by_similarity("bench_press", ["db_bench_press", "chest_fly"], k=5)
    assert ranked == ["db_bench_press", "chest_fly"]  # passthrough, caller's own order preserved


def test_rank_by_similarity_unknown_exercise_falls_back():
    with _patched_model(_build_artifact()):
        ranked = sim_module.rank_by_similarity("never_seen_exercise", ["db_bench_press"], k=5)
    assert ranked == ["db_bench_press"]
