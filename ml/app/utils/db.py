from __future__ import annotations

import os
import threading
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "gymgenius")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None
_lock = threading.Lock()


def mongo() -> Database:
    global _client, _db
    if _db is not None:
        return _db
    with _lock:
        if _db is not None:
            return _db
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=2000,
            retryWrites=True,
        )
        _db = _client[MONGO_DB]
    return _db


def get_collection(name: str) -> Collection:
    return mongo()[name]


def mongo_ping() -> dict:
    try:
        return mongo().command("ping")
    except PyMongoError as e:
        raise e


def ensure_indexes() -> None:
    """Create the indexes documented in docs/SPEC.md §3. Idempotent - safe to call
    on every startup. mongo() is deliberately called INSIDE the try block: for a
    `mongodb+srv://` URI its constructor eagerly resolves DNS, and that failure
    must not prevent the app from finishing startup (see Recommender.db)."""
    try:
        db = mongo()
        db.exercises.create_index("exerciseId", unique=True)
        db.histories.create_index([("username", 1), ("workoutDate", -1)])
        db.profiles.create_index("username", unique=True)
        db.progression_state.create_index([("username", 1), ("exerciseId", 1)], unique=True)
        db.progression_events.create_index([("username", 1), ("exerciseId", 1), ("ts", -1)])
        db.recommendations.create_index("recommendationId", unique=True)
        db.recommendations.create_index([("username", 1), ("createdAt", -1)])
        db.fitness_assessments.create_index([("username", 1), ("createdAt", -1)])
    except PyMongoError:
        pass
