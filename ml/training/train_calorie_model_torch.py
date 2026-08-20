"""PyTorch MLP benchmark for the calorie model (docs/ML_SPEC.md §4) - an explicit
comparison against train_calorie_model.py's scikit-learn model, NOT what actually
ships (model_registry.py only ever loads the sklearn artifact). The point of this
script is the benchmark itself: does a small neural net beat gradient boosting on
this data, and by how much. Run: python train_calorie_model_torch.py

At ~1k rows this is exactly the regime where a neural net is expected to struggle
to beat tree-based models (docs/ML_SPEC.md §6) - the training loop here spends
most of its effort fighting overfitting for that reason: small hidden layers,
dropout, weight decay, and early stopping on a held-out validation split, not just
more epochs.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calorie_data import load_dataset  # noqa: E402
from calorie_features import build_features  # noqa: E402

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "app" / "models" / "checkpoints"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "calorie_pytorch_eval.json"
COMPARISON_REPORT_PATH = Path(__file__).resolve().parent / "reports" / "calorie_model_comparison.json"
SKLEARN_REPORT_PATH = Path(__file__).resolve().parent / "reports" / "calorie_sklearn_eval.json"
MODEL_VERSION = "calorie-pytorch-benchmark-0.1.0"

torch.manual_seed(42)


class CalorieMLP(nn.Module):
    """Deliberately small - a wide/deep net has no chance of generalizing on
    ~1k rows and would just memorize the training set."""

    def __init__(self, n_features: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(8, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def _standardize(X_train: np.ndarray, *others: np.ndarray):
    """Neural nets are sensitive to feature scale in a way tree models aren't -
    GradientBoostingRegressor splits on raw feature values regardless of scale,
    but unscaled inputs here would make the MLP's gradient steps badly
    conditioned across features of very different magnitudes (hours vs. bpm vs.
    kg vs. one-hot 0/1). Stats are fit on train only, applied to everything else."""
    mean = X_train.mean(axis=0, keepdims=True)
    std = X_train.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    scaled = [(X_train - mean) / std]
    for X in others:
        scaled.append((X - mean) / std)
    return (*scaled, mean, std)


def main() -> None:
    df, is_synthetic = load_dataset()
    X, y, feature_names = build_features(df)

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    X_train_s, X_val_s, X_test_s, mean, std = _standardize(X_train, X_val, X_test)

    # The target needs standardizing too, not just the inputs. calories_burned
    # sits in the hundreds; Linear layers start with small (near-zero) weights,
    # so an unscaled target forces the model to learn large output magnitudes
    # from a near-zero starting point, which a handful of full-batch gradient
    # steps at a normal learning rate doesn't get anywhere close to closing -
    # the first version of this script trained on raw-scale y and it never
    # converged (test MAE ~250 vs. sklearn's ~38, an obvious red flag that
    # turned out to be this, not "the neural net is just worse here").
    y_train_mean, y_train_std = y_train.mean(), y_train.std()
    y_train_z = (y_train - y_train_mean) / y_train_std
    y_val_z = (y_val - y_train_mean) / y_train_std

    X_train_t = torch.from_numpy(X_train_s.astype(np.float32))
    y_train_t = torch.from_numpy(y_train_z.astype(np.float32))
    X_val_t = torch.from_numpy(X_val_s.astype(np.float32))
    y_val_t = torch.from_numpy(y_val_z.astype(np.float32))
    X_test_t = torch.from_numpy(X_test_s.astype(np.float32))

    model = CalorieMLP(n_features=X.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss()

    best_val_loss = float("inf")
    best_state = None
    patience, patience_left = 20, 20
    max_epochs = 500
    history = []

    for epoch in range(max_epochs):
        model.train()
        optimizer.zero_grad()
        pred = model(X_train_t)
        loss = loss_fn(pred, y_train_t)
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_pred = model(X_val_t)
            val_loss = loss_fn(val_pred, y_val_t).item()
        history.append({"epoch": epoch, "trainLoss": round(loss.item(), 2), "valLoss": round(val_loss, 2)})

        if val_loss < best_val_loss - 1e-3:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_left = patience
        else:
            patience_left -= 1
            if patience_left <= 0:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        test_pred_z = model(X_test_t).numpy()
    test_pred = test_pred_z * y_train_std + y_train_mean  # back to raw calories for a comparable MAE
    torch_mae = mean_absolute_error(y_test, test_pred)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": best_state,
            "feature_names": feature_names,
            "mean": mean,
            "std": std,
            "yMean": float(y_train_mean),
            "yStd": float(y_train_std),
            "modelVersion": MODEL_VERSION,
        },
        CHECKPOINT_DIR / "calorie_pytorch_benchmark.pt",
    )

    report = {
        "modelVersion": MODEL_VERSION,
        "dataSource": "synthetic" if is_synthetic else "real",
        "nTrain": len(X_train),
        "nVal": len(X_val),
        "nTest": len(X_test),
        "epochsRun": len(history),
        "bestValLossStandardized": round(best_val_loss, 4),
        "testMAE": round(float(torch_mae), 2),
        "trainedAt": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    _write_comparison(report)

    if is_synthetic:
        print(
            "\nWARNING: trained on synthetic data - re-run once the real Kaggle dataset is present.",
            file=sys.stderr,
        )


def _write_comparison(torch_report: dict) -> None:
    if not SKLEARN_REPORT_PATH.exists():
        print(f"(skipping comparison - run train_calorie_model.py first to generate {SKLEARN_REPORT_PATH})")
        return
    sklearn_report = json.loads(SKLEARN_REPORT_PATH.read_text())
    winner = "pytorch_mlp" if torch_report["testMAE"] < sklearn_report["chosenMAE"] else sklearn_report["chosenModel"]
    comparison = {
        "sklearn": {"model": sklearn_report["chosenModel"], "testMAE": sklearn_report["chosenMAE"]},
        "pytorchMLP": {"testMAE": torch_report["testMAE"]},
        "winner": winner,
        "note": (
            "Benchmark only - the sklearn model is what ships regardless of this result "
            "(docs/ML_SPEC.md §6: classical ML is the deliberate choice at this data volume). "
            "This comparison exists to make that choice a measured one, not an assumed one."
        ),
        "comparedAt": datetime.now(timezone.utc).isoformat(),
    }
    COMPARISON_REPORT_PATH.write_text(json.dumps(comparison, indent=2))
    print("\n--- Comparison ---")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
