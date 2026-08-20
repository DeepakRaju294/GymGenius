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
    weightUnit: 'lb',
    height: '',
    heightUnit: 'in',
    equipment: []
  });

  const EQUIPMENT_OPTIONS = ['barbell', 'dumbbell', 'bench', 'cable', 'machine', 'bodyweight'];

  // docs/ML_SPEC.md §3 - optional, skippable cold-start questions. Answering
  // any of these gives apply_progression a real starting-weight suggestion
  // instead of an unscaled population guess the first time you log an exercise.
  const [coldStart, setColdStart] = useState({
    pushUpsPerSet: '',
    benchPressKnownWeightLb: '',
    benchPressKnownReps: '',
    squatComfort: ''
  });

  const toggleEquipment = (item) => {
    setProfile(prev => ({
      ...prev,
      equipment: prev.equipment.includes(item)
        ? prev.equipment.filter(e => e !== item)
        : [...prev.equipment, item]
    }));
  };

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
      const { token, user } = res.data.data;

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

      const hasColdStartAnswer =
        coldStart.pushUpsPerSet || coldStart.squatComfort || (coldStart.benchPressKnownWeightLb && coldStart.benchPressKnownReps);
      if (hasColdStartAnswer) {
        axios
          .post(
            'http://localhost:5000/api/v1/cold-start/assessment',
            {
              pushUpsPerSet: coldStart.pushUpsPerSet ? Number(coldStart.pushUpsPerSet) : undefined,
              benchPressKnownWeightLb: coldStart.benchPressKnownWeightLb ? Number(coldStart.benchPressKnownWeightLb) : undefined,
              benchPressKnownReps: coldStart.benchPressKnownReps ? Number(coldStart.benchPressKnownReps) : undefined,
              squatComfort: coldStart.squatComfort || undefined
            },
            { headers: { Authorization: `Bearer ${token}` } }
          )
          .catch(() => {
            // Best-effort - a missed cold-start assessment just means the population
            // starting-range fallback is used instead; it never blocks onboarding.
          });
      }

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

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Weight</label>
                  <input
                    name="weight"
                    type="number"
                    value={profile.weight}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Unit</label>
                  <select
                    name="weightUnit"
                    value={profile.weightUnit}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={`${inputBase} appearance-none pr-8`}
                  >
                    <option value="lb" className="bg-[#0e141a]">lb</option>
                    <option value="kg" className="bg-[#0e141a]">kg</option>
                  </select>
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Height</label>
                  <input
                    name="height"
                    type="number"
                    value={profile.height}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={inputBase}
                    required
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Unit</label>
                  <select
                    name="heightUnit"
                    value={profile.heightUnit}
                    onChange={(e) => handleChange(e, setProfile)}
                    className={`${inputBase} appearance-none pr-8`}
                  >
                    <option value="in" className="bg-[#0e141a]">in</option>
                    <option value="cm" className="bg-[#0e141a]">cm</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
                  Equipment you have access to
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {EQUIPMENT_OPTIONS.map((item) => (
                    <label
                      key={item}
                      className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#0e141a]/70 px-3 py-2 text-sm text-[#dbe7ff] capitalize cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={profile.equipment.includes(item)}
                        onChange={() => toggleEquipment(item)}
                        className="accent-[#3d63e3]"
                      />
                      {item}
                    </label>
                  ))}
                </div>
                <p className="text-xs text-[#9fb0c9] mt-1.5">
                  This is what your recommendations will be filtered to - you can change it later in your profile.
                </p>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/10 p-4 space-y-3">
                <p className="text-xs font-semibold text-[#b9c7da]">
                  Optional - a couple of quick questions so your first weight suggestions aren't a guess
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[#9fb0c9] mb-1">Push-ups in a row (approx.)</label>
                    <input
                      type="number"
                      value={coldStart.pushUpsPerSet}
                      onChange={(e) => setColdStart(prev => ({ ...prev, pushUpsPerSet: e.target.value }))}
                      className={inputBase}
                      placeholder="e.g. 15"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#9fb0c9] mb-1">Squat comfort</label>
                    <select
                      value={coldStart.squatComfort}
                      onChange={(e) => setColdStart(prev => ({ ...prev, squatComfort: e.target.value }))}
                      className={`${inputBase} appearance-none`}
                    >
                      <option value="" className="bg-[#0e141a]">Skip</option>
                      <option value="none" className="bg-[#0e141a]">New to squatting</option>
                      <option value="bodyweight" className="bg-[#0e141a]">Comfortable bodyweight</option>
                      <option value="loaded" className="bg-[#0e141a]">Comfortable with added weight</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-[#9fb0c9] mb-1">Bench press weight you know (lb)</label>
                    <input
                      type="number"
                      value={coldStart.benchPressKnownWeightLb}
                      onChange={(e) => setColdStart(prev => ({ ...prev, benchPressKnownWeightLb: e.target.value }))}
                      className={inputBase}
                      placeholder="e.g. 135"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#9fb0c9] mb-1">...for how many reps</label>
                    <input
                      type="number"
                      value={coldStart.benchPressKnownReps}
                      onChange={(e) => setColdStart(prev => ({ ...prev, benchPressKnownReps: e.target.value }))}
                      className={inputBase}
                      placeholder="e.g. 8"
                    />
                  </div>
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