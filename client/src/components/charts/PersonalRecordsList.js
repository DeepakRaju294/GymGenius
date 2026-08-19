import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function PersonalRecordsList() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('http://localhost:5000/api/v1/history/records', {
          headers: { Authorization: `Bearer ${token}` }
        });
        const list = res.data?.data?.records || [];
        list.sort((a, b) => b.maxEstimated1RM - a.maxEstimated1RM);
        setRecords(list);
      } catch (err) {
        setError('Failed to load personal records.');
      } finally {
        setLoading(false);
      }
    };
    fetchRecords();
  }, []);

  if (loading) return <p className="text-sm text-[#9fb0c9]">Loading...</p>;
  if (error) return <p className="text-sm text-red-300">{error}</p>;
  if (records.length === 0) {
    return <p className="text-sm text-[#9fb0c9]">Your personal records will show up here once you log some workouts.</p>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {records.map(r => (
        <div key={r.exerciseId} className="rounded-xl border border-white/10 bg-black/20 p-3">
          <div className="text-sm font-semibold text-[#cfe0ff]">{r.name}</div>
          <div className="text-xs text-[#9fb0c9] tabular-nums mt-1">
            Best: {r.maxWeight} lb &middot; {r.maxReps} reps &middot; est. 1RM {r.maxEstimated1RM} lb
          </div>
        </div>
      ))}
    </div>
  );
}
