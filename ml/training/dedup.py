"""docs/ML_SPEC.md §1 step 3 - two-stage catalog dedup. Operates on already-
normalized canonical rows (list of dicts), independent of which raw dataset they
came from, so this is testable without needing the real Kaggle CSVs downloaded.

Canonical row shape expected:
{name, primaryMuscle, equipment: [...], movementPattern, sourceDataset}
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CANDIDATE_THRESHOLD = 0.75  # below this, names aren't similar enough to even consider

# Common gym abbreviations, expanded before similarity comparison only (display
# name is untouched) - pure character-ngram similarity has zero overlap between
# "DB" and "Dumbbell", so without this, ubiquitous abbreviation variants never
# even become dedup candidates in the first place.
_ABBREVIATIONS = {
    r"\bdb\b": "dumbbell",
    r"\bbb\b": "barbell",
    r"\bkb\b": "kettlebell",
    r"\bohp\b": "overhead press",
    r"\brdl\b": "romanian deadlift",
    r"\bbw\b": "bodyweight",
}


def _normalize_for_similarity(name: str) -> str:
    text = name.lower()
    for pattern, expansion in _ABBREVIATIONS.items():
        text = re.sub(pattern, expansion, text)
    return text


def _structural_agreement(a: Dict, b: Dict) -> bool:
    """A candidate pair is only auto-mergeable if it agrees on primaryMuscle, has
    compatible equipment, and (once assigned) the same movementPattern -
    docs/ML_SPEC.md §1 step 3. Missing movementPattern on either side is treated
    as "don't know" rather than "disagrees" - falls through to REVIEW, not
    KEEP_SEPARATE, since that's a "we can't tell yet" case, not a "definitely
    different" one."""
    if a.get("primaryMuscle") != b.get("primaryMuscle"):
        return False
    eq_a, eq_b = set(a.get("equipment") or []), set(b.get("equipment") or [])
    if eq_a and eq_b and eq_a.isdisjoint(eq_b):
        return False
    pattern_a, pattern_b = a.get("movementPattern"), b.get("movementPattern")
    if not pattern_a or not pattern_b or pattern_a != pattern_b:
        # Missing on either side is "don't know", not "agrees" - never
        # auto-merge on an absent signal, only on a confirmed matching one.
        return False
    return True


def _reason_for_review(a: Dict, b: Dict) -> str:
    if a.get("primaryMuscle") != b.get("primaryMuscle"):
        return "CONFLICTING_PRIMARY_MUSCLE"
    if not a.get("movementPattern") or not b.get("movementPattern"):
        return "UNKNOWN_MOVEMENT_PATTERN"
    return "AMBIGUOUS_DUPLICATE"


def find_duplicate_groups(rows: List[Dict]) -> Tuple[List[List[int]], List[Dict]]:
    """Returns (merge_groups, review_rows). merge_groups is a list of index lists
    - each inner list is a set of row indices to collapse into one exercise.
    review_rows is what would go into catalog_review.csv: [{indexA, indexB,
    similarity, nameA, nameB, decision, reason}]."""
    if len(rows) < 2:
        return [[i] for i in range(len(rows))], []

    names = [_normalize_for_similarity(r["name"]) for r in rows]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    tfidf = vectorizer.fit_transform(names)
    sims = cosine_similarity(tfidf)

    n = len(rows)
    parent = list(range(n))  # union-find for merge groups

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    review_rows: List[Dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sims[i, j])
            if sim < CANDIDATE_THRESHOLD:
                continue
            if _structural_agreement(rows[i], rows[j]):
                union(i, j)
                review_rows.append(
                    {
                        "similarity": round(sim, 3),
                        "nameA": rows[i]["name"],
                        "nameB": rows[j]["name"],
                        "decision": "AUTO_MERGE",
                        "reason": None,
                    }
                )
            else:
                review_rows.append(
                    {
                        "similarity": round(sim, 3),
                        "nameA": rows[i]["name"],
                        "nameB": rows[j]["name"],
                        "decision": "REVIEW",
                        "reason": _reason_for_review(rows[i], rows[j]),
                    }
                )

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    return list(groups.values()), review_rows


def merge_group(rows: List[Dict], indices: List[int]) -> Dict:
    """Collapses a merge group into one canonical row - keeps the first row's
    fields, unions equipment/secondaryMuscles, combines source provenance."""
    base = dict(rows[indices[0]])
    all_equipment: set = set(base.get("equipment") or [])
    all_secondary: set = set(base.get("secondaryMuscles") or [])
    sources: set = {base.get("sourceDataset")} if base.get("sourceDataset") else set()

    for idx in indices[1:]:
        row = rows[idx]
        all_equipment.update(row.get("equipment") or [])
        all_secondary.update(row.get("secondaryMuscles") or [])
        if row.get("sourceDataset"):
            sources.add(row["sourceDataset"])
        # Fill gaps from later duplicates - e.g. one source has a gifUrl, another doesn't.
        for field in ("mechanics", "utility", "movementPattern", "movementPatternSource", "gifUrl"):
            if not base.get(field) and row.get(field):
                base[field] = row[field]

    base["equipment"] = sorted(all_equipment)
    base["secondaryMuscles"] = sorted(all_secondary - {base.get("primaryMuscle")})
    base["source"] = ",".join(sorted(sources)) if sources else base.get("sourceDataset")
    base.pop("sourceDataset", None)
    return base
