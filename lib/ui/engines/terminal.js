/**
 * Terminal Rendering Engine — ANSI + Unicode Box Drawing
 * @module lib/ui/engines/terminal
 *
 * Renders styled terminal output for stderr display.
 * Wraps ansi.js utilities with component-oriented API.
 */

const ansi = require('../ansi');

/**
 * Render a bordered box with title.
 * @param {string} title
 * @param {string[]} lines - Content lines (may include ANSI)
 * @param {number} [width] - Box width (auto if omitted)
 * @returns {string}
 */
function box(title, lines, width) {
  const w = width || ansi.getTermWidth();
  const innerWidth = w - 6;
  const titleStr = title ? ` ${title} ` : '';
  const topLine = ansi.BOX.topLeft + ansi.BOX.horizontal
    + ansi.BOX.horizontal + ansi.BOX.horizontal + titleStr
    + ansi.hline(Math.max(0, w - 5 - ansi.stripAnsi(titleStr).length))
    + ansi.BOX.topRight;
  const bottomLine = ansi.BOX.bottomLeft
    + ansi.hline(w - 2)
    + ansi.BOX.bottomRight;
  const bodyLines = lines.map(l => ansi.boxLine(l, innerWidth));
  return [topLine, ...bodyLines, bottomLine].join('\n');
}

/**
 * Render a progress bar with filled/empty blocks.
 * @param {number} percent - 0~100
 * @param {number} width - Bar character width
 * @param {string} [color] - Color for filled portion
 * @returns {string}
 */
function progressBar(percent, width, color) {
  const p = Math.max(0, Math.min(100, percent || 0));
  const filled = Math.round((p / 100) * width);
  const empty = width - filled;
  const filledStr = '\u2588'.repeat(filled);
  const emptyStr = '\u2591'.repeat(empty);
  const bar = color
    ? ansi.colorize(filledStr, color) + ansi.dim(emptyStr)
    : filledStr + emptyStr;
  return bar;
}

/**
 * Get status symbol with color.
 * @param {string} status - completed|running|pending|failed|approval_waiting
 * @returns {string}
 */
function statusSymbol(status) {
  const map = {
    completed: { sym: ansi.SYMBOLS.done, color: 'green' },
    running:   { sym: ansi.SYMBOLS.running, color: 'cyan' },
    pending:   { sym: ansi.SYMBOLS.pending, color: 'gray' },
    failed:    { sym: ansi.SYMBOLS.failed, color: 'red' },
    approval_waiting: { sym: ansi.SYMBOLS.waiting, color: 'yellow' },
    idle:      { sym: ansi.SYMBOLS.idle, color: 'gray' },
    spawning:  { sym: ansi.SYMBOLS.spawning, color: 'yellow' },
  };
  const entry = map[status] || map.pending;
  return ansi.colorize(entry.sym, entry.color);
}

/**
 * Get color for a match rate value based on thresholds.
 * @param {number} rate
 * @param {Object} [thresholds] - { good: 90, warn: 70 }
 * @returns {string} color name
 */
function rateColor(rate, thresholds) {
  const t = thresholds || { good: 90, warn: 70 };
  if (rate >= t.good) return 'green';
  if (rate >= t.warn) return 'yellow';
  return 'red';
}

module.exports = {
  box,
  progressBar,
  statusSymbol,
  rateColor,
  // Re-export ansi utilities for convenience
  colorize: ansi.colorize,
  bold: ansi.bold,
  dim: ansi.dim,
  hline: ansi.hline,
  stripAnsi: ansi.stripAnsi,
  boxLine: ansi.boxLine,
  truncate: ansi.truncate,
  getTermWidth: ansi.getTermWidth,
  getWidthBreakpoint: ansi.getWidthBreakpoint,
  isColorDisabled: ansi.isColorDisabled,
  BOX: ansi.BOX,
  SYMBOLS: ansi.SYMBOLS,
  COLORS: ansi.COLORS,
};
