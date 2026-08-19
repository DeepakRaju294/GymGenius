// Seeds the canonical exercise catalog (docs/SPEC.md §3/§4.4 - "referenced
// everywhere and populated nowhere"). Run with: npm run seed
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', 'config.env') });
const mongoose = require('mongoose');
const Exercise = require('../models/exerciseModel');

const exercises = [
    { exerciseId: 'bench_press', name: 'Barbell Bench Press', primaryMuscle: 'chest', secondaryMuscles: ['triceps', 'shoulders'], equipment: ['barbell', 'bench'], tags: ['push', 'strength', 'hypertrophy'] },
    { exerciseId: 'incline_db_press', name: 'Incline Dumbbell Press', primaryMuscle: 'chest', secondaryMuscles: ['shoulders', 'triceps'], equipment: ['dumbbell', 'bench'], tags: ['push', 'hypertrophy'] },
    { exerciseId: 'overhead_press', name: 'Overhead Press', primaryMuscle: 'shoulders', secondaryMuscles: ['triceps'], equipment: ['barbell'], tags: ['push', 'strength'] },
    { exerciseId: 'lateral_raise', name: 'Dumbbell Lateral Raise', primaryMuscle: 'shoulders', secondaryMuscles: [], equipment: ['dumbbell'], tags: ['push', 'hypertrophy'] },
    { exerciseId: 'tricep_pushdown', name: 'Cable Tricep Pushdown', primaryMuscle: 'triceps', secondaryMuscles: [], equipment: ['cable'], tags: ['push', 'hypertrophy'] },
    { exerciseId: 'barbell_row', name: 'Barbell Row', primaryMuscle: 'back', secondaryMuscles: ['biceps', 'rear delts'], equipment: ['barbell'], tags: ['pull', 'strength', 'hypertrophy'] },
    { exerciseId: 'lat_pulldown', name: 'Lat Pulldown', primaryMuscle: 'lats', secondaryMuscles: ['biceps'], equipment: ['cable'], tags: ['pull', 'hypertrophy'] },
    { exerciseId: 'pull_up', name: 'Pull-Up', primaryMuscle: 'lats', secondaryMuscles: ['biceps', 'back'], equipment: ['bodyweight'], tags: ['pull', 'strength'] },
    { exerciseId: 'seated_cable_row', name: 'Seated Cable Row', primaryMuscle: 'back', secondaryMuscles: ['biceps'], equipment: ['cable'], tags: ['pull', 'hypertrophy'] },
    { exerciseId: 'bicep_curl', name: 'Dumbbell Bicep Curl', primaryMuscle: 'biceps', secondaryMuscles: ['forearms'], equipment: ['dumbbell'], tags: ['pull', 'hypertrophy'] },
    { exerciseId: 'squat', name: 'Barbell Back Squat', primaryMuscle: 'quads', secondaryMuscles: ['glutes', 'hamstrings'], equipment: ['barbell'], tags: ['legs', 'strength'] },
    { exerciseId: 'deadlift', name: 'Conventional Deadlift', primaryMuscle: 'hamstrings', secondaryMuscles: ['glutes', 'back'], equipment: ['barbell'], tags: ['legs', 'strength'] },
    { exerciseId: 'leg_press', name: 'Leg Press', primaryMuscle: 'quads', secondaryMuscles: ['glutes'], equipment: ['machine'], tags: ['legs', 'hypertrophy'] },
    { exerciseId: 'romanian_deadlift', name: 'Romanian Deadlift', primaryMuscle: 'hamstrings', secondaryMuscles: ['glutes'], equipment: ['barbell'], tags: ['legs', 'hypertrophy'] },
    { exerciseId: 'walking_lunge', name: 'Walking Lunge', primaryMuscle: 'glutes', secondaryMuscles: ['quads'], equipment: ['dumbbell'], tags: ['legs', 'hypertrophy'] },
    { exerciseId: 'calf_raise', name: 'Standing Calf Raise', primaryMuscle: 'calves', secondaryMuscles: [], equipment: ['machine'], tags: ['legs', 'endurance'] },
    { exerciseId: 'plank', name: 'Plank', primaryMuscle: 'core', secondaryMuscles: [], equipment: ['bodyweight'], tags: ['core', 'endurance'] },
    { exerciseId: 'hanging_leg_raise', name: 'Hanging Leg Raise', primaryMuscle: 'core', secondaryMuscles: [], equipment: ['bodyweight'], tags: ['core', 'hypertrophy'] },
    { exerciseId: 'face_pull', name: 'Cable Face Pull', primaryMuscle: 'rear delts', secondaryMuscles: ['back'], equipment: ['cable'], tags: ['pull', 'hypertrophy'] },
];

async function seed() {
    if (!process.env.MONGO_URI) {
        console.error('MONGO_URI is not set - copy server/config.env.example to server/config.env first.');
        process.exit(1);
    }
    await mongoose.connect(process.env.MONGO_URI);
    for (const ex of exercises) {
        await Exercise.findOneAndUpdate({ exerciseId: ex.exerciseId }, ex, { upsert: true, new: true, setDefaultsOnInsert: true });
    }
    console.log(`Seeded ${exercises.length} exercises.`);
    await mongoose.disconnect();
}

seed().catch((err) => {
    console.error(err);
    process.exit(1);
});
