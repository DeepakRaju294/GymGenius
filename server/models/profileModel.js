const mongoose = require('mongoose');

const profileSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        ref: 'User'
    },
    firstName: {
        type: String,
        trim: true,
        required: true
    },
    lastName: {
        type: String,
        trim: true,
        required: true
    },
    email: {
        type: String,
        trim: true,
        required: true,
        unique: true
    },
    gender: {
        type: String,
        trim: true,
        required: true
    },
    fitnessGoal: {
        type: String,
        trim: true,
        required: true
    },
    weight: {
        type: Number,
        required: true
    },
    weightUnit: {
        type: String,
        enum: ['lb', 'kg'],
        default: 'lb'
    },
    height: {
        type: Number,
        required: true
    },
    heightUnit: {
        type: String,
        enum: ['in', 'cm'],
        default: 'in'
    },
    equipment: {
        type: [String],
        default: []
    }
});

const Profile = mongoose.model("Profile", profileSchema);

module.exports = Profile;