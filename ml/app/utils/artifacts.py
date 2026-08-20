from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

# ml/app/utils/artifacts.py -> ml/app/utils -> ml/app -> ml -> ml/artifacts
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"


@lru_cache(maxsize=None)
def load_json(filename: str) -> Dict[str, Any]:
    path = ARTIFACTS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def artifacts_version() -> str:
    path = ARTIFACTS_DIR / "version.txt"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unknown"
