import { React, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function NewWorkout() {
  const [time, setTime] = useState(0);
  const [exercises, setExercises] = useState([]);
  const [workoutFocus, setWorkoutFocus] = useState('');
  const [goalText, setGoalText] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [selectedExerciseId, setSelectedExerciseId] = useState('');

  const navigate = useNavigate();
  const location = useLocation();

  const authHeaders = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  };

  useEffect(() => {
    const fetchWeeklyGoal = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;

        const now = new Date();
        const startOfWeek = new Date(now);
        const day = now.getDay();
        startOfWeek.setDate(now.getDate() - day);
        startOfWeek.setHours(0, 0, 0, 0);

        const response = await axios.get('http://localhost:5000/api/v1/goal', {
          headers: authHeaders(),
          params: { weekStart: startOfWeek }
        });

        if (response.data?.data?.goal?.goalText) {
          setGoalText(response.data.data.goal.goalText);
        }
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error('Failed to load goalText:', err.response?.data || err.message);
        }
      }
    };

    const fetchCatalog = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/v1/exercises', {
          headers: authHeaders()
        });
        const list = response.data?.data?.exercises || [];
        setCatalog(list);
        if (list.length && !selectedExerciseId) setSelectedExerciseId(list[0].exerciseId);
      } catch (err) {
        console.error('Failed to load exercise catalog:', err.response?.data || err.message);
      }
    };

    fetchWeeklyGoal();
    fetchCatalog();

    // Pre-fill from a recommendation the user chose to start (Dashboard "Start This Workout").
    const state = location.state;
    if (state?.recommendedExercises?.length) {
      setExercises(
        state.recommendedExercises.map((item) => ({
          exerciseId: item.exerciseId,
          name: item.exercise,
          recommendationId: state.recommendationId,
          recommendationItemId: item.recommendationItemId,
          sets: [
            {
              reps: String(item.prescription.reps),
              weight: item.prescription.weight > 0 ? String(item.prescription.weight) : '',
              weightUnit: item.prescription.unit || 'lb',
              notes: ''
            }
          ]
        }))
      );
      if (!workoutFocus) setWorkoutFocus('Recommended session');
    }

    const interval = setInterval(() => setTime(t => t + 1), 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function convertTime(totalSeconds) {
    let hour = Math.floor(totalSeconds / 3600);
    let min = Math.floor((totalSeconds % 3600) / 60);
    let sec = totalSeconds % 60;

    const pad = val => String(val).padStart(2, '0');

    return `${pad(hour)}:${pad(min)}:${pad(sec)}`;
  }

  const addExercise = () => {
    const catalogEntry = catalog.find(ex => ex.exerciseId === selectedExerciseId);
    if (!catalogEntry) {
      alert('Pick an exercise first.');
      return;
    }
    setExercises([
      ...exercises,
      {
        exerciseId: catalogEntry.exerciseId,
        name: catalogEntry.name,
        sets: [{ reps: '', weight: '', weightUnit: 'lb', notes: '' }]
      }
    ]);
  };

  const addSet = exerciseIndex => {
    const updated = [...exercises];
    updated[exerciseIndex].sets.push({ reps: '', weight: '', weightUnit: 'lb', notes: '' });
    setExercises(updated);
  };

  const handleSetChange = (exerciseIndex, setIndex, field, value) => {
    const updated = [...exercises];
    updated[exerciseIndex].sets[setIndex][field] = value;
    setExercises(updated);
  };

  const deleteExercise = exerciseIndex => {
    const updated = exercises.filter((_, index) => index !== exerciseIndex);
    setExercises(updated);
  };

  const deleteSet = (exerciseIndex, setIndex) => {
    const updated = [...exercises];
    updated[exerciseIndex].sets = updated[exerciseIndex].sets.filter((_, i) => i !== setIndex);
    setExercises(updated);
  };

  const handleEndWorkout = async () => {
    try {
      if (exercises.length === 0) {
        alert('Please add at least one exercise before ending the workout.');
        return;
      }

      const preparedExercises = [];
      for (const ex of exercises) {
        if (!ex.sets.length) {
          alert(`${ex.name} needs at least one set.`);
          return;
        }
        const sets = [];
        for (const s of ex.sets) {
          const reps = Number(s.reps);
          const weight = Number(s.weight);
          if (!Number.isFinite(reps) || reps < 0 || !Number.isFinite(weight) || weight < 0) {
            alert(`${ex.name} has a set with a missing or invalid reps/weight value.`);
            return;
          }
          sets.push({ reps, weight, weightUnit: s.weightUnit || 'lb', notes: s.notes || '' });
        }
        preparedExercises.push({
          exerciseId: ex.exerciseId,
          name: ex.name,
          recommendationId: ex.recommendationId,
          recommendationItemId: ex.recommendationItemId,
          sets
        });
      }

      const workoutData = {
        goalText,
        workoutFocus,
        workoutDate: new Date(),
        workoutDuration: Math.floor(time / 60),
        exercises: preparedExercises
      };

      await axios.post('http://localhost:5000/api/v1/history', workoutData, {
        headers: { ...authHeaders(), 'Content-Type': 'application/json' }
      });
      alert('Workout saved!');
      navigate('/dashboard');
    } catch (err) {
      console.error('Failed to save workout:', err.response?.data || err.message);
      alert(err.response?.data?.message || 'Failed to save workout.');
    }
  };

  const inputBase =
    'w-full rounded-lg px-4 py-2.5 bg-[#0e141a]/70 text-[#dbe7ff] placeholder-[#90a0b5]/70 border border-white/10 focus:outline-none focus:ring-2 focus:ring-white/15';

  return (
    <div className="relative min-h-screen text-white px-4 pb-16">
      <div className="absolute inset-0 -z-10" style={{ background: 'linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)' }} />
      <div className="absolute inset-0 -z-10 pointer-events-none" style={{ background: 'radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)' }} />
      <div className="absolute inset-0 -z-10 pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]" />

      <div className="relative flex items-center justify-center pt-10 pb-6">
        <Link to="/" className="absolute left-4 top-1/2 -translate-y-1/2 opacity-90 hover:opacity-100 transition">
          <img src="/Back.png" alt="Back" className="w-10 h-10" />
        </Link>
        <h2 className="text-[26px] md:text-[30px] font-extrabold tracking-tight text-[#8fb0ff]">New Workout</h2>
      </div>

      <section className="mx-auto w-full max-w-3xl rounded-[18px] border border-white/10 bg-white/5 backdrop-blur p-6 md:p-8 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] mb-8">
        <input
          type="text"
          className={`${inputBase} text-center font-semibold text-lg mb-4`}
          placeholder="Workout Focus"
          value={workoutFocus}
          onChange={e => setWorkoutFocus(e.target.value)}
        />
        <h3 className="text-center text-2xl font-bold text-[#cfe0ff] mb-2">{convertTime(time)}</h3>
        {goalText && <p className="text-center text-sm text-[#9fb0c9]">Weekly Goal: {goalText}</p>}
      </section>

      <div className="mx-auto w-full max-w-3xl space-y-6">
        {exercises.map((exercise, exIndex) => (
          <div key={exIndex} className="rounded-[20px] border border-white/10 bg-white/5 backdrop-blur p-6 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h4 className="font-semibold text-[#cfe0ff]">{exercise.name}</h4>
              {exercise.recommendationItemId && (
                <span className="text-xs uppercase tracking-wide text-[#7fd39a] bg-[#7fd39a]/10 border border-[#7fd39a]/30 rounded-full px-2 py-0.5">
                  Recommended
                </span>
              )}
            </div>

            <div className="space-y-3">
              {exercise.sets.map((set, setIndex) => (
                <div key={setIndex} className="flex flex-wrap items-center gap-3">
                  <input
                    type="number"
                    placeholder="Weight"
                    value={set.weight}
                    onChange={e => handleSetChange(exIndex, setIndex, 'weight', e.target.value)}
                    className={`${inputBase} w-24`}
                    required
                  />
                  <select
                    value={set.weightUnit}
                    onChange={e => handleSetChange(exIndex, setIndex, 'weightUnit', e.target.value)}
                    className={`${inputBase} w-20 appearance-none`}
                  >
                    <option value="lb" className="bg-[#0e141a]">lb</option>
                    <option value="kg" className="bg-[#0e141a]">kg</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Reps"
                    value={set.reps}
                    onChange={e => handleSetChange(exIndex, setIndex, 'reps', e.target.value)}
                    className={`${inputBase} w-24`}
                    required
                  />
                  <input
                    type="text"
                    placeholder="Notes"
                    value={set.notes}
                    onChange={e => handleSetChange(exIndex, setIndex, 'notes', e.target.value)}
                    className={`${inputBase} flex-1`}
                  />
                  <button
                    onClick={() => deleteSet(exIndex, setIndex)}
                    className="bg-red-900 hover:bg-red-950 text-white/80 px-3 py-1 rounded-lg transition-colors"
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => addSet(exIndex)}
                className="bg-green-900 hover:bg-green-950 text-white/80 px-4 py-2 rounded-lg transition-colors"
              >
                + Add Set
              </button>
              <button
                onClick={() => deleteExercise(exIndex)}
                className="bg-red-900 hover:bg-red-950 text-white/80 px-4 py-2 rounded-lg transition-colors"
              >
                🗑 Delete Exercise
              </button>
            </div>
          </div>
        ))}

        <div className="rounded-[20px] border border-white/10 bg-white/5 backdrop-blur p-4 flex flex-wrap items-center gap-3">
          <select
            value={selectedExerciseId}
            onChange={e => setSelectedExerciseId(e.target.value)}
            className={`${inputBase} flex-1 min-w-[200px] appearance-none`}
          >
            {catalog.length === 0 && <option value="">Loading exercises...</option>}
            {catalog.map(ex => (
              <option key={ex.exerciseId} value={ex.exerciseId} className="bg-[#0e141a]">
                {ex.name}
              </option>
            ))}
          </select>
          <button
            onClick={addExercise}
            className="bg-blue-900 hover:bg-blue-950 text-white/80 px-6 py-3 rounded-xl font-semibold shadow-[0_10px_28px_-10px_rgba(35,80,220,0.25)] transition-colors"
          >
            + Add Exercise
          </button>
        </div>

        <button
          onClick={handleEndWorkout}
          className="w-full bg-red-900 hover:bg-red-950 text-white/80 px-6 py-3 rounded-xl font-semibold shadow-[0_10px_28px_-10px_rgba(220,35,35,0.25)] transition-colors"
        >
          End Workout
        </button>
      </div>
    </div>
  );
}
