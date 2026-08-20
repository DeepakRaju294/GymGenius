# GymGenius ML Expansion — Data-Driven Fitness Intelligence

Extends [docs/SPEC.md](SPEC.md) (the recommendation/optimization engine already implemented) with capabilities bootstrapped from public datasets, so the platform doesn't have to wait for its own user base to accumulate before any of this is useful. Scope is broader than "pick the next exercise" — it covers everything a real ML-driven fitness product would plausibly ship — but every capability here plugs into the existing `ml/` FastAPI service, the existing MongoDB collections, and the existing Selection/Prescription/Adaptation pipeline. Nothing here is a side project bolted onto GymGenius; it's the same product with real data behind it.

**The shape of this whole spec, stated once instead of five separate times**: public data solves cold start; first-party behavioral data eventually solves personalization. Public datasets give GymGenius a real exercise universe, exercise structure, similarity, and reasonable priors for a user with no history. From there, the platform progressively replaces generalized assumptions with *this user's* performance, swaps, and progression — and the learned re-ranker in §5 is what eventually trains on first-party GymGenius behavior instead of Kaggle data. Read every section below as one step in `rules → public-data priors → personal history → population learning → personalized ranking`, not as five unrelated ML features.

## 0. What's already sitting in the repo, unused

`ml/artifacts/` exists locally (gitignored — it was never committed) and already anticipates exactly this work:

| File | What it is | What it means for this spec |
|---|---|---|
| `default_weights.json` | Per-exercise starting weights (`"Barbell Bench Press": 45`) | Superseded by design — [docs/SPEC.md](SPEC.md) §3 deliberately dropped a fixed default weight per exercise. §3 below replaces this with a *predicted per-movement-family starting range*, not a fixed number. |
| `equipment_map.json`, `muscle_groups.json` | Synonym maps (`"db"` → `"dumbbell"`, `"quadriceps"` → `"quads"`) | Exactly what's needed to normalize inconsistent labels across public exercise datasets into one canonical taxonomy. Used directly in §1's ingestion pipeline. |
| `stoplist.json` | `["Upright Row (barbell wide grip)"]` | Not a stopword list despite the name — an exercise **caution** signal. Formalized into a tagged, non-blanket caution system in §1 (not a hard exclude-by-default list — see the redesign there). |
| `workout_focus_tags.json` | `"push"` → `["chest","shoulders","triceps"]`, etc. | A better focus-matching design than what's currently implemented — `_exercise_matches_focus()` only matches an exercise's own `tags` literally against the requested focus string. §1 fixes this. |
| `progression.yaml` | `weights: {align: 0.35, recency: 0.25, frequency: 0.25, success: 0.15}` | The scoring weights currently hardcoded in `selection/scorer.py`. §5's learned re-ranker is what eventually replaces fixed weights like these with weights fit to real feedback data. |
| `version.txt` | `artifacts-0.1.0` | An existing versioning convention for this config bundle — reused as `ARTIFACTS_VERSION` in §7 rather than inventing a new one. |

None of this was wasted; it was the intended shape of exactly this work, just never wired up.

## 1. Real exercise catalog (replaces the 18 hand-seeded exercises) — the foundation everything else depends on

**Problem**: `server/scripts/seedExercises.js` seeds 18 exercises by hand. Every downstream feature — Selection, substitution on `SWAPPED`, muscle-volume charts, the cold-start estimator in §3 — is only as good as this catalog.

