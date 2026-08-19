import React, { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";

export default function CurrentGoal({ onChange, goal }) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [goalExists, setGoalExists] = useState(false);

  const getWeekStart = () => {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - dayOfWeek);
    weekStart.setHours(0, 0, 0, 0);
    return weekStart.toISOString();
  };

  useEffect(() => {
    const fetchGoal = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        const weekStart = getWeekStart();
        const response = await axios.get("http://localhost:5000/api/v1/goal", {
          headers: { Authorization: `Bearer ${token}` },
          params: { weekStart },
        });

        if (response.data?.data?.goal?.goalText) {
          onChange({ target: { value: response.data.data.goal.goalText } });
          setGoalExists(true);
        }
      } catch (err) {
        if (err.response?.status !== 404) console.error(err);
        setGoalExists(false);
      }
    };
    fetchGoal();
    // Runs once on mount only - `onChange` is Dashboard's setState setter passed
    // down fresh each render; depending on it here would refetch on every parent
    // re-render instead of once when this card mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSaveGoal = async () => {
    if (!goal.trim()) {
      alert("Please enter a goal before saving.");
      return;
    }

    try {
      setIsSaving(true);
      const token = localStorage.getItem("token");
      if (!token) {
        alert("You must be logged in to save goals.");
        return;
      }

      const weekStart = getWeekStart();
      const goalData = { goalText: goal.trim(), weekStart };
      const config = {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      };

      if (goalExists) {
        await axios.put("http://localhost:5000/api/v1/goal", goalData, config);
      } else {
        await axios.post("http://localhost:5000/api/v1/goal", goalData, config);
        setGoalExists(true);
      }

      setLastSaved(new Date());
    } catch (err) {
      console.error("Failed to save goal:", err.response?.data || err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card
      className="
        w-full max-w-2xl rounded-3xl border-white/10 bg-white/5
        backdrop-blur
        shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]
      "
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-center text-3xl font-extrabold tracking-tight">
          This Week’s Goal
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-5">
        <div
          className="
            rounded-2xl border border-white/10 p-4
            bg-black/20
            shadow-[inset_0_0_0_1px_rgba(255,255,255,0.03),inset_0_12px_40px_-20px_rgba(255,255,255,0.06)]
          "
        >
          <Textarea
            value={goal}
            onChange={onChange}
            placeholder="Enter your goal..."
            className="
              min-h-[9rem] resize-none bg-transparent
              focus-visible:ring-2 focus-visible:ring-white/15
              font-hand text-2xl leading-relaxed
              text-[#e6eee2] placeholder-[#9fb49a]/80 placeholder:italic
              border-none shadow-none
            "
          />
        </div>

        <p className="text-center text-gray-300/90">
          Tip: keep it specific and measurable.
        </p>

        <div className="flex items-center justify-between">
          <Button
            onClick={handleSaveGoal}
            disabled={isSaving || !goal.trim()}
            className={`
              px-6 py-2 rounded-lg font-semibold text-white
              transition-colors shadow-md
              ${isSaving || !goal.trim()
                ? "bg-gray-700/60 border border-white/10 cursor-not-allowed"
                : "bg-[#1a1f24] border border-white/10 hover:bg-[#22282f]"}
            `}
          >
            {isSaving ? "Saving..." : "Save Goal"}
          </Button>

          {lastSaved && (
            <span className="text-sm text-gray-400">
              Saved at {lastSaved.toLocaleTimeString()}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
