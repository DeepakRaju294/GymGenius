import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import StrengthProgressChart from '../components/charts/StrengthProgressChart';
import MuscleVolumeChart from '../components/charts/MuscleVolumeChart';
import WorkoutFrequencyHeatmap from '../components/charts/WorkoutFrequencyHeatmap';
import PersonalRecordsList from '../components/charts/PersonalRecordsList';

export default function Progress() {
  const [exercises, setExercises] = useState([]);
  const [selectedExerciseId, setSelectedExerciseId] = useState('');

  useEffect(() => {
    const fetchLoggedExercises = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:5000/api/v1/history/records', {
          headers: { Authorization: `Bearer ${token}` }
        });
        const list = res.data?.data?.records || [];
        setExercises(list);
        if (list.length) setSelectedExerciseId(list[0].exerciseId);
      } catch (err) {
        console.error('Failed to load exercises for progress chart:', err.response?.data || err.message);
      }
    };
    fetchLoggedExercises();
  }, []);

  const selected = exercises.find(e => e.exerciseId === selectedExerciseId);

  const shellBg = "absolute inset-0 -z-10";
  const card = "rounded-[18px] border border-white/10 bg-white/5 backdrop-blur p-6 md:p-8 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]";

  return (
    <div className="relative min-h-screen text-white">
      <div className={shellBg} style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
      <div className={`${shellBg} pointer-events-none`} style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
      <div className={`${shellBg} pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]`} />

      <div className="relative flex items-center justify-center px-4 pt-10 pb-6">
        <Link to="/dashboard" className="absolute left-4 top-1/2 -translate-y-1/2 opacity-90 hover:opacity-100 transition">
          <img src="/Back.png" alt="Back" className="w-10 h-10" />
        </Link>
        <h2 className="text-[26px] md:text-[30px] font-extrabold tracking-tight text-[#8fb0ff]">Progress</h2>
      </div>

      <main className="mx-auto w-full max-w-4xl px-4 pb-16 space-y-6">
        <section className={card}>
          <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
            <h3 className="text-sm font-semibold text-[#b9c7da]">Strength progression</h3>
            {exercises.length > 0 && (
              <select
                value={selectedExerciseId}
                onChange={e => setSelectedExerciseId(e.target.value)}
                className="rounded-lg px-3 py-1.5 bg-[#0e141a]/70 text-[#dbe7ff] border border-white/10 text-sm appearance-none"
              >
                {exercises.map(e => (
                  <option key={e.exerciseId} value={e.exerciseId} className="bg-[#0e141a]">{e.name}</option>
                ))}
              </select>
            )}
          </div>
          {exercises.length === 0 ? (
            <p className="text-sm text-[#9fb0c9]">Log a workout to start tracking strength progress.</p>
          ) : (
            <StrengthProgressChart exerciseId={selectedExerciseId} exerciseName={selected?.name} />
          )}
        </section>

        <section className={card}>
          <h3 className="text-sm font-semibold text-[#b9c7da] mb-3">Weekly volume by muscle group</h3>
          <MuscleVolumeChart />
        </section>

        <section className={card}>
          <h3 className="text-sm font-semibold text-[#b9c7da] mb-3">Workout frequency</h3>
          <WorkoutFrequencyHeatmap />
        </section>

        <section className={card}>
          <h3 className="text-sm font-semibold text-[#b9c7da] mb-3">Personal records</h3>
          <PersonalRecordsList />
        </section>
      </main>
    </div>
  );
}