**Datasets** (verified currently listed on Kaggle as of this writing — check each one's license tab before ingesting, see §8):
- [Exercises Dataset](https://www.kaggle.com/datasets/akankshamishra0512/exercises-dataset) — 1,000+ exercises with muscles, equipment, instructions.
- [Gym Exercises Dataset](https://www.kaggle.com/datasets/rishitmurarka/gym-exercises-dataset) — adds `utility` (basic/auxiliary) and `mechanics` (compound/isolated) per exercise.
- [Fitness Exercises Dataset](https://www.kaggle.com/datasets/exercisedb/fitness-exercises-dataset) — 1,500+ exercises with instructional GIFs (a Kaggle mirror of the free ExerciseDB dataset).
- [Gym Exercise Data](https://www.kaggle.com/datasets/niharika41298/gym-exercise-data) — 2,500+ exercises, a third independent source to cross-reference against.

**Schema additions** — one field beyond what was previously planned, and it's the most consequential addition in this whole spec:

```js
// server/models/exerciseModel.js additions
mechanics: { type: String, enum: ['compound', 'isolation'] },
utility: { type: String, enum: ['basic', 'auxiliary'] },
movementPattern: {
  type: String,
  enum: [
    'horizontal_push', 'vertical_push', 'horizontal_pull', 'vertical_pull',
    'squat', 'hinge', 'lunge', 'knee_flexion',
    'elbow_flexion', 'elbow_extension', 'shoulder_abduction',
    'core_flexion', 'core_anti_extension'
  ]
},
gifUrl: { type: String },
source: { type: String },       // which dataset(s) contributed this entry, for provenance
```

`movementPattern` matters because muscle group + equipment + mechanics can match while the movement itself is unrelated (dumbbell bench press and dumbbell fly are both "chest, dumbbell, compound-ish" but are not good substitutes for each other). §2's substitution ranking is built around this field, not around cosine similarity over the coarser attributes alone.

**Pipeline** (`ml/training/ingest_exercise_catalog.py`):
1. Download each CSV into `ml/training/datasets/` (gitignored via the repo's existing `**/data/**` pattern), recording provenance in a manifest (see §8).
2. Normalize equipment/muscle-group text through `ml/artifacts/equipment_map.json` / `muscle_groups.json`.
3. **Two-stage dedup across the three sources**, not a single similarity score with an automatic merge threshold — a name-similarity match alone will both false-merge ("Incline Bench Press" vs "Decline Bench Press" read as near-identical strings) and miss real duplicates ("DB Bulgarian Split Squat" vs "Rear-Foot Elevated Dumbbell Split Squat"):
   - **Candidate generation**: `scikit-learn`'s `TfidfVectorizer` + cosine similarity over normalized exercise names, to produce a shortlist of plausible duplicates cheaply.
   - **Merge validation**: a candidate pair is only auto-merged if it also agrees on `primaryMuscle`, has compatible `equipment`, and (once assigned) the same `movementPattern`. Anything that passes name-similarity but fails structural agreement is written to a review file instead of merged automatically:
     ```text
     0.96  Dumbbell Bench Press <-> DB Bench Press           AUTO-MERGE
     0.84  Incline DB Press <-> Dumbbell Bench Press         REVIEW
     0.63  Cable Fly <-> Pec Deck                            KEEP SEPARATE
     ```
   - `movementPattern` itself has to be assigned per source row before validation can use it — do this as a rule-based lookup keyed on exercise name/equipment/mechanics first (most rows are unambiguous — "barbell back squat" is obviously `squat`), and only hand-review the ambiguous remainder. Not a model; a lookup table, same spirit as `equipment_map.json`.
4. **Caution metadata** — not a blanket exclude-by-default blacklist. A single universal "these exercises are dangerous" list doesn't hold up (an upright row is a real risk for someone with a shoulder-impingement history and a non-issue for most people). Store tags instead of a binary flag:
   ```js
   // new fields on the exercises schema
   cautionTags: { type: [String], default: [] },        // e.g. "high_shoulder_external_rotation", "high_spinal_loading"
   cautionReason: { type: String },
   evidenceLevel: { type: String, enum: ['common_guidance', 'anecdotal'] }
   ```
   `candidate_pool()` doesn't exclude anything by default from this; a future (out-of-scope-here) profile field for self-reported limitations would down-rank or exclude exercises whose `cautionTags` match, so a caution tag becomes personalized filtering instead of a claim that an exercise is inherently dangerous for everyone.
5. **Focus matching fix**: `_exercise_matches_focus()` in `selection/candidate_pool.py` currently checks the exercise's own `tags` array against the requested focus string directly, so `focus="push"` doesn't match an exercise tagged only `"chest"`. Replace with a lookup through `workout_focus_tags.json` (`"push"` → `{chest, shoulders, triceps}`) matched against `primaryMuscle`.

**Output**: `npm run seed` (or a new `ml/training/seed_from_catalog.py` writing directly to Mongo) populates hundreds-to-thousands of real, structurally-validated exercises instead of 18.

## 2. Exercise similarity — smarter `SWAPPED` substitutions

**Problem**: `adaptation`'s `SWAPPED` strategy currently just filters `candidate_pool()` to the same `primaryMuscle`. Once §1 grows the catalog, "same primary muscle" is far too coarse.

**Design — a pipeline, not a raw nearest-neighbors query over the whole catalog**, so similarity retrieval can't silently bypass the constraints the rest of Selection already enforces:

```text
1. Hard filter   - equipment the user actually has, this user's caution-tag exclusions,
                    the requested muscle/movement family, any manual exclusions
2. Similarity    - rank the survivors by movementPattern match first, then muscle/equipment/
                    mechanics/utility similarity (scikit-learn NearestNeighbors, cosine metric)
3. Rank          - re-use the existing score_rules() signals (recency, frequency, balance)
                    to break ties among similarly-ranked substitutes
4. Return top N
```

**Integration**:
- `ml/training/build_exercise_similarity_index.py` — offline job, rebuilt whenever the catalog changes, serialized to `ml/app/models/checkpoints/exercise_similarity.joblib` (the repo's `.gitignore` already reserves `app/models/checkpoints/*` for exactly this).
- `ml/app/services/ml/similarity.py::nearest_exercises(exercise_id, k=5, exclude=[])` — step 2 only; steps 1 and 3 stay in `candidate_pool()`/`scorer.py` so the similarity model is a ranking signal inside the existing pipeline, not a replacement for it.

**Evaluation**: no ground truth for "is this a good substitute" exists yet — ship it, then use `swap` feedback (already logged, [docs/SPEC.md](SPEC.md) §4.7) as an implicit signal: a substitution that gets swapped again immediately is worth reviewing manually before trusting the index further.

## 3. Cold-start strength estimator (not a generic "fitness level")

[docs/SPEC.md](SPEC.md) §3 deliberately removed a fixed default starting weight per exercise. That was right, but it left a real gap for a brand-new user with zero history — `apply_progression` just returns `None`.

**Why this isn't a "fitness-level classifier"**: general fitness and exercise-specific strength aren't the same variable. Someone can be aerobically fit and a complete novice at barbell bench press; a strong lifter can have mediocre sit-up numbers. The [Body performance Data](https://www.kaggle.com/datasets/kukuroo3/body-performance-data) dataset's A–D label (built from grip strength, sit-ups, broad jump, sit-and-reach) doesn't cleanly map to "what weight should this person start bench press at" — training a classifier on it and using the output to scale barbell loads would be answering a related-sounding but different question, with false precision attached.

**What to predict instead**: per-movement-family strength, not a single overall tier — `upper_push`, `upper_pull`, `squat`, `hinge` (matching §1's `movementPattern` groupings). Two ways to get there, and the second is more direct than the dataset-trained model:
- **Direct**: ask 3-4 short onboarding questions with real signal — push-ups in a minute, whether they've bench pressed before and roughly what weight, an approximate goblet-squat or bodyweight-squat comfort level. This alone gets most of the value with no model at all.
- **Model-assisted**: [Gym Members Exercise Dataset](https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset)'s `Experience_Level` field, combined with the direct-question answers, trains a `scikit-learn` `HistGradientBoostingClassifier` to fill in movement families the user didn't directly answer for, from the ones they did.

**Where the starting range actually comes from** (this needs to be explicit, or whoever implements it invents an unstated policy): not a single number, and not hidden inside the model — a small, explicitly-authored table of safe exploration ranges per `movementPattern` + `equipment` combination, scaled by the predicted strength tier for that movement family:
```text
horizontal_push + dumbbell, beginner tier:   5-15 lb per hand
horizontal_push + barbell,  beginner tier:   scaled from bodyweight + anchor-question answers
*, machine:                                  not predicted - stack calibration varies too much
                                              per machine/gym; first session is user-entered
```
This table lives in `ml/artifacts/` alongside the other config, versioned the same way (§7) — it is a deliberately conservative starting *suggestion*, always user-adjustable, never presented as authoritative.

**Integration**:
- New collection `fitness_assessments`: `{ username, inputs: {...}, predictedByFamily: {upper_push: "beginner", ...}, confidence, modelVersion, createdAt }`.
- New optional onboarding step in `Login.js`'s profile-completion flow (skippable).
- `prescription/progression.py::apply_progression()` gains a fallback: when `last_top_weight()` is `None`, look up the exercise's `movementPattern`/`equipment` in the starting-range table, scaled by the relevant predicted tier, instead of returning `None` unconditionally.

**Evaluation**: split by user (`GroupShuffleSplit`, not a random row split — Kaggle rows aren't independent of the person they came from, and the same concern applies to any first-party data used here later), report per-family accuracy/F1. Always surfaced to the user as a confidence-qualified, editable suggestion.

## 4. Calorie / intensity estimation

Lower priority than §1-3 — it's a genuinely new standalone feature, but unlike the catalog, substitution, and cold-start work, it doesn't improve the core `recommend → perform → evaluate → adapt` loop. Sequenced last for that reason (see roadmap, §9).

**Dataset**: [Gym Members Exercise Dataset](https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset) — 973 rows of age, gender, weight, height, max/avg/resting BPM, session duration, workout type, calories burned.

**Model**: `scikit-learn`'s `GradientBoostingRegressor` (baseline: `Ridge`) predicting `calories_burned` from `duration, avg_bpm, weight, workout_type`. At ~1k rows, classical gradient boosting is the right ceiling.

**The catch**: almost no GymGenius user will have heart-rate data. Ship two paths:
- **Model path** (`ml/app/services/ml/calorie_model.py::estimate(...)`) when heart rate is available.
- **MET fallback** (`estimate_met(duration, weight, exercise_ids)`) — a static per-exercise MET-value table, not learned — what actually runs for most users.

**Integration**: optional `avgHeartRate: Number` on `historyModel`'s set schema; new `POST /estimate-calories` proxied through the server; an "Estimated calories" line in `History.js` and the Progress page.

**Evaluation**: hold out 20% of the Kaggle rows, report MAE against the model and against the MET fallback — ship the model only if it beats the fallback by a real margin.

## 5. Learned re-ranker (the original ask — gated on real usage data)

`selection/scorer.py`'s weights (`0.30 align + 0.25 recency + 0.20 frequency + 0.25 balance`) are fixed because there's no labeled data yet to fit them. The `recommendations` + `rec_feedback` + `completionRate`/`progressionRate` infrastructure ([docs/SPEC.md](SPEC.md) §4.7, §4.3) exists specifically to accumulate that data.

**Don't optimize for acceptance alone.** `P(accept | candidate)` is the obvious target and a bad one — a model trained on it can learn "this user always accepts bench press" and over-recommend it even when program balance suffers, since acceptance says nothing about whether the recommendation was actually good for the user's training. The target should be a composite outcome, using signals already logged elsewhere in the spec:
```text
utility = acceptance
        + completionRate weight        (did they do what was prescribed - §4.3)
        + progressionRate weight       (did they improve - §4.3)
        - immediate_swap penalty
        - repeated_same_muscle penalty (from the balance term already in score_rules)
```
Longer-term this becomes `P(successful_session | recommendation)` rather than `P(click | recommendation)` — a ranking objective aligned with what GymGenius is actually for, not with engagement.

**Trigger condition**: a volume threshold is an engineering safeguard, not evidence the data is statistically adequate — the spec's original framing ("≥2,000 pairs across ≥50 users") could still pass with 90% of samples from ten highly active users, or with 95% identical labels. Gate on all of the following, not just row count:
- ≥ 2,000 recommendation-feedback pairs
- ≥ 50 distinct users, no single user contributing more than ~10% of pairs
- both accepted and swapped/rejected outcomes represented (not near-all-one-label)
- a meaningful spread of distinct candidate exercises represented, not dominated by a handful

**Model**: `scikit-learn`'s `LogisticRegression` or `GradientBoostingClassifier` on the composite target above. **Evaluate split by user**, not by row — the goal is generalizing to a new user's preferences, and a random row split leaks the same user's other feedback into both train and test.

**Integration**: `ml/training/train_reranker.py` reads from `recommendations`/`rec_feedback`, refuses to run below the gate, evaluates against the current fixed-weight formula on held-out (by-user) data, ships only if it wins, exports to `ml/app/models/checkpoints/reranker.joblib`. `selection/scorer.py` gets a second implementation behind a flag, so the fixed-weight version stays an instant rollback.

## 6. What's explicitly out of scope, and why

- **[FitRec](https://cseweb.ucsd.edu/~jmcauley/datasets/fitrec.html)** (UCSD/McAuley Lab, 250k+ Endomondo workout records, LSTM-based in the original paper) is real and large, but its documentation states it's **released for academic use only and not for commercial redistribution**. Flagged out of scope for anything shipped; usable only for private prototyping with that constraint understood, never for a production feature without separate legal review.
- **Deep learning generally**: every model above is classical. At the data volumes actually available — thousands of exercises, low-thousands of feedback events even at real usage — deep learning needs far more data to beat these and adds real operational cost (GPU/inference infra, harder debugging) this product doesn't need. Revisit only if a specific future capability genuinely requires sequence modeling.
- **Online/continuous learning**: all training here is offline, batch, manually triggered. A deliberate simplicity choice, not a limitation to fix later by default.

## 7. Infrastructure this adds

```
ml/
  training/                          # offline only - never imported by the FastAPI app
    datasets/                        # raw downloads, gitignored (**/data/** already covers it)
    ingest_exercise_catalog.py       # §1
    normalize.py                     # wraps artifacts/equipment_map.json, muscle_groups.json
    build_exercise_similarity_index.py  # §2
    train_cold_start_estimator.py    # §3
    train_calorie_model.py           # §4
    train_reranker.py                # §5 - refuses to run below the volume/diversity gate
    evaluate.py                      # shared GroupShuffleSplit-by-user + metric reporting
  app/
    models/
      checkpoints/                   # .gitignore already reserves this; only .gitkeep is tracked
    services/
      ml/
        model_registry.py            # single load point for every artifact below
        calorie_model.py
        cold_start.py
        similarity.py
        reranker.py
```

**`model_registry.py`** — one abstraction (`get_model("calorie")`, `get_model("cold_start")`, etc.) instead of four services independently reading `.joblib` files, handling:
- artifact path + `MODEL_VERSION`/`ARTIFACTS_VERSION` resolution,
- version-compatibility checks,
- **startup fallback behavior, defined explicitly rather than left as an accident of whatever exception happens to propagate**:
  ```text
  artifact file missing            -> fall back to the deterministic/rule-based implementation, log once
  artifact/config version mismatch -> refuse to load it, fall back, log a warning
  deserialization fails            -> fall back; the recommendation service must never become
                                       unavailable because a .joblib didn't deploy correctly
  ```

**Dependency split**: `requirements.txt` (runtime — inference-only: `scikit-learn`, `joblib`, plus what's already there) stays separate from a new `requirements-training.txt` (`pandas`, plus anything else only `ml/training/` needs) — training tooling has no reason to ship into the serving container.

## 8. Licensing checklist (do this before ingesting anything)

Kaggle dataset licenses vary per dataset and change over time — check the license tab on each dataset's page before use. FitRec's non-commercial restriction (§6) is the one confirmed constraint as of this writing; treat every other dataset's license as unverified until you've opened its page.

Track this with a manifest rather than loose CSVs, so every trained model can cite exactly what it was trained on:
```yaml
# ml/training/datasets/manifest.yaml
gym_members_exercise:
  source_url: https://www.kaggle.com/datasets/valakhorasani/gym-members-exercise-dataset
  downloaded_at: 2026-08-19
  license: <fill in from the dataset page>
  license_verified_at: 2026-08-19
  sha256: <hash of the downloaded file>
  rows: 973
  usable_commercially: <fill in>
```
Every `train_*.py` script's eval report (§7) records which manifest entry (and hash) it trained against.

## 9. Phased roadmap

Continues [docs/SPEC.md](SPEC.md)'s numbering — Phases 0-7 are implemented, Phase 8 (hardening) is still open and independent of this work. Ordered so the phases that improve the core recommend → perform → evaluate → adapt loop come before the more peripheral one:

| Phase | Work | Depends on |
|---|---|---|
| 9 | Catalog foundation (§1): ingestion, two-stage dedup + review report, `movementPattern` taxonomy, caution tags, provenance, focus-tag matching fix | [docs/SPEC.md](SPEC.md) Phase 2 |
| 10 | Better substitutions (§2): hard-filter + similarity + rank pipeline, wired into `SWAPPED` | Phase 9 |
| 11 | Cold-start prescription (§3): onboarding questions, per-movement-family strength estimate, starting-range table, `apply_progression` fallback | Phase 9 |
| 12 | Calorie estimation (§4): MET baseline first, model only if it validates as better | Independent — can run any time after Phase 9 |
| 13 | Learned re-ranker (§5): blocked on the volume/diversity gate, not on calendar time; composite utility target, by-user evaluation split | [docs/SPEC.md](SPEC.md) Phases 6-7 generating real feedback volume |

Phases 9-12 don't depend on each other beyond the catalog and can run in any order or in parallel once Phase 9 lands; Phase 13 is the only one gated on something other than engineering time.
