/**
 * Instinct Session Loader
 * @module lib/instinct/loader
 * @version 0.1.0
 *
 * Called at SessionStart to load converged patterns into session context.
 * Produces compact text for prompt injection (max 20 patterns, ~500 tokens).
 */

const store = require('./store');
const confidence = require('./confidence');

const MAX_CONVERGED_PATTERNS = 20;

/**
 * Load converged patterns and generate compact prompt text.
 * @returns {string} Prompt injection text (empty string if no converged patterns)
 */
function loadConvergedPatterns() {
  try {
    const projectHash = store.getProjectHash();
    const patternsData = store.loadPatterns(projectHash);
    const confidenceData = store.loadConfidence(projectHash);

    if (!patternsData.patterns.length) return '';

    const converged = [];
    for (const pattern of patternsData.patterns) {
      const score = confidenceData.scores[pattern.id];
      if (!score) continue;
      if (score.convergedAt !== null && !confidence.isDeactivated(score.current)) {
        converged.push({ pattern, score: score.current });
      }
    }

    if (converged.length === 0) return '';

    // Sort by confidence descending, take top N
    converged.sort((a, b) => b.score - a.score);
    const top = converged.slice(0, MAX_CONVERGED_PATTERNS);

    const lines = ['## Project Instinct (auto-learned patterns)'];
    for (const { pattern, score } of top) {
      const lang = pattern.pattern.language ? ` [${pattern.pattern.language}]` : '';
      lines.push(`- [${pattern.category}]${lang} ${pattern.pattern.description} (confidence: ${score.toFixed(2)})`);
      if (pattern.correction.description) {
        lines.push(`  Fix: ${pattern.correction.description}`);
      }
    }

    return lines.join('\n');
  } catch {
    // Graceful degradation: instinct failure should never break session start
    return '';
  }
}

/**
 * Get a summary of the instinct profile.
 * @returns {{ totalPatterns: number, converged: number, active: number, deactivated: number, lastUpdated: string }}
 */
function getProfileSummary() {
  try {
    const projectHash = store.getProjectHash();
    const patternsData = store.loadPatterns(projectHash);
    const confidenceData = store.loadConfidence(projectHash);

    let converged = 0;
    let active = 0;
    let deactivated = 0;

    for (const pattern of patternsData.patterns) {
      const score = confidenceData.scores[pattern.id];
      if (!score) { active++; continue; }
      if (confidence.isDeactivated(score.current)) {
        deactivated++;
      } else if (score.convergedAt !== null) {
        converged++;
      } else {
        active++;
      }
    }

    return {
      totalPatterns: patternsData.patterns.length,
      converged,
      active,
      deactivated,
      lastUpdated: patternsData.metadata.lastUpdated || 'never',
    };
  } catch {
    return { totalPatterns: 0, converged: 0, active: 0, deactivated: 0, lastUpdated: 'error' };
  }
}

module.exports = {
  MAX_CONVERGED_PATTERNS,
  loadConvergedPatterns,
  getProfileSummary,
};
