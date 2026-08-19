import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const [form, setForm] = useState({ username: '', password: '' });
  const [profile, setProfile] = useState({
    firstName: '',
    lastName: '',
    gender: '',
    fitnessGoal: '',
    weight: '',
    height: ''
  });

  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e, setter) => {
    setter(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await axios.post('http://localhost:5000/api/v1/auth/login', form);
      const { token, user } = res.data;

      localStorage.setItem('token', token);
      localStorage.setItem('username', user.username);
      localStorage.setItem('email', user.email);

      try {
        const profileRes = await axios.get('http://localhost:5000/api/v1/profile', {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (profileRes.data.success && profileRes.data.data) {
          navigate('/dashboard');
        } else {
          setStep(2);
        }
      } catch {
        setStep(2);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const token = localStorage.getItem('token');
      const email = localStorage.getItem('email');

      await axios.post(
        'http://localhost:5000/api/v1/profile',
        { ...profile, email },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessage('Profile completed successfully!');
      setTimeout(() => navigate('/dashboard'), 1500);
    } catch (err) {
      setError(err.response?.data?.message || 'Profile update failed.');
    } finally {
      setLoading(false);
    }
  };

  const inputBase =
    "w-full rounded-lg px-4 py-2.5 bg-[#0e141a]/70 text-[#dbe7ff] placeholder-[#90a0b5]/70 " +
    "border border-white/10 focus:outline-none focus:ring-2 focus:ring-white/15";

  const shellBg = "absolute inset-0 -z-10";
  const card =
    "rounded-[18px] border border-white/10 bg-white/5 backdrop-blur p-6 md:p-8 " +
    "shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] w-full max-w-md";

  return (
    <div className="relative min-h-screen text-white flex items-start justify-center pt-12 md:pt-24" >
      <div className={shellBg} style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
      <div className={`${shellBg} pointer-events-none`} style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
      <div className={`${shellBg} pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]`} />

      <div className="w-full max-w-md">
        <h2 className="text-center text-[32px] md:text-[38px] font-extrabold tracking-tight text-[#8fb0ff] mb-16">
          {step === 1 ? 'Log In' : 'Complete Your Profile'}
        </h2>

        <form
          onSubmit={step === 1 ? handleLoginSubmit : handleProfileSubmit}
          className={card}
        >
          {step === 1 ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  name="username"
                  value={form.username}
                  onChange={(e) => handleChange(e, setForm)}
                  required
                  className={inputBase}
                  placeholder="Enter your username"
                  autoComplete="username"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  name="password"
                  value={form.password}
                  onChange={(e) => handleChange(e, setForm)}
                  required
                  className={inputBase}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                />
              </div>

              <p className="text-sm text-[#9fb0c9] text-center mt-2">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => navigate('/register')}
                  className="text-[#8fb0ff] font-semibold hover:underline"
                >
                  Create one
                </button>
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">First Name</label>
                  <input
                    name="firstName"
                    value={profile.firstName}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Last Name</label>
                  <input
                    name="lastName"
                    value={profile.lastName}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Gender</label>
                <select
                  name="gender"
                  value={profile.gender}
                  onChange={(e) => handleChange(e, setProfile)}
                  className={`${inputBase} appearance-none pr-8`}
                  required
                >
                  <option value="" className="bg-[#0e141a]">Select…</option>
                  <option value="Male" className="bg-[#0e141a]">Male</option>
                  <option value="Female" className="bg-[#0e141a]">Female</option>
                  <option value="Other" className="bg-[#0e141a]">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Fitness Goal</label>
                <input
                  name="fitnessGoal"
                  value={profile.fitnessGoal}
                  onChange={(e) => handleChange(e, setProfile)}
                  className={inputBase}
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Weight (lb)</label>
                  <input
                    name="weight"
                    type="number"
                    value={profile.weight}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Height (in)</label>
                  <input
                    name="height"
                    type="number"
                    value={profile.height}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="
              mt-6 w-full h-11 rounded-xl text-base font-semibold
              bg-[#2b47aa] hover:bg-[#3456cc] text-white
              shadow-[0_10px_28px_-10px_rgba(35,80,220,0.5)]
              transition-colors disabled:opacity-70
            "
          >
            {loading ? (step === 1 ? 'Logging in...' : 'Saving...') : (step === 1 ? 'Log In' : 'Submit')}
          </button>

          {error && <p className="text-red-300 text-sm text-center mt-3">{error}</p>}
          {message && <p className="text-green-300 text-sm text-center mt-3">{message}</p>}
        </form>
      </div>
    </div>
  );
}