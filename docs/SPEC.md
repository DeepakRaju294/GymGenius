# GymGenius — Technical Spec: Current State & Roadmap

Scope: the recommendation/optimization engine and progress visualization — the two pieces of the product that don't exist yet — plus every other gap found while auditing the codebase. Basic CRUD (auth, goals, workout logging/history) already works end-to-end and is not re-documented here.

## 1. Architecture today

```
client (React, Tailwind, shadcn/ui)
   |  fetch, Bearer JWT
   v
server (Express + Mongoose, MongoDB Atlas)
   |  axios proxy, POST /recommend, POST /feedback
   v
ml (FastAPI, Python) ──reads/writes──> MongoDB (separate collections: workouts/profiles/exercises)
                       ──reads/writes──> Redis (recommendation cache)
```

The three services exist as scaffolding but are not integrated: the ml service cannot start, and even if it could, it reads a different Mongo schema than the one the server actually writes. Redis is not deployed/configured anywhere yet either.

## 2. Blocking defects (not gaps — things that are actively broken)

| # | Where | Problem |
|---|---|---|
| 1 | `ml/app/main.py:5-7` | Imports `app.services.recommender` (singular) and `app.util.db`/`app.util.cache` (singular) — real paths are `recommenders.py` and `app/utils/`. `ModuleNotFoundError` on boot. |
| 2 | `ml/app/main.py` | `Recommender` is imported but never instantiated; `/recommend` and `/feedback` reference an undefined `recommender` name. |
| 3 | `ml/app/services/recommenders.py:79` | Unclosed parenthesis — `SyntaxError`, module won't parse. |
| 4 | `ml/app/api/schemas.py` | Uses `ConfigDict` (Pydantic v2 API) but `ml/requirements.txt` pins `pydantic==1.10.12`. |
| 5 | `ml/requirements.txt` | `pymongo` and `redis` are imported directly in `utils/db.py`/`utils/cache.py` but missing from requirements. |
| 6 | `server/config.env` (fixed in this change) | Live MongoDB Atlas credentials and JWT secret were about to be committed — `.gitignore` matched `.env`/`.env.*` but not `config.env`. Now gitignored, unstaged, replaced with `server/config.env.example`. |
| 7 | `server/package.json` | Only lists `nodemon` as a dependency; `express`, `mongoose`, `bcryptjs`, `jsonwebtoken`, `cors`, `axios`, `dotenv` are all required in code but absent — `npm install` on a clean checkout won't produce a runnable server. |

Everything downstream in this spec assumes #1–5 get fixed first (Phase 1 below) — there's no point designing plateau logic on top of a service that can't boot.

## 3. Data model gap

The server and ml service don't describe the same data:

| | Server (`historyModel.js`, actual) | ML service expects (`features.py`) |
|---|---|---|
| Collection | `histories` | `workouts` |
| Timestamp field | `workoutDate` | `ts` |
| Exercise identity | none — free-text `name` only | `exerciseId` (join key into `db.exercises` catalog) |
| Muscle group | none | `primaryMuscle` (used for rest-window filtering and volume vectors) |
| Weight | `weight` (string, no unit — client hardcodes "kg" in `History.js` display, "lb" in `Profile.js` label) | `weight_lbs` (float) |
| Reps | `reps` (string) | `reps` (int) |
| Exercise catalog | doesn't exist | `db.exercises` with `tags`/`goals`/`equipment` — referenced but never seeded anywhere in the repo |
| Profile equipment | `profileModel.js` has no `equipment` field | `equipment_profile()` reads `db.profiles.equipment` — always empty for real users |

None of this is a "connect two working systems" job — it's building the missing exercise catalog and retrofitting `historyModel` with typed, identified fields, then pointing the ml service at the server's real collection instead of an imaginary `workouts` collection.

### Proposed schema changes

**New collection `exercises`** (canonical catalog, seeded once):
```js
{ exerciseId: String (unique), name: String, primaryMuscle: String,
  secondaryMuscles: [String], equipment: [String], tags: [String] /* goals */,
  defaultWeightLbs: Number }
```

**`historyModel.js` — `exercises` subdocument, replacing the untyped `Object`:**
```js
exercises: [{
  exerciseId: { type: String, required: true },   // FK into exercises catalog
  name: String,                                     // denormalized for display
  sets: [{ reps: Number, weight: Number, weightUnit: { type: String, enum: ['lb','kg'], default: 'lb' }, notes: String }]
}],
```
Add `timestamps: true`. Coerce `reps`/`weight` to `Number` client-side before POST (`NewWorkout.js` currently sends raw input-`.value` strings).

**`profileModel.js`**: add `equipment: [String]` and `weightUnit`/`heightUnit` fields so the ml service's equipment filter and any future unit conversion have real data to read.

