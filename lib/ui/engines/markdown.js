/**
 * Markdown Rendering Engine — Plain text for LLM context
 * @module lib/ui/engines/markdown
 *
 * Renders clean markdown/plain text for additionalContext.
 * No ANSI escape codes, no Box Drawing — optimized for LLM consumption.
 */

/**
 * Render a markdown table from headers and rows.
 * @param {string[]} headers
 * @param {string[][]} rows
 * @returns {string}
 */
function table(headers, rows) {
  if (!headers || headers.length === 0) return '';
  const sep = headers.map(() => '---');
  const lines = [
    '| ' + headers.join(' | ') + ' |',
    '| ' + sep.join(' | ') + ' |',
  ];
  for (const row of rows) {
    const cells = headers.map((_, i) => (row[i] != null ? String(row[i]) : ''));
    lines.push('| ' + cells.join(' | ') + ' |');
  }
  return lines.join('\n');
}

/**
 * Render a markdown heading.
 * @param {number} level - 1~6
 * @param {string} text
 * @returns {string}
 */
function heading(level, text) {
  return '#'.repeat(Math.min(6, Math.max(1, level))) + ' ' + text;
}

/**
 * Render a bullet list.
 * @param {string[]} items
 * @returns {string}
 */
function list(items) {
  return (items || []).map(item => `- ${item}`).join('\n');
}

/**
 * Render bold text in markdown.
 * @param {string} text
 * @returns {string}
 */
function bold(text) {
  return `**${text}**`;
}

/**
 * Render a status line (plain text).
 * @param {string} phase
 * @param {string} state - Done|In Progress|Pending
 * @returns {string}
 */
function status(phase, state) {
  return `${phase}: ${state}`;
}

/**
 * Render progress as text fraction.
 * @param {number} percent
 * @param {number} [completed]
 * @param {number} [total]
 * @returns {string}
 */
function progressText(percent, completed, total) {
  const p = Math.round(percent || 0);
  if (completed != null && total != null) {
    return `${p}% (${completed}/${total})`;
  }
  return `${p}%`;
}

/**
 * Render sparkline trend as text.
 * @param {number[]} values
 * @returns {string}
 */
function sparkline(values) {
  if (!values || values.length === 0) return '';
  const blocks = '\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const chars = values.map(v => {
    const idx = Math.round(((v - min) / range) * 7);
    return blocks[idx];
  });
  const first = values[0];
  const last = values[values.length - 1];
  const trend = last > first ? 'improving' : last < first ? 'declining' : 'stable';
  return `${chars.join('')}  ${values.join('% → ')}%  (${trend})`;
}

/**
 * Render a horizontal separator.
 * @returns {string}
 */
function separator() {
  return '---';
}

/**
 * Render key-value pairs as a compact list.
 * @param {Object} kvPairs - { key: value, ... }
 * @returns {string}
 */
function keyValue(kvPairs) {
  return Object.entries(kvPairs || {})
    .map(([k, v]) => `- ${bold(k)}: ${v}`)
    .join('\n');
}

module.exports = {
  table,
  heading,
  list,
  bold,
  status,
  progressText,
  sparkline,
  separator,
  keyValue,
};
