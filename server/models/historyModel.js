const mongoose = require('mongoose');

const historySchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        ref: 'User'
    },
    goalText: {
        type: String,
        required: true, 
        trim: true, 
        ref: 'Goal'
    },
    workoutFocus: {
        type: String,
        required: true, 
        trim: true
    },
    workoutDate: {
        type: Date,
        required: true
    },
    workoutDuration: {
        type: Number,
        required: true
    },
    exercises: {
        type: Object,
        required: true
    }
})

const History = mongoose.model('History', historySchema);

module.exports = History;
