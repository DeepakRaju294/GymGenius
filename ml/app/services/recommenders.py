from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional

from app.util.db import mongo
from app.util.cache import cache_get, cache_set
from app.services.features import (
    candidate_pool,
    score_rules,
    choose_sets_reps,
    apply_progression,
    now,
)

try:
    from app.util.cache import _client as _redis_client  
except Exception:  
    _redis_client = None


class Recommender:
    def __init__(self) -> None:
        self.db = mongo()
        self.ttl_seconds = int(os.getenv("REC_TTL_SECONDS", "1800")) 


    def recommend(
        self,
        username: str,
        goal: Optional[str],
        focus: Optional[str],
        topn: int = 6,
    ) -> Dict:
        
        key = self._cache_key(username, goal, focus)
        cached = cache_get(key)
        if cached:
            return cached

        candidates, history = candidate_pool(username, focus)

        if not candidates:
            items = self._fallback_items(goal, topn)
            rec = {"recId": uuid.uuid4().hex, "items": items}
            cache_set(key, rec, self.ttl_seconds)
            self._log_event(username, "rec_shown", rec)
            return rec

        scores = score_rules(username, candidates, history, goal)
        ranked = sorted(candidates, key=lambda ex: scores.get(str(ex["_id"]), 0.0), reverse=True)[:topn]

        items: List[Dict] = []
        for ex in ranked:
            sets, reps = choose_sets_reps(goal)
            weight = apply_progression(username, ex, history)
            items.append(
                {
                    "exerciseId": str(ex["_id"]),
                    "name": ex.get("name", "Exercise"),
                    "sets": int(sets),
                    "reps": int(reps),
                    "weight_lbs": float(weight),
                    "reason": "rule-based match",
                }
            )

        rec = {"recId": uuid.uuid4().hex, "items": items}
        cache_set(key, rec, self.ttl_seconds)
        self._log_event(username, "rec_shown", rec)
        return rec

    def record_feedback(self, fb_model) -> None:
        
        doc = fb_model.model_dump() if hasattr(fb_model, "model_dump") else dict(fb_model)
        doc["ts"] = now()
        self.db.rec_feedback.insert_one(doc)
        self._log_event(doc.get("username", ""), "rec_feedback", doc
        if doc.get("action") in {"swap", "thumbs_down"}:
            self._invalidate_user_cache(doc.get("username", ""))

    def _cache_key(self, username: str, goal: Optional[str], focus: Optional[str]) -> str:
        g = goal or ""
        f = focus or ""
        return f"rec:{username}:{g}:{f}"

    def _fallback_items(self, goal: Optional[str], topn: int) -> List[Dict]:
        
        sets, reps = choose_sets_reps(goal)
        items: List[Dict] = []
        for ex in self.db.exercises.find().limit(topn):
            items.append(
                {
                    "exerciseId": str(ex["_id"]),
                    "name": ex.get("name", "Exercise"),
                    "sets": int(sets),
                    "reps": int(reps),
                    "weight_lbs": float(ex.get("default_weight_lbs", 10.0)),
                    "reason": "fallback",
                }
            )
        return items

    def _log_event(self, username: str, etype: str, payload: Dict) -> None:
        try:
            self.db.events.insert_one(
                {"username": username, "type": etype, "payload": payload, "ts": now()}
            )
        except Exception:
            pass

    def _invalidate_user_cache(self, username: str) -> None:
        """Delete all rec cache keys for this user (pattern match)."""
        if not username or _redis_client is None:
            return
        try:
            r = _redis_client()
            it = r.scan_iter(match=f"rec:{username}:*")
            for k in it:
                try:
                    r.delete(k)
                except Exception:
                    pass
        except Exception:
            pass
