/**
 * Review Orchestrator — L1 + L2 + L3 Code Review Orchestration
 * @module lib/code-quality/review-orchestrator
 * @version 0.1.0
 *
 * Coordinates the 3-Layer code review architecture:
 *   L1 (code-analyzer)      — Universal design quality (always runs)
 *   L2 (language reviewers)  — Language-specific idioms (auto-selected by file extension)
 *   L3 (domain agents)       — Domain safety (opt-in via --domain flag)
 *
 * This module provides:
 *   - File extension → L2 agent mapping
 *   - L3 domain → agent mapping
 *   - Severity-based result merging
 *   - Unified markdown report generation
 */

const path = require('path');
const { SEVERITY, severityToAction } = require('./design-rules');

// ---------------------------------------------------------------------------
// L2 Agent Selection — file extension based (separate from domain/detector.js)
// ---------------------------------------------------------------------------

const L2_AGENT_MAP = Object.freeze({
  '.c':   'c-cpp-reviewer',
  '.cpp': 'c-cpp-reviewer',
  '.cc':  'c-cpp-reviewer',
  '.cxx': 'c-cpp-reviewer',
  '.h':   'c-cpp-reviewer',
  '.hpp': 'c-cpp-reviewer',
  '.cs':  'csharp-reviewer',
  '.py':  'python-reviewer',
});

/**
 * Select the L2 agent name for a given file path.
 * @param {string} filePath
 * @returns {string|null} Agent name or null if no L2 agent covers this extension.
 */
function selectL2Agent(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return L2_AGENT_MAP[ext] || null;
}

/**
 * Collect unique L2 agents needed for a set of files.
 * @param {string[]} filePaths
 * @returns {string[]} Unique agent names (deduplicated).
 */
function collectL2Agents(filePaths) {
  const agents = new Set();
  for (const fp of filePaths) {
    const agent = selectL2Agent(fp);
    if (agent) agents.add(agent);
  }
  return [...agents];
}

/**
 * Detect language label from file extension (for report display).
 * @param {string} filePath
 * @returns {string}
 */
function detectLanguage(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const map = {
    '.c': 'C', '.cpp': 'C++', '.cc': 'C++', '.cxx': 'C++',
    '.h': 'C/C++ Header', '.hpp': 'C++ Header',
    '.cs': 'C#',
    '.py': 'Python',
    '.js': 'JavaScript', '.jsx': 'JavaScript (JSX)',
    '.ts': 'TypeScript', '.tsx': 'TypeScript (TSX)',
  };
  return map[ext] || ext;
}

// ---------------------------------------------------------------------------
// L3 Domain Agent Mapping — opt-in via --domain flag
// ---------------------------------------------------------------------------

const L3_DOMAIN_MAP = Object.freeze({
  mcu: ['safety-auditor', 'mcu-critical-analyzer'],
  mpu: ['linux-bsp-expert'],
  wpf: ['wpf-architect'],
});

/**
 * Get L3 domain agents for a given domain type.
 * @param {string} domainType - 'mcu' | 'mpu' | 'wpf'
 * @returns {string[]} Agent names, empty array if domain not recognized.
 */
function getL3Agents(domainType) {
  return L3_DOMAIN_MAP[domainType] || [];
}

// ---------------------------------------------------------------------------
// Severity ordering (for sorting findings)
// ---------------------------------------------------------------------------

const SEVERITY_ORDER = Object.freeze({
  [SEVERITY.CRITICAL]: 0,
  [SEVERITY.HIGH]: 1,
  [SEVERITY.MEDIUM]: 2,
  [SEVERITY.LOW]: 3,
});

/**
 * Compare two findings by severity (most severe first).
 * @param {{ severity: string }} a
 * @param {{ severity: string }} b
 * @returns {number}
 */
function compareBySeverity(a, b) {
  return (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4);
}

// ---------------------------------------------------------------------------
// Result Merging
// ---------------------------------------------------------------------------

/**
 * @typedef {Object} Finding
 * @property {string} severity  - CRITICAL | HIGH | MEDIUM | LOW
 * @property {string} layer     - 'L1' | 'L2' | 'L3'
 * @property {string} rule      - Rule ID (e.g., 'SQ-001', 'RAII', 'async-void')
 * @property {string} file      - File path
 * @property {string|number} line - Line number or range
 * @property {string} title     - Short issue title
 * @property {string} fix       - Recommended fix
 */

/**
 * @typedef {Object} ReviewResult
 * @property {string} target       - Review target path
 * @property {string[]} files      - List of reviewed files
 * @property {string[]} languages  - Detected languages
 * @property {string} timestamp    - ISO timestamp
 * @property {Finding[]} findings  - All findings sorted by severity
 * @property {Object} summary      - Count by severity
 * @property {number} score        - Quality score 0-100
 * @property {string} decision     - BLOCK | WARNING | APPROVE
 */

