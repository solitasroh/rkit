/**
 * Agent Team Panel — Dual-Render Component
 * @module lib/ui/components/agent-panel
 *
 * terminal(data, config) -> ANSI string (stderr)
 * context(data, config)  -> markdown string (additionalContext)
 * renderAgentPanel()     -> backward-compatible wrapper
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');

// ============================================================
// Constants
// ============================================================

const STATUS_ICON = {
  spawning:  'spawning',
  working:   'running',
  idle:      'idle',
  completed: 'completed',
  failed:    'failed',
  pending:   'pending',
};

const STATUS_COLOR = {
  spawning:  'yellow',
  working:   'cyan',
  idle:      'white',
  completed: 'green',
  failed:    'red',
  pending:   'gray',
};

const PATTERN_DISPLAY = {
  leader:     'leader',
  parallel:   'parallel swarm',
  sequential: 'sequential',
  hybrid:     'hybrid',
};

const STATUS_TEXT = {
  spawning:  'Spawning',
  working:   'Working',
  idle:      'Idle',
  completed: 'Completed',
  failed:    'Failed',
  pending:   'Pending',
};

// ============================================================
// Internal Helpers
// ============================================================

function formatTime(isoTime) {
  if (!isoTime) return '';
  try {
    const d = new Date(isoTime);
    return d.toTimeString().slice(0, 8);
  } catch {
    return '';
  }
}

// ============================================================
// Dual-Render API
// ============================================================

/**
 * Terminal render — ANSI team roster box.
 * @param {Object} data - { agentState }
 * @param {Object} [config] - { maxMessages, showPattern, width }
 * @returns {string}
 */
