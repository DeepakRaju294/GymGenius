# GymGenius — Technical Spec: Current State & Roadmap

Scope: the recommendation/optimization engine and progress visualization — the two pieces of the product that don't exist yet — plus every other gap found while auditing the codebase. Basic CRUD (auth, goals, workout logging/history) already works end-to-end and is not re-documented here.

> **Revision note (2)**: updated after a second design review. Recommendations are now persisted records (§4.7) linked to the workouts actually logged against them, so the system can tell prescribed performance from actual performance — that link is what makes `completionRate` (§4.3) and real outcome analysis possible, not just estimated-1RM trend-watching. The state machine no longer resets to `NORMAL` on a single noisy improvement (§4.2). Exercise catalog entries no longer carry a fake default weight (§3). Basic request validation and mass-assignment protection move up to Phase 2.5 instead of waiting for general hardening.
>
> **Revision note (1)**: the roadmap ships a simple end-to-end recommendation loop (selection + plain progressive overload) before plateau detection exists at all, so the architecture gets validated with real traffic before the harder algorithm is built on top of it. Progression state is event-sourced rather than overwrite-in-place, plateau thresholds are configurable instead of hardcoded, Redis is optional rather than a boot requirement, and plateau-logic tests move up next to the code instead of waiting for a general hardening phase.

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

The three services exist as scaffolding but are not integrated: the ml service cannot start, and even if it could, it reads a different Mongo schema than the one the server actually writes. Redis is not deployed/configured anywhere yet either — treat it as optional (see §4.4) rather than something blocking Phase 1; nothing about the recommendation loop requires a cache until there's an actual latency problem to solve.

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
  secondaryMuscles: [String], equipment: [String], tags: [String] /* goals */ }
```
No `defaultWeightLbs` field — there's no meaningful default bench/squat/curl weight across a beginner and an advanced lifter; a fixed catalog default would just be wrong for most users. For an exercise the user has never logged, the MVP requires the user to enter a starting weight themselves rather than guessing one; a smarter cold-start (inferring from similar-exercise history or profile experience level) is a later refinement, not a Phase 2 requirement.

**`historyModel.js` — `exercises` subdocument, replacing the untyped `Object`:**
```js
exercises: [{
  exerciseId: { type: String, required: true },   // FK into exercises catalog
  recommendationId: { type: String },               // set if this exercise came from a recommendation (§4.7); absent for freely-logged exercises
  name: String,                                     // denormalized for display
  sets: [{ reps: Number, weight: Number, weightUnit: { type: String, enum: ['lb','kg'], default: 'lb' }, notes: String }]
}],
```
Add `timestamps: true`. Coerce `reps`/`weight` to `Number` client-side before POST (`NewWorkout.js` currently sends raw input-`.value` strings). `recommendationId` is what lets the system later compare *prescribed* sets/reps/weight (stored on the `recommendations` document, §4.7) against *actual* logged performance — without it, "did the user succeed" can only be inferred from raw trend-watching, which conflates "the user wasn't given this prescription" with "the user was given it and failed."

**`profileModel.js`**: add `equipment: [String]` and `weightUnit`/`heightUnit` fields so the ml service's equipment filter and any future unit conversion have real data to read.

**ml service**: repoint `fetch_user_history`/`equipment_profile` at the server's actual `histories`/`profiles` collections and field names instead of a parallel `workouts` schema. One database, one shape — not two services independently modeling the same workout.

## 4. Recommendation / optimization engine

### 4.0 The MVP loop — ship this before the plateau engine

The recommender's job splits into three concerns that should stay separate in code, not just in this doc:

- **Selection** — *which exercises* should today's session include (goal/equipment/muscle-balance/recency).
- **Prescription** — *given* an exercise, what sets/reps/weight today (plain progressive overload).
- **Adaptation** — *when normal prescription stops working*, what changes (plateau detection → REP_ADJUST → REVERSE → SWAPPED).

The first shippable slice is Selection + Prescription wired all the way through, with the *response shape* Adaptation will later populate already in place:

```json
{
  "recommendationId": "rec_8f2a...",
  "exercise": "Bench Press",
  "prescription": { "sets": 3, "reps": 5, "weight": 195, "unit": "lb" },
  "strategy": "NORMAL",
  "reason": "Up 5 lb from your last bench session.",
  "change": { "previous": "185 lb × 8", "today": "195 lb × 5" }
}
```

Adaptation later just starts populating `strategy` with `REP_ADJUST`/`REVERSE`/`SWAPPED` and writing a different `reason`/`change` — the client and the API contract don't change shape when plateau logic lands. This is why Phase 3 in the roadmap (§7) is "ship the simple loop end-to-end," not "build the plateau engine": it validates the client↔server↔ml wiring and the data model against real usage before the harder algorithm is built on top of assumptions no one has tested yet. `recommendationId` is generated the moment this response is built (§4.7) — it's what the client sends back on `POST /feedback` and what `NewWorkout.js` attaches to a logged exercise if the user actually performs the suggestion.

### 4.1 What exists today (and its gap)

`score_rules()` (`features.py`) is a reasonable Selection-stage ranker (goal alignment + recency + frequency + success-rate weighting) — worth keeping. But `apply_progression()` is not real Prescription logic: it unconditionally adds +2.5/+5 lbs to whatever was last logged, regardless of whether the user actually progressed, stalled, or regressed. `success_rate()` is a stub returning `1.0` for everything. There is no Adaptation stage at all — no plateau detection, no "try lower reps/higher weight → if that fails, reverse → if that fails, swap exercise" logic anywhere in the codebase.

### 4.2 Plateau-detection state machine (Adaptation — build after §4.0 ships)

Don't make a single current-state document the only record of what happened — it can't answer "why did this change three weeks ago," and it can't feed chart annotations (§5.3) after the fact. Split into two collections:

**`progression_state`** — current status per `(username, exerciseId)`, one document, overwritten as state changes:
```js
{ username, exerciseId,
  currentStrategy: 'NORMAL' | 'REP_ADJUST' | 'REVERSE' | 'SWAPPED',
  strategyStartedAt: Date, strategySessionCount: Number,
  baselineEstimated1RM: Number, lastEvaluatedAt: Date, reason: String }
