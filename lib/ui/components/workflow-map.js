/**
 * Workflow Map — Dual-Render Component
 * @module lib/ui/components/workflow-map
 *
 * terminal(data, config) -> ANSI string (stderr)
 * context(data, config)  -> markdown string (additionalContext)
 * renderWorkflowMap()    -> backward-compatible wrapper
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');

// ============================================================
// Constants
// ============================================================

const PHASES = ['PM', 'PLAN', 'DESIGN', 'DO', 'CHECK', 'REPORT'];
const PHASE_KEYS = ['pm', 'plan', 'design', 'do', 'check', 'report'];

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

function getPhaseStatus(phaseKey, featureData) {
  if (!featureData) return 'pending';
  const current = (featureData.phase || '').toLowerCase();
  if (current === 'completed') return 'completed';
  const currentIdx = PHASE_KEYS.indexOf(current);
  const idx = PHASE_KEYS.indexOf(phaseKey);
  if (idx < currentIdx) return 'completed';
  if (idx === currentIdx) return 'running';
  return 'pending';
}

function renderPhaseBox(label, status) {
  const symbol = T.statusSymbol(status);
  const color = status === 'completed' ? 'green'
    : status === 'running' ? 'cyan'
    : status === 'failed' ? 'red'
    : status === 'approval_waiting' ? 'yellow'
    : 'gray';

  if (status === 'running') {
    return T.bold(T.colorize(`[${label} `, color)) + symbol + T.bold(T.colorize(']', color));
  }
  return T.colorize(`[${label} `, color) + symbol + T.colorize(']', color);
}

// ============================================================
// Dual-Render API
// ============================================================

/**
 * Terminal render — ANSI workflow diagram with arrows and branches.
 * @param {Object} data - { pdcaStatus, agentState, feature }
 * @param {Object} [config] - { showIteration, showBranch, width }
 * @returns {string}
 */
