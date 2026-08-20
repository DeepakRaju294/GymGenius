"""docs/ML_SPEC.md §3 - cold-start strength estimator. The "Direct" path (short
onboarding questions -> a per-movement-family tier) is rule-based and needs no
training data, so it's built now; the "Model-assisted" path
(HistGradientBoostingClassifier filling gaps from the Gym Members Exercise
Dataset) is blocked on real Kaggle data and stays unbuilt - see
ml/training/train_cold_start_estimator.py's absence, tracked in
docs/ML_SPEC.md §9."""

from __future__ import annotations

from typing import Dict, Optional

from app.utils.artifacts import load_json

FAMILIES = ("upper_push", "upper_pull", "squat", "hinge")
TIERS = ("beginner", "intermediate", "advanced")

# Maps a movementPattern (docs/ML_SPEC.md §1's taxonomy) to the coarser strength
# family the cold-start onboarding questions actually ask about.
PATTERN_TO_FAMILY = {
    "horizontal_push": "upper_push",
    "vertical_push": "upper_push",
    "horizontal_pull": "upper_pull",
    "vertical_pull": "upper_pull",
    "squat": "squat",
    "lunge": "squat",
    "hinge": "hinge",
}


def assess_direct(
    push_ups_per_set: Optional[int] = None,
    bench_press_known_weight_lb: Optional[float] = None,
    bench_press_known_reps: Optional[int] = None,
    squat_comfort: Optional[str] = None,  # "none" | "bodyweight" | "loaded"
) -> Dict[str, Dict]:
    """docs/ML_SPEC.md §3's "Direct" evidence tier: a handful of short onboarding
    questions with real signal, no model. Only answered questions produce a
    prediction - an unanswered family is simply absent from the result, left for
    tier 4 (model, not yet available) or tier 5 (population range) to fill in."""
    result: Dict[str, Dict] = {}

    if bench_press_known_weight_lb is not None and bench_press_known_reps:
        # Direct anchor performance beats a push-up-count proxy when both are given.
        est_1rm = bench_press_known_weight_lb * (1 + bench_press_known_reps / 30.0)
        tier = "advanced" if est_1rm >= 185 else "intermediate" if est_1rm >= 115 else "beginner"
        result["upper_push"] = {
            "tier": tier,
            "source": "anchor_performance",
            "confidence": 0.85,
            "evidence": [f"bench_press_{bench_press_known_weight_lb:g}x{bench_press_known_reps}"],
            # Raw fields (not just the display string above) so apply_progression's
            # tier 3 can use this as an actual weight anchor, not merely a tier label -
            # the anchor is assumed given for the family's most common free-weight
            # equipment (barbell for upper_push here).
            "anchorExerciseId": "bench_press",
            "anchorEquipment": "barbell",
            "anchorWeightLb": bench_press_known_weight_lb,
            "anchorReps": bench_press_known_reps,
        }
    elif push_ups_per_set is not None:
        tier = "advanced" if push_ups_per_set >= 30 else "intermediate" if push_ups_per_set >= 12 else "beginner"
        result["upper_push"] = {
            "tier": tier,
            "source": "onboarding_question",
            "confidence": 0.6,
            "evidence": [f"push_ups_per_set_{push_ups_per_set}"],
        }

    if squat_comfort is not None:
        tier = {"none": "beginner", "bodyweight": "beginner", "loaded": "intermediate"}.get(squat_comfort, "beginner")
        result["squat"] = {
            "tier": tier,
            "source": "onboarding_question",
            "confidence": 0.5,
            "evidence": [f"squat_comfort_{squat_comfort}"],
        }

    return result


def starting_range_for(movement_pattern: str, equipment: str, tier: str, bodyweight_kg: Optional[float]) -> Optional[Dict]:
    """docs/ML_SPEC.md §3 tier 5 - conservative population-level starting range.
    Returns {"weightLb": float} or None if this pattern/equipment isn't predicted
    at all (e.g. machine - stack calibration varies too much per gym)."""
    ranges = load_json("starting_ranges.json")
    pattern_entry = ranges.get(movement_pattern)
    if not pattern_entry:
        return None
    equipment_entry = pattern_entry.get(equipment)
    if not equipment_entry:
        return None
    tier_entry = equipment_entry.get(tier)
    if not tier_entry:
        return None

    lo, hi = tier_entry["range"]
    if tier_entry["type"] == "fixed":
        weight_lb = (lo + hi) / 2.0
    elif tier_entry["type"] == "bodyweight_multiplier":
        if bodyweight_kg is None:
            return None
        bodyweight_lb = bodyweight_kg * 2.20462
        weight_lb = bodyweight_lb * ((lo + hi) / 2.0)
    else:
        return None

    return {"weightLb": round(weight_lb, 1), "tier": tier}


def transfer_weight(movement_pattern: str, from_equipment: str, to_equipment: str, known_weight_lb: float) -> Optional[float]:
    """docs/ML_SPEC.md §3 tier 2/3 - converts a known weight on one equipment
    type to a starting estimate on another WITHIN the same movementPattern.
    Never called across different patterns - "same movementPattern" is a
    precondition the caller must already have established."""
    if from_equipment == to_equipment:
        return known_weight_lb

    transfer_map = load_json("equipment_transfer.json")
    pattern_entry = transfer_map.get(movement_pattern)
    if not pattern_entry:
        return None

    key = f"{from_equipment}->{to_equipment}"
    multiplier = pattern_entry.get(key)
    if multiplier is None:
        return None

    return round(known_weight_lb * multiplier, 1)