```

**`progression_events`** — append-only audit trail, one document per transition, never overwritten:
```js
{ username, exerciseId, ts: Date,
  type: 'PLATEAU_DETECTED' | 'REP_ADJUST_STARTED' | 'REVERSE_STARTED' | 'EXERCISE_SWAPPED' | 'PROGRESS_RESUMED',
  metrics: { estimated1RM: Number, priorEstimated1RM: Number } }
```
`progression_state` answers "what should I recommend right now"; `progression_events` answers "what happened and when" — the latter is what `StrengthProgressChart` (§5.3) annotates against.

**Trend signal**: estimated 1RM per session via the Epley formula — `weight * (1 + reps / 30)` — taken from the best set of that exercise in each session. Using estimated 1RM instead of raw weight lets a rep/weight trade-off (the whole point of the REP_ADJUST/REVERSE states) still register as progress or stall on a single comparable number.

**Plateau trigger**: configurable, not hardcoded — see the `ProgressionPolicy` below. Default policy: after at least 3 logged sessions of an exercise, compare estimated 1RM trend over the last 3 sessions; if no session improves over the previous by more than a 2% threshold, increment a stall counter; a plateau is declared once the counter reaches 2 (two consecutive stalled comparisons, not one noisy session).

```python
@dataclass
class ProgressionPolicy:
    plateau_window: int = 3
    improvement_threshold: float = 0.02
    stalls_before_intervention: int = 2
    rep_adjust_sessions: int = 2   # sessions to trial REP_ADJUST before trying REVERSE
    reverse_sessions: int = 2      # sessions to trial REVERSE before SWAPPED
    improvements_before_reset: int = 2   # consecutive improved sessions required to drop back to NORMAL
```
Keeping these as constructor parameters (not literals inside the detection function) means thresholds can be tuned — or made per-user/per-goal later — without touching the state-machine logic itself.

**State transitions**, evaluated each time `recommend()` builds an item for that exercise:

```
NORMAL ──plateau──▶ REP_ADJUST ──still plateaued after rep_adjust_sessions──▶ REVERSE ──still plateaued after reverse_sessions──▶ SWAPPED
  ▲                     │                                                        │
  └──── improvements_before_reset consecutive improved sessions, from any state ───┘
