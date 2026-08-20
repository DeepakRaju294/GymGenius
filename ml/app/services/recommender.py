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
from app.services.ml.similarity import rank_by_similarity


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
        fitness_assessment = self.db.fitness_assessments.find_one({"username": username}, sort=[("createdAt", -1)])
        bodyweight_kg = self._bodyweight_kg(username)

        if not candidates:
            items = self._fallback_items(goal, topn)
        else:
            scores = score_rules(candidates, history, goal, catalog)
            ranked = sorted(candidates, key=lambda ex: scores.get(ex["exerciseId"], 0.0), reverse=True)[:topn]
            items = []
            used_ids: set = set()
            for ex in ranked:
                resolved_ex, swap_note = self._resolve_candidate(username, ex, ranked, used_ids)
                used_ids.add(resolved_ex["exerciseId"])
                items.append(
                    self._build_item(
                        username,
                        resolved_ex,
                        history,
                        goal,
                        catalog=catalog,
                        fitness_assessment=fitness_assessment,
                        bodyweight_kg=bodyweight_kg,
                        swap_note=swap_note,
                    )
                )

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

    def _resolve_candidate(self, username: str, ex: dict, ranked: List[dict], used_ids: set) -> "tuple[dict, Optional[str]]":
        """If this candidate's OWN progression state is already SWAPPED, don't
        keep recommending it (docs/SPEC.md §4.2's whole point of that state) -
        substitute a similar exercise from the rest of today's already
        hard-filtered candidate pool instead (docs/ML_SPEC.md §2). Ranking among
        those candidates never bypasses equipment/caution filtering, since
        `ranked` already passed through Selection. Returns (exercise_to_actually_
        recommend, swap_note); swap_note is None when no substitution happened."""
        exercise_id = ex["exerciseId"]
        state = self.db.progression_state.find_one({"username": username, "exerciseId": exercise_id})
        if not state or state.get("currentStrategy") != "SWAPPED":
            return ex, None

        pool_ids = [c["exerciseId"] for c in ranked if c["exerciseId"] not in used_ids]
        substitute_ids = rank_by_similarity(exercise_id, pool_ids, k=3)
        by_id = {c["exerciseId"]: c for c in ranked}
        for sub_id in substitute_ids:
            if sub_id in by_id:
                return by_id[sub_id], f"Swapped out for {ex.get('name', 'the previous exercise')}, which had plateaued."

        return ex, None  # no eligible substitute in today's pool - better to keep the original than drop it

    def _build_item(
        self,
        username: str,
        ex: dict,
        history: List[dict],
        goal: Optional[str],
        catalog: Optional[Dict[str, dict]] = None,
        fitness_assessment: Optional[dict] = None,
        bodyweight_kg: Optional[float] = None,
        swap_note: Optional[str] = None,
    ) -> Dict:
        exercise_id = ex["exerciseId"]
        state = self._get_or_advance_state(username, exercise_id, history)
        strategy = state.get("currentStrategy", "NORMAL")
        sets, reps = choose_sets_reps(goal)
        progression = apply_progression(
            exercise_id,
            ex.get("primaryMuscle"),
            history,
            movement_pattern=ex.get("movementPattern"),
            equipment=ex.get("equipment"),
            catalog=catalog,
            fitness_assessment=fitness_assessment,
            bodyweight_kg=bodyweight_kg,
        )
        baseline_weight, evidence_tier = progression if progression else (None, None)
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
            # This branch means the SUBSTITUTE itself already carries a SWAPPED
            # state from its own independent history - rare (a substitute would
            # have to have separately plateaued through its own full cycle), but
            # possible; not the common path, which is swap_note below.
            weight = baseline_weight
            reason = f"Still plateaued after reversing on {ex.get('name', 'this exercise')} too - may be worth reviewing this muscle group's programming."
        else:
            weight = baseline_weight
            reason = self._normal_reason(weight, prev_weight, evidence_tier, ex.get("name", "this exercise"))

        if swap_note:
            reason = f"{swap_note} {reason}"

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

    def _normal_reason(self, weight: float, prev_weight: Optional[float], evidence_tier: Optional[str], exercise_name: str) -> str:
        if evidence_tier == "recent_history":
            if prev_weight is not None and weight > prev_weight:
                return f"Up {weight - prev_weight:g} lb from your last session."
            return "Matching your last session's weight."
        if evidence_tier == "related_exercise_history":
            return f"Estimated from your history on a similar movement - adjust as needed for {exercise_name}."
        if evidence_tier == "anchor_performance":
            return "Based on what you told us about your strength on a related lift."
        if evidence_tier == "population_range":
            return "A conservative starting suggestion for a first attempt - not personalized yet, adjust freely."
        return "First time logging this - start here and we'll tune it from your results."

    def _bodyweight_kg(self, username: str) -> Optional[float]:
        """For §3 tier 5's bodyweight_multiplier starting ranges. Profile weight
        may be logged in lb or kg (docs/SPEC.md §3's profileModel)."""
        profile = self.db.profiles.find_one({"username": username})
        if not profile or profile.get("weight") is None:
            return None
        weight = profile["weight"]
        return weight if profile.get("weightUnit") == "kg" else weight * 0.453592

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
