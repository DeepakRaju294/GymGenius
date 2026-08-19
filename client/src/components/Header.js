import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="w-full bg-gradient-to-r from-[#0b0f14] via-[#101418] to-[#0b0f14] text-white border-b border-white/10 py-4 px-6 flex items-center justify-between font-sans">

      <Link
        to="/history"
        className="opacity-80 hover:opacity-100 transition duration-150"
        aria-label="View workout history"
      >
        <img src="/History.png" alt="History" className="w-10 h-10" />
      </Link>

      <div className="text-center">
          <img
            src="/Logo.png"
            alt="GymGenius Logo"
            className="w-12 h-12 mx-auto"
          />
        <h1 className="text-3xl font-bold tracking-tight">
          GymGenius
        </h1>
        <p className="text-sm text-gray-300 tracking-wide">
          Fitness that evolves with you
        </p>
      </div>

      <Link
        to="/profile"
        className="opacity-80 hover:opacity-100 transition duration-150"
        aria-label="Go to profile"
      >
        <img src="/Profile.png" alt="Profile" className="w-10 h-10" />
      </Link>
    </header>
  );
}