**ml service**: repoint `fetch_user_history`/`equipment_profile` at the server's actual `histories`/`profiles` collections and field names instead of a parallel `workouts` schema. One database, one shape — not two services independently modeling the same workout.

## 4. Recommendation / optimization engine

### 4.1 What exists today (and its gap)

`score_rules()` (`features.py`) is a reasonable *exercise-selection* ranker (goal alignment + recency + frequency + success-rate weighting) — worth keeping. But `apply_progression()` is not the progression logic the product needs: it unconditionally adds +2.5/+5 lbs to whatever was last logged, regardless of whether the user actually progressed, stalled, or regressed. `success_rate()` is a stub returning `1.0` for everything. There is no plateau detection and no "try lower reps/higher weight → if that fails, reverse → if that fails, swap exercise" logic anywhere in the codebase.

### 4.2 Plateau-detection state machine (new)

Per `(username, exerciseId)`, track a **progression state** in a new collection `progression_state`:

```js
{ username, exerciseId, state: 'NORMAL' | 'REP_ADJUST' | 'REVERSE' | 'SWAPPED',
  enteredStateAt: Date, stallSessions: Number, lastEstimated1RM: Number }
```

**Trend signal**: estimated 1RM per session via the Epley formula — `weight * (1 + reps / 30)` — taken from the best set of that exercise in each session. Using estimated 1RM instead of raw weight lets a rep/weight trade-off (the whole point of the REP_ADJUST/REVERSE states) still register as progress or stall on a single comparable number.

**Plateau trigger**: after at least 3 logged sessions of an exercise, compare estimated 1RM trend over the last 3 sessions. If the trend is flat-or-down (no session improves over the previous by more than a small epsilon, e.g. 2%), increment `stallSessions`; a real plateau is declared once `stallSessions >= 2` (i.e., two consecutive stalled comparisons, not one noisy session).

**State transitions**, evaluated each time `recommend()` builds an item for that exercise:

```
NORMAL ──plateau──▶ REP_ADJUST ──still plateaued after 2 sessions──▶ REVERSE ──still plateaued──▶ SWAPPED
  ▲                     │                                                │
  └──── improvement resumes at any state ─────────────────────────────────┘
```

