"""Trains the scikit-learn calorie model - the one docs/ML_SPEC.md §4 actually
ships via model_registry.py. Run: python train_calorie_model.py"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calorie_data import load_dataset  # noqa: E402
from calorie_features import build_features  # noqa: E402

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "app" / "models" / "checkpoints"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "calorie_sklearn_eval.json"
MODEL_VERSION = "calorie-sklearn-0.1.0"


def main() -> None:
    df, is_synthetic = load_dataset()
    X, y, feature_names = build_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    ridge = Ridge(alpha=1.0).fit(X_train, y_train)
    ridge_mae = mean_absolute_error(y_test, ridge.predict(X_test))

    gbr = GradientBoostingRegressor(random_state=42).fit(X_train, y_train)
    gbr_mae = mean_absolute_error(y_test, gbr.predict(X_test))

    chosen_name, chosen_model, chosen_mae = (
        ("gradient_boosting", gbr, gbr_mae) if gbr_mae <= ridge_mae else ("ridge", ridge, ridge_mae)
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = CHECKPOINT_DIR / "calorie_sklearn.joblib"
    joblib.dump(
        {"model": chosen_model, "feature_names": feature_names, "modelVersion": MODEL_VERSION},
        artifact_path,
    )

    report = {
        "modelVersion": MODEL_VERSION,
        "dataSource": "synthetic" if is_synthetic else "real",
        "nTrain": len(X_train),
        "nTest": len(X_test),
        "ridgeMAE": round(float(ridge_mae), 2),
        "gradientBoostingMAE": round(float(gbr_mae), 2),
        "chosenModel": chosen_name,
        "chosenMAE": round(float(chosen_mae), 2),
        "trainedAt": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    if is_synthetic:
        print(
            "\nWARNING: trained on synthetic data (no ml/training/datasets/gym_members_exercise.csv "
            "present yet). Re-run once the real Kaggle dataset is downloaded before trusting these numbers.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
