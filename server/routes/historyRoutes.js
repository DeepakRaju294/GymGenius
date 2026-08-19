const express = require('express');
const router = express.Router();
const historyController = require('./../controllers/historyController');
const authMiddleware = require('../middleware/authMiddleware');

router 
    .route('/:id')
    .get(authMiddleware, historyController.getWorkout)
    .patch(authMiddleware, historyController.updateWorkout)
    .delete(authMiddleware, historyController.deleteWorkout)

router
    .route('/')
    .post(authMiddleware, historyController.createWorkout)
    .get(authMiddleware, historyController.getAllWorkouts)

module.exports = router;