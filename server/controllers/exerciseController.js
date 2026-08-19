const Exercise = require('./../models/exerciseModel');

exports.getExercises = async (req, res) => {
    try {
        const exercises = await Exercise.find({}).sort({ name: 1 });
        res.status(200).json({
            success: true,
            data: { exercises }
        })
    }
    catch (err) {
        res.status(500).json({
            success: false,
            message: err.message
        })
    }
}
