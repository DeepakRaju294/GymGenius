"""Loads the Gym Members Exercise Dataset (docs/ML_SPEC.md §4) for the calorie
model benchmark. Falls back to a labeled-synthetic sample shaped like the real
dataset's known schema when the real CSV isn't present yet (ml/training/datasets/
is gitignored - nothing here is committed, real or synthetic), so the training/
comparison pipeline can be built and tested before Kaggle access is set up.

Real dataset: https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset
Expected columns once downloaded: Age, Gender, Weight (kg), Height (m), Max_BPM,
Avg_BPM, Resting_BPM, Session_Duration (hours), Workout_Type, Calories_Burned.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "gym_members_exercise.csv"
WORKOUT_TYPES = ["Cardio", "Strength", "HIIT", "Yoga"]

RAW_TO_CANONICAL = {
    "Age": "age",
    "Gender": "gender",
    "Weight (kg)": "weight_kg",
    "Height (m)": "height_m",
    "Max_BPM": "max_bpm",
    "Avg_BPM": "avg_bpm",
    "Resting_BPM": "resting_bpm",
    "Session_Duration (hours)": "session_duration_hours",
    "Workout_Type": "workout_type",
    "Calories_Burned": "calories_burned",
}


def _make_synthetic(n: int = 973, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(18, 66, n)
    gender = rng.choice(["Male", "Female"], n)
    weight_kg = rng.normal(75, 15, n).clip(45, 140)
    height_m = rng.normal(1.72, 0.1, n).clip(1.5, 2.05)
    resting_bpm = rng.normal(65, 8, n).clip(45, 90)
    avg_bpm = (resting_bpm + rng.normal(70, 20, n)).clip(90, 190)
    max_bpm = (avg_bpm + rng.normal(20, 8, n)).clip(120, 205)
    session_duration_hours = rng.normal(0.9, 0.35, n).clip(0.2, 2.2)
    workout_type = rng.choice(WORKOUT_TYPES, n)

    # A real-ish signal (roughly MET-shaped: duration * intensity * bodyweight),
    # not pure noise, so the sklearn/PyTorch comparison in train_calorie_model*.py
    # is measuring something real rather than both models fitting random labels.
    intensity_factor = {"Cardio": 8.5, "HIIT": 10.5, "Strength": 6.0, "Yoga": 3.0}
    intensity = np.array([intensity_factor[w] for w in workout_type])
    bpm_factor = 0.5 + (avg_bpm - 90) / 100.0
    calories_burned = (
        session_duration_hours * 60 * intensity * bpm_factor * (weight_kg / 70.0)
        + rng.normal(0, 25, n)
    ).clip(50, None)

    df = pd.DataFrame(
        {
            "age": age,
            "gender": gender,
            "weight_kg": weight_kg,
            "height_m": height_m,
            "max_bpm": max_bpm,
            "avg_bpm": avg_bpm,
            "resting_bpm": resting_bpm,
            "session_duration_hours": session_duration_hours,
            "workout_type": workout_type,
            "calories_burned": calories_burned,
        }
    )
    return df


def load_dataset() -> Tuple[pd.DataFrame, bool]:
    """Returns (dataframe, is_synthetic). Reads the real CSV if present, else
    generates a labeled-synthetic sample - callers must not present synthetic
    results as if they were trained on real data (see eval report `dataSource`)."""
    if DATASET_PATH.exists():
        raw = pd.read_csv(DATASET_PATH)
        raw = raw.rename(columns=RAW_TO_CANONICAL)
        return raw, False
    return _make_synthetic(), True


if __name__ == "__main__":
    df, synthetic = load_dataset()
    print(f"Loaded {len(df)} rows (synthetic={synthetic})")
    print(df.describe(include="all"))
