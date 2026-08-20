from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

GoalLiteral = Literal["strength", "hypertrophy", "endurance"]
FocusLiteral = Optional[str]
FeedbackAction = Literal["accept", "swap", "thumbs_up", "thumbs_down"]
StrategyLiteral = Literal["NORMAL", "REP_ADJUST", "REVERSE", "SWAPPED"]


class Prescription(BaseModel):
    sets: int = Field(..., ge=1, le=10)
    reps: int = Field(..., ge=1, le=30)
    weight: float = Field(..., ge=0, description="Suggested working weight")
    unit: Literal["lb", "kg"] = "lb"


class Change(BaseModel):
    previous: str
    today: str


class RecItem(BaseModel):
    recommendationItemId: str = Field(..., description="Identifies this one prescribed exercise within the recommendation")
    exerciseId: str
    exercise: str = Field(..., description="Human-readable exercise name")
    prescription: Prescription
    strategy: StrategyLiteral = Field(..., description="Adaptation strategy behind this prescription")
    reason: Optional[str] = Field(None, description="Human-readable rationale shown to the user")
    change: Optional[Change] = Field(None, description="Previous vs. today's prescription, if there's history to compare against")


class RecommendRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(..., description="User identifier")
    goal: Optional[GoalLiteral] = Field(None, description="Training goal for this session")
    workoutFocus: FocusLiteral = Field(None, description="Focus tag (e.g., 'push', 'pull', 'legs')")


class RecommendContext(BaseModel):
    goal: Optional[str] = None
    focus: Optional[str] = None
    policyVersion: str = Field(..., description="Which ProgressionPolicy generated this recommendation")


class RecommendResponse(BaseModel):
    recommendationId: str = Field(..., description="Identifies this whole recommendation session")
    items: List[RecItem]
    context: RecommendContext


class FeedbackRequest(BaseModel):
    recommendationId: str = Field(..., description="Which recommendation session this feedback is about")
    recommendationItemId: Optional[str] = Field(None, description="Which item within it, if the feedback is item-specific")
    username: str
    action: FeedbackAction
    reason: Optional[str] = Field(None, description="Optional reason ('no equipment', 'too heavy')")


class EstimateCaloriesRequest(BaseModel):
    durationHours: float = Field(..., gt=0, le=6)
    weightKg: float = Field(..., gt=0, le=300)
    workoutType: Literal["Cardio", "Strength", "HIIT", "Yoga"] = "Strength"
    avgHeartRate: Optional[float] = Field(None, gt=0, le=250, description="If omitted, falls back to the MET-intensity estimate")
    totalSets: int = Field(0, ge=0, description="Used by the MET fallback to infer session intensity")


class EstimateCaloriesResponse(BaseModel):
    estimatedCalories: float
    method: Literal["model", "met"]
    modelVersion: Optional[str] = None
    intensityCategory: Optional[str] = None
