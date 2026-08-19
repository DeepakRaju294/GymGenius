// Lightweight request validation + mass-assignment protection (docs/SPEC.md §2.5).
// Pulled forward ahead of general hardening because the workout and recommendation
// endpoints are the ones about to see real new traffic as the data model changes.

const isNonEmptyString = (v) => typeof v === 'string' && v.trim().length > 0;
const isFiniteNumber = (v) => typeof v === 'number' && Number.isFinite(v);

function validateWorkoutBody(req, res, next) {
    const { workoutFocus, workoutDate, workoutDuration, exercises } = req.body || {};

    if (!isNonEmptyString(workoutFocus)) {
        return res.status(400).json({ success: false, message: 'workoutFocus is required.' });
    }
    if (!workoutDate || Number.isNaN(new Date(workoutDate).getTime())) {
        return res.status(400).json({ success: false, message: 'workoutDate must be a valid date.' });
    }
    if (!isFiniteNumber(workoutDuration) || workoutDuration < 0) {
        return res.status(400).json({ success: false, message: 'workoutDuration must be a non-negative number.' });
    }
    if (!Array.isArray(exercises) || exercises.length === 0) {
        return res.status(400).json({ success: false, message: 'At least one exercise is required.' });
    }

    for (const ex of exercises) {
        if (!isNonEmptyString(ex.exerciseId) || !isNonEmptyString(ex.name)) {
            return res.status(400).json({ success: false, message: 'Each exercise needs an exerciseId and a name.' });
        }
        if (!Array.isArray(ex.sets) || ex.sets.length === 0) {
            return res.status(400).json({ success: false, message: `${ex.name} needs at least one set.` });
        }
        for (const s of ex.sets) {
            if (!isFiniteNumber(s.reps) || s.reps < 0 || !isFiniteNumber(s.weight) || s.weight < 0) {
                return res.status(400).json({ success: false, message: `${ex.name} has a set with an invalid reps/weight value.` });
            }
        }
    }

    // Whitelist exactly the fields the schema owns - never let the request body
    // dictate username/_id/timestamps (the mass-assignment gap flagged in §6).
    req.body = {
        goalText: typeof req.body.goalText === 'string' ? req.body.goalText : '',
        workoutFocus,
        workoutDate,
        workoutDuration,
        exercises: exercises.map((ex) => ({
            exerciseId: ex.exerciseId,
            recommendationId: isNonEmptyString(ex.recommendationId) ? ex.recommendationId : undefined,
            recommendationItemId: isNonEmptyString(ex.recommendationItemId) ? ex.recommendationItemId : undefined,
            name: ex.name,
            sets: ex.sets.map((s) => ({
                reps: s.reps,
                weight: s.weight,
                weightUnit: s.weightUnit === 'kg' ? 'kg' : 'lb',
                notes: typeof s.notes === 'string' ? s.notes : ''
            }))
        }))
    };

    next();
}

function validateRecommendationRequest(req, res, next) {
    const { goal, workoutFocus } = req.body || {};
    const allowedGoals = ['strength', 'hypertrophy', 'endurance'];
    if (goal !== undefined && goal !== null && !allowedGoals.includes(goal)) {
        return res.status(400).json({ success: false, message: `goal must be one of ${allowedGoals.join(', ')}.` });
    }
    if (workoutFocus !== undefined && workoutFocus !== null && typeof workoutFocus !== 'string') {
        return res.status(400).json({ success: false, message: 'workoutFocus must be a string.' });
    }
    next();
}

function validateFeedbackRequest(req, res, next) {
    const { recommendationId, action } = req.body || {};
    const allowedActions = ['accept', 'swap', 'thumbs_up', 'thumbs_down'];
    if (!isNonEmptyString(recommendationId)) {
        return res.status(400).json({ success: false, message: 'recommendationId is required.' });
    }
    if (!allowedActions.includes(action)) {
        return res.status(400).json({ success: false, message: `action must be one of ${allowedActions.join(', ')}.` });
    }
    next();
}

module.exports = { validateWorkoutBody, validateRecommendationRequest, validateFeedbackRequest };
