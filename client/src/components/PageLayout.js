import React from "react";
import { Link } from "react-router-dom";
import { Button } from "./ui/button";

export default function PageLayout({ children, backgroundImage = "/Home.png" }) {
  return (
    <div
      className="relative min-h-screen text-white flex flex-col bg-cover bg-center"
      style={{ backgroundImage: `url('${backgroundImage}')` }}
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
          {children}
        </main>
      </div>
    </div>
  );
}
