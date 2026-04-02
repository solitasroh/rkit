/**
 * PDCA Progress Bar — Dual-Render Component
 * @module lib/ui/components/progress-bar
 *
 * terminal(data, config) -> ANSI string (stderr)
 * context(data, config)  -> markdown string (additionalContext)
 * renderPdcaProgressBar() -> backward-compatible wrapper
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');

// ============================================================
// Constants
// ============================================================

const PHASES = ['pm', 'plan', 'design', 'do', 'check', 'report'];
const PHASE_LABELS = {
  pm: 'PM', plan: 'PLAN', design: 'DESIGN',
  do: 'DO', check: 'CHECK', report: 'REPORT',
};

const STATUS_TEXT = {
  completed: 'Done',
  running: 'Active',
  pending: 'Pending',
  failed: 'Failed',
  approval_waiting: 'Awaiting Approval',
};

// ============================================================
// Internal Helpers
// ============================================================

/**
 * Resolve feature from pdcaStatus (mirrors ansi.resolveFeature logic).
 */
function resolveFeature(pdcaStatus, featureName) {
  if (!pdcaStatus) return { name: null, data: null };
  const features = pdcaStatus.features || {};
  if (featureName && features[featureName]) {
    return { name: featureName, data: features[featureName] };
  }
  const primary = pdcaStatus.primaryFeature || pdcaStatus.activeFeature;
  if (primary && features[primary]) {
    return { name: primary, data: features[primary] };
  }
  const keys = Object.keys(features);
  if (keys.length === 1) {
    return { name: keys[0], data: features[keys[0]] };
  }
  return { name: featureName || null, data: null };
}

function getPhaseStatus(phase, featureData) {
  if (!featureData) return 'pending';
  const currentPhase = (featureData.phase || '').toLowerCase();
  if (currentPhase === 'completed') return 'completed';
  const currentIdx = PHASES.indexOf(currentPhase);
  const phaseIdx = PHASES.indexOf(phase);

  if (featureData.pendingApprovals && Array.isArray(featureData.pendingApprovals)) {
    const hasApproval = featureData.pendingApprovals.some(
      a => (a.from || '').toLowerCase() === phase
    );
    if (hasApproval && phase === currentPhase) return 'approval_waiting';
  }

  if (phaseIdx < currentIdx) return 'completed';
  if (phaseIdx === currentIdx) return 'running';
  return 'pending';
}

function calculatePercent(featureData) {
  if (!featureData) return 0;
  const phaseWeight = 1 / PHASES.length;
  let sum = 0;
  for (const phase of PHASES) {
    const status = getPhaseStatus(phase, featureData);
    if (status === 'completed') {
      sum += phaseWeight;
    } else if (status === 'running' || status === 'approval_waiting') {
      sum += phaseWeight * 0.5;
    }
  }
  return Math.round(sum * 100);
}

