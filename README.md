# GymGenius

Full-stack fitness app that helps users track workouts, set goals, and get
data-driven training recommendations that adapt when progress stalls. See
[docs/SPEC.md](docs/SPEC.md) for the full architecture and design rationale.

## Services

- `client/` - React (Create React App) + Tailwind + shadcn/ui
- `server/` - Express + Mongoose (MongoDB)
- `ml/` - FastAPI recommendation/optimization engine (Python)

## Running locally

**1. Configure secrets** (never committed - see `.gitignore`):

```
cp server/config.env.example server/config.env   # fill in MONGO_URI, JWT_SECRET
cp ml/.env.example ml/.env                       # MONGO_URI + MONGO_DB must match server's
```

`ml/.env`'s `MONGO_DB` must be the same database the Node server actually
connects to - check the path segment of `server/config.env`'s `MONGO_URI`, or
the Atlas UI, since the ml service reads the server's own collections directly.

**2. Install dependencies:**

```
npm install --prefix server
npm install --prefix client
npm install                        # root - installs `concurrently` for step 4
python -m venv ml/.venv
ml/.venv/Scripts/pip install -r ml/requirements.txt   # ml/.venv/bin/pip on macOS/Linux
```

**3. Seed the exercise catalog** (once, or after adding new exercises):

```
npm run seed
```

**4. Run everything:**

```
npm run dev                                     # server (:5000) + client (:3000)
ml/.venv/Scripts/uvicorn app.main:app --reload --port 8000 --app-dir ml   # separate terminal
```

The server proxies `/api/v1/recommendation` to the ml service at `REC_URL`
(defaults to `http://localhost:8000`).

## Tests

```
cd ml && .venv/Scripts/pytest        # plateau state machine (docs/SPEC.md §4.6)
cd client && npm test
```
