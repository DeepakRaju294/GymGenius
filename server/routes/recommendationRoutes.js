const express = require("express");
const axios = require("axios");

const router = express.Router();
const REC_URL = process.env.REC_URL || "http://localhost:8000";

function getUsername(req) {
  return req.user?.username || req.body?.username;
}

router.post("/", async (req, res) => {
  try {
    const username = getUsername(req);
    const { goal, workoutFocus } = req.body || {};
    const { data } = await axios.post(`${REC_URL}/recommend`, { username, goal, workoutFocus }, { timeout: 800 });
    res.json({ success: true, data });
  } catch {
    res.status(502).json({ success: false, message: "Recommender unavailable" });
  }
});

router.post("/feedback", async (req, res) => {
  try {
    const username = getUsername(req);
    const { recId, exerciseId, action, reason } = req.body || {};
    await axios.post(`${REC_URL}/feedback`, { recId, username, exerciseId, action, reason }, { timeout: 500 });
    res.status(204).end();
  } catch {
    res.status(202).end();
  }
});

module.exports = router;   