function terminal(data, config = {}) {
  const uiConfig = loadUiConfig();
  const width = config.width || T.getTermWidth();
  const maxMessages = config.maxMessages != null ? config.maxMessages : uiConfig.display.maxRecentMessages;
  const showPattern = config.showPattern !== false;
  const innerWidth = width - 6;
  const agentColumns = uiConfig.layout.agentColumns;

  const agentState = data.agentState;

  // Inactive / no state fallback
  if (!agentState || !agentState.enabled) {
    const title = ' Agent Team ';
    const titlePad = Math.max(1, width - title.length - 5);
    return [
      `${T.BOX.topLeft}${T.hline(3)}${title}${T.hline(titlePad)}${T.BOX.topRight}`,
      T.boxLine('Agent Team is inactive.', innerWidth),
      T.boxLine('Use /pdca team to check team status or', innerWidth),
      T.boxLine('start a CTO Team skill to launch agents.', innerWidth),
      `${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`,
    ].join('\n');
  }

  const lines = [];

  // Header with team name and pattern
  const teamName = agentState.teamName || 'Agent Team';
  const patternStr = showPattern && agentState.orchestrationPattern
    ? `Pattern: ${PATTERN_DISPLAY[agentState.orchestrationPattern] || agentState.orchestrationPattern}`
    : '';

  const titleLeft = ` Agent Team: ${T.truncate(teamName, 25)} `;
  const titleRight = patternStr ? ` ${patternStr} ` : '';
  const titleFill = Math.max(1, width - titleLeft.length - titleRight.length - 4);
  lines.push(
    `${T.BOX.topLeft}${T.hline(3)}${titleLeft}${T.hline(titleFill)}${titleRight}${T.hline(1)}${T.BOX.topRight}`
  );

  lines.push(T.boxLine('', innerWidth));

  // Teammate roster
  const teammates = agentState.teammates || [];
  if (teammates.length === 0) {
    lines.push(T.boxLine(T.dim('No teammates registered.'), innerWidth));
  } else {
    for (const t of teammates) {
      const status = t.status || 'pending';
      const statusKey = STATUS_ICON[status] || 'pending';
      const icon = T.statusSymbol(statusKey);
      const color = STATUS_COLOR[status] || 'gray';
      const nameCol = T.truncate(t.name || 'unknown', agentColumns.name).padEnd(agentColumns.name);
      const statusCol = `[${status}]`.padEnd(agentColumns.status);
      const task = T.truncate(t.currentTask || '', innerWidth - agentColumns.name - agentColumns.status - 8);

      const styledStatus = T.colorize(statusCol, color);
      lines.push(T.boxLine(`${icon}  ${nameCol}${styledStatus}${task}`, innerWidth));
    }
  }

  lines.push(T.boxLine('', innerWidth));

  // Recent communications
  const messages = agentState.recentMessages || [];
  if (messages.length > 0 && maxMessages > 0) {
    const recentHeader = `${T.hline(3)} Recent Communications (last ${Math.min(messages.length, maxMessages)}) ${T.hline(Math.max(1, innerWidth - 40))}`;
    lines.push(T.boxLine(recentHeader, innerWidth));

    const recentSlice = messages.slice(-maxMessages);
    for (const msg of recentSlice) {
      const from = T.truncate(msg.from || '?', 10);
      const to = T.truncate(msg.to || '?', 10);
      const content = T.truncate(msg.content || '', innerWidth - 40);
      const time = formatTime(msg.timestamp);
      const direction = `${from}${T.BOX.arrowRight}${to}:`;
      const padding = Math.max(0, innerWidth - T.stripAnsi(direction).length - content.length - time.length - 6);
      lines.push(T.boxLine(
        `${T.dim(direction)}  ${content}${' '.repeat(padding)}  ${T.dim(time)}`,
        innerWidth
      ));
    }

    lines.push(T.boxLine('', innerWidth));
  }

  // Task summary footer
  const progress = agentState.progress || {};
  const parts = [];
  if (progress.totalTasks != null) parts.push(`Tasks: ${progress.totalTasks} total`);
  if (progress.inProgressTasks) parts.push(`${progress.inProgressTasks} working`);
  if (progress.completedTasks) parts.push(`${progress.completedTasks} done`);
  if (progress.failedTasks) parts.push(`${progress.failedTasks} failed`);
  if (progress.pendingTasks) parts.push(`${progress.pendingTasks} pending`);

  if (parts.length > 0) {
    lines.push(T.boxLine(
      T.truncate(parts.join(`  ${T.SYMBOLS.bullet}  `), innerWidth),
      innerWidth
    ));
  }

  // Close box
  lines.push(`${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`);

  return lines.join('\n');
}

/**
 * Context render — markdown table with Agent | Status | Task columns.
 * @param {Object} data - { agentState }
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config = {}) {
  const agentState = data.agentState;

  if (!agentState || !agentState.enabled) {
    return 'Agent Team is inactive.';
  }

  const teammates = agentState.teammates || [];
  if (teammates.length === 0) {
    return 'Agent Team: No teammates registered.';
  }

  const parts = [];

  const teamName = agentState.teamName || 'Agent Team';
  const pattern = agentState.orchestrationPattern
    ? PATTERN_DISPLAY[agentState.orchestrationPattern] || agentState.orchestrationPattern
    : '';
  parts.push(M.heading(3, `Agent Team: ${teamName}${pattern ? ` (${pattern})` : ''}`));
  parts.push('');

  const headers = ['Agent', 'Status', 'Task'];
  const rows = teammates.map(t => {
    const status = t.status || 'pending';
    const statusLabel = STATUS_TEXT[status] || status;
    return [t.name || 'unknown', statusLabel, t.currentTask || ''];
  });
  parts.push(M.table(headers, rows));

  return parts.join('\n');
}

/**
 * Backward-compatible wrapper.
 * @param {Object|null} agentState
 * @param {Object} [opts]
 * @returns {string}
 */
function renderAgentPanel(agentState, opts = {}) {
  return terminal(
    { agentState },
    { maxMessages: opts.maxMessages, showPattern: opts.showPattern, width: opts.width }
  );
}

module.exports = { terminal, context, renderAgentPanel };