/**
 * Merge findings from multiple layers into a unified result.
 * @param {Object} options
 * @param {string} options.target        - Review target path
 * @param {string[]} options.files       - Reviewed file list
 * @param {Finding[]} [options.l1Findings=[]] - L1 findings
 * @param {Finding[]} [options.l2Findings=[]] - L2 findings
 * @param {Finding[]} [options.l3Findings=[]] - L3 findings
 * @returns {ReviewResult}
 */
function mergeResults({ target, files, l1Findings = [], l2Findings = [], l3Findings = [] }) {
  const allFindings = [...l1Findings, ...l2Findings, ...l3Findings].sort(compareBySeverity);

  const languages = [...new Set(files.map(detectLanguage))];

  const summary = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
  };
  for (const f of allFindings) {
    if (summary[f.severity] !== undefined) {
      summary[f.severity]++;
    }
  }

  // Score: 100 - (critical*15 + high*7 + medium*3 + low*1), clamped to [0, 100]
  const rawScore = 100
    - (summary.CRITICAL * 15)
    - (summary.HIGH * 7)
    - (summary.MEDIUM * 3)
    - (summary.LOW * 1);
  const score = Math.max(0, Math.min(100, rawScore));

  let decision = 'APPROVE';
  if (summary.CRITICAL > 0) decision = 'BLOCK';
  else if (summary.HIGH > 0 || summary.MEDIUM > 0) decision = 'WARNING';

  return {
    target,
    files,
    languages,
    timestamp: new Date().toISOString(),
    findings: allFindings,
    summary,
    score,
    decision,
  };
}

// ---------------------------------------------------------------------------
// Report Formatting
// ---------------------------------------------------------------------------

/**
 * Format a ReviewResult as a markdown report.
 * @param {ReviewResult} result
 * @returns {string}
 */
function formatReport(result) {
  const lines = [];

  lines.push('# Code Review Report');
  lines.push('');
  lines.push('## Review Target');
  lines.push(`- Path: ${result.target}`);
  lines.push(`- Files: ${result.files.length}`);
  lines.push(`- Languages: ${result.languages.join(', ')}`);
  lines.push(`- Date: ${result.timestamp.slice(0, 10)}`);
  lines.push('');
  lines.push(`## Quality Score: ${result.score}/100`);
  lines.push('');

  // Summary table
  lines.push('## Summary');
  lines.push('');
  lines.push('| Severity | Count | Action |');
  lines.push('|----------|------:|--------|');
  for (const sev of [SEVERITY.CRITICAL, SEVERITY.HIGH, SEVERITY.MEDIUM, SEVERITY.LOW]) {
    lines.push(`| ${sev} | ${result.summary[sev]} | ${severityToAction(sev)} |`);
  }
  lines.push('');
  lines.push(`**Decision**: ${result.decision}`);
  lines.push('');

  // Group findings by action
  const groups = [
    { action: 'BLOCK', label: 'BLOCK (Immediate Fix Required)', severities: [SEVERITY.CRITICAL] },
    { action: 'WARNING', label: 'WARNING (Fix Recommended)', severities: [SEVERITY.HIGH, SEVERITY.MEDIUM] },
    { action: 'APPROVE', label: 'APPROVE (Informational)', severities: [SEVERITY.LOW] },
  ];

  for (const group of groups) {
    const groupFindings = result.findings.filter(f => group.severities.includes(f.severity));
    lines.push(`## ${group.label}`);
    lines.push('');
    if (groupFindings.length === 0) {
      lines.push('No findings.');
      lines.push('');
      continue;
    }
    lines.push('| Severity | Layer | File | Line | Rule | Issue | Fix |');
    lines.push('|----------|-------|------|------|------|-------|-----|');
    for (const f of groupFindings) {
      lines.push(`| ${f.severity} | ${f.layer} | ${f.file} | ${f.line} | ${f.rule} | ${f.title} | ${f.fix} |`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Instinct Integration
// ---------------------------------------------------------------------------

/**
 * Collect instinct patterns from a review result.
 * Called after mergeResults() to persist learned patterns.
 * Graceful degradation: returns 0 on any failure.
 * @param {ReviewResult} reviewResult
 * @param {string} sessionId
 * @returns {number} Number of patterns collected
 */
function collectInstinctPatterns(reviewResult, sessionId) {
  try {
    const collector = require('../instinct/collector');
    const patterns = collector.extractPatterns(reviewResult, sessionId);
    if (patterns.length > 0) {
      collector.saveExtractedPatterns(patterns, sessionId);
    }
    return patterns.length;
  } catch {
    return 0;
  }
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  // L2 selection
  L2_AGENT_MAP,
  selectL2Agent,
  collectL2Agents,
  detectLanguage,

  // L3 selection
  L3_DOMAIN_MAP,
  getL3Agents,

  // Result merging
  mergeResults,
  compareBySeverity,

  // Report
  formatReport,

  // Instinct
  collectInstinctPatterns,
};
