import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";

const STRATEGY_LABEL = {
  NORMAL: null,
  REP_ADJUST: "Plateau adjustment",
  REVERSE: "Reversing adjustment",
  SWAPPED: "Suggested swap",
};

const GOAL_OPTIONS = [
  { value: "", label: "Any goal" },
  { value: "strength", label: "Strength" },
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "endurance", label: "Endurance" },
];

export default function RecommendationCard() {
  const [goal, setGoal] = useState("");
  const [focus, setFocus] = useState("");
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [feedbackSent, setFeedbackSent] = useState({});
  const navigate = useNavigate();

  const authHeaders = () => {
    const token = localStorage.getItem("token");
    return { Authorization: `Bearer ${token}` };
  };

  const fetchRecommendation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(
        "http://localhost:5000/api/v1/recommendation",
        { goal: goal || undefined, workoutFocus: focus || undefined },
        { headers: authHeaders() }
      );
      if (res.data?.success) {
        setRecommendation(res.data.data);
        setFeedbackSent({});
      } else {
        setError("Could not get a recommendation right now.");
      }
    } catch (err) {
      setError(
        err.response?.status === 502
          ? "The recommendation engine is unavailable right now."
          : "Failed to load a recommendation."
      );
    } finally {
      setLoading(false);
    }
  };

  const sendFeedback = async (item, action) => {
    setFeedbackSent((prev) => ({ ...prev, [item.recommendationItemId]: action }));
    try {
      await axios.post(
        "http://localhost:5000/api/v1/recommendation/feedback",
        {
          recommendationId: recommendation.recommendationId,
          recommendationItemId: item.recommendationItemId,
          action,
        },
        { headers: authHeaders() }
      );
    } catch {
      // Best-effort - the feedback endpoint itself tolerates the recommender being down.
    }
  };

  const startWorkout = () => {
    if (!recommendation) return;
    axios
      .post(
        "http://localhost:5000/api/v1/recommendation/feedback",
        { recommendationId: recommendation.recommendationId, action: "accept" },
        { headers: authHeaders() }
      )
      .catch(() => {});
    navigate("/new-workout", {
      state: {
        recommendationId: recommendation.recommendationId,
        recommendedExercises: recommendation.items,
      },
    });
  };

  return (
    <Card className="w-full max-w-2xl rounded-3xl border-white/10 bg-white/5 backdrop-blur shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]">
      <CardHeader className="pb-2">
        <CardTitle className="text-center text-3xl font-extrabold tracking-tight">
          Today's Suggestion
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-5">
        {!recommendation && (
          <>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="rounded-lg px-3 py-2 bg-[#0e141a]/70 text-[#dbe7ff] border border-white/10 text-sm"
              >
                {GOAL_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value} className="bg-[#0e141a]">
                    {o.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={focus}
                onChange={(e) => setFocus(e.target.value)}
                placeholder="Focus (e.g. push, pull, legs)"
                className="rounded-lg px-3 py-2 bg-[#0e141a]/70 text-[#dbe7ff] placeholder-[#90a0b5]/70 border border-white/10 text-sm flex-1 min-w-[180px]"
              />
            </div>
            <Button
              onClick={fetchRecommendation}
              disabled={loading}
              className="w-full h-11 rounded-xl font-semibold bg-[#3456cc] hover:bg-[#3d63e3] text-white transition-colors"
            >
              {loading ? "Thinking..." : "Get a Suggestion"}
            </Button>
            {error && <p className="text-red-300 text-sm text-center">{error}</p>}
          </>
        )}

        {recommendation && (
          <div className="space-y-4">
            {recommendation.items.length === 0 && (
              <p className="text-center text-[#9fb0c9] text-sm">
                No exercises matched right now - try a different focus or check your equipment in your profile.
              </p>
            )}

            {recommendation.items.map((item) => {
              const strategyLabel = STRATEGY_LABEL[item.strategy];
              const sent = feedbackSent[item.recommendationItemId];
              return (
                <div
                  key={item.recommendationItemId}
                  className="rounded-2xl border border-white/10 bg-black/20 p-4 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="font-semibold text-[#cfe0ff]">{item.exercise}</h4>
                    {strategyLabel && (
                      <span className="text-xs uppercase tracking-wide text-[#f0b955] bg-[#f0b955]/10 border border-[#f0b955]/30 rounded-full px-2 py-0.5">
                        {strategyLabel}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[#dbe7ff]">
                    {item.prescription.sets} sets x {item.prescription.reps} reps
                    {item.prescription.weight > 0 ? ` @ ${item.prescription.weight} ${item.prescription.unit}` : ""}
                  </p>
                  {item.reason && <p className="text-xs text-[#9fb0c9]">{item.reason}</p>}
                  {item.change && (
                    <p className="text-xs text-[#9fb0c9]/80">
                      {item.change.previous} &rarr; {item.change.today}
                    </p>
                  )}
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => sendFeedback(item, "thumbs_up")}
                      className="text-xs px-2 py-1 rounded-lg border border-white/10 hover:bg-white/10 text-[#dbe7ff]"
                    >
                      👍
                    </button>
                    <button
                      onClick={() => sendFeedback(item, "thumbs_down")}
                      className="text-xs px-2 py-1 rounded-lg border border-white/10 hover:bg-white/10 text-[#dbe7ff]"
                    >
                      👎
                    </button>
                    <button
                      onClick={() => sendFeedback(item, "swap")}
                      className="text-xs px-2 py-1 rounded-lg border border-white/10 hover:bg-white/10 text-[#dbe7ff]"
                    >
                      Swap
                    </button>
                    {sent && <span className="text-xs text-[#7fd39a] self-center">Thanks!</span>}
                  </div>
                </div>
              );
            })}

            <div className="flex gap-3">
              <Button
                onClick={startWorkout}
                disabled={recommendation.items.length === 0}
                className="flex-1 h-11 rounded-xl font-semibold bg-[#3456cc] hover:bg-[#3d63e3] text-white transition-colors"
              >
                Start This Workout
              </Button>
              <Button
                onClick={() => setRecommendation(null)}
                className="h-11 rounded-xl font-semibold bg-[#1a1f24] border border-white/10 hover:bg-[#22282f] text-white transition-colors"
              >
                Refresh
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
