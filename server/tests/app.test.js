const request = require('supertest');
const jwt = require('jsonwebtoken');
const app = require('../app');

// These only cover routing/middleware wiring, not full request handling - none
// of these paths reach MongoDB, so they run without a live database connection.

describe('GET /', () => {
    test('health check responds without auth', async () => {
        const res = await request(app).get('/');
        expect(res.status).toBe(200);
        expect(res.text).toBe('API is working');
    });
});

describe('authMiddleware wiring', () => {
    test('protected route rejects a request with no token', async () => {
        const res = await request(app).get('/api/v1/history');
        expect(res.status).toBe(401);
    });

    test('protected route rejects an invalid token', async () => {
        const res = await request(app).get('/api/v1/history').set('Authorization', 'Bearer not-a-real-token');
        expect(res.status).toBe(403);
    });

    // A "valid token reaches the controller" test intentionally isn't here - past
    // auth, historyController calls History.find(), and without a live/mocked
    // Mongo connection Mongoose buffers the query indefinitely rather than
    // failing fast, which would just make this suite flaky. That path is
    // exercised by actually running the server (see docs/SPEC.md's manual
    // verification notes), not by this lightweight, DB-less suite.

    test('exercises route also requires auth', async () => {
        const res = await request(app).get('/api/v1/exercises');
        expect(res.status).toBe(401);
    });

    test('recommendation route requires auth', async () => {
        const res = await request(app).post('/api/v1/recommendation').send({});
        expect(res.status).toBe(401);
    });
});

describe('CORS configuration', () => {
    test('does not reflect an arbitrary origin (was a wide-open cors() before this)', async () => {
        const res = await request(app).get('/').set('Origin', 'http://evil.example.com');
        expect(res.headers['access-control-allow-origin']).not.toBe('http://evil.example.com');
        expect(res.headers['access-control-allow-origin']).not.toBe('*');
    });

    test('reflects the configured CLIENT_URL origin', async () => {
        const res = await request(app).get('/').set('Origin', 'http://localhost:3000');
        expect(res.headers['access-control-allow-origin']).toBe('http://localhost:3000');
    });
});

describe('request validation wiring', () => {
    test('POST /api/v1/history rejects a malformed body before touching the database', async () => {
        process.env.JWT_SECRET = process.env.JWT_SECRET || 'test-secret-for-jest-only';
        const token = jwt.sign({ id: 'x', username: 'testuser' }, process.env.JWT_SECRET, { expiresIn: '1h' });

        const res = await request(app)
            .post('/api/v1/history')
            .set('Authorization', `Bearer ${token}`)
            .send({ workoutFocus: '', workoutDuration: -1, exercises: [] });

        expect(res.status).toBe(400);
    });
});
