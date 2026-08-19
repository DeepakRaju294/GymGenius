from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from app.utils.db import mongo
from app.utils.onerm import best_set_1rm

REST_WINDOW_HOURS = int(__import__("os").getenv("REST_WINDOW_HOURS", "48"))


def now() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(dt: datetime) -> float:
    return max(0.0, (now() - dt).total_seconds() / 86400.0)


def fetch_user_history(username: str, limit: int = 200) -> List[dict]:
    """Reads the server's real `histories` collection (Mongoose `History` model) -
    the ml service has no parallel workout representation of its own. Most-recent
    session first."""
    db = mongo()
    cur = db.histories.find({"username": username}).sort("workoutDate", -1).limit(limit)
    return list(cur)


def get_exercise_catalog() -> Dict[str, dict]:
    db = mongo()
    return {ex["exerciseId"]: ex for ex in db.exercises.find({}) if ex.get("exerciseId")}


def equipment_profile(username: str) -> set:
    db = mongo()
    p = db.profiles.find_one({"username": username}) or {}
    eq = p.get("equipment") or []
    return set(eq)


def last_done_by_exercise(history: Sequence[dict]) -> Dict[str, datetime]:
    last: Dict[str, datetime] = {}
    for doc in history:  # most-recent-first
        ts = doc.get("workoutDate")
        for ex in doc.get("exercises", []):
            ex_id = ex.get("exerciseId")
            if ex_id and ex_id not in last and isinstance(ts, datetime):
                last[ex_id] = ts
    return last


def frequency_28d(history: Sequence[dict]) -> Dict[str, int]:
    cutoff = now() - timedelta(days=28)
    freq: Dict[str, int] = defaultdict(int)
    for doc in history:
        ts = doc.get("workoutDate")
        if not isinstance(ts, datetime) or ts < cutoff:
            continue
        for ex in doc.get("exercises", []):
            ex_id = ex.get("exerciseId")
            if ex_id:
                freq[ex_id] += 1
    return freq


def recent_muscles(history: Sequence[dict], catalog: Dict[str, dict], window_hours: int = REST_WINDOW_HOURS) -> set:
    cutoff = now() - timedelta(hours=window_hours)
    muscles: set = set()
    for doc in history:
        ts = doc.get("workoutDate")
        if not isinstance(ts, datetime) or ts < cutoff:
            continue
        for ex in doc.get("exercises", []):
            cat = catalog.get(ex.get("exerciseId"), {})
            pm = cat.get("primaryMuscle")
            if isinstance(pm, str) and pm:
                muscles.add(pm)
    return muscles


def sessions_for_exercise(history: Sequence[dict], exercise_id: str) -> List[Tuple[datetime, float]]:
    """Chronological (oldest-first) list of (session date, best-set estimated 1RM)
    for one exercise, one entry per workout session that included it."""
    out: List[Tuple[datetime, float]] = []
    for doc in history:
        ts = doc.get("workoutDate")
        if not isinstance(ts, datetime):
            continue
        for ex in doc.get("exercises", []):
            if ex.get("exerciseId") == exercise_id:
                score = best_set_1rm(ex.get("sets", []))
                if score > 0:
                    out.append((ts, score))
    out.sort(key=lambda pair: pair[0])
    return out


def last_top_weight(history: Sequence[dict], exercise_id: str) -> Optional[float]:
    """Heaviest weight actually used for this exercise in its most recent session
    (most-recent-first order from fetch_user_history)."""
    for doc in history:
        for ex in doc.get("exercises", []):
            if ex.get("exerciseId") == exercise_id:
                weights = [s.get("weight") for s in ex.get("sets", []) if isinstance(s.get("weight"), (int, float))]
                if weights:
                    return float(max(weights))
    return None
