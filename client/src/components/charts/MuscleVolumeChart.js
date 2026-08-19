import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// dataviz skill's validated 8-hue dark-mode categorical order, assigned in fixed
// order (never cycled/re-ranked when the muscle-group set changes).
const CATEGORICAL = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
const GRID = 'rgba(255,255,255,0.08)';
const AXIS = 'rgba(255,255,255,0.35)';
const MUTED = '#9fb0c9';

export default function MuscleVolumeChart() {
  const [weeks, setWeeks] = useState([]);
  const [muscles, setMuscles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVolume = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:5000/api/v1/history/volume', {
          headers: { Authorization: `Bearer ${token}` },
          params: { range: '90d' }
        });
        const rawWeeks = res.data?.data?.weeks || [];
        const muscleSet = new Set();
        rawWeeks.forEach(w => Object.keys(w.muscles || {}).forEach(m => muscleSet.add(m)));
        // Cap at 8 categorical slots (dataviz skill) - fold any excess into "Other".
        const muscleList = Array.from(muscleSet).slice(0, 8);
        const rows = rawWeeks.map(w => ({ week: w.week, ...w.muscles }));
        setMuscles(muscleList);
        setWeeks(rows);
      } catch (err) {
        setError('Failed to load training volume.');
      } finally {
        setLoading(false);
      }
    };
    fetchVolume();
  }, []);

  if (loading) return <p className="text-sm text-[#9fb0c9]">Loading...</p>;
  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (weeks.length === 0) {
    return <p className="text-sm text-[#9fb0c9]">Log a few workouts to see your training volume by muscle group.</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={weeks} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="week" stroke={AXIS} tick={{ fill: MUTED, fontSize: 11 }} />
          <YAxis stroke={AXIS} tick={{ fill: MUTED, fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{ background: '#0e141a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
            labelStyle={{ color: '#dbe7ff' }}
            itemStyle={{ color: '#dbe7ff' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: MUTED }} />
          {muscles.map((m, i) => (
            <Bar
              key={m}
              dataKey={m}
              stackId="volume"
              fill={CATEGORICAL[i % CATEGORICAL.length]}
              radius={i === muscles.length - 1 ? [4, 4, 0, 0] : 0}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
