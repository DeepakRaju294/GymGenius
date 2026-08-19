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

// Enforce one goal per user per week at the database level - createGoal's
// check-then-create was otherwise a race condition (docs/SPEC.md §6).
goalSchema.index({ username: 1, weekStart: 1 }, { unique: true });

const Goal = mongoose.model('Goal', goalSchema);

module.exports = Goal;