"""docs/ML_SPEC.md §4 - two paths: the trained model when heart-rate data is
available, a MET-intensity-category fallback (§4's redesign - not a per-exercise
table) otherwise, which is what actually runs for most users. No pandas import
here on purpose - training deps stay out of the serving path (§7)."""

from __future__ import annotations

from typing import Dict, Optional

from .model_registry import get_model

WORKOUT_TYPES = ["Cardio", "Strength", "HIIT", "Yoga"]

# MET values per intensity category, inferred from session structure (set density),
# not from which exercises made it up - docs/ML_SPEC.md §4's explicit reasoning.
MET_INTENSITY_TABLE = {
    "resistance_training_light": 3.5,
    "resistance_training_moderate": 5.0,
    "resistance_training_vigorous": 6.5,
    "circuit_training": 8.0,
}


def _encode(duration_hours: float, avg_bpm: float, weight_kg: float, workout_type: str, feature_names) -> list:
    values = {"session_duration_hours": duration_hours, "avg_bpm": avg_bpm, "weight_kg": weight_kg}
    for wt in WORKOUT_TYPES:
        values[f"workout_{wt}"] = 1.0 if workout_type == wt else 0.0
    return [values.get(name, 0.0) for name in feature_names]


def estimate(duration_hours: float, avg_bpm: Optional[float], weight_kg: float, workout_type: str, total_sets: int = 0) -> Dict:
    """Model path when avg_bpm is available; falls back to MET automatically if
    there's no heart rate, or if the model artifact isn't loaded for any reason."""
    if avg_bpm is None:
        return estimate_met(duration_hours, weight_kg, total_sets)

    artifact = get_model("calorie")
    if artifact is None:
        return estimate_met(duration_hours, weight_kg, total_sets)

    model = artifact["model"]
    feature_names = artifact["feature_names"]
    x = _encode(duration_hours, avg_bpm, weight_kg, workout_type, feature_names)
    calories = float(model.predict([x])[0])
    return {
        "estimatedCalories": round(calories, 1),
        "method": "model",
        "modelVersion": artifact.get("modelVersion"),
    }


def estimate_met(duration_hours: float, weight_kg: float, total_sets: int) -> Dict:
    """Classifies session intensity from work-set density (sets / duration), not
    per-exercise MET values - see docs/ML_SPEC.md §4 for why."""
    density = (total_sets / duration_hours) if duration_hours > 0 else 0.0
    if density >= 12:
        category = "circuit_training"
    elif density >= 8:
        category = "resistance_training_vigorous"
    elif density >= 4:
        category = "resistance_training_moderate"
    else:
        category = "resistance_training_light"

    met = MET_INTENSITY_TABLE[category]
    calories = met * weight_kg * duration_hours
    return {
        "estimatedCalories": round(calories, 1),
        "method": "met",
        "intensityCategory": category,
    }
