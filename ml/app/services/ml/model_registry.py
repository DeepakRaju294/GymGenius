"""docs/ML_SPEC.md §7 - single load point for every trained artifact, with startup
fallback behavior defined explicitly rather than left as an accident of whatever
exception happens to propagate. The recommendation/estimation service must never
become unavailable because a .joblib didn't deploy correctly."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import joblib

from app.utils.artifacts import artifacts_version

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "checkpoints"

# Only "calorie" has a trainer today (ml/training/train_calorie_model.py). The rest
# are named here ahead of their Phase 10-13 implementations so model_status()
# reports them as not-yet-built rather than silently omitting them.
_ARTIFACT_FILENAMES = {
    "calorie": "calorie_sklearn.joblib",
    "cold_start": "cold_start.joblib",
    "similarity": "exercise_similarity.joblib",
    "reranker": "reranker.joblib",
}

_cache: Dict[str, Optional[dict]] = {}
_status: Dict[str, dict] = {}


def get_model(name: str) -> Optional[dict]:
    """Returns the artifact dict as saved by the corresponding train_*.py script,
    or None if unavailable. Callers must have a deterministic fallback for None."""
    if name in _cache:
        return _cache[name]

    filename = _ARTIFACT_FILENAMES.get(name)
    if not filename:
        _record_status(name, loaded=False, fallback_reason="unknown_model_name")
        _cache[name] = None
        return None

    path = CHECKPOINT_DIR / filename
    if not path.exists():
        logger.warning("model artifact missing, falling back to deterministic implementation: %s", path)
        _record_status(name, loaded=False, fallback_reason="artifact_missing")
        _cache[name] = None
        return None

    try:
        artifact = joblib.load(path)
    except Exception:
        logger.exception("failed to deserialize model artifact, falling back: %s", path)
        _record_status(name, loaded=False, fallback_reason="deserialization_failed")
        _cache[name] = None
        return None

    _cache[name] = artifact
    _record_status(name, loaded=True, model_version=artifact.get("modelVersion"))
    return artifact


def _record_status(
    name: str,
    loaded: bool,
    fallback_reason: Optional[str] = None,
    model_version: Optional[str] = None,
) -> None:
    if loaded:
        _status[name] = {
            "loaded": True,
            "modelVersion": model_version,
            "artifactsVersion": artifacts_version(),
            "loadedAt": datetime.now(timezone.utc).isoformat(),
        }
    else:
        _status[name] = {
            "loaded": False,
            "fallback": "deterministic",
            "fallbackReason": fallback_reason,
        }


def model_status() -> Dict[str, dict]:
    """GET /ml/status (see app.main) reads this - answers "is a model actually
    being used or did it silently fall back, and why" without digging through logs."""
    for name in _ARTIFACT_FILENAMES:
        if name not in _status:
            get_model(name)
    return dict(_status)
