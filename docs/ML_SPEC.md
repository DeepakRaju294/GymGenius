# GymGenius ML Expansion — Data-Driven Fitness Intelligence

Extends [docs/SPEC.md](SPEC.md) (the recommendation/optimization engine already implemented) with capabilities bootstrapped from public datasets, so the platform doesn't have to wait for its own user base to accumulate before any of this is useful. Scope is broader than "pick the next exercise" — it covers everything a real ML-driven fitness product would plausibly ship — but every capability here plugs into the existing `ml/` FastAPI service, the existing MongoDB collections, and the existing Selection/Prescription/Adaptation pipeline. Nothing here is a side project bolted onto GymGenius; it's the same product with real data behind it.

## 0. What's already sitting in the repo, unused

`ml/artifacts/` exists locally (gitignored — it was never committed) and already anticipates exactly this work:

| File | What it is | What it means for this spec |
|---|---|---|
| `default_weights.json` | Per-exercise starting weights (`"Barbell Bench Press": 45`) | Superseded by design — [docs/SPEC.md](SPEC.md) §3 deliberately dropped a fixed default weight per exercise (no single number is right across a beginner and an advanced lifter). §3 below replaces this with a *predicted* starting tier instead of a fixed number. |
| `equipment_map.json`, `muscle_groups.json` | Synonym maps (`"db"` → `"dumbbell"`, `"quadriceps"` → `"quads"`) | Exactly what's needed to normalize the messy, inconsistent labels across multiple public exercise datasets into one canonical taxonomy. Used directly in §1's ingestion pipeline. |
| `stoplist.json` | `["Upright Row (barbell wide grip)"]` | Not a stopword list despite the name — an exercise **contraindication list** (barbell upright rows are commonly flagged for shoulder impingement risk). Formalized into a real `cautionExercises` mechanism in §1. |
| `workout_focus_tags.json` | `"push"` → `["chest","shoulders","triceps"]`, etc. | A better focus-matching design than what's currently implemented — `candidate_pool()`'s `_exercise_matches_focus()` only matches an exercise's own `tags` array literally against the requested focus string, so `focus="push"` doesn't match an exercise tagged only `"chest"`. §1 fixes this. |
| `progression.yaml` | `weights: {align: 0.35, recency: 0.25, frequency: 0.25, success: 0.15}` | The exact scoring weights that were hardcoded in the original (broken) `features.py` and are now hardcoded again in `selection/scorer.py`. §4's learned re-ranker is what eventually replaces fixed weights like these with weights fit to real feedback data. |
| `version.txt` | `artifacts-0.1.0` | An existing versioning convention for this config bundle — reused as `ARTIFACTS_VERSION` in §5 rather than inventing a new one. |

None of this was wasted; it was the intended shape of exactly this work, just never wired up.

## 1. Real exercise catalog (replaces the 18 hand-seeded exercises)

**Problem**: `server/scripts/seedExercises.js` seeds 18 exercises by hand. Every downstream feature — Selection, substitution on `SWAPPED`, muscle-volume charts — is only as good as this catalog, and 18 exercises is a toy.