function relativeTime(isoTime) {
  if (!isoTime) return 'N/A';
  const diffMs = Date.now() - new Date(isoTime).getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

// ============================================================
// Dual-Render API
// ============================================================

/**
 * Terminal render — ANSI progress bar with phase symbols.
 * @param {Object} data - { pdcaStatus, feature }
 * @param {Object} [config] - { compact, width }
 * @returns {string}
 */
function terminal(data, config = {}) {
  const uiConfig = loadUiConfig();
  const compact = config.compact || false;
  const width = config.width || T.getTermWidth();
  const bp = T.getWidthBreakpoint();
  const barWidth = uiConfig.layout.barWidths[bp] || uiConfig.layout.barWidths.normal;

  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);

  // No data fallback
  if (!featureData) {
    if (compact) {
      return T.dim('[No active feature]');
    }
    const inner = width - 4;
    return [
      `${T.BOX.topLeft}${T.hline(inner + 2)}${T.BOX.topRight}`,
      `${T.BOX.vertical}  ${T.truncate('No active PDCA feature', inner)}  ${T.BOX.vertical}`,
      `${T.BOX.bottomLeft}${T.hline(inner + 2)}${T.BOX.bottomRight}`,
    ].join('\n');
  }

  const percent = calculatePercent(featureData);

  // Build phase badges
  const badges = PHASES.map(phase => {
    const status = getPhaseStatus(phase, featureData);
    const symbol = T.statusSymbol(status);
    const color = status === 'completed' ? 'green'
      : status === 'running' ? 'cyan'
      : status === 'failed' ? 'red'
      : status === 'approval_waiting' ? 'yellow'
      : 'gray';
    const label = PHASE_LABELS[phase];
    // statusSymbol already colorizes the symbol, so build label+symbol separately
    return T.colorize(label, color) + symbol;
  });

  // Compact mode: single line
  if (compact) {
    const displayName = T.truncate(featureName, 20);
    const phaseStr = badges.join(' ');
    const percentStr = `${percent}%`;
    const bar = T.progressBar(percent, Math.min(barWidth, 19));
    return `[${displayName}] ${phaseStr}  ${percentStr}  ${bar}`;
  }

  // Full mode: 3-line box
  const innerWidth = width - 4;

  // Line 1: header with feature name and percent
  const headerLabel = ` ${featureName} `;
  const percentLabel = ` ${percent}% `;
  const headerLineLen = innerWidth - headerLabel.length - percentLabel.length;
  const headerLine = `${T.BOX.topLeft}${T.hline(3)}${headerLabel}${T.hline(Math.max(1, headerLineLen))}${percentLabel}${T.hline(1)}${T.BOX.topRight}`;

  // Line 2: phase badges + bar
  const phaseStr = badges.join('  ');
  const bar = T.progressBar(percent, barWidth);
  const midContent = `  ${phaseStr}  ${bar}  `;
  const midPadding = Math.max(0, innerWidth - T.stripAnsi(midContent).length);
  const midLine = `${T.BOX.vertical}${midContent}${' '.repeat(midPadding)}${T.BOX.vertical}`;

  // Line 3: footer with details
  const lastUpdated = featureData.timestamps
    ? relativeTime(featureData.timestamps.lastUpdated)
    : 'N/A';
  const iterCount = featureData.iterationCount || 0;
  const matchRate = featureData.matchRate != null ? `${featureData.matchRate}%` : 'N/A';

  let footerInfo;
  if (bp === 'wide' || bp === 'ultrawide') {
    footerInfo = `Phase: ${featureData.phase || 'N/A'} ${T.SYMBOLS.bullet} last: ${lastUpdated} ${T.SYMBOLS.bullet} Iter: ${iterCount} ${T.SYMBOLS.bullet} matchRate: ${matchRate}`;
  } else {
    footerInfo = `${featureData.phase || 'N/A'} ${T.SYMBOLS.bullet} last: ${lastUpdated} ${T.SYMBOLS.bullet} iter: ${iterCount}`;
  }
  footerInfo = T.truncate(footerInfo, innerWidth - 2);
  const footerPadding = Math.max(0, innerWidth - footerInfo.length - 2);
  const footerLine = `${T.BOX.bottomLeft}${T.hline(1)} ${footerInfo}${' '.repeat(footerPadding)} ${T.BOX.bottomRight}`;

  return [headerLine, midLine, footerLine].join('\n');
}

/**
 * Context render — markdown table with Phase | Status columns.
 * @param {Object} data - { pdcaStatus, feature }
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config = {}) {
  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);

  if (!featureData) {
    return 'No active PDCA feature.';
  }

  const percent = calculatePercent(featureData);
  const parts = [];

  parts.push(M.heading(3, `PDCA Progress: ${featureName} (${percent}%)`));
  parts.push('');

  const headers = ['Phase', 'Status'];
  const rows = PHASES.map(phase => {
    const status = getPhaseStatus(phase, featureData);
    return [PHASE_LABELS[phase], STATUS_TEXT[status] || status];
  });
  parts.push(M.table(headers, rows));

  // Summary line
  const iterCount = featureData.iterationCount || 0;
  const matchRate = featureData.matchRate != null ? `${featureData.matchRate}%` : 'N/A';
  parts.push('');
  parts.push(`Phase: ${featureData.phase || 'N/A'}, Iterations: ${iterCount}, Match Rate: ${matchRate}`);

  return parts.join('\n');
}

/**
 * Backward-compatible wrapper.
 * @param {Object|null} pdcaStatus
 * @param {Object} [opts]
 * @returns {string}
 */
function renderPdcaProgressBar(pdcaStatus, opts = {}) {
  return terminal(
    { pdcaStatus, feature: opts.feature },
    { compact: opts.compact, width: opts.width }
  );
}

module.exports = { terminal, context, renderPdcaProgressBar };
