const History = require('./../models/historyModel');
const Exercise = require('./../models/exerciseModel');

exports.getWorkout = async (req, res) => {
    try {
        const workout = await History.findOne({ _id: req.params.id, username: req.user.username });
        if (!workout) {
            return res.status(404).json({ success: false, message: 'Workout not found' });
        }
        res.status(200).json({
            success: true,
            data: { workout }
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.getAllWorkouts = async (req, res) => {
    try {
        const page = Math.max(parseInt(req.query.page, 10) || 1, 1);
        const limit = Math.min(Math.max(parseInt(req.query.limit, 10) || 10, 1), 50);
        const skip = (page - 1) * limit;

        const [workouts, total] = await Promise.all([
            History.find({ username: req.user.username })
                .sort({ workoutDate: -1, _id: -1 })
                .skip(skip)
                .limit(limit),
            History.countDocuments({ username: req.user.username })
        ]);

        res.status(200).json({
            success: true,
            data: {
                workouts,
                total,
                page,
                totalPages: Math.max(Math.ceil(total / limit), 1)
            }
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}

exports.createWorkout = async (req, res) => {
    try {
        const { workoutFocus, goalText, workoutDate, workoutDuration, exercises } = req.body;
        const workout = await History.create({ username: req.user.username, goalText, workoutFocus, workoutDate, workoutDuration, exercises });
        res.status(201).json({
            success: true,
            data: { workout }
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.updateWorkout = async (req, res) => {
    try {
        const { workoutFocus, goalText, workoutDate, workoutDuration, exercises } = req.body;
        const workout = await History.findOneAndUpdate(
            { _id: req.params.id, username: req.user.username },
            { workoutFocus, goalText, workoutDate, workoutDuration, exercises },
            { new: true, runValidators: true }
        );
        if (!workout) {
            return res.status(404).json({ success: false, message: 'Workout not found' });
        }
        res.status(200).json({
            success: true,
            data: { workout }
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}


exports.deleteWorkout = async (req, res) => {
    try {
        const workout = await History.findOneAndDelete({ _id: req.params.id, username: req.user.username });
        if (!workout) {
            return res.status(404).json({ success: false, message: 'Workout not found' });
        }
        res.status(200).json({
            success: true,
            message: 'Workout has been deleted'
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }

}

// -- Progress visualization aggregation (docs/SPEC.md §5.2) ------------------------

function parseRangeDays(range, fallback = 90) {
    const match = /^(\d+)d$/.exec(range || '');
    return match ? parseInt(match[1], 10) : fallback;
}

function estimated1RM(weight, reps) {
    if (!weight || !reps) return 0;
    return reps === 1 ? weight : weight * (1 + reps / 30);
}

exports.getProgress = async (req, res) => {
    try {
        const { exerciseId } = req.query;
        if (!exerciseId) {
            return res.status(400).json({ success: false, message: 'exerciseId is required.' });
        }
        const since = new Date(Date.now() - parseRangeDays(req.query.range) * 86400000);

        const workouts = await History.find({
            username: req.user.username,
            workoutDate: { $gte: since },
            'exercises.exerciseId': exerciseId
        }).sort({ workoutDate: 1 });

        const points = [];
        for (const w of workouts) {
            const ex = w.exercises.find(e => e.exerciseId === exerciseId);
            if (!ex || !ex.sets.length) continue;
            let best = ex.sets[0];
            let bestScore = -Infinity;
            for (const s of ex.sets) {
                const score = estimated1RM(s.weight, s.reps);
                if (score > bestScore) { bestScore = score; best = s; }
            }
            points.push({
                date: w.workoutDate,
                weight: best.weight,
                reps: best.reps,
                estimated1RM: Math.round(bestScore * 10) / 10
            });
        }

        res.status(200).json({ success: true, data: { exerciseId, points } });
    }
    catch (err) {
        res.status(500).json({ success: false, message: err.message });
    }
}

exports.getVolume = async (req, res) => {
    try {
        const since = new Date(Date.now() - parseRangeDays(req.query.range) * 86400000);

        const [workouts, catalog] = await Promise.all([
            History.find({ username: req.user.username, workoutDate: { $gte: since } }),
            Exercise.find({})
        ]);

        const muscleById = new Map(catalog.map(e => [e.exerciseId, e.primaryMuscle]));

        function weekStartOf(date) {
            const d = new Date(date);
            d.setHours(0, 0, 0, 0);
            d.setDate(d.getDate() - d.getDay());
            return d.toISOString().slice(0, 10);
        }

        const buckets = new Map();
        for (const w of workouts) {
            const week = weekStartOf(w.workoutDate);
            if (!buckets.has(week)) buckets.set(week, {});
            const byMuscle = buckets.get(week);
            for (const ex of w.exercises) {
                const muscle = muscleById.get(ex.exerciseId) || 'other';
                const volume = ex.sets.reduce((sum, s) => sum + (s.weight * s.reps), 0);
                byMuscle[muscle] = (byMuscle[muscle] || 0) + volume;
            }
        }

        const weeks = Array.from(buckets.keys()).sort().map(week => ({ week, muscles: buckets.get(week) }));
        res.status(200).json({ success: true, data: { weeks } });
    }
    catch (err) {
        res.status(500).json({ success: false, message: err.message });
    }
}

exports.getFrequency = async (req, res) => {
    try {
        const since = new Date(Date.now() - parseRangeDays(req.query.range, 365) * 86400000);
        const workouts = await History.find({ username: req.user.username, workoutDate: { $gte: since } }).select('workoutDate');

        const counts = new Map();
        for (const w of workouts) {
            const day = w.workoutDate.toISOString().slice(0, 10);
            counts.set(day, (counts.get(day) || 0) + 1);
        }
        const days = Array.from(counts.entries()).map(([date, count]) => ({ date, count }));
        res.status(200).json({ success: true, data: { days } });
    }
    catch (err) {
        res.status(500).json({ success: false, message: err.message });
    }
}

exports.getRecords = async (req, res) => {
    try {
        const workouts = await History.find({ username: req.user.username });
        const records = new Map();

        for (const w of workouts) {
            for (const ex of w.exercises) {
                let rec = records.get(ex.exerciseId);
                if (!rec) {
                    rec = { exerciseId: ex.exerciseId, name: ex.name, maxWeight: 0, maxReps: 0, maxEstimated1RM: 0, dateMaxWeight: null, dateMaxEstimated1RM: null };
                    records.set(ex.exerciseId, rec);
                }
                for (const s of ex.sets) {
                    if (s.weight > rec.maxWeight) { rec.maxWeight = s.weight; rec.dateMaxWeight = w.workoutDate; }
                    if (s.reps > rec.maxReps) rec.maxReps = s.reps;
                    const score = Math.round(estimated1RM(s.weight, s.reps) * 10) / 10;
                    if (score > rec.maxEstimated1RM) { rec.maxEstimated1RM = score; rec.dateMaxEstimated1RM = w.workoutDate; }
                }
            }
        }

        res.status(200).json({ success: true, data: { records: Array.from(records.values()) } });
    }
    catch (err) {
        res.status(500).json({ success: false, message: err.message });
    }
}