```

- **NORMAL**: current `apply_progression` behavior — small weight/rep increment session over session.
- **REP_ADJUST**: lower target reps (e.g. −2 from the goal's rep range), raise weight (e.g. +5–10%). This replaces `apply_progression`'s flat increment for this exercise while in this state.
- **REVERSE**: the opposite adjustment — raise reps (e.g. +3–4), lower weight back toward the pre-REP_ADJUST baseline. This is what "if that doesn't work, do the opposite" means concretely.
- **SWAPPED**: stop recommending this exercise; call `candidate_pool()` filtered to the same `primaryMuscle` and excluding this `exerciseId`, and recommend a replacement. Keep `progression_state` for the original exercise (don't delete it — a user might return to it later) but mark it deprioritized so it isn't re-suggested immediately.
- A non-`NORMAL` state resets to **NORMAL** only after `improvements_before_reset` *consecutive* improved sessions, not a single one. One 2.3%-better session right after switching to `REP_ADJUST` is barely evidence the new strategy worked — bouncing straight back to `NORMAL` on that alone would mean the state machine never actually tests an intervention before abandoning it. A single improvement still resets the stall counter (so the plateau doesn't re-trigger immediately), it just doesn't by itself flip the strategy back. Every transition writes one `progression_events` document.

**Feedback loop wiring**: `POST /feedback` already accepts `action: accept | swap | thumbs_up | thumbs_down`. An explicit `swap` should immediately push that exercise's state forward one step (skip waiting for more stalled sessions) rather than only invalidating the cache as it does today — a user asking to swap is a stronger signal than a computed plateau.

**Response contract**: `strategy`/`reason`/`change` (§4.0) get populated for real once this lands, e.g. *reason: "Bench press has plateaued at ~185 lb for 3 sessions — try 195 lb × 5 today."*

### 4.3 Feature engineering work

- Replace the `success_rate()` stub with two separate signals, not one — they answer different questions and get conflated if merged:
  - **`completionRate(username, exerciseId)`**: fraction of an exercise's last N *recommended* sessions (i.e. logged with a matching `recommendationId`, §4.7) where the user completed the prescribed sets/reps/weight. A session can complete-as-prescribed with zero estimated-1RM movement — e.g. two sessions in a row at `185×8×3, all sets completed` — and that's a successful, not a failed, session; it just isn't progression yet.
  - **`progressionRate(username, exerciseId)`**: fraction of an exercise's last N sessions where estimated 1RM improved over the prior session — this is what §4.2's plateau trigger actually watches.
  - `completionRate` needs the `recommendationId` link (§3, §4.7) to mean anything; it can't be computed from freely-logged exercises with no attached prescription.
- Wire `build_user_vector()` (currently computed but never called) into `score_rules()` — bias candidate selection toward muscle groups underrepresented in recent volume, so recommendations balance a user's training rather than only optimizing per-exercise progression.
- Add a `plateau_state(username, exerciseId)` accessor that the Prescription stage calls in place of the current unconditional `apply_progression()` call.

### 4.4 Fix order for Phase 1 (make it boot)

1. Fix `app.util` → `app.utils` imports in `main.py`, `features.py`, `recommenders.py`.
2. Fix `app.services.recommender` → `app.services.recommenders` in `main.py`; instantiate `recommender = Recommender()` at module scope.
3. Fix the missing `)` at `recommenders.py:79`.
4. Pin `pydantic>=2` consistently (schemas.py already assumes v2) and add `pymongo` to `requirements.txt`. Add a `CACHE_ENABLED` env flag (default `false`) that gates every call into `utils/cache.py`; add `redis` as an optional dependency, not a hard boot requirement — nothing in §4.0's MVP loop needs caching, and Redis isn't deployed anywhere yet anyway. Revisit once there's an actual latency problem to solve.
5. Point `fetch_user_history`/`equipment_profile` at the server's real `histories`/`profiles` collections (see §3) instead of `workouts`.
6. Seed the `exercises` catalog collection — currently referenced everywhere and populated nowhere.

### 4.5 Code organization

`features.py` and `recommenders.py` are already carrying Selection, Prescription, and (soon) Adaptation logic in two files with no separation. Split along the §4.0 boundaries before Adaptation adds a fourth state machine on top of an already-overloaded `features.py`:

```
ml/app/services/
  selection/
    candidate_pool.py   # today's candidate_pool() + score_rules()
    scorer.py
  prescription/
    progression.py       # today's apply_progression(), choose_sets_reps()
    targets.py
  adaptation/
    plateau.py            # §4.2 trend/trigger detection
    strategies.py          # REP_ADJUST / REVERSE / SWAPPED logic
  recommender.py           # orchestrates the three stages, unchanged public interface