function terminal(data, config = {}) {
  const uiConfig = loadUiConfig();
  const width = config.width || T.getTermWidth();
  const showIteration = config.showIteration !== false;
  const showBranch = config.showBranch !== false;
  const innerWidth = width - 6;
  const thresholds = uiConfig.thresholds.matchRate;

  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);
  const agentState = data.agentState;

  // No data fallback
  if (!featureData) {
    const title = ' Workflow Map ';
    const titleLine = `${T.BOX.topLeft}${T.hline(3)}${title}${T.hline(Math.max(1, width - title.length - 5))}${T.BOX.topRight}`;
    const emptyMsg = 'No active PDCA feature. Start with /pdca pm {feature-name}';
    return [
      titleLine,
      T.boxLine(T.truncate(emptyMsg, innerWidth), innerWidth),
      `${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`,
    ].join('\n');
  }

  const lines = [];

  // Title line
  const titleText = ` Workflow Map: ${T.truncate(featureName, 30)} `;
  const titlePad = Math.max(1, width - titleText.length - 5);
  lines.push(`${T.BOX.topLeft}${T.hline(3)}${titleText}${T.hline(titlePad)}${T.BOX.topRight}`);

  // Empty line
  lines.push(T.boxLine('', innerWidth));

  // Phase chain line
  const phaseBoxes = PHASES.map((label, i) => {
    const status = getPhaseStatus(PHASE_KEYS[i], featureData);
    return renderPhaseBox(label, status);
  });
  const connector = `${T.hline(2)}${T.BOX.arrowRight}`;
  const chainStr = phaseBoxes.join(connector);
  lines.push(T.boxLine(chainStr, innerWidth));

  // Conditional branch line (CHECK threshold)
  if (showBranch) {
    const currentPhase = (featureData.phase || '').toLowerCase();
    const checkIdx = PHASE_KEYS.indexOf('check');
    const currentIdx = PHASE_KEYS.indexOf(currentPhase);

    if (currentIdx >= checkIdx - 1) {
      const branchLine = `${' '.repeat(4)}CHECK: ${T.colorize(`\u2265${thresholds.good}% \u2192 REPORT`, 'green')}  ${T.colorize(`<${thresholds.good}% \u2192 ACT`, 'yellow')}`;
      lines.push(T.boxLine(branchLine, innerWidth));
    } else {
      lines.push(T.boxLine('', innerWidth));
    }
  } else {
    lines.push(T.boxLine('', innerWidth));
  }

  // Parallel swarm subtree
  const hasSwarm = agentState &&
    agentState.orchestrationPattern === 'parallel' &&
    Array.isArray(agentState.teammates) &&
    agentState.teammates.length > 1;

  if (hasSwarm) {
    lines.push(T.boxLine('', innerWidth));
    const agentSummary = agentState.teammates.map(t => {
      const status = t.status || 'pending';
      const symbol = T.statusSymbol(status);
      const color = status === 'completed' ? 'green'
        : status === 'working' ? 'cyan'
        : status === 'spawning' ? 'yellow'
        : status === 'failed' ? 'red'
        : 'gray';
      return `${T.BOX.vertical}${T.hline(1)}${T.colorize(`[${T.truncate(t.name, 15)} `, color)}${symbol}${T.colorize(']', color)}`;
    });

    const swarmHeader = `    DO swarm:`;
    lines.push(T.boxLine(T.bold(swarmHeader), innerWidth));
    for (const agent of agentSummary) {
      lines.push(T.boxLine(`      ${agent}`, innerWidth));
    }
  }

  // Summary footer line
  const matchRate = featureData.matchRate != null ? `${featureData.matchRate}%` : 'N/A';
  const iterCount = featureData.iterationCount || 0;

  let summaryParts = [`Iter: ${iterCount}`, `matchRate: ${matchRate}`];

  if (hasSwarm) {
    const working = agentState.teammates.filter(t => t.status === 'working').length;
    const spawning = agentState.teammates.filter(t => t.status === 'spawning').length;
    const pending = agentState.teammates.filter(t => t.status === 'pending' || !t.status).length;
    summaryParts.push(
      `Agents: ${agentState.teammates.length} (${working} working, ${spawning} spawning, ${pending} pending)`
    );
  }

  lines.push(T.boxLine('', innerWidth));
  const summaryStr = summaryParts.join(`  ${T.SYMBOLS.bullet}  `);
  lines.push(T.boxLine(T.truncate(summaryStr, innerWidth), innerWidth));

  // Close main box
  lines.push(`${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`);

  // Iteration history (separate box below)
  if (showIteration && featureData.iterationHistory && featureData.iterationHistory.length > 0) {
    lines.push('');
    const iterTitle = ' Iteration History ';
    const iterTitlePad = Math.max(1, width - iterTitle.length - 5);
    lines.push(`${T.BOX.topLeft}${T.hline(3)}${iterTitle}${T.hline(iterTitlePad)}${T.BOX.topRight}`);

    for (const iter of featureData.iterationHistory) {
      const iterNum = iter.iteration || '?';
      const phase = iter.phase || 'N/A';
      const rate = iter.matchRate != null ? `${iter.matchRate}%` : 'N/A';
      const isCurrent = !iter.completedAt;

      let iterLine = `  Iter ${iterNum}: ${phase}`;
      if (iter.outcome) {
        iterLine += `${T.BOX.arrowRight}${iter.outcome}`;
      }
      iterLine += `  matchRate: ${rate}`;
      if (isCurrent) {
        iterLine = T.bold(iterLine + '  (current)');
      }

      lines.push(T.boxLine(T.truncate(iterLine, innerWidth), innerWidth));
    }

    lines.push(`${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`);
  }

  return lines.join('\n');
}

/**
 * Context render — plain text phase chain.
 * @param {Object} data - { pdcaStatus, agentState, feature }
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config = {}) {
  const { name: featureName, data: featureData } = resolveFeature(data.pdcaStatus, data.feature);

  if (!featureData) {
    return 'No active PDCA feature.';
  }

  // Phase chain: PM(Done) -> Plan(Done) -> Design(Active) -> ...
  const chain = PHASES.map((label, i) => {
    const status = getPhaseStatus(PHASE_KEYS[i], featureData);
    const statusLabel = STATUS_TEXT[status] || status;
    return `${label}(${statusLabel})`;
  });

  const parts = [];
  parts.push(`Workflow: ${featureName}`);
  parts.push(chain.join(' -> '));

  const matchRate = featureData.matchRate != null ? `${featureData.matchRate}%` : 'N/A';
  const iterCount = featureData.iterationCount || 0;
  parts.push(`Iterations: ${iterCount}, Match Rate: ${matchRate}`);

  return parts.join('\n');
}

/**
 * Backward-compatible wrapper.
 * @param {Object|null} pdcaStatus
 * @param {Object|null} agentState
 * @param {Object} [opts]
 * @returns {string}
 */
function renderWorkflowMap(pdcaStatus, agentState, opts = {}) {
  return terminal(
    { pdcaStatus, agentState, feature: opts.feature },
    { showIteration: opts.showIteration, showBranch: opts.showBranch, width: opts.width }
  );
}

module.exports = { terminal, context, renderWorkflowMap };
