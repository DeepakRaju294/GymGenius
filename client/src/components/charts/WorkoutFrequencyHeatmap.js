import React, { useEffect, useState } from 'react';
import axios from 'axios';

// One-hue sequential ramp (dataviz skill) - index 0 is "no workout" (near-surface
// neutral), 1..5 step up in lightness with intensity.
const STEPS = ['#22262c', '#1c5cab', '#256abf', '#2a78d6', '#3987e5', '#6da7ec'];

function stepFor(count, max) {
  if (count === 0) return STEPS[0];
  const ratio = count / Math.max(max, 1);
  const idx = 1 + Math.min(4, Math.round(ratio * 4));
  return STEPS[idx];
}

export default function WorkoutFrequencyHeatmap() {
  const [days, setDays] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFrequency = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:5000/api/v1/history/frequency', {
          headers: { Authorization: `Bearer ${token}` },
          params: { range: '365d' }
        });
        const map = {};
        (res.data?.data?.days || []).forEach(d => { map[d.date] = d.count; });
        setDays(map);
      } catch (err) {
        setError('Failed to load workout frequency.');
      } finally {
        setLoading(false);
      }
    };
    fetchFrequency();
  }, []);

  if (loading) return <p className="text-sm text-[#9fb0c9]">Loading...</p>;
  if (error) return <p className="text-sm text-red-300">{error}</p>;

  const today = new Date();
  const totalDays = 168; // ~24 weeks - keeps the grid a reasonable width
  const cells = [];
  for (let i = totalDays - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    cells.push({ date: key, count: days[key] || 0 });
  }
  const max = Math.max(1, ...cells.map(c => c.count));
  const totalWorkouts = cells.reduce((sum, c) => sum + c.count, 0);

  return (
    <div>
      <p className="text-xs text-[#9fb0c9] mb-2 tabular-nums">
        {totalWorkouts} workout{totalWorkouts === 1 ? '' : 's'} in the last {totalDays} days
      </p>
      <div className="grid grid-flow-col grid-rows-7 gap-1 overflow-x-auto pb-2" style={{ gridAutoColumns: '10px' }}>
        {cells.map(c => (
          <div
            key={c.date}
            title={`${c.date}: ${c.count} workout${c.count === 1 ? '' : 's'}`}
            className="w-[10px] h-[10px] rounded-[2px]"
            style={{ background: stepFor(c.count, max) }}
          />
        ))}
      </div>
    </div>
  );
}
