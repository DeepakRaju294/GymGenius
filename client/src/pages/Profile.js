import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";

export default function Profile() {
  const navigate = useNavigate();
  const [editable, setEditable] = useState(false);
  const [userInfo, setUserInfo] = useState({
    "Username": "",
    "First Name": "",
    "Last Name": "",
    "Email": "",
    "Gender": "",
    "Fitness Goal": "",
    "Weight": "",
    "Height": "",
  });
  const [weightUnit, setWeightUnit] = useState("lb");
  const [heightUnit, setHeightUnit] = useState("in");
  const [equipment, setEquipment] = useState([]);

  const EQUIPMENT_OPTIONS = ['barbell', 'dumbbell', 'bench', 'cable', 'machine', 'bodyweight'];

  const toggleEquipment = (item) => {
    if (!editable) return;
    setEquipment((prev) =>
      prev.includes(item) ? prev.filter((e) => e !== item) : [...prev, item]
    );
  };

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await axios.get("http://localhost:5000/api/v1/profile", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const p = res.data?.data || {};
        setUserInfo({
          "Username": p.username || "",
          "First Name": p.firstName || "",
          "Last Name": p.lastName || "",
          "Email": p.email || "",
          "Gender": p.gender || "",
          "Fitness Goal": p.fitnessGoal || "",
          "Weight": p.weight ?? "",
          "Height": p.height ?? "",
        });
        setWeightUnit(p.weightUnit || "lb");
        setHeightUnit(p.heightUnit || "in");
        setEquipment(Array.isArray(p.equipment) ? p.equipment : []);
      } catch (err) {
        console.error("Error fetching profile:", err.response?.data || err.message);
        alert("Could not load profile.");
      }
    };
    fetchProfile();
  }, []);

  const handleFieldChange = (e) => {
    const { name, value } = e.target;
    setUserInfo((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    try {
      const token = localStorage.getItem("token");
      const payload = {
        username:    userInfo["Username"],
        firstName:   userInfo["First Name"],
        lastName:    userInfo["Last Name"],
        email:       userInfo["Email"],
        gender:      userInfo["Gender"], 
        fitnessGoal: userInfo["Fitness Goal"],
        weight:      userInfo["Weight"],
        weightUnit,
        height:      userInfo["Height"],
        heightUnit,
        equipment,
      };
      await axios.patch("http://localhost:5000/api/v1/profile", payload, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, 
      });
      setEditable(false);
    } catch (err) {
      console.error("Error updating profile:", err.response?.data || err.message);
      alert("Failed to update profile.");
    }
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem('token');
      
      if (token) {
        await axios.post('http://localhost:5000/api/v1/auth/logout', {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      localStorage.removeItem('email');
      
      navigate('/');
    }
  };

  const inputBase =
    "w-full rounded-lg px-4 py-2.5 bg-[#0e141a]/70 text-[#dbe7ff] placeholder-[#90a0b5]/70 " +
    "border border-white/10 " +
    (editable ? "focus:outline-none focus:ring-2 focus:ring-white/15" : "opacity-90 cursor-not-allowed");

  return (
    <div className="relative min-h-screen text-white overflow-hidden">
      <div className="absolute inset-0 -z-10" style={{ background: "linear-gradient(180deg, #0d1218 0%, #0a0f14 100%)" }} />
      <div className="absolute inset-0 -z-10 pointer-events-none" style={{ background: "radial-gradient(60% 50% at 90% 90%, rgba(150,180,220,0.16) 0%, rgba(150,180,220,0.06) 40%, rgba(13,18,24,0) 75%)" }} />
      <div className="absolute inset-0 -z-10 pointer-events-none bg-[radial-gradient(120%_80%_at_50%_50%,transparent_60%,rgba(0,0,0,0.28)_100%)]" />

      <Link to="/dashboard" className="absolute top-6 left-6 opacity-90 hover:opacity-100 transition">
        <img src="/Back.png" alt="Back" className="w-10 h-10" />
      </Link>

      <button 
        onClick={handleLogout}
        className="absolute top-6 right-6 bg-red-600/80 hover:bg-red-700/90 text-white px-3 py-1.5 rounded-lg text-sm font-medium backdrop-blur transition-colors"
      >
        Log Out
      </button>

      <main className="mx-auto w-full max-w-xl px-4 pt-12 pb-12">
        <section className="rounded-[18px] border border-white/10 bg-white/5 backdrop-blur p-6 md:p-8 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]">
          <h2 className="text-center text-[26px] md:text-[30px] font-extrabold tracking-tight mb-6 text-[#8fb0ff]">
            My Information
          </h2>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Username</label>
            <input
              name="Username"
              value={userInfo["Username"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={inputBase}
              placeholder=""
            />
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">First Name</label>
            <input
              name="First Name"
              value={userInfo["First Name"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={inputBase}
              placeholder=""
            />
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Last Name</label>
            <input
              name="Last Name"
              value={userInfo["Last Name"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={inputBase}
              placeholder=""
            />
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Email</label>
            <input
              type="email"
              name="Email"
              value={userInfo["Email"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={inputBase}
              placeholder=""
            />
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Gender</label>
            <select
              name="Gender"
              value={userInfo["Gender"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={`${inputBase} appearance-none pr-8`} 
            >
              <option value="" className="bg-[#0e141a]">Select…</option>
              <option value="male" className="bg-[#0e141a]">Male</option>
              <option value="female" className="bg-[#0e141a]">Female</option>
              <option value="other" className="bg-[#0e141a]">Other</option>
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Fitness Goal</label>
            <textarea
              name="Fitness Goal"
              rows={2}
              value={userInfo["Fitness Goal"]}
              onChange={handleFieldChange}
              disabled={!editable}
              className={inputBase + " resize-none"}
              placeholder=""
            />
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Weight ({weightUnit})</label>
              <input
                type="number"
                inputMode="decimal"
                name="Weight"
                value={userInfo["Weight"]}
                onChange={handleFieldChange}
                disabled={!editable}
                className={inputBase}
                placeholder=""
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">Height ({heightUnit})</label>
              <input
                type="number"
                inputMode="decimal"
                name="Height"
                value={userInfo["Height"]}
                onChange={handleFieldChange}
                disabled={!editable}
                className={inputBase}
                placeholder=""
              />
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-xs font-semibold text-[#b9c7da] mb-1.5">
              Equipment you have access to
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {EQUIPMENT_OPTIONS.map((item) => (
                <label
                  key={item}
                  className={`flex items-center gap-2 rounded-lg border border-white/10 bg-[#0e141a]/70 px-3 py-2 text-sm text-[#dbe7ff] capitalize ${editable ? "cursor-pointer" : "opacity-70 cursor-not-allowed"}`}
                >
                  <input
                    type="checkbox"
                    checked={equipment.includes(item)}
                    onChange={() => toggleEquipment(item)}
                    disabled={!editable}
                    className="accent-[#3d63e3]"
                  />
                  {item}
                </label>
              ))}
            </div>
            <p className="text-xs text-[#9fb0c9] mt-1.5">
              Your recommendations are filtered to exercises you can actually do with this equipment.
            </p>
          </div>

          <button
            onClick={editable ? handleSave : () => setEditable(true)}
            className="
              w-full h-11 rounded-xl text-base font-semibold
              bg-[#3456cc] hover:bg-[#3d63e3]
              text-white shadow-[0_10px_28px_-10px_rgba(35,80,220,0.6)]
              transition-colors
            "
          >
            {editable ? "Save Profile" : "Edit Profile"}
          </button>
        </section>
      </main>
    </div>
  );
}