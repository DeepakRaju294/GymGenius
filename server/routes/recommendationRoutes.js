const express = require("express");
const axios = require("axios");
const authMiddleware = require("../middleware/authMiddleware");
const { validateRecommendationRequest, validateFeedbackRequest } = require("../middleware/validate");

const router = express.Router();
const REC_URL = process.env.REC_URL || "http://localhost:8000";

router.post("/", authMiddleware, validateRecommendationRequest, async (req, res) => {
  try {
    const username = req.user.username;
    const { goal, workoutFocus } = req.body || {};
    const { data } = await axios.post(`${REC_URL}/recommend`, { username, goal, workoutFocus }, { timeout: 2000 });
    res.json({ success: true, data });
  } catch (err) {
    res.status(502).json({ success: false, message: "Recommender unavailable" });
  }
});

router.post("/feedback", authMiddleware, validateFeedbackRequest, async (req, res) => {
  try {
    const username = req.user.username;
    const { recommendationId, recommendationItemId, action, reason } = req.body || {};
    await axios.post(`${REC_URL}/feedback`, { recommendationId, recommendationItemId, username, action, reason }, { timeout: 1000 });
    res.status(204).end();
  } catch (err) {
    res.status(202).end();
  }
});

module.exports = router;
