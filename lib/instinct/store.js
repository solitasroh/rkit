/**
 * Instinct Store — Pattern & Confidence Persistence
 * @module lib/instinct/store
 * @version 0.1.0
 *
 * Manages .rkit/instinct/{project-hash}/ directory:
 *   - patterns.json: learned patterns (schema v1.0.0)
 *   - confidence.json: per-pattern confidence scores
 *
 * Uses atomic writes (tmp → rename) to prevent corruption.
 * Graceful degradation: returns empty structures on read failure.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

// Lazy require to avoid circular dependency
let _platform = null;
function getPlatform() {
  if (!_platform) { _platform = require('../core/platform'); }
  return _platform;
}

const INSTINCT_DIR = 'instinct';
const PATTERNS_FILE = 'patterns.json';
const CONFIDENCE_FILE = 'confidence.json';
const MAX_PATTERNS_SIZE = 500 * 1024; // 500KB

/**
 * Get the base instinct directory path.
 * @returns {string} .rkit/instinct/
 */
function getInstinctBase() {
  return path.join(getPlatform().PROJECT_DIR, '.rkit', INSTINCT_DIR);
}

/**
 * Generate a 12-char hex project hash.
 * Primary: git remote URL. Fallback: directory path.
 * @returns {string}
 */
function getProjectHash() {
  try {
    const remote = execSync('git remote get-url origin', { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
    return crypto.createHash('sha256').update(remote).digest('hex').slice(0, 12);
  } catch {
    const projectDir = getPlatform().PROJECT_DIR;
    return crypto.createHash('sha256').update(projectDir).digest('hex').slice(0, 12);
  }
}

/**
 * Get the project-specific instinct directory.
 * @param {string} [projectHash]
 * @returns {string}
 */
function getProjectDir(projectHash) {
  const hash = projectHash || getProjectHash();
  return path.join(getInstinctBase(), hash);
}

/**
 * Ensure directory exists.
 * @param {string} dirPath
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * Atomic write: write to .tmp then rename.
 * @param {string} filePath
 * @param {Object} data
 */
function atomicWrite(filePath, data) {
  ensureDir(path.dirname(filePath));
  const tmp = filePath + '.tmp';
  try {
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2), 'utf8');
    fs.renameSync(tmp, filePath);
  } catch (err) {
    try { fs.unlinkSync(tmp); } catch { /* ignore cleanup failure */ }
    throw err;
  }
}

/**
 * Safe JSON read with backup on parse failure.
 * @param {string} filePath
 * @param {Object} fallback - Return value on failure
 * @returns {Object}
 */
function safeRead(filePath, fallback) {
  if (!fs.existsSync(filePath)) return fallback;
  try {
    const raw = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(raw);
  } catch {
    // Backup corrupted file
    try {
      const bak = filePath + '.bak';
      fs.copyFileSync(filePath, bak);
    } catch { /* ignore backup failure */ }
    return fallback;
  }
}

// ---------------------------------------------------------------------------
// Empty structure factories
// ---------------------------------------------------------------------------

function createEmptyPatterns(projectHash) {
  return {
    version: '1.0.0',
    projectId: projectHash,
    projectMeta: { remoteUrl: '', domain: 'unknown', languages: [] },
    patterns: [],
    metadata: { totalSessions: 0, lastUpdated: new Date().toISOString(), schemaVersion: '1.0.0' },
  };
}

function createEmptyConfidence(projectHash) {
  return {
    version: '1.0.0',
    projectId: projectHash,
    scores: {},
    globalCandidates: [],
  };
}

// ---------------------------------------------------------------------------
// CRUD Operations
// ---------------------------------------------------------------------------

/**
 * Load patterns for a project.
 * @param {string} [projectHash]
 * @returns {Object} patterns.json data
 */
function loadPatterns(projectHash) {
  const hash = projectHash || getProjectHash();
  const filePath = path.join(getProjectDir(hash), PATTERNS_FILE);
  return safeRead(filePath, createEmptyPatterns(hash));
}

/**
 * Save patterns for a project.
 * @param {string} projectHash
 * @param {Object} data
 */
function savePatterns(projectHash, data) {
  const filePath = path.join(getProjectDir(projectHash), PATTERNS_FILE);
  data.metadata = data.metadata || {};
  data.metadata.lastUpdated = new Date().toISOString();
  atomicWrite(filePath, data);
}

/**
 * Load confidence data for a project.
 * @param {string} [projectHash]
 * @returns {Object} confidence.json data
 */
function loadConfidence(projectHash) {
  const hash = projectHash || getProjectHash();
  const filePath = path.join(getProjectDir(hash), CONFIDENCE_FILE);
  return safeRead(filePath, createEmptyConfidence(hash));
}

/**
 * Save confidence data for a project.
 * @param {string} projectHash
 * @param {Object} data
 */
function saveConfidence(projectHash, data) {
  const filePath = path.join(getProjectDir(projectHash), CONFIDENCE_FILE);
  atomicWrite(filePath, data);
}

// ---------------------------------------------------------------------------
// v0.9.14 Extension Points (stubs)
// ---------------------------------------------------------------------------

function loadGlobalPatterns() {
  const filePath = path.join(getInstinctBase(), 'global', PATTERNS_FILE);
  return safeRead(filePath, createEmptyPatterns('global'));
}

function promoteToGlobal(/* patternId, projectHash */) {
  // v0.9.14: implement cross-project promotion
  throw new Error('Global promotion not yet implemented (v0.9.14)');
}

module.exports = {
  getInstinctBase,
  getProjectHash,
  getProjectDir,
  createEmptyPatterns,
  createEmptyConfidence,
  loadPatterns,
  savePatterns,
  loadConfidence,
  saveConfidence,
  loadGlobalPatterns,
  promoteToGlobal,
  MAX_PATTERNS_SIZE,
};
