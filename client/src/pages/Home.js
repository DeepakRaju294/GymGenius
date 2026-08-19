import React, { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import axios from "axios";

export default function Home() {
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = localStorage.getItem('token');
      
      if (!token) {
        setIsChecking(false);
        return;
      }

      try {
        await axios.get('http://localhost:5000/api/v1/profile', {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        navigate('/dashboard');
      } catch (error) {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('email');
        setIsChecking(false);
      }
    };

    checkAuthStatus();
  }, [navigate]);

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div
      className="relative min-h-screen text-white flex flex-col bg-cover bg-center"
      style={{
        backgroundImage: "url('/Home.png')"
      }}
    >
      <div className="absolute inset-0 bg-black bg-opacity-60"></div>
      
      <div className="relative flex flex-col flex-grow">
        <header className="flex justify-between items-center p-6">
          <h1 className="text-3xl font-bold tracking-tight">GymGenius</h1>
          <Link to="/login">
            <Button
              variant="outline"
              className="border-white text-white hover:bg-white hover:text-black"
            >
              Log In
            </Button>
          </Link>
        </header>

        <main className="flex-grow flex flex-col items-center justify-center text-center px-6">
          <h2 className="text-4xl sm:text-5xl font-extrabold mb-4">
            Track Smarter. Train Harder.
          </h2>
          <p className="text-lg sm:text-xl max-w-2xl mb-6 text-gray-300">
            GymGenius helps you visualize your workouts, monitor progress, and
            get intelligent AI-based training recommendations.
          </p>
          <Link to="/login">
            <Button size="lg" className="text-lg font-semibold">
              Get Started <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
        </main>
      </div>
    </div>
  );
}