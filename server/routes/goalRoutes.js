const express = require('express');
const goalController = require('./../controllers/goalController')
const authMiddleware = require('../middleware/authMiddleware');
const router = express.Router();

router
    .route('/')
    .get(authMiddleware, goalController.getGoal)
    .post(authMiddleware, goalController.createGoal)
    .put(authMiddleware, goalController.updateGoal)

module.exports = router;