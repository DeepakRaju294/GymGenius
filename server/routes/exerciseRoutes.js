const express = require('express');
const exerciseController = require('./../controllers/exerciseController');
const authMiddleware = require('../middleware/authMiddleware');
const router = express.Router();

router
    .route('/')
    .get(authMiddleware, exerciseController.getExercises)

module.exports = router;
