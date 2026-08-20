"""docs/ML_SPEC.md §1 "Output" - loads ingest_exercise_catalog.py's validated
output into MongoDB's exercises collection (upsert by exerciseId, same pattern
as server/scripts/seedExercises.js). Run: python seed_from_catalog.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.db import mongo  # noqa: E402

CATALOG_PATH = Path(__file__).resolve().parent / "datasets" / "catalog_processed.json"


def main() -> None:
    if not CATALOG_PATH.exists():
        print(f"No catalog at {CATALOG_PATH} - run ingest_exercise_catalog.py first.", file=sys.stderr)
        sys.exit(1)

    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    db = mongo()
    upserted = 0
    for row in rows:
        db.exercises.update_one({"exerciseId": row["exerciseId"]}, {"$set": row}, upsert=True)
        upserted += 1

    print(f"Upserted {upserted} exercises into db.exercises.")


if __name__ == "__main__":
    main()
