"""docs/ML_SPEC.md §1 step 6 / §9 Phase 9 exit criteria - fails loudly rather than
silently coercing bad public data into the schema. Run standalone as:
python validate_catalog.py [path-to-catalog_processed.json]
or import validate(rows) for use inside ingest_exercise_catalog.py.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.artifacts import load_json  # noqa: E402

CATALOG_PATH = Path(__file__).resolve().parent / "datasets" / "catalog_processed.json"
REVIEW_PATH = Path(__file__).resolve().parent / "reports" / "catalog_review.csv"


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.stats: Dict = {}

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate(rows: List[Dict], known_sources: List[str] = None) -> ValidationResult:
    result = ValidationResult()
    taxonomies = load_json("taxonomies.json")
    known_sources = set(known_sources or [])

    selectable = [r for r in rows if r.get("isSelectable", True)]
    total = len(rows)
    n_selectable = len(selectable)

    # 100% of selectable rows must satisfy every check below.
    for r in selectable:
        name = r.get("name", "<unnamed>")
        if not r.get("primaryMuscle"):
            result.errors.append(f"{name}: selectable exercise missing primaryMuscle")
        if not r.get("equipment"):
            result.errors.append(f"{name}: selectable exercise missing equipment")
        if not r.get("movementPattern"):
            result.errors.append(f"{name}: selectable exercise missing movementPattern")
        if r.get("movementPattern") and r["movementPattern"] not in taxonomies["movementPatterns"]:
            result.errors.append(f"{name}: invalid movementPattern '{r['movementPattern']}'")
        for pat in r.get("secondaryMovementPatterns") or []:
            if pat not in taxonomies["movementPatterns"]:
                result.errors.append(f"{name}: invalid secondaryMovementPattern '{pat}'")
        if r.get("mechanics") and r["mechanics"] not in taxonomies["mechanics"]:
            result.errors.append(f"{name}: invalid mechanics '{r['mechanics']}'")
        if r.get("utility") and r["utility"] not in taxonomies["utility"]:
            result.errors.append(f"{name}: invalid utility '{r['utility']}'")
        if known_sources and r.get("source"):
            for src in r["source"].split(","):
                if src not in known_sources:
                    result.errors.append(f"{name}: source '{src}' does not reference an ingested dataset")

    # No duplicate canonical names among selectable exercises.
    name_counts = Counter(r["name"] for r in selectable)
    for name, count in name_counts.items():
        if count > 1:
            result.errors.append(f"duplicate canonical name among selectable exercises: '{name}' ({count}x)")

    # No gifUrl mapped to more than one distinct exercise.
    gif_counts: Dict[str, set] = {}
    for r in rows:
        gif = r.get("gifUrl")
        if gif:
            gif_counts.setdefault(gif, set()).add(r["name"])
    for gif, names in gif_counts.items():
        if len(names) > 1:
            result.errors.append(f"gifUrl '{gif}' mapped to multiple exercises: {sorted(names)}")

    review_count = 0
    if REVIEW_PATH.exists():
        review_count = max(len(REVIEW_PATH.read_text(encoding="utf-8").splitlines()) - 1, 0)  # minus header

    result.stats = {
        "totalRows": total,
        "selectableRows": n_selectable,
        "selectableYield": round(n_selectable / total, 3) if total else 0.0,
        "reviewRowCount": review_count,
    }
    return result


def main() -> None:
    if not CATALOG_PATH.exists():
        print(f"No catalog found at {CATALOG_PATH} - run ingest_exercise_catalog.py first.", file=sys.stderr)
        sys.exit(1)

    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    result = validate(rows)

    print(json.dumps(result.stats, indent=2))
    if result.errors:
        print(f"\n{len(result.errors)} validation error(s):", file=sys.stderr)
        for err in result.errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        if len(result.errors) > 50:
            print(f"  ... and {len(result.errors) - 50} more", file=sys.stderr)
        sys.exit(1)

    print("\nCatalog validation passed.")


if __name__ == "__main__":
    main()
