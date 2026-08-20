"""docs/ML_SPEC.md §2 - offline job, rebuilt whenever the catalog changes.
Run: python build_exercise_similarity_index.py"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.utils.db import mongo  # noqa: E402
from similarity_features import build_feature_matrix  # noqa: E402

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "app" / "models" / "checkpoints"
MODEL_VERSION = "similarity-0.1.0"


def main() -> None:
    db = mongo()
    exercises = list(db.exercises.find({"isSelectable": True}))
    if len(exercises) < 2:
        print(
            f"Only {len(exercises)} selectable exercise(s) in db.exercises - need at least 2 to build a "
            "similarity index. Run seed_from_catalog.py (or server/scripts/seedExercises.js) first.",
            file=sys.stderr,
        )
        sys.exit(1)

    X, exercise_ids, feature_names = build_feature_matrix(exercises)
    movement_patterns = {ex["exerciseId"]: ex.get("movementPattern") for ex in exercises}
    primary_muscles = {ex["exerciseId"]: ex.get("primaryMuscle") for ex in exercises}

    n_neighbors = min(len(exercises), 25)  # cap - we only ever need a handful of substitutes per call
    index = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine").fit(X)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "index": index,
            "features": X,  # kept alongside the index so similarity.py can query
            # kneighbors() through the public API (X[i:i+1]) rather than reaching
            # into a private sklearn attribute for the fitted training data.
            "exerciseIds": exercise_ids,
            "movementPatterns": movement_patterns,
            "primaryMuscles": primary_muscles,
            "featureNames": feature_names,
            "modelVersion": MODEL_VERSION,
            "builtAt": datetime.now(timezone.utc).isoformat(),
        },
        CHECKPOINT_DIR / "exercise_similarity.joblib",
    )
    print(f"Built similarity index over {len(exercises)} exercises -> {CHECKPOINT_DIR / 'exercise_similarity.joblib'}")


if __name__ == "__main__":
    main()
