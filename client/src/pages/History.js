import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

export default function History() {
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalWorkouts, setTotalWorkouts] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  
  const WORKOUTS_PER_PAGE = 10; 

  useEffect(() => {
    const fetchWorkoutHistory = async () => {
      try {
        setLoading(true);
        setError(null);

        const token = localStorage.getItem('token');
        if (!token) throw new Error('No authentication token found. Please log in again.');

        const response = await axios.get(`http://localhost:5000/api/v1/history?page=${currentPage}&limit=${WORKOUTS_PER_PAGE}`, {
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          timeout: 10000
        });

        let workoutData = [];
        if (response.data && response.data.success) {
          workoutData = Array.isArray(response.data?.data?.workouts)
            ? response.data.data.workouts
            : [];
          
          setTotalWorkouts(response.data.data?.total || workoutData.length);
          setTotalPages(response.data.data?.totalPages || Math.ceil(workoutData.length / WORKOUTS_PER_PAGE));
        }

        const sorted = workoutData.sort((a, b) => {
          const dateA = new Date(a.workoutDate || a.date || a.createdAt);
          const dateB = new Date(b.workoutDate || b.date || b.createdAt);
          return dateB - dateA;
        });

        setWorkouts(sorted);
      } catch (err) {
        let msg = 'Failed to load workout history. ';
        if (err.response) {
          if (err.response.status === 401) msg = 'Authentication failed. Please log in again.';
          else if (err.response.status === 404) msg = 'Workout history endpoint not found.';
          else if (err.response.status >= 500) msg = 'Server error. Please try again later.';
          else msg += err.response.data?.message || `Server returned ${err.response.status} error.`;
        } else if (err.request) msg = 'Network error. Please check your connection and try again.';
        else if (String(err.message).includes('timeout')) msg = 'Request timed out. Please try again.';
        else msg += err.message;

        setError(msg);
        setWorkouts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkoutHistory();
  }, [currentPage]);

  const formatDate = (s) => {
    if (!s) return 'No date';
    const d = new Date(s);
    if (isNaN(d.getTime())) return 'Invalid date';
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const formatDuration = (m) => {
    if (!m) return '0 mins';
    const minutes = parseInt(m);
    if (isNaN(minutes)) return '0 mins';
    if (minutes >= 60) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
    return `${minutes} min${minutes !== 1 ? 's' : ''}`;
  };

  const renderSets = (sets) => {
    if (!sets) return <p className="text-[#9fb0c9]/70 text-sm ml-2">No sets recorded</p>;
    const list = Array.isArray(sets) ? sets : typeof sets === 'object' ? Object.values(sets) : [];
    if (!list.length) return <p className="text-[#9fb0c9]/70 text-sm ml-2">No sets recorded</p>;

    return (
      <div className="ml-2 mt-1 space-y-1">
        {list.map((set, i) => (
          <div key={i} className="text-sm text-[#dbe7ff]/90 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#3d63e3]/80 shadow-[0_0_8px_1px_rgba(61,99,227,0.5)]" />
            <span>
              Set {i + 1}: {set.reps || 0} reps × {set.weight || 0} kg
              {set.notes && <span className="text-[#9fb0c9]/70 ml-2">({set.notes})</span>}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const renderExercises = (exercises) => {
    if (!exercises) return <p className="text-[#9fb0c9]/70 text-sm">No exercises recorded</p>;
    const list = Array.isArray(exercises) ? exercises : typeof exercises === 'object' ? Object.values(exercises) : [];
    if (!list.length) return <p className="text-[#9fb0c9]/70 text-sm">No exercises recorded</p>;

    return (
      <div className="space-y-3">
        {list.map((exercise, i) => (
          <div key={i} className="border-l border-white/10 pl-3">
            <h4 className="font-semibold text-[#cfe0ff] tracking-tight">
              {exercise.name || exercise.exerciseName || `Exercise ${i + 1}`}
            </h4>
            {renderSets(exercise.sets)}
          </div>
        ))}
      </div>
    );
  };

  const retryFetch = () => {
    setError(null);
    setLoading(true);
    window.location.reload();
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo(0, 0);
    }
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    const pages = [];
    const maxVisiblePages = 7;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    pages.push(
      <button
        key="prev"
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          currentPage === 1
            ? 'text-[#9fb0c9]/50 cursor-not-allowed'
            : 'text-[#cfe0ff] hover:bg-white/10'
        }`}
      >
        ← Previous
      </button>
    );

    if (startPage > 1) {
      pages.push(
        <button
          key={1}
          onClick={() => handlePageChange(1)}
          className="px-3 py-2 rounded-lg text-sm font-medium text-[#cfe0ff] hover:bg-white/10 transition-colors"
        >
          1
        </button>
      );
      if (startPage > 2) {
        pages.push(
          <span key="ellipsis1" className="px-2 py-2 text-[#9fb0c9]/70 text-sm">
            ...
          </span>
        );
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            i === currentPage
              ? 'bg-[#3d63e3] text-white shadow-[0_0_12px_2px_rgba(61,99,227,0.4)]'
              : 'text-[#cfe0ff] hover:bg-white/10'
          }`}
        >
          {i}
        </button>
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push(
          <span key="ellipsis2" className="px-2 py-2 text-[#9fb0c9]/70 text-sm">
            ...
          </span>
        );
      }
      pages.push(
        <button
          key={totalPages}
          onClick={() => handlePageChange(totalPages)}
          className="px-3 py-2 rounded-lg text-sm font-medium text-[#cfe0ff] hover:bg-white/10 transition-colors"
        >
          {totalPages}
        </button>
      );
    }
    pages.push(
      <button
        key="next"
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          currentPage === totalPages
            ? 'text-[#9fb0c9]/50 cursor-not-allowed'
            : 'text-[#cfe0ff] hover:bg-white/10'
        }`}
      >
        Next →
      </button>
    );

    return (
      <div className="flex items-center justify-center gap-1 mt-8 pt-6 border-t border-white/10">
        {pages}
      </div>
    );
  };

  const shellBg = "absolute inset-0 -z-10";
  const card    = "rounded-[18px] border border-white/10 bg-white/5 backdrop-blur p-6 md:p-8 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]";

  if (loading) {
    return (
      <div className="relative min-h-screen text-white">
        <div className={shellBg} style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
        <div className={`${shellBg} pointer-events-none`} style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
        <div className={`${shellBg} pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]`} />

        <div className="relative flex items-center justify-center px-4 pt-10 pb-6">
          <Link to="/dashboard" className="absolute left-4 top-1/2 -translate-y-1/2 opacity-90 hover:opacity-100 transition">
            <img src="/Back.png" alt="Back" className="w-10 h-10" />
          </Link>
          <h2 className="text-[26px] md:text-[30px] font-extrabold tracking-tight text-[#8fb0ff]">History</h2>
        </div>

        <main className="mx-auto w-full max-w-4xl px-4 pb-16">
          <section className={`${card} text-center`}>
            <h3 className="text-[#cfe0ff] font-semibold mb-4">Loading your workout history…</h3>
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-2 border-white/20 border-t-[#3d63e3]" />
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen text-white">
      <div className={shellBg} style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
      <div className={`${shellBg} pointer-events-none`} style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
      <div className={`${shellBg} pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]`} />

      <div className="relative flex items-center justify-center px-4 pt-10 pb-6">
        <Link to="/dashboard" className="absolute left-4 top-1/2 -translate-y-1/2 opacity-90 hover:opacity-100 transition">
          <img src="/Back.png" alt="Back" className="w-10 h-10" />
        </Link>
        <h2 className="text-[26px] md:text-[30px] font-extrabold tracking-tight text-[#8fb0ff]">
          History
        </h2>
      </div>

      <main className="mx-auto w-full max-w-4xl px-4 pb-16">
        <section className={card}>
          {!error && totalWorkouts > 0 && (
            <div className="mb-6 text-center">
              <p className="text-sm text-[#9fb0c9]">
                Showing {((currentPage - 1) * WORKOUTS_PER_PAGE) + 1}-{Math.min(currentPage * WORKOUTS_PER_PAGE, totalWorkouts)} of {totalWorkouts} workouts
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-4 mb-6">
              <div className="flex gap-3">
                <div className="h-5 w-5 mt-0.5 rounded-full bg-red-500/70 shadow-[0_0_12px_1px_rgba(239,68,68,0.5)]" />
                <div>
                  <h3 className="text-sm font-semibold text-red-300">Error Loading Workouts</h3>
                  <p className="text-red-200/90 text-sm mt-1">{error}</p>
                  <button
                    onClick={retryFetch}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm bg-red-400/20 hover:bg-red-400/30 text-red-100 transition"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}

          {!error && workouts.length === 0 ? (
            <div className="text-center py-14">
              <div className="text-6xl mb-4">🏋🏾‍♀️</div>
              <h3 className="text-xl font-semibold text-[#cfe0ff] mb-2">No workouts yet</h3>
              <p className="text-[#9fb0c9]">Your workout history will appear here.</p>
            </div>
          ) : (
            <>
              <div className="divide-y divide-white/10 rounded-[14px] overflow-hidden">
                {workouts.map((workout, i) => (
                  <div
                    key={workout._id || workout.id || `workout-${i}`}
                    className="p-5 hover:bg-white/[0.04] transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="inline-block h-2 w-2 rounded-full bg-[#3d63e3] shadow-[0_0_10px_2px_rgba(61,99,227,0.6)]" />
                          <h3 className="text-lg md:text-xl font-bold text-[#dbe7ff] truncate">
                            {workout.workoutFocus || workout.name || workout.title || 'Unnamed Workout'}
                          </h3>
                        </div>
                        {workout.goalText && (
                          <p className="text-sm text-[#9fb0c9]">
                            <span className="text-[#b9c7da] font-medium">Goal:</span> {workout.goalText}
                          </p>
                        )}
                        {workout.notes && (
                          <p className="text-sm text-[#9fb0c9] mt-1">
                            <span className="text-[#b9c7da] font-medium">Notes:</span> {workout.notes}
                          </p>
                        )}
                      </div>

                      <div className="text-right shrink-0">
                        <div className="text-sm text-[#cfe0ff] font-medium">
                          {formatDate(workout.workoutDate || workout.date || workout.createdAt)}
                        </div>
                        <div className="text-xs text-[#9fb0c9]">
                          {formatDuration(workout.workoutDuration || workout.duration)}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 border-t border-white/10 pt-4">
                      <h4 className="text-sm font-semibold text-[#b9c7da] mb-3 tracking-wide uppercase">
                        Exercises
                      </h4>
                      {renderExercises(workout.exercises)}
                    </div>
                  </div>
                ))}
              </div>
              
              {renderPagination()}
            </>
          )}
        </section>
      </main>
    </div>
  );
}