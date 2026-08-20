const express = require('express');
const cors = require('cors');
const authRouter = require('./routes/authRoutes');
const goalRouter = require('./routes/goalRoutes');
const historyRouter = require('./routes/historyRoutes');
const profileRouter = require('./routes/profileRoutes');
const recommendationRouter = require('./routes/recommendationRoutes');
const exerciseRouter = require('./routes/exerciseRoutes');
const calorieRouter = require('./routes/calorieRoutes');
const app = express();

app.use(cors());
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

module.exports = app;