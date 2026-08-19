const express = require('express');
const profileController = require('./../controllers/profileController')
const authMiddleware = require('../middleware/authMiddleware');
const router = express.Router();

router
    .route('/')
    .get(authMiddleware, profileController.getProfile)
    .post(authMiddleware, profileController.createProfile)
    .patch(authMiddleware, profileController.updateProfile)
    .delete(authMiddleware, profileController.deleteProfile)

module.exports = router;