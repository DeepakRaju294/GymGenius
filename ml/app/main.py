import os

from dotenv import load_dotenv

load_dotenv()  # picks up ml/.env in local dev; a real deployment sets these directly

from fastapi import FastAPI, HTTPException, Response

from app.api.schemas import FeedbackRequest, RecommendRequest, RecommendResponse
from app.services.recommender import Recommender
from app.utils.cache import redis_ping
from app.utils.db import ensure_indexes, mongo_ping

APP_NAME = os.getenv("SERVICE_NAME", "recommender")
BUILD_SHA = os.getenv("BUILD_SHA", "dev")

app = FastAPI(title="GymGenius Recommender", version=BUILD_SHA)
recommender = Recommender()


@app.on_event("startup")
def _startup() -> None:
    ensure_indexes()


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": APP_NAME, "version": BUILD_SHA}


@app.get("/readyz")
def readyz():
    checks = {"mongo": "ok", "redis": "ok"}
    try:
        mongo_ping()
    except Exception:
        checks["mongo"] = "fail"
    try:
        if not redis_ping():
            checks["redis"] = "fail"
    except Exception:
        checks["redis"] = "fail"

    if "fail" in checks.values():
        raise HTTPException(status_code=503, detail={"status": "fail", **checks, "version": BUILD_SHA})
    return {"status": "ok", **checks, "version": BUILD_SHA}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    try:
        return recommender.recommend(username=req.username, goal=req.goal, focus=req.workoutFocus, topn=6)
    except Exception:
        raise HTTPException(status_code=500, detail="failed to generate recommendations")


@app.post("/feedback", status_code=204)
def feedback(req: FeedbackRequest):
    try:
        recommender.record_feedback(req)
    except Exception:
        pass
    return Response(status_code=204)
