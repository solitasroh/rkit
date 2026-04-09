/**
 * Instinct Pattern Collector
 * @module lib/instinct/collector
 * @version 0.1.0
 *
 * Extracts patterns from L1/L2 review results and user corrections,
 * then persists them via store.js with confidence tracking.
 */

const crypto = require('crypto');
const store = require('./store');
const confidence = require('./confidence');

/**
 * Pattern categories (aligned with patterns.json schema).
 */
const CATEGORIES = ['naming', 'structure', 'idiom', 'security', 'convention', 'architecture'];

/**
 * Map L1/L2 rule categories to instinct pattern categories.
 */
const RULE_CATEGORY_MAP = {
  // L1 (design-rules.js)
  structure: 'structure',
  complexity: 'structure',
  cohesion: 'architecture',
  architecture: 'architecture',
  solid: 'structure',
  dry: 'convention',
  naming: 'naming',
  'anti-pattern': 'structure',
  // L2 general
  RAII: 'idiom',
  'const': 'idiom',
  'smart-pointer': 'idiom',
  'async-await': 'idiom',
  nullable: 'idiom',
  IDisposable: 'idiom',
  'type-hints': 'idiom',
  'context-manager': 'idiom',
  dataclass: 'idiom',
  // Security (L1/L2)
  Security: 'security',
  security: 'security',
  Concurrency: 'security',
  'Anti-Pattern': 'convention',
};

/**
 * Detect language from file extension.
 * @param {string} filePath
 * @returns {string}
 */
function detectLanguageFromFile(filePath) {
  const ext = (filePath || '').split('.').pop().toLowerCase();
  const map = { c: 'c', cpp: 'cpp', cc: 'cpp', cxx: 'cpp', h: 'c', hpp: 'cpp', cs: 'csharp', py: 'python', js: 'javascript', ts: 'typescript' };
  return map[ext] || 'unknown';
}

/**
 * Find a similar existing pattern by category + language + description.
 * @param {Object[]} existing - Existing patterns array
 * @param {Object} newPattern - Pattern to match
 * @returns {Object|null}
 */
function findSimilarPattern(existing, newPattern) {
  return existing.find(p =>
    p.category === newPattern.category &&
    p.pattern.language === newPattern.pattern.language &&
    p.pattern.description === newPattern.pattern.description
  ) || null;
}

/**
 * Extract patterns from a ReviewResult (from review-orchestrator).
 * @param {Object} reviewResult - { findings: [{ rule, file, severity, layer, title, fix }] }
 * @param {string} sessionId
 * @returns {Object[]} Array of pattern objects (patterns.json schema)
 */
function extractPatterns(reviewResult, sessionId) {
  if (!reviewResult || !reviewResult.findings) return [];

  const patterns = [];
  const seen = new Set();

  for (const finding of reviewResult.findings) {
    // Deduplicate within same extraction (same rule + language)
    const lang = detectLanguageFromFile(finding.file);
    const dedupeKey = `${finding.rule}:${lang}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);

    const category = RULE_CATEGORY_MAP[finding.rule] || RULE_CATEGORY_MAP[finding.category] || 'convention';

    patterns.push({
      id: crypto.randomUUID(),
      category,
      pattern: {
        description: finding.title,
        example: `${finding.file}:${finding.line}`,
        language: lang,
      },
      correction: {
        description: finding.fix || '',
        example: '',
      },
      confidence: confidence.INITIAL_CONFIDENCE,
      scope: 'project',
      origin: {
        projectId: '',
        sessionId,
        timestamp: new Date().toISOString(),
        source: 'review',
      },
      sessions: [{ sessionId, timestamp: new Date().toISOString(), action: 'detected' }],
      tags: [lang, finding.layer || 'L1'].filter(Boolean),
    });
  }

  return patterns;
}

/**
 * Extract a pattern from a user correction event.
 * @param {{ before: string, after: string, filePath: string }} correctionEvent
 * @param {string} sessionId
 * @returns {Object|null}
 */
function extractCorrectionPattern(correctionEvent, sessionId) {
  if (!correctionEvent || !correctionEvent.before || !correctionEvent.after) return null;

  const lang = detectLanguageFromFile(correctionEvent.filePath);
  return {
    id: crypto.randomUUID(),
    category: 'convention',
    pattern: {
      description: `User corrected code pattern`,
      example: correctionEvent.before.slice(0, 200),
      language: lang,
    },
    correction: {
      description: 'User-provided correction',
      example: correctionEvent.after.slice(0, 200),
    },
    confidence: confidence.INITIAL_CONFIDENCE,
    scope: 'project',
    origin: {
      projectId: '',
      sessionId,
      timestamp: new Date().toISOString(),
      source: 'correction',
    },
    sessions: [{ sessionId, timestamp: new Date().toISOString(), action: 'detected' }],
    tags: [lang, 'user-correction'].filter(Boolean),
  };
}

/**
 * Save extracted patterns to store, merging with existing and updating confidence.
 * @param {Object[]} newPatterns
 * @param {string} sessionId
 */
function saveExtractedPatterns(newPatterns, sessionId) {
  if (!newPatterns || newPatterns.length === 0) return;

  const projectHash = store.getProjectHash();
  const patternsData = store.loadPatterns(projectHash);
  const confidenceData = store.loadConfidence(projectHash);

  for (const np of newPatterns) {
    np.origin.projectId = projectHash;

    const existing = findSimilarPattern(patternsData.patterns, np);
    if (existing) {
      // Update existing pattern: add session entry, update confidence
      existing.sessions.push({ sessionId, timestamp: new Date().toISOString(), action: 'detected' });

      const score = confidenceData.scores[existing.id];
      if (score) {
        const result = confidence.updateConfidence(score.current, 'applied');
        score.current = result.score;
        score.history.push({ session: patternsData.metadata.totalSessions + 1, score: result.score, delta: result.delta, reason: 'applied' });
        score.convergedAt = confidence.isConverged(score.history) ? (patternsData.metadata.totalSessions + 1) : score.convergedAt;
        score.promotable = confidence.isPromotable(score.current, 1);
      }
    } else {
      // Add new pattern
      patternsData.patterns.push(np);
      confidenceData.scores[np.id] = {
        current: confidence.INITIAL_CONFIDENCE,
        history: [{ session: patternsData.metadata.totalSessions + 1, score: confidence.INITIAL_CONFIDENCE, delta: 0, reason: 'applied' }],
        convergedAt: null,
        promotable: false,
      };
    }
  }

  patternsData.metadata.totalSessions++;
  store.savePatterns(projectHash, patternsData);
  store.saveConfidence(projectHash, confidenceData);
}

module.exports = {
  CATEGORIES,
  RULE_CATEGORY_MAP,
  detectLanguageFromFile,
  findSimilarPattern,
  extractPatterns,
  extractCorrectionPattern,
  saveExtractedPatterns,
};
