const express = require('express');
const router = express.Router();
const historyController = require('./../controllers/historyController');
const authMiddleware = require('../middleware/authMiddleware');
const { validateWorkoutBody } = require('../middleware/validate');

// Aggregation routes (docs/SPEC.md §5.2) must be declared before '/:id' or Express
// would match e.g. '/progress' as an :id lookup.
router.get('/progress', authMiddleware, historyController.getProgress);
router.get('/volume', authMiddleware, historyController.getVolume);
router.get('/frequency', authMiddleware, historyController.getFrequency);
router.get('/records', authMiddleware, historyController.getRecords);

router
    .route('/:id')
    .get(authMiddleware, historyController.getWorkout)
    .patch(authMiddleware, validateWorkoutBody, historyController.updateWorkout)
    .delete(authMiddleware, historyController.deleteWorkout)

router
    .route('/')
    .post(authMiddleware, validateWorkoutBody, historyController.createWorkout)
    .get(authMiddleware, historyController.getAllWorkouts)

module.exports = router;
