/**
 * Audit Logger - JSONL-based audit logging system
 * @module lib/audit/audit-logger
 * @version 2.0.0
 *
 * Records all significant actions in rkit for transparency and traceability.
 * Storage: .rkit/audit/YYYY-MM-DD.jsonl (one JSON object per line)
 *
 * Design Reference: docs/02-design/features/rkit-v200-controllable-ai.design.md
 */

const fs = require('fs');
const path = require('path');
const { generateUUID } = require('../core/constants');

// Lazy require to avoid circular dependency
let _platform = null;
function getPlatform() {
  if (!_platform) { _platform = require('../core/platform'); }
  return _platform;
}

// ============================================================
// Constants
// ============================================================

const MCUKIT_VERSION = '2.0.0';
const DEFAULT_RETENTION_DAYS = 30;

/** @enum {string} Valid action types */
const ACTION_TYPES = [
  'phase_transition',
  'feature_created',
  'feature_archived',
  'file_created',
  'file_modified',
  'file_deleted',
  'config_changed',
  'automation_level_changed',
  'checkpoint_created',
  'rollback_executed',
  'agent_spawned',
  'agent_completed',
  'agent_failed',
  'gate_passed',
  'gate_failed',
  'destructive_blocked',
];

// v2.1.8 (B2 fix sync): convenience loggers below (logPermission/logCheckpoint/
// logTrust/logSystem) emit 'permission'/'checkpoint'/'trust'/'system'
// categories — they must be enumerated here to prevent silent fallback to
// 'control' inside normalizeEntry().
/** @enum {string} Valid categories */
const CATEGORIES = ['pdca', 'file', 'config', 'control', 'team', 'quality', 'permission', 'checkpoint', 'trust', 'system'];

/** @enum {string} Valid result values */
const RESULTS = ['success', 'failure', 'blocked', 'skipped'];

/** @enum {string} Valid actor types */
const ACTORS = ['user', 'agent', 'system', 'hook'];

/** @enum {string} Valid target types */
const TARGET_TYPES = ['feature', 'file', 'config', 'agent', 'checkpoint'];

/** @enum {string} Valid blast radius levels */
const BLAST_RADII = ['low', 'medium', 'high', 'critical'];

// ============================================================
// Helpers
// ============================================================

/**
 * Get the audit directory path
 * @returns {string} Absolute path to .rkit/audit/
 */
function getAuditDir() {
  return path.join(getPlatform().PROJECT_DIR, '.rkit', 'audit');
}

/**
 * Get JSONL file path for a given date
 * @param {string|Date} [date] - Date to use (defaults to today)
 * @returns {string} Absolute path to YYYY-MM-DD.jsonl
 */
function getAuditFilePath(date) {
  const d = date instanceof Date ? date : (date ? new Date(date) : new Date());
  const dateStr = d.toISOString().slice(0, 10); // YYYY-MM-DD
  return path.join(getAuditDir(), `${dateStr}.jsonl`);
}

/**
 * Ensure audit directory exists
 */
