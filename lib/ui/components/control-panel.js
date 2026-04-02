/**
 * Control Panel — Dual-Render Component
 * @module lib/ui/components/control-panel
 *
 * terminal(data, config) -> ANSI string (stderr)
 * context(data, config)  -> markdown string (additionalContext)
 * renderControlPanel()   -> backward-compatible wrapper
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');

// ============================================================
// Constants
// ============================================================

const LEVEL_NAMES = {
  0: 'Manual',
  1: 'Guided',
  2: 'Semi-Auto',
  3: 'Auto',
  4: 'Full-Auto',
};

const LEVEL_COLORS = {
  0: 'green',
  1: 'green',
  2: 'yellow',
  3: 'red',
  4: 'red',
};

const SHORTCUTS = [
  { cmd: '/pdca status',     desc: 'Show full PDCA status' },
  { cmd: '/pdca approve',    desc: 'Approve pending item' },
  { cmd: '/pdca reject',     desc: 'Reject current phase with feedback' },
  { cmd: '/pdca rollback',   desc: 'Rollback to last checkpoint' },
  { cmd: '/pdca map',        desc: 'Show workflow map' },
  { cmd: '/pdca team',       desc: 'Show Agent Team panel' },
  { cmd: '/control level N', desc: 'Change automation level (0-4)' },
];

// ============================================================
// Internal Helpers
// ============================================================

function renderSlider(level, sliderWidth) {
  const safeLevel = Math.max(0, Math.min(4, level || 0));
  const color = LEVEL_COLORS[safeLevel] || 'yellow';
  const name = LEVEL_NAMES[safeLevel] || 'Unknown';

  // Build slider track: position the dot proportionally
  const pos = Math.round(safeLevel * (sliderWidth - 1) / 4);
  const before = T.hline(pos);
  const after = T.hline(sliderWidth - pos - 1);
  const dot = T.colorize('\u25CF', color); // filled circle
  const slider = `L0 ${before}${dot}${after} L4`;

  const labels = 'Manual  Semi-Auto  Full-Auto';
  const current = `[Current: L${safeLevel} ${name}]`;

  return [
    `Automation Level   ${slider}`,
    `                   ${labels}`,
    `                   ${T.colorize(current, color)}`,
  ];
}

// ============================================================
// Dual-Render API
// ============================================================

/**
 * Terminal render — ANSI slider + approvals box.
 * @param {Object} data - { controlState, automationLevel }
 * @param {Object} [config] - { showShortcuts, showApprovals, width }
 * @returns {string}
 */
function terminal(data, config = {}) {
  const uiConfig = loadUiConfig();
  const width = config.width || T.getTermWidth();
  const showShortcuts = config.showShortcuts !== false;
  const showApprovals = config.showApprovals !== false;
  const innerWidth = width - 6;
  const sliderWidth = uiConfig.layout.sliderWidth;

  const controlState = data.controlState;

  // Resolve automation level
  const level = data.automationLevel != null
    ? data.automationLevel
    : (controlState && controlState.automationLevel != null
      ? controlState.automationLevel
      : 2);

  const pendingApprovals = (controlState && controlState.pendingApprovals) || [];

  const lines = [];

  // Title
  const title = ' Control Panel ';
  const titlePad = Math.max(1, width - title.length - 5);
  lines.push(`${T.BOX.topLeft}${T.hline(3)}${title}${T.hline(titlePad)}${T.BOX.topRight}`);

  lines.push(T.boxLine('', innerWidth));

  // Automation level slider
  const sliderLines = renderSlider(level, sliderWidth);
  for (const sl of sliderLines) {
    lines.push(T.boxLine(sl, innerWidth));
  }

  lines.push(T.boxLine('', innerWidth));

  // Pending approvals
  if (showApprovals) {
    if (pendingApprovals.length > 0) {
      const approvalHeader = `${T.hline(3)} Pending Approvals (${pendingApprovals.length}) ${T.hline(Math.max(1, innerWidth - 30))}`;
      lines.push(T.boxLine(approvalHeader, innerWidth));

      for (const approval of pendingApprovals) {
        const from = approval.from || '?';
        const to = approval.to || '?';
        const desc = T.truncate(approval.description || '', innerWidth - 20);
        const icon = T.colorize(T.bold(T.SYMBOLS.waiting), 'yellow');
        const transition = `[${from.toUpperCase()}${T.BOX.arrowRight}${to.toUpperCase()}]`;
        lines.push(T.boxLine(`${icon} ${transition}  ${desc}`, innerWidth));
      }

      lines.push(T.boxLine(
        `  ${T.BOX.arrowRight} /pdca approve  or  /pdca reject`,
        innerWidth
      ));
    } else {
      lines.push(T.boxLine(
        T.colorize('No pending approvals', 'green'),
        innerWidth
      ));
    }

    lines.push(T.boxLine('', innerWidth));
  }

  // Keyboard shortcuts
  if (showShortcuts) {
    const shortcutHeader = `${T.hline(3)} Keyboard Shortcuts ${T.hline(Math.max(1, innerWidth - 25))}`;
    lines.push(T.boxLine(shortcutHeader, innerWidth));

    for (const sc of SHORTCUTS) {
      const cmdCol = sc.cmd.padEnd(20);
      lines.push(T.boxLine(`${T.bold(cmdCol)}${sc.desc}`, innerWidth));
    }

    lines.push(T.boxLine('', innerWidth));
  }

  // Emergency stop notice
  const stopNotice = `Emergency stop: ${T.bold('/control stop')}  or  ${T.bold('Ctrl+C')} ${T.dim('\u2192 mcukit saves checkpoint and halts')}`;
  lines.push(T.boxLine(T.truncate(stopNotice, innerWidth), innerWidth));

  // Close box
  lines.push(`${T.BOX.bottomLeft}${T.hline(width - 2)}${T.BOX.bottomRight}`);

  return lines.join('\n');
}

/**
 * Context render — compact automation summary.
 * @param {Object} data - { controlState, automationLevel }
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config = {}) {
  const controlState = data.controlState;

  const level = data.automationLevel != null
    ? data.automationLevel
    : (controlState && controlState.automationLevel != null
      ? controlState.automationLevel
      : 2);

  const pendingApprovals = (controlState && controlState.pendingApprovals) || [];
  const name = LEVEL_NAMES[level] || 'Unknown';

  return `Automation: L${level} ${name}, Pending: ${pendingApprovals.length}`;
}

/**
 * Backward-compatible wrapper.
 * @param {Object|null} controlState
 * @param {number|null} automationLevel
 * @param {Object} [opts]
 * @returns {string}
 */
function renderControlPanel(controlState, automationLevel, opts = {}) {
  return terminal(
    { controlState, automationLevel },
    { showShortcuts: opts.showShortcuts, showApprovals: opts.showApprovals, width: opts.width }
  );
}

module.exports = { terminal, context, renderControlPanel };