```
`Recommender.recommend()` becomes an orchestrator calling into the three packages rather than a single file accumulating every concern.

### 4.6 Testing the plateau logic

Build this alongside §4.2, not deferred to general hardening (§6/§7) — the state machine is small, deterministic, and easy to get subtly wrong, which is exactly what synthetic-history unit tests are for. Cover at minimum:

- A flat-weight, flat-reps history over `plateau_window` sessions → plateau detected, transitions to `REP_ADJUST`.
- An improving history → stays `NORMAL`, no false-positive plateau.
- `REP_ADJUST` with subsequent improvement → resets to `NORMAL`.
- `REP_ADJUST` with continued stall through `rep_adjust_sessions` → transitions to `REVERSE`.
- `REVERSE` with continued stall through `reverse_sessions` → transitions to `SWAPPED`.
- Improvement resuming from any non-`NORMAL` state → resets to `NORMAL` and logs a `PROGRESS_RESUMED` event.
- Explicit `swap` feedback → advances state immediately regardless of `stallSessions`.

Aim for on the order of 20–30 scenarios (boundary cases around the session-count thresholds, not just the happy path) before enabling this in production — this is cheap to test exhaustively and expensive to get wrong silently.

### 4.7 Recommendation record — closing the loop

Nothing so far persists *what GymGenius actually told the user to do* — only the resulting state/events. Without that record, the system can only ever reason about logged workouts in isolation; it can't answer "did the user do what we suggested" or "how often does REP_ADJUST actually work." Add a `recommendations` collection, written once per `/recommend` call:

```js
recommendations {
  recommendationId, username, createdAt,
  items: [{ exerciseId, prescription, strategy, reason, change }],
  context: { goal, equipment, policyVersion }
}
```

`policyVersion` tags which `ProgressionPolicy` (§4.2) generated this recommendation, so a future policy-tuning change doesn't retroactively corrupt analysis of past recommendations. The loop this closes:

```
recommendation ──user logs a workout with matching recommendationId (§3)──▶ actual performance
      │                                                                            │
      └──────────────────── compare prescribed vs. actual ◀───────────────────────┘
                                        │
                                        ▼
                          completionRate / progressionRate (§4.3)
                                        │
                                        ▼
                    "does REP_ADJUST actually work for this user/goal?"
