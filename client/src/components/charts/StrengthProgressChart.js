import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Sequential-blue series color (dataviz skill's validated dark-mode categorical
// slot 1) - a single series names itself via the section title, so no legend.
const SERIES_BLUE = '#3987e5';
const GRID = 'rgba(255,255,255,0.08)';
const AXIS = 'rgba(255,255,255,0.35)';
const MUTED = '#9fb0c9';

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-white/10 bg-[#0e141a] px-3 py-2 text-xs text-[#dbe7ff] shadow-lg">
      <div className="font-semibold mb-1">{formatDate(label)}</div>
      <div className="tabular-nums">Est. 1RM: {p.estimated1RM} lb</div>
      <div className="text-[#9fb0c9] tabular-nums">{p.weight} lb x {p.reps}</div>
    </div>
  );
}

export default function StrengthProgressChart({ exerciseId, exerciseName }) {
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!exerciseId) return;
    const fetchProgress = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:5000/api/v1/history/progress', {
          headers: { Authorization: `Bearer ${token}` },
          params: { exerciseId, range: '180d' }
        });
        setPoints(res.data?.data?.points || []);
      } catch (err) {
        setError('Failed to load progress.');
      } finally {
        setLoading(false);
      }
    };
    fetchProgress();
  }, [exerciseId]);

  if (loading) return <p className="text-sm text-[#9fb0c9]">Loading...</p>;
  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (points.length < 2) {
    return <p className="text-sm text-[#9fb0c9]">Log a couple more sessions of {exerciseName} to see a trend.</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={points} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDate} stroke={AXIS} tick={{ fill: MUTED, fontSize: 11 }} />
          <YAxis stroke={AXIS} tick={{ fill: MUTED, fontSize: 11 }} width={48} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="estimated1RM"
            stroke={SERIES_BLUE}
            strokeWidth={2}
            dot={{ r: 3, fill: SERIES_BLUE, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
