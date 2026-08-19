import React from "react";
import { Link } from "react-router-dom";
import { Button } from "./ui/button";

export default function StartWorkout() {
  return (
    <Link to="/new-workout" className="w-full max-w-2xl">
      <Button
        className="
          w-full h-16 rounded-2xl text-xl font-bold
          bg-[#1a1f24] border border-white/10
          hover:bg-[#22282f]
          shadow-[0_10px_30px_-12px_rgba(0,0,0,0.6)]
          transition-colors
        "
      >
        Start Workout
      </Button>
    </Link>
  );
}