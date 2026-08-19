const mongoose = require('mongoose');

const exerciseSchema = new mongoose.Schema({
    exerciseId: {
        type: String,
        required: true,
        unique: true,
        trim: true
    },
    name: {
        type: String,
        required: true,
        trim: true
    },
    primaryMuscle: {
        type: String,
        required: true,
        trim: true
    },
    secondaryMuscles: {
        type: [String],
        default: []
    },
    equipment: {
        type: [String],
        default: []
    },
    tags: {
        type: [String],
        default: []
    }
});

const Exercise = mongoose.model('Exercise', exerciseSchema);

module.exports = Exercise;
