const express = require('express');
const cors = require('cors');
const authRouter = require('./routes/authRoutes');
const goalRouter = require('./routes/goalRoutes');
const historyRouter = require('./routes/historyRoutes');
const profileRouter = require('./routes/profileRoutes');
const recommendationRouter = require('./routes/recommendationRoutes');
const exerciseRouter = require('./routes/exerciseRoutes');
const calorieRouter = require('./routes/calorieRoutes');
const coldStartRouter = require('./routes/coldStartRoutes');
const app = express();

// docs/SPEC.md §6 - was app.use(cors()) with no options, allowing any origin.
// CLIENT_URL supports a comma-separated list for multiple environments; falls
// back to the React dev server default so this doesn't break local dev for
// anyone who hasn't added CLIENT_URL to their config.env yet.
const allowedOrigins = (process.env.CLIENT_URL || 'http://localhost:3000')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);

app.use(cors({
    origin: allowedOrigins,
    credentials: true
}));
app.use(express.json());

app.get('/', (req, res) => {
    res.send("API is working");
});

app.use('/api/v1/goal', goalRouter);
app.use('/api/v1/history', historyRouter);
app.use('/api/v1/profile', profileRouter);
app.use('/api/v1/auth', authRouter);
app.use('/api/v1/recommendation', recommendationRouter);
app.use('/api/v1/exercises', exerciseRouter);
app.use('/api/v1/calories', calorieRouter);
app.use('/api/v1/cold-start', coldStartRouter);

module.exports = app;