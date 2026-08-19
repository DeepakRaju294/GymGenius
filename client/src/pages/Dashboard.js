import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import StartWorkout from "../components/StartWorkout";
import CurrentGoal from "../components/CurrentGoal";
import axios from "axios";

export default function Dashboard() {
  const [goal, setGoal] = useState("");
  const [goalExists, setGoalExists] = useState(false);

  useEffect(() => {
    const fetchGoal = async () => {
      try {
        const now = new Date();
        const startOfWeek = new Date(now);
        const day = now.getDay();
        startOfWeek.setDate(now.getDate() - day);
        startOfWeek.setHours(0, 0, 0, 0);

        const token = localStorage.getItem("token");
        const res = await axios.get("http://localhost:5000/api/v1/goal", {
          headers: { Authorization: `Bearer ${token}` },
          params: {weekStart: startOfWeek}
        });

        if (res.data?.data?.goalText) {
          setGoal(res.data.data.goalText);
          setGoalExists(true);
        }
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error("Failed to fetch goal:", err.response?.data || err.message);
        }
      }
    };

    fetchGoal();
  }, []);

  const handleGoalChange = async (e) => {
    const newGoal = e.target.value;
    setGoal(newGoal);
    const now = new Date();
    const startOfWeek = new Date(now);
    const day = now.getDay();
    startOfWeek.setDate(now.getDate() - day);
    startOfWeek.setHours(0, 0, 0, 0);
    
    try {
      const token = localStorage.getItem("token");
      const payload = { goalText: newGoal, weekStart: startOfWeek };

      if (goalExists) {
        await axios.put("http://localhost:5000/api/v1/goal", payload, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } else {
        await axios.post("http://localhost:5000/api/v1/goal", payload, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setGoalExists(true);
      }
    } catch (err) {
      console.error("Failed to save goal:", err.response?.data || err.message);
    }
  };

  return (
    <div className="relative min-h-screen text-white overflow-hidden">
      <div
        className="absolute inset-0 -z-10"
        style={{
          background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)",
        }}
      />

      <div
        className="absolute inset-0 -z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(60% 50% at 90% 90%, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.05) 40%, rgba(13,18,24,0) 75%)",
        }}
      />

      <div
        className="absolute inset-0 -z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(50% 40% at 50% 8%, rgba(255,255,255,0.06) 0%, rgba(13,18,24,0) 70%)",
        }}
      />

      <div className="absolute inset-0 -z-10 pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]" />

      <Header />

      <main className="mx-auto w-full max-w-4xl px-6 pt-16 pb-24 flex flex-col items-center gap-12 relative z-10">
        <StartWorkout />
        <CurrentGoal goal={goal} onChange={handleGoalChange} />
      </main>
    </div>
  );
}
