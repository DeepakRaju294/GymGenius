"""Shared feature engineering for both calorie models (docs/ML_SPEC.md §4) - kept
in one place so the sklearn and PyTorch trainers see identical inputs and the
benchmark comparison is actually apples-to-apples."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["session_duration_hours", "avg_bpm", "weight_kg", "workout_type"]
TARGET_COLUMN = "calories_burned"
WORKOUT_TYPES = ["Cardio", "Strength", "HIIT", "Yoga"]


def build_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
    """One-hot encodes workout_type, returns (X, y, feature_names)."""
    workout_dummies = pd.get_dummies(
        pd.Categorical(df["workout_type"], categories=WORKOUT_TYPES), prefix="workout"
    )
    numeric = df[["session_duration_hours", "avg_bpm", "weight_kg"]].reset_index(drop=True)
    X_df = pd.concat([numeric, workout_dummies.reset_index(drop=True)], axis=1)
    X = X_df.to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMN].to_numpy(dtype=np.float32)
    return X, y, list(X_df.columns)