- **NORMAL**: current `apply_progression` behavior — small weight/rep increment session over session.
- **REP_ADJUST**: lower target reps (e.g. −2 from the goal's rep range), raise weight (e.g. +5–10%). This replaces `apply_progression`'s flat increment for this exercise while in this state.
- **REVERSE**: the opposite adjustment — raise reps (e.g. +3–4), lower weight back toward the pre-REP_ADJUST baseline. This is what "if that doesn't work, do the opposite" means concretely.
- **SWAPPED**: stop recommending this exercise; call `candidate_pool()` filtered to the same `primaryMuscle` and excluding this `exerciseId`, and recommend a replacement. Keep `progression_state` for the original exercise (don't delete it — a user might return to it later) but mark it deprioritized so it isn't re-suggested immediately.
- Any state resets to **NORMAL** the moment estimated 1RM improves beyond epsilon again.

**Feedback loop wiring**: `POST /feedback` already accepts `action: accept | swap | thumbs_up | thumbs_down`. An explicit `swap` should immediately push that exercise's state forward one step (skip waiting for more stalled sessions) rather than only invalidating the cache as it does today — a user asking to swap is a stronger signal than a computed plateau.

**Response contract addition**: `RecItem.reason` (already exists in `schemas.py`, currently unused for this) should carry a human-readable explanation, e.g. *"Bench press has plateaued at ~185 lb for 3 sessions — try 195 lb × 5 today."* This is what the client surfaces to the user; it's also the natural place to note when an exercise was swapped and why.

### 4.3 Feature engineering work

- Replace `success_rate()` stub with a real definition: fraction of an exercise's last N sessions where estimated 1RM improved over the prior session.
- Wire `build_user_vector()` (currently computed but never called) into `score_rules()` — bias candidate selection toward muscle groups underrepresented in recent volume, so recommendations balance a user's training rather than only optimizing per-exercise progression.
- Add a `plateau_state(username, exerciseId)` accessor that `recommenders.py` calls in place of the current unconditional `apply_progression()` call.

### 4.4 Fix order for Phase 1 (make it boot)

1. Fix `app.util` → `app.utils` imports in `main.py`, `features.py`, `recommenders.py`.
2. Fix `app.services.recommender` → `app.services.recommenders` in `main.py`; instantiate `recommender = Recommender()` at module scope.
3. Fix the missing `)` at `recommenders.py:79`.
4. Pin `pydantic>=2` consistently (schemas.py already assumes v2) and add `pymongo`, `redis` to `requirements.txt`.
5. Point `fetch_user_history`/`equipment_profile` at the server's real `histories`/`profiles` collections (see §3) instead of `workouts`.
6. Seed the `exercises` catalog collection — currently referenced everywhere and populated nowhere.

## 5. Progress visualization

Nothing exists yet: no charting library in `client/package.json`, no chart code on any page, no server aggregation endpoints to feed one.

### 5.1 Library

**Recharts** — pairs naturally with the shadcn/ui primitives already scaffolded (`components.json`, `components/ui/{button,card,textarea}.js`); shadcn ships a `chart` component built directly on Recharts, so adding it continues the existing design system instead of introducing a second one.

### 5.2 New server endpoints (`historyController.js`)

Aggregation belongs in the server (it already owns Mongoose/the data), not the ml service (whose job is recommendations, not general analytics):

- `GET /api/v1/history/progress?exerciseId=&range=90d` → `[{ date, weight, reps, estimated1RM }]` time series for one exercise.
- `GET /api/v1/history/volume?range=` → weekly training volume (`Σ weight × reps × sets`) grouped by `primaryMuscle`, for a stacked chart — requires the `exercises` catalog join from §3.
- `GET /api/v1/history/frequency?range=` → workout count per day, for a calendar heatmap.
- `GET /api/v1/history/records` → per-exercise personal records (max weight, max reps, max estimated 1RM, and the date each was hit).

### 5.3 New client surface

A "Progress" tab/page, plus a recommendation surface on the Dashboard:

- **StrengthProgressChart** — line chart of estimated 1RM per exercise over time, annotated with the plateau/adjustment transitions pulled from `progression_state` (e.g. a marker where the app switched to REP_ADJUST).
- **MuscleVolumeChart** — stacked area/bar of weekly volume per muscle group.
- **WorkoutFrequencyHeatmap** — GitHub-contributions-style calendar.
- **PersonalRecordsList** — simple cards/table from the `/records` endpoint.
- **Today's Suggestion** card on `Dashboard.js` — calls `POST /api/v1/recommendation` (currently never called from the client at all) and renders `RecItem.reason`, with accept/swap/thumbs-up/down controls wired to `POST /api/v1/recommendation/feedback`.

## 6. Other issues found (not blocking, but should be tracked)

- **Response-shape inconsistency**: most controllers return `{success, data|message}`; `authController` returns bare `{token,user}` or `{error}` (different key, no `success`). Pick one envelope.
- **Mass assignment**: `historyController.updateWorkout` passes the entire raw request body into `findOneAndUpdate` with no field whitelist — a client could attempt to overwrite `username`/`_id`.
- **No request validation anywhere** in `server/controllers` — no joi/zod/express-validator; Mongoose schema validators are the only line of defense, and their errors (e.g. raw Mongo duplicate-key messages) leak to the client as-is via generic `500` catches.
- **Race condition**: `goalController.createGoal` checks-then-creates instead of using a unique compound index on `(username, weekStart)`.
- **CORS**: `app.use(cors())` with no options — allows all origins.
- **Pagination**: `History.js` requests `?page&limit`; `historyController.getAllWorkouts` ignores both and returns the full unpaginated collection every time.
- **Missing route**: client's `Profile.js` calls `POST /api/v1/auth/logout`, which doesn't exist server-side (404, silently ignored — logout works only because the client also clears `localStorage` unconditionally).
- **Unit inconsistency**: weight is unitless in the DB, labeled "kg" in `History.js` and "lb" in `Profile.js` — needs a single stored unit (see §3 schema change).
- **No tests** beyond the untouched CRA-default `App.test.js` (which itself no longer matches `App.js`'s actual content). No server tests, no ml tests.
- **No root-level orchestration**: no root `package.json`/`concurrently` script to run client+server+ml together; no `ml/.env.example` documenting `MONGO_URI`/`MONGO_DB`/`REDIS_URL`/`CACHE_TTL_SECONDS`.
- **Dead/unused code**: `build_user_vector()` computed but never called (see §4.3 — now given a job); `PageLayout.js` component exists but `Home.js` duplicates its markup inline instead of using it.

## 7. Phased roadmap

| Phase | Work | Depends on |
|---|---|---|
| 0 | Security hygiene: stop tracking `config.env`, add `config.env.example` | — *(done in this change)* |
| 1 | Fix ml service boot defects (§4.4 items 1–4); make `/healthz`/`/readyz` actually pass | Phase 0 |
| 2 | Data model: exercise catalog + `historyModel` typed fields + repoint ml at real collections (§3) | Phase 1 |
| 3 | Plateau-detection state machine (§4.2) + real `success_rate`/`build_user_vector` wiring (§4.3) | Phase 2 |
| 4 | Client: call `/recommendation`, render suggestion + feedback controls | Phase 3 |
| 5 | Server aggregation endpoints for visualization (§5.2) | Phase 2 |
| 6 | Client charts: strength progression, muscle volume, frequency heatmap, PRs (§5.3) | Phase 5 |
| 7 | Hardening: validation library, consistent response envelope, mass-assignment fix, pagination, CORS, tests | Independent — can run alongside 1–6 |
