"""docs/ML_SPEC.md §1 - orchestrates the full catalog ingestion pipeline: load
each configured source that's actually present -> normalize -> assign
movementPattern -> apply caution tags -> two-stage dedup -> validate. Fails
loudly (non-zero exit) on integrity violations, per §1 step 6.

Run: python ingest_exercise_catalog.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.artifacts import load_json  # noqa: E402
from dedup import find_duplicate_groups, merge_group  # noqa: E402
from normalize import assign_movement_pattern, normalize_equipment, normalize_muscle  # noqa: E402
from validate_catalog import validate  # noqa: E402

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"
CATALOG_PATH = DATASETS_DIR / "catalog_processed.json"
REVIEW_PATH = REPORTS_DIR / "catalog_review.csv"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "exercise"


def _split_list(value, separator: str) -> List[str]:
    if pd.isna(value) or not value:
        return []
    return [v.strip() for v in str(value).split(separator) if v.strip()]


def _load_source(source_key: str, config: Dict) -> List[Dict]:
    path = DATASETS_DIR / config["filename"]
    if not path.exists():
        print(f"  [skip] {source_key}: {config['filename']} not present in {DATASETS_DIR}")
        return []

    if not config.get("columnsVerified", False):
        print(
            f"  [warning] {source_key}: rawColumns are unverified guesses - "
            f"run inspect_columns.py on {config['filename']} and check source_configs.json"
        )

    df = pd.read_csv(path)
    cols = config["rawColumns"]
    sep = config.get("listSeparator", ",")
    rows: List[Dict] = []

    for _, raw in df.iterrows():
        name = str(raw.get(cols.get("name"), "")).strip()
        if not name or name.lower() == "nan":
            continue

        primary_raw = raw.get(cols.get("primaryMuscle"))
        primary = normalize_muscle(str(primary_raw)) if pd.notna(primary_raw) else None

        equipment_raw = raw.get(cols.get("equipment"))
        equipment = [normalize_equipment(e) for e in _split_list(equipment_raw, sep)]

        secondary_raw = raw.get(cols.get("secondaryMuscles")) if cols.get("secondaryMuscles") else None
        secondary = [normalize_muscle(m) for m in _split_list(secondary_raw, sep)]

        pattern, pattern_source, secondary_patterns = assign_movement_pattern(name)

        mechanics = raw.get(cols.get("mechanics")) if cols.get("mechanics") else None
        mechanics = str(mechanics).strip().lower() if pd.notna(mechanics) else None
        utility = raw.get(cols.get("utility")) if cols.get("utility") else None
        utility = str(utility).strip().lower() if pd.notna(utility) else None
        gif_url = raw.get(cols.get("gifUrl")) if cols.get("gifUrl") else None
        gif_url = str(gif_url).strip() if pd.notna(gif_url) else None

        rows.append(
            {
                "name": name,
                "primaryMuscle": primary,
                "secondaryMuscles": secondary,
                "equipment": equipment,
                "mechanics": mechanics if mechanics in ("compound", "isolation") else None,
                "utility": utility if utility in ("basic", "auxiliary") else None,
                "movementPattern": pattern,
                "movementPatternSource": pattern_source if pattern else None,
                "secondaryMovementPatterns": secondary_patterns,
                "gifUrl": gif_url,
                "sourceDataset": source_key,
            }
        )

    print(f"  [loaded] {source_key}: {len(rows)} rows")
    return rows


def _apply_caution_tags(rows: List[Dict]) -> None:
    caution = load_json("stoplist.json")
    match_index = {}
    for entry in caution.get("entries", []):
        for match_name in entry["matchNames"]:
            match_index[match_name.strip().lower()] = entry

    for row in rows:
        entry = match_index.get(row["name"].strip().lower())
        if entry:
            row["cautionTags"] = entry["cautionTags"]
            row["cautionReason"] = entry["cautionReason"]
            row["evidenceLevel"] = entry["evidenceLevel"]
        else:
            row["cautionTags"] = []


def main() -> None:
    source_configs = json.loads((Path(__file__).resolve().parent / "source_configs.json").read_text(encoding="utf-8"))

    print("Loading sources:")
    all_rows: List[Dict] = []
    known_sources: List[str] = []
    for source_key, config in source_configs["sources"].items():
        rows = _load_source(source_key, config)
        if rows:
            known_sources.append(source_key)
        all_rows.extend(rows)

    if not all_rows:
        print(
            f"\nNo source datasets found in {DATASETS_DIR}. Nothing to ingest yet - "
            "download at least one dataset (see docs/ML_SPEC.md §1) and re-run.",
            file=sys.stderr,
        )
        sys.exit(0)  # not a failure - a documented, expected state before Kaggle access is set up

    print(f"\n{len(all_rows)} total rows loaded from {len(known_sources)} source(s). Deduping...")
    groups, review_rows = find_duplicate_groups(all_rows)

    merged: List[Dict] = []
    for group in groups:
        if len(group) == 1:
            merged.append(dict(all_rows[group[0]], source=all_rows[group[0]].pop("sourceDataset", None)))
        else:
            merged.append(merge_group(all_rows, group))

    for row in merged:
        row["exerciseId"] = _slugify(row["name"])
        row["isSelectable"] = bool(row.get("primaryMuscle") and row.get("equipment") and row.get("movementPattern"))

    # De-dupe exerciseId collisions from slugification (distinct names slugifying identically).
    seen_ids: Dict[str, int] = {}
    for row in merged:
        base_id = row["exerciseId"]
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            row["exerciseId"] = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0

    _apply_caution_tags(merged)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("similarity,nameA,nameB,decision,reason\n")
        for r in review_rows:
            f.write(f'{r["similarity"]},"{r["nameA"]}","{r["nameB"]}",{r["decision"]},{r["reason"] or ""}\n')

    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    print(f"{len(merged)} exercises after dedup ({len(all_rows) - len(merged)} merged).")
    print(f"Catalog written to {CATALOG_PATH}")
    print(f"Review report written to {REVIEW_PATH} ({len(review_rows)} pairs)")

    print("\nValidating...")
    result = validate(merged, known_sources=known_sources)
    print(json.dumps(result.stats, indent=2))
    if not result.ok:
        print(f"\n{len(result.errors)} validation error(s):", file=sys.stderr)
        for err in result.errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("\nCatalog validation passed. Run seed_from_catalog.py to load it into MongoDB.")


if __name__ == "__main__":
    main()
