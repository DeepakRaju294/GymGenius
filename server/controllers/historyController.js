const express = require('express');
const History = require('./../models/historyModel');

exports.getWorkout = async (req, res) =>{
    try{
        const workout = await History.findOne({_id: req.params.id, username: req.user.username});
        res.status(200).json({
            success: true,
            data: {workout}
        })
    }
    catch(err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.getAllWorkouts = async (req, res) => {
    try{
        const workouts = await History.find({username: req.user.username}).sort({ workoutDate: -1, _id: -1 });
        res.status(200).json({
            success: true,
            data: {workouts}
        })
    }
    catch(err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.createWorkout = async (req, res) => {
    try{
        const { workoutFocus, goalText, workoutDate, workoutDuration, exercises} = req.body;
        const workout = await History.create({username: req.user.username, goalText, workoutFocus, workoutDate, workoutDuration, exercises}); 
        res.status(201).json({
            success: true,
            data: {workout}
        })
    }
    catch(err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.updateWorkout = async (req, res) => {
    try{
        const workout = await History.findOneAndUpdate({_id: req.params.id, username: req.user.username}, req.body, {new: true});
        res.status(200).json({
            success: true,
            data: {workout}
        })
    }
    catch(err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.deleteWorkout = async (req, res) => {
    try{
        const workout = await History.findOneAndDelete({_id: req.params.id, username: req.user.username});
        res.status(200).json({
            success: true,
            message: 'Workout has been deleted'
        })
    }
    catch(err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }

}