function ensureAuditDir() {
  const dir = getAuditDir();
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// ============================================================
// Sanitization (v2.1.10 C2 fix sync)
// ============================================================

// Sensitive key blacklist + value length cap.
// Prevents accidental PII/token leakage into .rkit/audit/*.jsonl.
const SENSITIVE_KEY_PATTERNS = [
  /password/i,
  /secret/i,
  /token/i,
  /api[_-]?key/i,
  /authorization/i,
  /cookie/i,
  /session[_-]?key/i,
  /private[_-]?key/i,
];
const DETAILS_VALUE_MAX_CHARS = 500;

/**
 * Sanitize the `details` object before logging.
 * - Redacts values for keys matching SENSITIVE_KEY_PATTERNS
 * - Truncates string values exceeding DETAILS_VALUE_MAX_CHARS
 * - Drops non-serializable nested values
 *
 * @param {*} details - Raw details object (may be null/undefined/non-object)
 * @returns {Object} Sanitized details (always plain object, safe to JSON.stringify)
 */
function sanitizeDetails(details) {
  if (!details || typeof details !== 'object' || Array.isArray(details)) return {};
  const out = {};
  for (const [key, value] of Object.entries(details)) {
    if (SENSITIVE_KEY_PATTERNS.some((re) => re.test(key))) {
      out[key] = '[REDACTED]';
      continue;
    }
    if (typeof value === 'string' && value.length > DETAILS_VALUE_MAX_CHARS) {
      out[key] = value.slice(0, DETAILS_VALUE_MAX_CHARS) + '…[truncated]';
      continue;
    }
    if (
      value === null ||
      typeof value === 'number' ||
      typeof value === 'boolean' ||
      typeof value === 'string'
    ) {
      out[key] = value;
    } else if (typeof value === 'object') {
      try {
        const nested = {};
        for (const [nk, nv] of Object.entries(value)) {
          if (SENSITIVE_KEY_PATTERNS.some((re) => re.test(nk))) {
            nested[nk] = '[REDACTED]';
          } else if (typeof nv === 'string' && nv.length > DETAILS_VALUE_MAX_CHARS) {
            nested[nk] = nv.slice(0, DETAILS_VALUE_MAX_CHARS) + '…[truncated]';
          } else {
            nested[nk] = nv;
          }
        }
        out[key] = nested;
      } catch {
        out[key] = '[non-serializable]';
      }
    }
  }
  return out;
}

/**
 * Validate an audit log entry and fill defaults
 * @param {Object} entry - Partial audit log entry
 * @returns {Object} Complete AuditLogEntry
 */
function normalizeEntry(entry) {
  return {
    id: entry.id || generateUUID(),
    timestamp: entry.timestamp || new Date().toISOString(),
    sessionId: entry.sessionId || '',
    actor: ACTORS.includes(entry.actor) ? entry.actor : 'system',
    actorId: entry.actorId || '',
    action: ACTION_TYPES.includes(entry.action) ? entry.action : entry.action || 'unknown',
    category: CATEGORIES.includes(entry.category) ? entry.category : 'control',
    target: entry.target || '',
    targetType: TARGET_TYPES.includes(entry.targetType) ? entry.targetType : 'feature',
    details: sanitizeDetails(entry.details),
    result: RESULTS.includes(entry.result) ? entry.result : 'success',
    reason: entry.reason || null,
    destructiveOperation: Boolean(entry.destructiveOperation),
    blastRadius: BLAST_RADII.includes(entry.blastRadius) ? entry.blastRadius : null,
    rkitVersion: MCUKIT_VERSION,
  };
}

// ============================================================
// Public API
// ============================================================

/**
 * Append an audit log entry to the daily JSONL file
 * @param {Object} entry - Partial or complete AuditLogEntry
 */
function writeAuditLog(entry) {
  try {
    ensureAuditDir();
    const normalized = normalizeEntry(entry);
    const line = JSON.stringify(normalized) + '\n';
    const filePath = getAuditFilePath(new Date(normalized.timestamp));
    fs.appendFileSync(filePath, line, 'utf8');
  } catch (e) {
    // Audit logging is non-critical; never throw
    if (process.env.MCUKIT_DEBUG) {
      console.error(`[AuditLogger] Write failed: ${e.message}`);
    }
  }
}

/**
 * Read audit log entries with optional filters
 * @param {Object} [options] - Filter options
 * @param {string|Date} [options.date] - Date to read (defaults to today)
 * @param {string} [options.feature] - Filter by target feature name
 * @param {string} [options.action] - Filter by action type
 * @param {string} [options.category] - Filter by category
 * @param {string} [options.actor] - Filter by actor type
 * @param {number} [options.limit] - Maximum entries to return (0 = unlimited)
 * @returns {Object[]} Array of AuditLogEntry objects
 */
function readAuditLogs(options = {}) {
  try {
    const filePath = getAuditFilePath(options.date);
    if (!fs.existsSync(filePath)) return [];

    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.trim().split('\n').filter(Boolean);

    let entries = lines.map(line => {
      try { return JSON.parse(line); } catch { return null; }
    }).filter(Boolean);

    // Apply filters
    if (options.feature) {
      entries = entries.filter(e => e.target === options.feature);
    }
    if (options.action) {
      entries = entries.filter(e => e.action === options.action);
    }
    if (options.category) {
      entries = entries.filter(e => e.category === options.category);
    }
    if (options.actor) {
      entries = entries.filter(e => e.actor === options.actor);
    }

    // Apply limit
    if (options.limit && options.limit > 0) {
      entries = entries.slice(-options.limit);
    }

    return entries;
  } catch (e) {
    if (process.env.MCUKIT_DEBUG) {
      console.error(`[AuditLogger] Read failed: ${e.message}`);
    }
    return [];
  }
}

/**
 * Generate a summary of the day's audit actions
 * @param {string|Date} [date] - Date to summarize (defaults to today)
 * @returns {Object} Summary with counts by action, category, result, actor
 */
function generateDailySummary(date) {
  const entries = readAuditLogs({ date });

  const summary = {
    date: (date instanceof Date ? date : (date ? new Date(date) : new Date())).toISOString().slice(0, 10),
    totalEntries: entries.length,
    byAction: {},
    byCategory: {},
    byResult: {},
    byActor: {},
    destructiveCount: 0,
    criticalCount: 0,
    features: [],
    firstEntry: entries.length > 0 ? entries[0].timestamp : null,
    lastEntry: entries.length > 0 ? entries[entries.length - 1].timestamp : null,
  };

  const featureSet = new Set();

  for (const entry of entries) {
    // Count by action
    summary.byAction[entry.action] = (summary.byAction[entry.action] || 0) + 1;

    // Count by category
    summary.byCategory[entry.category] = (summary.byCategory[entry.category] || 0) + 1;

    // Count by result
    summary.byResult[entry.result] = (summary.byResult[entry.result] || 0) + 1;

    // Count by actor
    summary.byActor[entry.actor] = (summary.byActor[entry.actor] || 0) + 1;

    // Track destructive operations
    if (entry.destructiveOperation) summary.destructiveCount++;

    // Track critical blast radius
    if (entry.blastRadius === 'critical') summary.criticalCount++;

    // Collect unique features
    if (entry.target && entry.targetType === 'feature') {
      featureSet.add(entry.target);
    }
  }

  summary.features = Array.from(featureSet);

  return summary;
}

/**
 * Delete audit log files older than the retention period
 * @param {number} [retentionDays=30] - Number of days to retain
 * @returns {number} Number of files deleted
 */
function cleanupOldLogs(retentionDays = DEFAULT_RETENTION_DAYS) {
  try {
    const auditDir = getAuditDir();
    if (!fs.existsSync(auditDir)) return 0;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - retentionDays);
    const cutoffStr = cutoff.toISOString().slice(0, 10);

    const files = fs.readdirSync(auditDir).filter(f => f.endsWith('.jsonl'));
    let deleted = 0;

    for (const file of files) {
      const dateStr = file.replace('.jsonl', '');
      // Compare date strings lexicographically (YYYY-MM-DD format)
      if (dateStr < cutoffStr) {
        try {
          fs.unlinkSync(path.join(auditDir, file));
          deleted++;
        } catch (e) {
          if (process.env.MCUKIT_DEBUG) {
            console.error(`[AuditLogger] Failed to delete ${file}: ${e.message}`);
          }
        }
      }
    }

    return deleted;
  } catch (e) {
    if (process.env.MCUKIT_DEBUG) {
      console.error(`[AuditLogger] Cleanup failed: ${e.message}`);
    }
    return 0;
  }
}

