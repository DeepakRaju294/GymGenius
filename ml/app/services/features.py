from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import os

from app.util.db import mongo


REST_WINDOW_HOURS = int(os.getenv("REST_WINDOW_HOURS", "48"))

GOAL_TO_REP: Dict[str, Tuple[int, int]] = {
    "strength": (3, 5),
    "hypertrophy": (3, 10),
    "endurance": (3, 15),
}
DEFAULT_GOAL = "hypertrophy"

UPPER_BODY = {"chest", "shoulders", "triceps", "biceps", "back", "lats", "forearms", "rear delts"}
LOWER_BODY = {"quads", "hamstrings", "glutes", "calves", "adductors", "abductors"}

F_PRIMARY_MUSCLE = "primaryMuscle"
F_EQUIPMENT = "equipment"
F_GOALS = "goals"
F_DEFAULT_WEIGHT = "default_weight_lbs"



def now() -> datetime:
    return datetime.now(timezone.utc)


def days_ago(dt: datetime) -> float:
    return max(0.0, (now() - dt).total_seconds() / 86400.0)


def fetch_user_history(username: str, limit: int = 200) -> List[dict]:

    db = mongo()
    cur = db.workouts.find({"username": username}).sort("ts", -1).limit(limit)
    return list(cur)


def equipment_profile(username: str) -> set:

    db = mongo()
    p = db.profiles.find_one({"username": username}) or {}
    eq = p.get("equipment") or []
    return set(eq)



def last_done_by_exercise(history: Sequence[dict]) -> Dict[str, datetime]:
    last: Dict[str, datetime] = {}
    for w in history:  
        ts = w.get("ts")
        for ex in w.get("exercises", []):
            ex_id = str(ex.get("exerciseId"))
            if ex_id and ex_id not in last and isinstance(ts, datetime):
                last[ex_id] = ts
    return last


def frequency_28d(history: Sequence[dict]) -> Dict[str, int]:
    cutoff = now() - timedelta(days=28)
    freq: Dict[str, int] = defaultdict(int)
    for w in history:
        ts = w.get("ts")
        if not isinstance(ts, datetime) or ts < cutoff:
            continue
        for ex in w.get("exercises", []):
            ex_id = str(ex.get("exerciseId"))
            if ex_id:
                freq[ex_id] += 1
    return freq


def success_rate(history: Sequence[dict]) -> Dict[str, float]:
    
    seen = set()
    for w in history:
        for ex in w.get("exercises", []):
            ex_id = str(ex.get("exerciseId"))
            if ex_id:
                seen.add(ex_id)
    return {ex_id: 1.0 for ex_id in seen}


def recent_muscles(history: Sequence[dict], window_hours: int = REST_WINDOW_HOURS) -> set:
    cutoff = now() - timedelta(hours=window_hours)
    muscles: set = set()
    for w in history:
        ts = w.get("ts")
        if not isinstance(ts, datetime) or ts < cutoff:
            continue
        for ex in w.get("exercises", []):
            pm = ex.get(F_PRIMARY_MUSCLE)
            if isinstance(pm, str) and pm:
                muscles.add(pm)
    return muscles


def _exercise_matches_focus(ex_doc: dict, focus: Optional[str]) -> bool:
    if not focus:
        return True
    tags = ex_doc.get("tags") or []
    ex_focus = ex_doc.get("focus")
    return (isinstance(tags, list) and focus in tags) or (isinstance(ex_focus, str) and ex_focus == focus)


def candidate_pool(username: str, focus: Optional[str]) -> Tuple[List[dict], List[dict]]:
    
    db = mongo()
    history = fetch_user_history(username)
    muscles_to_rest = recent_muscles(history)
    user_eq = equipment_profile(username)

    candidates: List[dict] = []
    for ex in db.exercises.find({}):
        if not _exercise_matches_focus(ex, focus):
            continue

        needs = set(ex.get(F_EQUIPMENT) or [])
        if needs and not needs.issubset(user_eq):
            continue

        pm = ex.get(F_PRIMARY_MUSCLE)
        if isinstance(pm, str) and pm in muscles_to_rest:
            continue

        candidates.append(ex)

    return candidates, history

def build_user_vector(history: Sequence[dict]) -> Dict[str, float]:

    vol: Dict[str, float] = defaultdict(float)
    total = 0.0
    for w in history:
        for ex in w.get("exercises", []):
            mg = ex.get(F_PRIMARY_MUSCLE, "other") or "other"
            sets = ex.get("sets") or 0
            reps = ex.get("reps") or 0
            weight = ex.get("weight_lbs") or 0.0
            lifted = float(max(weight * reps * sets, 1.0))  
            vol[mg] += lifted
            total += lifted
    if total <= 0:
        total = 1.0
    return {k: v / total for k, v in vol.items()}


def _goal_alignment(ex_doc: dict, goal: str) -> float:

    goals = ex_doc.get(F_GOALS) or []
    if isinstance(goals, list) and goal in goals:
        return 1.0
    return 0.6


def score_rules(
    username: str,
    candidates: Sequence[dict],
    history: Sequence[dict],
    goal: Optional[str],
) -> Dict[str, float]:

    g = goal or DEFAULT_GOAL
    last = last_done_by_exercise(history)
    freq = frequency_28d(history)
    sr = success_rate(history)

    scores: Dict[str, float] = {}
    for ex in candidates:
        exid = str(ex.get("_id"))

        rec_days = days_ago(last.get(exid, now() - timedelta(days=60)))
        rec_norm = min(rec_days / 30.0, 1.0)

        freq_pen = 1.0 / (1.0 + freq.get(exid, 0))

        succ = sr.get(exid, 1.0)

        align = _goal_alignment(ex, g)

        score = 0.35 * align + 0.25 * rec_norm + 0.25 * freq_pen + 0.15 * succ
        scores[exid] = float(score)

    return scores

def choose_sets_reps(goal: Optional[str]) -> Tuple[int, int]:

    g = goal or DEFAULT_GOAL
    sets, reps = GOAL_TO_REP.get(g, GOAL_TO_REP[DEFAULT_GOAL])
    return sets, reps


def _progression_increment_lbs(primary_muscle: Optional[str]) -> float:
    if isinstance(primary_muscle, str) and primary_muscle in LOWER_BODY:
        return 5.0
    return 2.5 


def apply_progression(username: str, exercise: dict, history: Sequence[dict]) -> float:
    
    ex_id = str(exercise.get("_id"))
    pm = exercise.get(F_PRIMARY_MUSCLE)
    inc = _progression_increment_lbs(pm)

    last_weight: Optional[float] = None
    for w in history:
        for ex in w.get("exercises", []):
            if str(ex.get("exerciseId")) == ex_id:
                lw = ex.get("weight_lbs")
                if isinstance(lw, (int, float)):
                    last_weight = float(lw)
                    break
        if last_weight is not None:
            break

    if last_weight is not None:
        suggested = last_weight + inc
    else:
        suggested = float(exercise.get(F_DEFAULT_WEIGHT, 10.0))

    return max(round(suggested, 1), 0.0)
