from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from app.services.history import last_top_weight, sessions_for_exercise
from app.services.ml.cold_start import starting_range_for, transfer_weight

LOWER_BODY = {"quads", "hamstrings", "glutes", "calves", "adductors", "abductors"}

PATTERN_TO_FAMILY = {
    "horizontal_push": "upper_push",
    "vertical_push": "upper_push",
    "horizontal_pull": "upper_pull",
    "vertical_pull": "upper_pull",
    "squat": "squat",
    "lunge": "squat",
    "hinge": "hinge",
}


def _progression_increment_lbs(primary_muscle: Optional[str]) -> float:
    if isinstance(primary_muscle, str) and primary_muscle in LOWER_BODY:
        return 5.0
    return 2.5


def _primary_equipment(equipment: Sequence[str]) -> Optional[str]:
    return equipment[0] if equipment else None


def _transfer_key_for(equipment: Optional[str]) -> Optional[str]:
    """equipment_transfer.json's keys use "dumbbell_per_hand" as the target unit
    (a dumbbell weight is inherently per-hand); the catalog just says "dumbbell".
    This is the one place that mapping lives."""
    if equipment == "dumbbell":
        return "dumbbell_per_hand"
    return equipment


def _related_exercise_weight(
    exercise_id: str,
    movement_pattern: str,
    target_equipment: Optional[str],
    history: Sequence[dict],
    catalog: Dict[str, dict],
) -> Optional[float]:
    """docs/ML_SPEC.md §3 tier 2: history for a DIFFERENT exercise sharing the
    same movementPattern, converted through equipment_transfer.json - never a
    raw weight copied across exercises, since "same pattern" doesn't mean
    "comparable absolute weight" (barbell vs. dumbbell vs. machine bench press)."""
    seen_exercise_ids = {ex.get("exerciseId") for doc in history for ex in doc.get("exercises", [])}
    for other_id in seen_exercise_ids:
        if other_id == exercise_id or other_id not in catalog:
            continue
        other = catalog[other_id]
        if other.get("movementPattern") != movement_pattern:
            continue
        other_weight = last_top_weight(history, other_id)
        if other_weight is None:
            continue
        other_equipment = _primary_equipment(other.get("equipment") or [])
        if other_equipment is None or target_equipment is None:
            continue
        transferred = transfer_weight(
            movement_pattern, _transfer_key_for(other_equipment), _transfer_key_for(target_equipment), other_weight
        )
        if transferred is not None:
            return transferred
    return None


def _anchor_weight(movement_pattern: str, target_equipment: Optional[str], fitness_assessment: Optional[dict]) -> Optional[float]:
    """docs/ML_SPEC.md §3 tier 3: a user-provided anchor performance, same
    transfer-mapping logic as tier 2 - self-reported instead of logged."""
    if not fitness_assessment or not target_equipment:
        return None
    family = PATTERN_TO_FAMILY.get(movement_pattern)
    if not family:
        return None
    entry = (fitness_assessment.get("predictedByFamily") or {}).get(family)
    if not entry or entry.get("source") != "anchor_performance":
        return None
    anchor_weight = entry.get("anchorWeightLb")
    anchor_equipment = entry.get("anchorEquipment")
    if anchor_weight is None or anchor_equipment is None:
        return None
    return transfer_weight(
        movement_pattern, _transfer_key_for(anchor_equipment), _transfer_key_for(target_equipment), anchor_weight
    )


def _tier_for_family(movement_pattern: Optional[str], fitness_assessment: Optional[dict]) -> str:
    family = PATTERN_TO_FAMILY.get(movement_pattern) if movement_pattern else None
    if fitness_assessment and family:
        entry = (fitness_assessment.get("predictedByFamily") or {}).get(family)
        if entry and entry.get("tier"):
            return entry["tier"]
    return "beginner"  # conservative default when nothing is known about this user


def apply_progression(
    exercise_id: str,
    primary_muscle: Optional[str],
    history: Sequence[dict],
    movement_pattern: Optional[str] = None,
    equipment: Optional[Sequence[str]] = None,
    catalog: Optional[Dict[str, dict]] = None,
    fitness_assessment: Optional[dict] = None,
    bodyweight_kg: Optional[float] = None,
) -> Optional[Tuple[float, str]]:
    """Evidence-priority order (docs/ML_SPEC.md §3 - "prefer the most specific
    evidence available"). Returns (weightLb, evidenceTier) or None if nothing
    at all is available (tier 6 - ask the user). Tier 4 (a trained cold-start
    model) is deliberately absent - blocked on real training data, not an
    oversight; see docs/ML_SPEC.md §9.
    """
    # Tier 1: logged history for this exact exercise.
    last_weight = last_top_weight(history, exercise_id)
    if last_weight is not None:
        inc = _progression_increment_lbs(primary_muscle)
        return max(round(last_weight + inc, 1), 0.0), "recent_history"

    target_equipment = _primary_equipment(equipment or [])

    # Tier 2: logged history for a related exercise, same movementPattern.
    if movement_pattern and catalog:
        related = _related_exercise_weight(exercise_id, movement_pattern, target_equipment, history, catalog)
        if related is not None:
            return related, "related_exercise_history"

    # Tier 3: user-provided anchor performance.
    if movement_pattern:
        anchor = _anchor_weight(movement_pattern, target_equipment, fitness_assessment)
        if anchor is not None:
            return anchor, "anchor_performance"

    # Tier 4 (model estimate) intentionally absent - see docstring.

    # Tier 5: conservative population starting range, scaled by cold-start tier if known.
    if movement_pattern and target_equipment:
        tier_label = _tier_for_family(movement_pattern, fitness_assessment)
        range_result = starting_range_for(movement_pattern, target_equipment, tier_label, bodyweight_kg)
        if range_result:
            return range_result["weightLb"], "population_range"

    # Tier 6: nothing available - caller must ask the user directly.
    return None