```

That last question — measuring whether a *strategy*, not just an exercise, tends to work — is what makes this an optimization system rather than a workout generator with an opinion. It's not needed for §4.0's MVP loop or even for §4.2's plateau detection to function; it's what turns the accumulated history into something the system can learn from later (e.g. tuning `ProgressionPolicy` per goal from observed `REP_ADJUST` success rates). Build it in Phase 4 (§7) — right after the MVP loop ships and before plateau detection needs something to measure its own effectiveness against.

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

- **StrengthProgressChart** — line chart of estimated 1RM per exercise over time, annotated with the plateau/adjustment transitions pulled from `progression_events` (e.g. a marker where the app switched to REP_ADJUST).
- **MuscleVolumeChart** — stacked area/bar of weekly volume per muscle group.
- **WorkoutFrequencyHeatmap** — GitHub-contributions-style calendar.
- **PersonalRecordsList** — simple cards/table from the `/records` endpoint.
- **Today's Suggestion** card on `Dashboard.js` — calls `POST /api/v1/recommendation` (currently never called from the client at all) and renders `RecItem.reason`, with accept/swap/thumbs-up/down controls wired to `POST /api/v1/recommendation/feedback`.

## 6. Other issues found (not blocking, but should be tracked)

- **Response-shape inconsistency**: most controllers return `{success, data|message}`; `authController` returns bare `{token,user}` or `{error}` (different key, no `success`). Pick one envelope.
- **Mass assignment**: `historyController.updateWorkout` passes the entire raw request body into `findOneAndUpdate` with no field whitelist — a client could attempt to overwrite `username`/`_id`. *(Addressed for the endpoints under active change in Phase 2.5, §7; remaining routes covered in Phase 8.)*
- **No request validation anywhere** in `server/controllers` — no joi/zod/express-validator; Mongoose schema validators are the only line of defense, and their errors (e.g. raw Mongo duplicate-key messages) leak to the client as-is via generic `500` catches. *(Same — Phase 2.5 covers workout/recommendation endpoints first, since those are the ones about to change shape; the rest is Phase 8.)*
- **Race condition**: `goalController.createGoal` checks-then-creates instead of using a unique compound index on `(username, weekStart)`.
- **CORS**: `app.use(cors())` with no options — allows all origins.
- **Pagination**: `History.js` requests `?page&limit`; `historyController.getAllWorkouts` ignores both and returns the full unpaginated collection every time.
- **Missing route**: client's `Profile.js` calls `POST /api/v1/auth/logout`, which doesn't exist server-side (404, silently ignored — logout works only because the client also clears `localStorage` unconditionally).
- **Unit inconsistency**: weight is unitless in the DB, labeled "kg" in `History.js` and "lb" in `Profile.js` — needs a single stored unit (see §3 schema change).
- **No tests** beyond the untouched CRA-default `App.test.js` (which itself no longer matches `App.js`'s actual content). No server tests, no ml tests.
- **No root-level orchestration**: no root `package.json`/`concurrently` script to run client+server+ml together; no `ml/.env.example` documenting `MONGO_URI`/`MONGO_DB`/`REDIS_URL`/`CACHE_TTL_SECONDS`.
- **Dead/unused code**: `build_user_vector()` computed but never called (see §4.3 — now given a job); `PageLayout.js` component exists but `Home.js` duplicates its markup inline instead of using it.

## 7. Phased roadmap

Ordered so the architecture gets proven with a simple recommendation loop before the harder Adaptation algorithm is built on top of it — not repair → sophisticated engine → UI, but repair → data model → simple loop → instrumentation → sophisticated optimization.

| Phase | Work | Depends on |
|---|---|---|
| 0 | Security hygiene: stop tracking `config.env`, add `config.env.example` | — *(done in this change)* |
| 1 | Fix ml service boot defects (§4.4); make `/healthz`/`/readyz` actually pass; Redis optional via `CACHE_ENABLED` | Phase 0 |
| 2 | Data model: exercise catalog + `historyModel` typed fields (incl. `recommendationId`) + repoint ml at real collections (§3) | Phase 1 |
| 2.5 | Request validation + mass-assignment fix on the endpoints about to see real new traffic: workout create/update, `/recommendation`, `/recommendation/feedback` (pulled forward from §6/§8 — cheaper to establish the boundary now than to debug schema changes against an unvalidated API) | Phase 2 |
| 3 | Ship the MVP loop end-to-end (§4.0): Selection (`score_rules`) + plain Prescription (`apply_progression`), `strategy`/`reason`/`change` response shape, client calls `/recommendation` and renders the suggestion with feedback controls | Phase 2.5 |
| 4 | Recommendation instrumentation (§4.7): persist the `recommendations` collection, wire `recommendationId` from suggestion through to a logged workout, real event logging (groundwork for `progression_events`, §4.2) | Phase 3 |
| 5 | Server aggregation endpoints (§5.2) + client charts: strength progression, muscle volume, frequency heatmap, PRs (§5.3) | Phase 2 |
| 6 | Plateau detection (§4.2): trend/trigger logic, `completionRate`/`progressionRate` (§4.3), `ProgressionPolicy` config, code split (§4.5), synthetic test suite (§4.6) before enabling | Phase 3, 4 |
| 7 | REP_ADJUST / REVERSE / SWAPPED strategies on top of the Phase 6 signal, annotated on the Phase 5 charts via `progression_events` | Phase 6 |
| 8 | Broader hardening: consistent response envelope, remaining pagination/CORS gaps, integration test coverage | Independent — can run alongside 1–7 |
