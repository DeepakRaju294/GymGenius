const mongoose = require('mongoose');

const goalSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        trim: true,
        ref: 'User'
    },
    goalText: {
        type: String,
        trim: true
    },
    weekStart: {
        type: Date,
        required: true
    },
});

const Goal = mongoose.model('Goal', goalSchema);

module.exports = Goal;