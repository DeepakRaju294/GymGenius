const mongoose = require('mongoose');

const setSchema = new mongoose.Schema({
    reps: {
        type: Number,
        required: true,
        min: 0
    },
    weight: {
        type: Number,
        required: true,
        min: 0
    },
    weightUnit: {
        type: String,
        enum: ['lb', 'kg'],
        default: 'lb'
    },
    notes: {
        type: String,
        trim: true
    }
}, { _id: false });

const exerciseEntrySchema = new mongoose.Schema({
    exerciseId: {
        type: String,
        required: true
    },
    // Set when this exercise came from a recommendation session (docs/SPEC.md §4.7);
    // absent for freely-logged exercises. recommendationItemId is what lets prescribed
    // performance be compared against actual performance - matching has to be at the
    // item level since one recommendation session suggests more than one exercise.
    recommendationId: {
        type: String
    },
    recommendationItemId: {
        type: String
    },
    name: {
        type: String,
        required: true,
        trim: true
    },
    sets: {
        type: [setSchema],
        default: []
    }
}, { _id: false });

const historySchema = new mongoose.Schema({
    username: {
        type: String,
        required: true
    },
    goalText: {
        type: String,
        trim: true
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
        type: [exerciseEntrySchema],
        required: true
    }
}, { timestamps: true });

historySchema.index({ username: 1, workoutDate: -1 });

const History = mongoose.model('History', historySchema);

module.exports = History;
