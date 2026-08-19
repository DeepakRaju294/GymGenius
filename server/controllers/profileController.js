const express = require('express');
const Profile = require('./../models/profileModel');

exports.getProfile = async (req, res) => {
    try{
        const profile =  await Profile.findOne({username: req.user.username});
        res.status(200).json({
            success: true,
            data: profile
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.createProfile = async (req, res) => {
    try{
        const {firstName, lastName, email, gender, fitnessGoal, weight, weightUnit, height, heightUnit, equipment} = req.body;
        const existingProfile = await Profile.findOne({username: req.user.username});
        if (existingProfile) {
            return res.status(400).json({
                success: false,
                message: 'Profile already exists for this user'
            });
        }
        const profile = await Profile.create({username: req.user.username, firstName, lastName, email, gender, fitnessGoal, weight, weightUnit, height, heightUnit, equipment});
        res.status(201).json({
            success: true,
            data: {profile}
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.updateProfile = async (req, res) => {
    try{
        const {firstName, lastName, email, gender, fitnessGoal, weight, weightUnit, height, heightUnit, equipment} = req.body;
        const profile = await Profile.findOneAndUpdate({ username: req.user.username }, {firstName, lastName, email, gender, fitnessGoal, weight, weightUnit, height, heightUnit, equipment}, {new: true, runValidators: true});
        res.status(200).json({
            success: true,
            data: profile
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.deleteProfile = async (req, res) => {
    try{
        
        await Profile.deleteOne({username: req.user.username});
        res.status(200).json({
            success: true,
            message: "Profile has been deleted"
        })
    }
    catch (err){
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}