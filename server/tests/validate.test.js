const { validateWorkoutBody, validateRecommendationRequest, validateFeedbackRequest } = require('../middleware/validate');

function mockRes() {
    const res = {};
    res.status = jest.fn().mockReturnValue(res);
    res.json = jest.fn().mockReturnValue(res);
    return res;
}

describe('validateWorkoutBody', () => {
    const validBody = () => ({
        workoutFocus: 'push',
        workoutDate: '2026-01-01',
        workoutDuration: 45,
        goalText: 'get stronger',
        exercises: [
            {
                exerciseId: 'bench_press',
                name: 'Bench Press',
                sets: [{ reps: 8, weight: 135, weightUnit: 'lb', notes: '' }]
            }
        ]
    });

    test('calls next() and passes through a valid body', () => {
        const req = { body: validBody() };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(next).toHaveBeenCalledTimes(1);
        expect(res.status).not.toHaveBeenCalled();
    });

    test('rejects a missing workoutFocus', () => {
        const req = { body: { ...validBody(), workoutFocus: '' } };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(next).not.toHaveBeenCalled();
        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects an invalid workoutDate', () => {
        const req = { body: { ...validBody(), workoutDate: 'not-a-date' } };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects a negative workoutDuration', () => {
        const req = { body: { ...validBody(), workoutDuration: -5 } };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects an empty exercises array', () => {
        const req = { body: { ...validBody(), exercises: [] } };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects an exercise missing exerciseId', () => {
        const body = validBody();
        body.exercises[0].exerciseId = '';
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects an exercise with no sets', () => {
        const body = validBody();
        body.exercises[0].sets = [];
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects a set with a negative weight', () => {
        const body = validBody();
        body.exercises[0].sets[0].weight = -10;
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('whitelists the body - strips fields not in the schema (mass-assignment protection)', () => {
        const body = { ...validBody(), username: 'someone-else', _id: 'forged-id', isAdmin: true };
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(next).toHaveBeenCalled();
        expect(req.body.username).toBeUndefined();
        expect(req.body._id).toBeUndefined();
        expect(req.body.isAdmin).toBeUndefined();
    });

    test('defaults weightUnit to lb when omitted or invalid', () => {
        const body = validBody();
        body.exercises[0].sets[0].weightUnit = 'stone';
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(req.body.exercises[0].sets[0].weightUnit).toBe('lb');
    });

    test('preserves a valid kg weightUnit', () => {
        const body = validBody();
        body.exercises[0].sets[0].weightUnit = 'kg';
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(req.body.exercises[0].sets[0].weightUnit).toBe('kg');
    });

    test('drops recommendationId/recommendationItemId when not strings', () => {
        const body = validBody();
        body.exercises[0].recommendationId = 12345;
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(req.body.exercises[0].recommendationId).toBeUndefined();
    });

    test('keeps a valid recommendationId/recommendationItemId', () => {
        const body = validBody();
        body.exercises[0].recommendationId = 'rec_123';
        body.exercises[0].recommendationItemId = 'recItem_1';
        const req = { body };
        const res = mockRes();
        const next = jest.fn();

        validateWorkoutBody(req, res, next);

        expect(req.body.exercises[0].recommendationId).toBe('rec_123');
        expect(req.body.exercises[0].recommendationItemId).toBe('recItem_1');
    });
});

describe('validateRecommendationRequest', () => {
    test('allows an empty body', () => {
        const req = { body: {} };
        const res = mockRes();
        const next = jest.fn();

        validateRecommendationRequest(req, res, next);

        expect(next).toHaveBeenCalled();
    });

    test('allows a valid goal', () => {
        const req = { body: { goal: 'strength' } };
        const res = mockRes();
        const next = jest.fn();

        validateRecommendationRequest(req, res, next);

        expect(next).toHaveBeenCalled();
    });

    test('rejects an invalid goal', () => {
        const req = { body: { goal: 'get-swole' } };
        const res = mockRes();
        const next = jest.fn();

        validateRecommendationRequest(req, res, next);

        expect(next).not.toHaveBeenCalled();
        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects a non-string workoutFocus', () => {
        const req = { body: { workoutFocus: 123 } };
        const res = mockRes();
        const next = jest.fn();

        validateRecommendationRequest(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });
});

describe('validateFeedbackRequest', () => {
    test('allows a valid feedback request', () => {
        const req = { body: { recommendationId: 'rec_123', action: 'accept' } };
        const res = mockRes();
        const next = jest.fn();

        validateFeedbackRequest(req, res, next);

        expect(next).toHaveBeenCalled();
    });

    test('rejects a missing recommendationId', () => {
        const req = { body: { action: 'accept' } };
        const res = mockRes();
        const next = jest.fn();

        validateFeedbackRequest(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('rejects an invalid action', () => {
        const req = { body: { recommendationId: 'rec_123', action: 'destroy' } };
        const res = mockRes();
        const next = jest.fn();

        validateFeedbackRequest(req, res, next);

        expect(res.status).toHaveBeenCalledWith(400);
    });

    test('accepts all four documented actions', () => {
        ['accept', 'swap', 'thumbs_up', 'thumbs_down'].forEach((action) => {
            const req = { body: { recommendationId: 'rec_123', action } };
            const res = mockRes();
            const next = jest.fn();

            validateFeedbackRequest(req, res, next);

            expect(next).toHaveBeenCalled();
        });
    });
});
