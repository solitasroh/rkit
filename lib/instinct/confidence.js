/**
 * Instinct Confidence Algorithm
 * @module lib/instinct/confidence
 * @version 0.1.0
 *
 * Calculates per-pattern confidence scores, determines convergence,
 * and identifies global promotion candidates.
 *
 * Algorithm (from ecc-insights-integration Design Section 7.5):
 *   applied:  confidence += APPLY_FACTOR * (1 - confidence)
 *   rejected: confidence -= REJECT_FACTOR * confidence
 *   decay:    confidence -= DECAY_FACTOR * confidence
 *
 * Convergence: CONVERGENCE_SESSIONS consecutive deltas < CONVERGENCE_THRESHOLD
 * Deactivation: confidence < DEACTIVATION_THRESHOLD
 * Promotion (v0.9.14): confidence >= 0.8 AND projectCount >= 3
 */

const INITIAL_CONFIDENCE = 0.3;
const APPLY_FACTOR = 0.2;
const REJECT_FACTOR = 0.3;
const DECAY_FACTOR = 0.05;
const CONVERGENCE_THRESHOLD = 0.05;
const CONVERGENCE_SESSIONS = 3;
const DEACTIVATION_THRESHOLD = 0.1;

/**
 * Update confidence score based on an action.
 * @param {number} current - Current confidence (0-1)
 * @param {'applied'|'rejected'|'decay'} action
 * @returns {{ score: number, delta: number }}
 */
function updateConfidence(current, action) {
  let score;
  switch (action) {
    case 'applied':
      score = current + APPLY_FACTOR * (1 - current);
      break;
    case 'rejected':
      score = current - REJECT_FACTOR * current;
      break;
    case 'decay':
      score = current - DECAY_FACTOR * current;
      break;
    default:
      score = current;
  }
  score = Math.max(0, Math.min(1, score));
  const delta = score - current;
  return { score: Math.round(score * 1000) / 1000, delta: Math.round(delta * 1000) / 1000 };
}

/**
 * Determine if a pattern has converged.
 * Converged = last N sessions all have |delta| < threshold.
 * @param {Array<{ delta: number }>} history - Recent session history entries
 * @returns {boolean}
 */
function isConverged(history) {
  if (!history || history.length < CONVERGENCE_SESSIONS) return false;
  const recent = history.slice(-CONVERGENCE_SESSIONS);
  return recent.every(h => Math.abs(h.delta) < CONVERGENCE_THRESHOLD);
}

/**
 * Check if a pattern should be deactivated (too low confidence).
 * @param {number} confidence
 * @returns {boolean}
 */
function isDeactivated(confidence) {
  return confidence < DEACTIVATION_THRESHOLD;
}

/**
 * Check if a pattern is a candidate for global promotion (v0.9.14).
 * @param {number} confidence
 * @param {number} projectCount - Number of projects where this pattern was observed
 * @returns {boolean}
 */
function isPromotable(confidence, projectCount) {
  return confidence >= 0.8 && projectCount >= 3;
}

module.exports = {
  INITIAL_CONFIDENCE,
  APPLY_FACTOR,
  REJECT_FACTOR,
  DECAY_FACTOR,
  CONVERGENCE_THRESHOLD,
  CONVERGENCE_SESSIONS,
  DEACTIVATION_THRESHOLD,
  updateConfidence,
  isConverged,
  isDeactivated,
  isPromotable,
};