// ============================================================
// Module Exports
// ============================================================

// Category-specific convenience loggers
function logControl(details) { return writeAuditLog({ ...details, category: 'control' }); }
function logPermission(details) { return writeAuditLog({ ...details, category: 'permission' }); }
function logCheckpoint(details) { return writeAuditLog({ ...details, category: 'checkpoint' }); }
function logPdca(details) { return writeAuditLog({ ...details, category: 'pdca' }); }
function logTrust(details) { return writeAuditLog({ ...details, category: 'trust' }); }
function logSystem(details) { return writeAuditLog({ ...details, category: 'system' }); }

/**
 * Generate weekly summary of audit logs
 * @param {string} [weekStart] - ISO date of week start (defaults to 7 days ago)
 * @returns {Object} Weekly summary
 */
function generateWeeklySummary(weekStart) {
  const start = weekStart ? new Date(weekStart) : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  const end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000);
  const dailySummaries = [];

  for (let d = new Date(start); d < end; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0];
    dailySummaries.push({ date: dateStr, ...generateDailySummary(dateStr) });
  }

  return {
    weekStart: start.toISOString().split('T')[0],
    weekEnd: end.toISOString().split('T')[0],
    dailySummaries,
    totalActions: dailySummaries.reduce((sum, d) => sum + (d.totalActions || 0), 0),
  };
}

/**
 * Get session statistics from today's logs
 * @returns {{ totalActions: number, byCategory: Object, byResult: Object }}
 */
function getSessionStats() {
  const today = new Date().toISOString().split('T')[0];
  const logs = readAuditLogs({ startDate: today });
  const byCategory = {};
  const byResult = {};

  for (const log of logs) {
    byCategory[log.category] = (byCategory[log.category] || 0) + 1;
    byResult[log.result] = (byResult[log.result] || 0) + 1;
  }

  return { totalActions: logs.length, byCategory, byResult };
}

module.exports = {
  writeAuditLog,
  readAuditLogs,
  generateDailySummary,
  generateWeeklySummary,
  cleanupOldLogs,
  getSessionStats,
  // Category-specific loggers
  logControl,
  logPermission,
  logCheckpoint,
  logPdca,
  logTrust,
  logSystem,
  // Constants (for external validation)
  ACTION_TYPES,
  CATEGORIES,
  RESULTS,
  ACTORS,
  TARGET_TYPES,
  BLAST_RADII,
  MCUKIT_VERSION,
  // Helpers (for testing)
  generateUUID,
  getAuditDir,
  getAuditFilePath,
  sanitizeDetails,
};
