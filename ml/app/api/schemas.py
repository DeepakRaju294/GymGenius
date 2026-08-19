from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class RecItem(BaseModel):
    exerciseId: str = Field(..., description="ID of the recommended exercise")
    name: str = Field(..., description="Human-readable exercise name")
    sets: int = Field(..., ge=1, le=10, description="Number of sets to perform")
    reps: int = Field(..., ge=1, le=30, description="Target reps per set")
    weight_lbs: float = Field(
        ..., ge=0, description="Suggested working weight (lbs only)"
    )
    reason: Optional[str] = Field(
        None, description="Short rationale (e.g., 'rule-based match', 'fallback')"
    )


GoalLiteral = Literal["strength", "hypertrophy", "endurance"]
FocusLiteral = Optional[str] 
FeedbackAction = Literal["accept", "swap", "thumbs_up", "thumbs_down"]


class RecommendRequest(BaseModel):
   
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(..., description="User identifier")
    goal: Optional[GoalLiteral] = Field(
        None, description="Training goal for this session"
    )
    workoutFocus: FocusLiteral = Field(
        None, description="Focus tag (e.g., 'push', 'pull', 'legs')"
    )


class FeedbackRequest(BaseModel):

    recId: str = Field(..., description="Recommendation bundle identifier")
    username: str = Field(..., description="User identifier")
    exerciseId: str = Field(..., description="Exercise identifier from the rec")
    action: FeedbackAction = Field(..., description="Feedback action")
    reason: Optional[str] = Field(
        None, description="Optional reason ('no equipment', 'too heavy')"
    )

class RecommendResponse(BaseModel):
    recId: str = Field(..., description="Recommendation bundle identifier")
    items: List[RecItem]
