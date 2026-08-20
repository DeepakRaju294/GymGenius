const express = require("express");
const axios = require("axios");
const authMiddleware = require("../middleware/authMiddleware");

const router = express.Router();
const REC_URL = process.env.REC_URL || "http://localhost:8000";

router.post("/estimate", authMiddleware, async (req, res) => {
    try {
        const { durationHours, weightKg, workoutType, avgHeartRate, totalSets } = req.body || {};
        if (typeof durationHours !== "number" || durationHours <= 0) {
            return res.status(400).json({ success: false, message: "durationHours must be a positive number." });
        }
        if (typeof weightKg !== "number" || weightKg <= 0) {
            return res.status(400).json({ success: false, message: "weightKg must be a positive number." });
        }
        const { data } = await axios.post(
            `${REC_URL}/estimate-calories`,
            { durationHours, weightKg, workoutType, avgHeartRate, totalSets },
            { timeout: 2000 }
        );
        res.json({ success: true, data });
    } catch (err) {
        res.status(502).json({ success: false, message: "Calorie estimator unavailable" });
    }
});

module.exports = router;
