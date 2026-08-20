import os

from dotenv import load_dotenv

load_dotenv()  # picks up ml/.env in local dev; a real deployment sets these directly

from fastapi import FastAPI, HTTPException, Response

from app.api.schemas import (
    ColdStartAssessmentRequest,
    ColdStartAssessmentResponse,
    EstimateCaloriesRequest,
    EstimateCaloriesResponse,
    FeedbackRequest,
    RecommendRequest,
    RecommendResponse,
)
from app.services.recommender import Recommender
from app.services.history import now
from app.services.ml import calorie_model
from app.services.ml.cold_start import assess_direct
from app.services.ml.model_registry import model_status
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


@app.post("/estimate-calories", response_model=EstimateCaloriesResponse)
def estimate_calories(req: EstimateCaloriesRequest):
    return calorie_model.estimate(
        duration_hours=req.durationHours,
        avg_bpm=req.avgHeartRate,
        weight_kg=req.weightKg,
        workout_type=req.workoutType,
        total_sets=req.totalSets,
    )


@app.get("/ml/status")
def ml_status():
    return model_status()


@app.post("/cold-start-assessment", response_model=ColdStartAssessmentResponse)
def cold_start_assessment(req: ColdStartAssessmentRequest):
    predicted_by_family = assess_direct(
        push_ups_per_set=req.pushUpsPerSet,
        bench_press_known_weight_lb=req.benchPressKnownWeightLb,
        bench_press_known_reps=req.benchPressKnownReps,
        squat_comfort=req.squatComfort,
    )
    try:
        recommender.db.fitness_assessments.insert_one(
            {
                "username": req.username,
                "inputs": req.model_dump(exclude={"username"}),
                "predictedByFamily": predicted_by_family,
                "modelVersion": "cold-start-direct-0.1.0",
                "createdAt": now(),
            }
        )
    except Exception:
        pass  # best-effort persistence - still return the assessment even if the write failed
    return {"predictedByFamily": predicted_by_family}