**Datasets** (verified currently listed on Kaggle as of this writing — check each one's license tab before ingesting, see §6):
- [Exercises Dataset](https://www.kaggle.com/datasets/akankshamishra0512/exercises-dataset) — 1,000+ exercises with muscles, equipment, instructions.
- [Gym Exercises Dataset](https://www.kaggle.com/datasets/rishitmurarka/gym-exercises-dataset) — adds `utility` (basic/auxiliary) and `mechanics` (compound/isolated) per exercise, which nothing in GymGenius has today.
- [Fitness Exercises Dataset](https://www.kaggle.com/datasets/exercisedb/fitness-exercises-dataset) — 1,500+ exercises with instructional GIFs (a Kaggle mirror of the free ExerciseDB dataset) — for actual exercise media, which the app has never had.
- [Gym Exercise Data](https://www.kaggle.com/datasets/niharika41298/gym-exercise-data) — 2,500+ exercises, a third independent source to cross-reference against.

**Pipeline** (`ml/training/ingest_exercise_catalog.py`):
1. Download each CSV into `ml/training/datasets/` (gitignored — already covered by the repo's `**/data/**` pattern).
2. Normalize equipment/muscle-group text through `ml/artifacts/equipment_map.json` / `muscle_groups.json` (extend these two files as new synonyms turn up — they're small, hand-curated, and that's fine).
3. **Dedupe near-duplicate exercise names across the three sources** (`"DB Bench Press"` vs `"Dumbbell Bench Press"` vs `"Bench Press (Dumbbell)"`) with `scikit-learn`'s `TfidfVectorizer` + cosine similarity over exercise names — this is the one genuinely ML-ish step in an otherwise-ETL pipeline, and it's the right tool for it (no deep learning needed for fuzzy string matching at this scale).
4. Merge into the `exercises` schema, extended with the new fields these datasets actually provide:
   ```js
   // server/models/exerciseModel.js additions
   mechanics: { type: String, enum: ['compound', 'isolation'] },
   utility: { type: String, enum: ['basic', 'auxiliary'] },
   gifUrl: { type: String },
   source: { type: String },       // which dataset(s) contributed this entry, for provenance
   ```
5. Write a `cautionExercises` collection seeded from an expanded `stoplist.json` (a handful of commonly-flagged-for-injury-risk movements — upright rows, behind-the-neck presses, etc.) with a short `reason` string per entry. `candidate_pool()` excludes these by default; a later, smaller feature could let a user's self-reported injuries in their profile expand this list per-user, but that's out of scope here.
6. Fix focus matching: `_exercise_matches_focus()` in `selection/candidate_pool.py` currently checks the exercise's own `tags` array against the requested focus string directly. Replace with a lookup through `workout_focus_tags.json` (`"push"` → `{chest, shoulders, triceps}`) matched against `primaryMuscle`, so a focus request actually expands to the muscle groups it should.

**Output**: `npm run seed` (or a new `ml/training/seed_from_catalog.py` writing directly to Mongo) populates hundreds-to-thousands of real exercises instead of 18, with data every other feature in this spec depends on.

## 2. Calorie / intensity estimation

Nothing in GymGenius estimates calories today — `workoutDuration` is logged and otherwise unused. This is a genuinely new, standalone feature, not a recommendation-engine tweak.

**Dataset**: [Gym Members Exercise Dataset](https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset) — 973 rows of age, gender, weight, height, max/avg/resting BPM, session duration, workout type, and calories burned.

**Model**: `scikit-learn`'s `GradientBoostingRegressor` (or start with `Ridge` as a baseline to beat) predicting `calories_burned` from `duration, avg_bpm, weight, workout_type`. At ~1k rows, classical gradient boosting is the right ceiling — a neural net would overfit and add nothing.

**The catch**: almost no GymGenius user will have heart-rate data. Ship two paths:
- **Model path** (`ml/app/services/ml/calorie_model.py::estimate(duration, avg_bpm, weight, workout_type)`) when heart rate is available.
- **MET fallback** (`ml/app/services/ml/calorie_model.py::estimate_met(duration, weight, exercise_ids)`) — standard MET-value-times-weight-times-duration formula, using MET values looked up per exercise (a small static table, not learned) — this is what actually runs for most users.

**Integration**:
- New optional fields on the set schema: `historyModel`'s `setSchema` gains `avgHeartRate: Number` (optional, not required — most users won't log it).
- New endpoint `POST /estimate-calories` on the ml service, proxied through the server the same way `/recommendation` is (`server/routes/historyRoutes.js` or a new `calorieRoutes.js`).
- Client: an "Estimated calories" line on a completed workout in `History.js` and on the Progress page — new user-visible value, not a recommendation-engine change.

**Evaluation**: hold out 20% of the Kaggle rows, report MAE against the model and against the MET fallback — ship the model only if it beats the fallback by a real margin; otherwise the MET table alone is good enough and the model isn't worth the maintenance.

## 3. Fitness-level classifier (a real cold-start, not a fixed default)

[docs/SPEC.md](SPEC.md) §3 deliberately removed a fixed default starting weight per exercise — there's no single "default bench press weight" that's right for both a beginner and an advanced lifter. That was the right call, but it left a gap: a brand-new user with zero logged history currently gets no guidance at all (`apply_progression` just returns `None` and the UI asks them to enter their own number). This closes that gap **without** reintroducing a fixed default — by predicting a *tier*, not a weight.

**Datasets**:
- [Body performance Data](https://www.kaggle.com/datasets/kukuroo3/body-performance-data) — age, gender, body measurements, grip force, sit-ups in 60s, broad jump, sit-and-reach, labeled into performance classes A–D.
- [Gym Members Exercise Dataset](https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset) (same as §2) — also carries an `Experience_Level` field, usable as a second labeled source.

**Model**: `scikit-learn`'s `RandomForestClassifier` (or `HistGradientBoostingClassifier`) predicting a fitness tier (`beginner | intermediate | advanced`) from a short set of inputs a new user can plausibly self-report or measure in five minutes: age, gender, body measurements already on the profile, plus 2-3 quick assessment numbers (e.g. push-ups in a minute, or grip strength if they have a dynamometer — optional fields, not blockers).

**Integration**:
- New collection `fitness_assessments`: `{ username, inputs: {...}, predictedTier, confidence, modelVersion, createdAt }` — the raw quiz answers plus what the model said, kept for later retraining.
- New onboarding step in `Login.js`'s profile-completion flow (step 2, optional — skippable): a short "quick fitness check" the classifier consumes.
- `prescription/progression.py::apply_progression()` gains a fallback path: when `last_top_weight()` is `None` (no history for this exercise), instead of returning `None` unconditionally, check for a `predictedTier` and use it to scale a conservative percentage of a *typical* first-session weight range for that exercise's `utility`/`mechanics` category (still user-adjustable, never presented as gospel) — closer to what a real trainer would do with a new client than either a fixed catalog number or "figure it out yourself."

**Evaluation**: standard train/test split, report accuracy/F1 per class. Report this to the user as a confidence-qualified suggestion ("intermediate, and you can change this any time"), never as a locked-in label.

## 4. Exercise similarity — smarter `SWAPPED` substitutions

**Problem**: `adaptation`'s `SWAPPED` strategy currently just filters `candidate_pool()` to the same `primaryMuscle` and picks by the existing selection score. Once §1 grows the catalog from 18 to hundreds of exercises, "same primary muscle" is too coarse — dozens of candidates tie, and the substitute might use completely different equipment or movement pattern than what the user was actually doing.

**Model**: no dataset needed beyond the enriched catalog from §1. Build a feature vector per exercise (one-hot `primaryMuscle` + `secondaryMuscles`, `equipment`, `mechanics`, `utility`) and index it with `scikit-learn`'s `NearestNeighbors` (cosine metric). This is a classic content-based-similarity setup — no deep learning needed; the feature space is small and categorical.

**Integration**:
- `ml/training/build_exercise_similarity_index.py` — offline job, rebuilt whenever the catalog changes, serialized to `ml/app/models/checkpoints/exercise_similarity.joblib` (the repo's `.gitignore` already reserves `app/models/checkpoints/*` for exactly this, with a tracked `.gitkeep` — that structure was anticipated, just never used).
- `ml/app/services/ml/similarity.py::nearest_exercises(exercise_id, k=5, exclude=[])` loads the index at startup and is called from `services/recommender.py`'s `SWAPPED` branch instead of the current same-muscle filter.

**Evaluation**: no ground truth for "is this a good substitute" exists yet — ship it, then use `swap` feedback (already logged, per [docs/SPEC.md](SPEC.md) §4.7) as an implicit signal: if a specific substitution gets swapped again immediately, that's a negative signal worth reviewing manually before trusting the index blindly.

## 5. Learned re-ranker (the original ask — gated on real usage data)

This is what "use scikit-learn to improve recommendations" concretely becomes, and it's explicitly **gated**, not immediate: `selection/scorer.py`'s weights (`0.30 align + 0.25 recency + 0.20 frequency + 0.25 balance`) are fixed because there's no labeled data yet to fit them. The `recommendations` + `rec_feedback` + `completionRate`/`progressionRate` infrastructure already built (per [docs/SPEC.md](SPEC.md) §4.7, §4.3) exists specifically to accumulate that data.

**Trigger condition** (don't attempt this early — a model trained on 40 feedback events will be worse than the fixed weights): a minimum volume threshold, e.g. **≥ 2,000 recommendation-feedback pairs across ≥ 50 distinct users**, checked by a small script before any training run is attempted. Until that threshold is hit, this phase doesn't start.

**Model**: `scikit-learn`'s `LogisticRegression` or `GradientBoostingClassifier` predicting P(accept | candidate features, user features, context) from logged `(candidate, chosen_goal, action)` tuples, replacing the fixed linear weights in `score_rules()` with a fitted model. Classical ML remains the right choice here too — this is small-scale tabular ranking, not the regime where deep learning (e.g. two-tower embedding models) starts paying for itself.

**Integration**: `ml/training/train_reranker.py` reads from `recommendations`/`rec_feedback`, trains, evaluates against the current fixed-weight formula on held-out data (ship only if it wins), and exports to `ml/app/models/checkpoints/reranker.joblib`. `selection/scorer.py` gets a second implementation (`score_rules_learned()`) behind a flag, so the fixed-weight version stays available as an instant rollback.

## 6. What's explicitly out of scope, and why

- **[FitRec](https://cseweb.ucsd.edu/~jmcauley/datasets/fitrec.html)** (UCSD/McAuley Lab, 250k+ Endomondo workout records with heart rate/GPS/speed, LSTM-based in the original paper) is real, large, and exactly the kind of dataset that would tempt a "let's do deep learning" detour. Its own documentation states it's **released for academic use only and not for commercial redistribution** — GymGenius may become a commercial product, so this is flagged out of scope for anything shipped, and usable only for private prototyping/research with that constraint understood. Don't build a production feature on it without separate legal review.
- **Deep learning generally**: every model above is classical (scikit-learn: random forest, gradient boosting, logistic regression, nearest-neighbors, TF-IDF). At the data volumes available here — thousands of exercises, low-thousands of feedback events even at real usage — deep learning would need far more data to beat these, and adds real operational cost (GPU/inference infra, retraining pipelines, a much harder debugging story) this product doesn't need. Revisit only if a specific capability genuinely requires sequence modeling (e.g., a future FitRec-style route/pace recommender for a running-focused pivot) — not for anything in this spec.
- **Online/continuous learning**: all training here is offline, batch, and manually triggered. Nothing retrains itself automatically. That's a deliberate simplicity choice, not a limitation to fix later by default.

## 7. Infrastructure this adds

```
ml/
  training/                          # offline only - never imported by the FastAPI app
    datasets/                        # raw downloads, gitignored (**/data/** already covers it)
    ingest_exercise_catalog.py       # §1
    normalize.py                     # wraps artifacts/equipment_map.json, muscle_groups.json
    train_calorie_model.py           # §2
    train_fitness_classifier.py      # §3
    build_exercise_similarity_index.py  # §4
    train_reranker.py                # §5 - refuses to run below the volume threshold
    evaluate.py                      # shared train/test split + metric reporting helpers
  app/
    models/
      checkpoints/                   # .gitignore already reserves this; only .gitkeep is tracked
    services/
      ml/
        calorie_model.py
        fitness_classifier.py
        similarity.py
        reranker.py
```

- `requirements.txt` gains back `pandas` and `scikit-learn` (both were in the original scaffold's requirements and were dropped when nothing used them yet — now something does) plus `joblib` for model serialization.
- `ARTIFACTS_VERSION` (from `ml/artifacts/version.txt`, currently `artifacts-0.1.0`) is stamped into every trained model's metadata alongside a `MODEL_VERSION`, so a served prediction can always be traced back to which config bundle and which training run produced it.
- Every `train_*.py` script writes a small JSON eval report next to its model artifact (metric, dataset version, row count, timestamp) — no model ships without one.

## 8. Licensing checklist (do this before ingesting anything)

Kaggle dataset licenses vary per dataset and this changes over time — check the license tab on each dataset's page before use, specifically for: commercial-use permission (several are CC0 or fine; some restrict redistribution), and whether the dataset itself was scraped from a source with its own terms (exercise GIF datasets in particular sometimes trace back to a paid API's data). FitRec's non-commercial restriction (§6) is the one confirmed constraint as of this writing — treat every other dataset's license as unverified until you've actually opened its page.

## 9. Phased roadmap

Continues [docs/SPEC.md](SPEC.md)'s numbering — Phases 0-7 are implemented, Phase 8 (hardening) is still open and independent of this work.

| Phase | Work | Depends on |
|---|---|---|
| 9 | Exercise catalog ingestion + normalization + dedup (§1); `cautionExercises`; fixed focus-tag matching | [docs/SPEC.md](SPEC.md) Phase 2 |
| 10 | Calorie/intensity model + MET fallback + `/estimate-calories` (§2) | Phase 9 |
| 11 | Fitness-level classifier + onboarding quiz + cold-start tier fallback in `apply_progression` (§3) | Phase 9 |
| 12 | Exercise similarity index, wired into `SWAPPED` (§4) | Phase 9 |
| 13 | Learned re-ranker — blocked on the volume threshold in §5, not on calendar time | [docs/SPEC.md](SPEC.md) Phase 6-7 generating real feedback volume |

Phases 9-12 don't depend on each other and can run in any order or in parallel; Phase 13 is the only one gated on something other than engineering time.
