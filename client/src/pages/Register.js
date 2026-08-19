import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios'; 

export default function Register() {
  const [form, setForm] = useState({ email: '', username: '', password: '' });
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setSuccess(false);

    try {
      await axios.post('http://localhost:5000/api/v1/auth/register', form);
      setMessage('Registration successful. You can now log in.');
      setSuccess(true);
    } catch (err) {
      setMessage(err.response?.data?.message || 'Registration failed');
      setSuccess(false);
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
    <div className="relative min-h-screen text-white flex items-start justify-center pt-12 md:pt-24">
      <div className={shellBg} style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
      <div className={`${shellBg} pointer-events-none`} style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
      <div className={`${shellBg} pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]`} />

      <div className="w-full max-w-md">
        <h2 className="text-center text-[32px] md:text-[38px] font-extrabold tracking-tight text-[#8fb0ff] mb-14">
          Register
        </h2>

        <form
          onSubmit={handleSubmit}
          className={card}
        >
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                name="email"
                id="email"
                value={form.email}
                onChange={handleChange}
                required
                className={inputBase}
                placeholder="Enter your email"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                Username
              </label>
              <input
                type="text"
                name="username"
                id="username"
                value={form.username}
                onChange={handleChange}
                required
                className={inputBase}
                placeholder="Choose a username"
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                Password
              </label>
              <input
                type="password"
                name="password"
                id="password"
                value={form.password}
                onChange={handleChange}
                required
                className={inputBase}
                placeholder="Create a password"
                autoComplete="new-password"
              />
            </div>

            <p className="text-sm text-[#9fb0c9] text-center mt-2">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-[#8fb0ff] font-semibold hover:underline"
              >
                Log in
              </button>
            </p>
          </div>

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
            {loading ? 'Registering...' : 'Register'}
          </button>

          {message && (
            <p className={`text-sm text-center mt-3 ${success ? 'text-green-300' : 'text-red-300'}`}>
              {message}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}