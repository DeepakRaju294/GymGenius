const express = require("express");
const axios = require("axios");
const authMiddleware = require("../middleware/authMiddleware");

const router = express.Router();
const REC_URL = process.env.REC_URL || "http://localhost:8000";

router.post("/assessment", authMiddleware, async (req, res) => {
    try {
        const { pushUpsPerSet, benchPressKnownWeightLb, benchPressKnownReps, squatComfort } = req.body || {};
        const { data } = await axios.post(
            `${REC_URL}/cold-start-assessment`,
            {
                username: req.user.username,
                pushUpsPerSet,
                benchPressKnownWeightLb,
                benchPressKnownReps,
                squatComfort,
            },
            { timeout: 2000 }
        );
        res.json({ success: true, data });
    } catch (err) {
        res.status(502).json({ success: false, message: "Cold-start assessment unavailable" });
    }
});

module.exports = router;
