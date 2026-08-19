import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Profile from './pages/Profile';
import NewWorkout from './pages/NewWorkout';
import Register from './pages/Register';
import Login from './pages/Login';
import Home from './pages/Home';
import Progress from './pages/Progress';

export default function App(){
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home/>} />
        <Route path="/dashboard" element={<Dashboard/>} />
        <Route path="/history" element={<History/>} />
        <Route path="/progress" element={<Progress/>} />
        <Route path="/profile" element={<Profile/>} />
        <Route path="/new-workout" element={<NewWorkout/>} />
        <Route path="/login" element={<Login/>} />
        <Route path="/register" element={<Register/>} />
      </Routes>
    </Router>
  );
}

