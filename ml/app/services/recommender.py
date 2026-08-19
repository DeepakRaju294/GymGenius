from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional

from app.utils.db import mongo
from app.utils.cache import CACHE_ENABLED, cache_delete_prefix, cache_get, cache_set
from app.services.history import get_exercise_catalog, last_top_weight, now, sessions_for_exercise
from app.services.selection.candidate_pool import candidate_pool
from app.services.selection.scorer import score_rules
from app.services.prescription.targets import choose_sets_reps
from app.services.prescription.progression import apply_progression
from app.services.adaptation.policy import ProgressionPolicy
from app.services.adaptation.plateau import advance, fresh_state
from app.services.adaptation.strategies import rep_adjust, reverse


class Recommender:
    """Orchestrates Selection -> Prescription -> Adaptation (docs/SPEC.md §4.0) and
    persists what was recommended (§4.7) so it can later be compared against what
    was actually logged."""

    def __init__(self) -> None:
        # Deliberately does NOT call mongo() here. main.py instantiates Recommender
        # at module import time so /healthz can respond even if Mongo is
        # unreachable - for a `mongodb+srv://` URI, MongoClient's constructor
        # eagerly resolves the SRV DNS record, so touching Mongo during __init__
        # would take the whole app down before it ever finished booting. `db` is a
        # lazy property instead; app.utils.db.mongo() memoizes the client after the
        # first successful connect, so this costs nothing on the hot path.
        self.policy = ProgressionPolicy()
        self.ttl_seconds = int(os.getenv("REC_TTL_SECONDS", "1800"))

    @property
    def db(self):
        return mongo()

    def recommend(self, username: str, goal: Optional[str], focus: Optional[str], topn: int = 6) -> Dict:
        cache_key = self._cache_key(username, goal, focus)
        if CACHE_ENABLED:
            cached = cache_get(cache_key)
            if cached:
                return cached

        candidates, history = candidate_pool(username, focus)
        catalog = get_exercise_catalog()

        if not candidates:
            items = self._fallback_items(goal, topn)
        else:
            scores = score_rules(candidates, history, goal, catalog)
            ranked = sorted(candidates, key=lambda ex: scores.get(ex["exerciseId"], 0.0), reverse=True)[:topn]
            items = [self._build_item(username, ex, history, goal) for ex in ranked]

        rec = {
            "recommendationId": uuid.uuid4().hex,
            "items": items,
            "context": {"goal": goal, "focus": focus, "policyVersion": self.policy.version},
        }
        self._persist_recommendation(username, rec)
        if CACHE_ENABLED:
            cache_set(cache_key, rec, self.ttl_seconds)
        self._log_event(username, "rec_shown", {"recommendationId": rec["recommendationId"]})
        return rec

    def record_feedback(self, fb) -> None:
        doc = fb.model_dump() if hasattr(fb, "model_dump") else dict(fb)
        doc["ts"] = now()
        self.db.rec_feedback.insert_one(doc)
        self._log_event(doc.get("username", ""), "rec_feedback", doc)
        # Invariant (docs/SPEC.md §8.8): swap/thumbs_down never touch progression_state
        # directly - a swap can mean "I don't like this exercise" as easily as "this
        # strategy failed"; only sustained poor completion/progression should move
        # the plateau state machine. This just clears the cache so a swap is reflected
        # in the next call.
        if CACHE_ENABLED and doc.get("action") in {"swap", "thumbs_down"}:
            cache_delete_prefix(f"rec:{doc.get('username', '')}:")

    # -- Selection + Prescription + Adaptation for one exercise ---------------

    def _build_item(self, username: str, ex: dict, history: List[dict], goal: Optional[str]) -> Dict:
        exercise_id = ex["exerciseId"]
        state = self._get_or_advance_state(username, exercise_id, history)
        strategy = state.get("currentStrategy", "NORMAL")
        sets, reps = choose_sets_reps(goal)
        baseline_weight = apply_progression(exercise_id, ex.get("primaryMuscle"), history)
        prev_weight = last_top_weight(history, exercise_id)

        if baseline_weight is None:
            weight = 0.0
            reason = f"No history yet for {ex.get('name', 'this exercise')} - enter your own starting weight and we'll tune it from there."
            strategy = "NORMAL"
        elif strategy == "REP_ADJUST":
            reps, weight = rep_adjust(reps, baseline_weight)
            reason = f"{ex.get('name', 'This exercise')} has plateaued - trying lower reps, higher weight."
        elif strategy == "REVERSE":
            reps, weight = reverse(reps, baseline_weight)
            reason = f"Still plateaued on {ex.get('name', 'this exercise')} - reversing to higher reps, lower weight."
        elif strategy == "SWAPPED":
            weight = baseline_weight
            reason = f"Still plateaued after reversing on {ex.get('name', 'this exercise')} - consider swapping it out for a similar movement."
        else:
            weight = baseline_weight
            reason = self._normal_reason(weight, prev_weight)

        change = None
        if prev_weight is not None:
            change = {"previous": f"{prev_weight:g} lb", "today": f"{weight:g} lb x {reps}"}

        return {
            "recommendationItemId": uuid.uuid4().hex,
            "exerciseId": exercise_id,
            "exercise": ex.get("name", "Exercise"),
            "prescription": {"sets": int(sets), "reps": int(reps), "weight": float(weight), "unit": "lb"},
            "strategy": strategy,
            "reason": reason,
            "change": change,
        }

    def _get_or_advance_state(self, username: str, exercise_id: str, history: List[dict]) -> Dict:
        state = self.db.progression_state.find_one({"username": username, "exerciseId": exercise_id})
        sessions = sessions_for_exercise(history, exercise_id)
        if not sessions:
            return state or fresh_state()

        latest_date, latest_1rm = sessions[-1]
        if state is None:
            state = fresh_state()

        already_evaluated = state.get("lastEvaluatedAt")
        if already_evaluated is not None and latest_date <= already_evaluated:
            return state  # nothing new logged since we last evaluated this exercise

        state, events = advance(state, latest_1rm, self.policy, session_ts=latest_date)
        state["lastEvaluatedAt"] = latest_date
        self.db.progression_state.update_one(
            {"username": username, "exerciseId": exercise_id},
            {"$set": state},
            upsert=True,
        )
        for ev in events:
            ev.update({"username": username, "exerciseId": exercise_id, "ts": now()})
            self.db.progression_events.insert_one(ev)
        return state

    def _normal_reason(self, weight: float, prev_weight: Optional[float]) -> str:
        if prev_weight is None:
            return "First time logging this - start here and we'll tune it from your results."
        if weight > prev_weight:
            return f"Up {weight - prev_weight:g} lb from your last session."
        return "Matching your last session's weight."

    # -- persistence ------------------------------------------------------------

    def _persist_recommendation(self, username: str, rec: Dict) -> None:
        doc = {
            "recommendationId": rec["recommendationId"],
            "username": username,
            "createdAt": now(),
            "items": rec["items"],
            "context": rec["context"],
        }
        try:
            self.db.recommendations.insert_one(doc)
        except Exception:
            pass

    def _cache_key(self, username: str, goal: Optional[str], focus: Optional[str]) -> str:
        return f"rec:{username}:{goal or ''}:{focus or ''}"

    def _fallback_items(self, goal: Optional[str], topn: int) -> List[Dict]:
        sets, reps = choose_sets_reps(goal)
        items: List[Dict] = []
        for ex in self.db.exercises.find().limit(topn):
            items.append(
                {
                    "recommendationItemId": uuid.uuid4().hex,
                    "exerciseId": ex.get("exerciseId"),
                    "exercise": ex.get("name", "Exercise"),
                    "prescription": {"sets": int(sets), "reps": int(reps), "weight": 0.0, "unit": "lb"},
                    "strategy": "NORMAL",
                    "reason": "Getting started - log a set to personalize your weight suggestions.",
                    "change": None,
                }
            )
        return items

    def _log_event(self, username: str, etype: str, payload: Dict) -> None:
        try:
            self.db.events.insert_one({"username": username, "type": etype, "payload": payload, "ts": now()})
        except Exception:
            pass
