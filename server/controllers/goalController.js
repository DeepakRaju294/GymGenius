const express = require('express');
const Goal = require('./../models/goalModel');

exports.getGoal = async (req, res) => {
    try{
        const {weekStart } = req.query;
        const goal = await Goal.findOne({username:req.user.username, weekStart});
        if (!goal) {
            return res.status(404).json({
                success: false,
                message: 'Goal not found for this week'
            });
        }
        res.status(200).json({
            success: true,
            data: {goal}
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.createGoal = async (req, res) => {
    try{
        const {goalText, weekStart } = req.body;
        const existingGoal = await Goal.findOne({username: req.user.username, weekStart});
        if (existingGoal) {
            return res.status(400).json({
                success: false,
                message: 'Goal already exists for this week'
            });
        }
        const goal = await Goal.create({username:req.user.username, goalText, weekStart});
        res.status(201).json({
            success: true,
            data: {goal}
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.updateGoal = async (req, res) => {
    try{
        const {goalText, weekStart} = req.body;
        const goal = await Goal.findOneAndUpdate({username:req.user.username, weekStart}, {goalText});
        if (!goal) {
            return res.status(404).json({
                success: false,
                message: 'Goal not found for this week'
            });
        }
        res.status(200).json({
            success: true,
            data: {goal}
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}
