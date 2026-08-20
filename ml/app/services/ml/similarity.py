"""docs/ML_SPEC.md §2 - step 2 of the substitution pipeline only (ranking).
Steps 1 (hard filter: equipment/caution/muscle) and 3 (final tie-break via
score_rules) stay in selection/candidate_pool.py and selection/scorer.py - the
`candidate_ids` this ranks are expected to already be the hard-filtered,
Selection-eligible pool, not the whole catalog, so this can never surface a
substitute that bypasses equipment or caution constraints."""

from __future__ import annotations

from typing import List, Optional

from .model_registry import get_model


def rank_by_similarity(exercise_id: str, candidate_ids: List[str], k: int = 5) -> List[str]:
    """Ranks candidate_ids by similarity to exercise_id - movementPattern match
    first, then feature cosine similarity. Falls back to returning candidate_ids
    as-is (already relevance-ranked by the caller via score_rules) if the
    similarity model isn't loaded or doesn't know this exercise yet."""
    artifact = get_model("similarity")
    if artifact is None:
        return candidate_ids[:k]

    exercise_ids: List[str] = artifact["exerciseIds"]
    if exercise_id not in exercise_ids:
        return candidate_ids[:k]

    target_idx = exercise_ids.index(exercise_id)
    target_pattern = artifact["movementPatterns"].get(exercise_id)

    _, indices = artifact["index"].kneighbors(
        artifact["features"][target_idx : target_idx + 1],
        n_neighbors=len(exercise_ids),
    )
    ranked_all = [exercise_ids[i] for i in indices[0]]

    candidate_set = set(candidate_ids)
    pattern_match: List[str] = []
    other: List[str] = []
    for eid in ranked_all:
        if eid == exercise_id or eid not in candidate_set:
            continue
        bucket = pattern_match if artifact["movementPatterns"].get(eid) == target_pattern else other
        bucket.append(eid)

    return (pattern_match + other)[:k]
