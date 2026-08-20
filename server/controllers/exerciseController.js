const Exercise = require('./../models/exerciseModel');

// docs/SPEC.md §6 - was an unbounded Exercise.find({}) with no cap; harmless at
// 18 hand-seeded rows, a real problem once docs/ML_SPEC.md Phase 9's real
// catalog (hundreds-thousands of rows) lands. Defaults to isSelectable exercises
// only (never surface incomplete/unreviewed catalog rows to users) and caps the
// response, with real page/limit support for callers that want it - the client's
// current exercise-picker dropdown keeps working unpaginated up to the cap.
exports.getExercises = async (req, res) => {
    try {
        const filter = req.query.includeAll === 'true' ? {} : { isSelectable: { $ne: false } };
        const page = req.query.page ? Math.max(parseInt(req.query.page, 10) || 1, 1) : null;
        const limit = Math.min(Math.max(parseInt(req.query.limit, 10) || 500, 1), 1000);

        let query = Exercise.find(filter).sort({ name: 1 }).limit(limit);
        if (page) {
            query = query.skip((page - 1) * limit);
        }

        const [exercises, total] = await Promise.all([
            query,
            Exercise.countDocuments(filter)
        ]);

        res.status(200).json({
            success: true,
            data: {
                exercises,
                total,
                page: page || 1,
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
