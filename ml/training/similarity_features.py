"""docs/ML_SPEC.md §2 - pure feature-vector construction for exercise similarity,
separated from build_exercise_similarity_index.py's Mongo I/O so this is testable
with synthetic exercise dicts, same pattern as calorie_features.py."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

MECHANICS = ["compound", "isolation"]
UTILITY = ["basic", "auxiliary"]


def build_feature_matrix(exercises: List[Dict]) -> Tuple[np.ndarray, List[str], List[str]]:
    """Returns (X, exerciseIds, featureNames). One row per exercise. movementPattern
    is deliberately NOT one-hot-encoded into this matrix - similarity.py buckets
    on exact movementPattern match first (docs/ML_SPEC.md §2: "rank the survivors
    by movementPattern match first, then ... similarity"), so it's a hard bucket
    boundary, not one more cosine-similarity feature that a lot of shared muscles/
    equipment could outweigh."""
    all_muscles = sorted({ex.get("primaryMuscle") for ex in exercises if ex.get("primaryMuscle")})
    all_secondary = sorted({m for ex in exercises for m in (ex.get("secondaryMuscles") or [])})
    all_equipment = sorted({e for ex in exercises for e in (ex.get("equipment") or [])})

    feature_names = (
        [f"primary_{m}" for m in all_muscles]
        + [f"secondary_{m}" for m in all_secondary]
        + [f"equipment_{e}" for e in all_equipment]
        + [f"mechanics_{m}" for m in MECHANICS]
        + [f"utility_{u}" for u in UTILITY]
    )

    rows = []
    exercise_ids = []
    for ex in exercises:
        vec = np.zeros(len(feature_names), dtype=np.float32)
        primary = ex.get("primaryMuscle")
        if primary and f"primary_{primary}" in feature_names:
            vec[feature_names.index(f"primary_{primary}")] = 1.0
        for m in ex.get("secondaryMuscles") or []:
            if f"secondary_{m}" in feature_names:
                vec[feature_names.index(f"secondary_{m}")] = 0.5  # weaker signal than primary
        for e in ex.get("equipment") or []:
            if f"equipment_{e}" in feature_names:
                vec[feature_names.index(f"equipment_{e}")] = 1.0
        if ex.get("mechanics") in MECHANICS:
            vec[feature_names.index(f"mechanics_{ex['mechanics']}")] = 1.0
        if ex.get("utility") in UTILITY:
            vec[feature_names.index(f"utility_{ex['utility']}")] = 1.0
        rows.append(vec)
        exercise_ids.append(ex["exerciseId"])

    X = np.vstack(rows) if rows else np.zeros((0, len(feature_names)), dtype=np.float32)
    return X, exercise_ids, feature_names
