const mongoose = require('mongoose');

// Mirrors ml/artifacts/taxonomies.json's movementPatterns - that file is the
// source of truth (also read directly by ml/training/validate_catalog.py);
// keep this list in sync if it changes there.
const MOVEMENT_PATTERNS = [
    'horizontal_push', 'vertical_push', 'horizontal_pull', 'vertical_pull',
    'squat', 'hinge', 'lunge', 'knee_flexion', 'knee_extension',
    'elbow_flexion', 'elbow_extension', 'shoulder_abduction', 'shoulder_rotation',
    'shoulder_elevation', 'ankle_plantarflexion',
    'core_flexion', 'core_anti_extension', 'core_rotation'
];

const exerciseSchema = new mongoose.Schema({
    exerciseId: {
        type: String,
        required: true,
        unique: true,
        trim: true
    },
    name: {
        type: String,
        required: true,
        trim: true
    },
    primaryMuscle: {
        type: String,
        required: true,
        trim: true
    },
    secondaryMuscles: {
        type: [String],
        default: []
    },
    equipment: {
        type: [String],
        default: []
    },
    tags: {
        type: [String],
        default: []
    },
    // docs/ML_SPEC.md §1 - real-catalog fields
    mechanics: {
        type: String,
        enum: ['compound', 'isolation']
    },
    utility: {
        type: String,
        enum: ['basic', 'auxiliary']
    },
    movementPattern: {
        type: String,
        enum: MOVEMENT_PATTERNS
    },
    movementPatternSource: {
        type: String,
        enum: ['dataset', 'rule', 'manual']
    },
    secondaryMovementPatterns: {
        type: [{ type: String, enum: MOVEMENT_PATTERNS }],
        default: []
    },
    gifUrl: {
        type: String
    },
    source: {
        type: String
    },
    // false for partially-normalized/media-only rows that shouldn't enter
    // recommendation generation yet - see docs/ML_SPEC.md §1/§9 (Phase 9 exit criteria)
    isSelectable: {
        type: Boolean,
        default: true
    },
    // Caution tags, not a blanket exclude-by-default blacklist - candidate_pool()
    // does not filter on these itself; a future per-user limitations field would.
    cautionTags: {
        type: [String],
        default: []
    },
    cautionReason: {
        type: String
    },
    evidenceLevel: {
        type: String,
        enum: ['common_guidance', 'anecdotal']
    }
});

exerciseSchema.index({ isSelectable: 1 });

const Exercise = mongoose.model('Exercise', exerciseSchema);

module.exports = Exercise;
