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
    height: {
        type: Number,
        required: true
    }
});

const Profile = mongoose.model("Profile", profileSchema);

module.exports = Profile;