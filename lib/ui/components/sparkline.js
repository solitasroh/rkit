/**
 * Sparkline Trend Component
 * @module lib/ui/components/sparkline
 *
 * Unicode block element sparkline for iteration trends.
 * Dual render: terminal (ANSI color) / context (markdown text).
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');

const BLOCKS = '\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588';

/**
 * Build sparkline characters from values.
 * @param {number[]} values
 * @returns {string} sparkline characters
 */
function buildSparkChars(values) {
  if (!values || values.length === 0) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values.map(v => {
    const idx = Math.round(((v - min) / range) * 7);
    return BLOCKS[idx];
  }).join('');
}

/**
 * Determine trend direction.
 * @param {number[]} values
 * @returns {'improving'|'declining'|'stable'}
 */
function trendDirection(values) {
  if (!values || values.length < 2) return 'stable';
  const first = values[0];
  const last = values[values.length - 1];
  if (last > first) return 'improving';
  if (last < first) return 'declining';
  return 'stable';
}

const TREND_ARROWS = { improving: '\u2191', declining: '\u2193', stable: '\u2192' };
const TREND_COLORS = { improving: 'green', declining: 'red', stable: 'yellow' };

/**
 * Terminal render — ANSI colored sparkline.
 * @param {number[]} values - Array of numeric values (e.g., match rates)
 * @param {Object} [opts]
 * @param {string} [opts.label] - Label prefix (e.g., "Match Rate")
 * @returns {string}
 */
function terminal(values, opts) {
  if (!values || values.length === 0) return '';
  const label = (opts && opts.label) || 'Trend';
  const chars = buildSparkChars(values);
  const trend = trendDirection(values);
  const arrow = T.colorize(TREND_ARROWS[trend], TREND_COLORS[trend]);
  const first = values[0];
  const last = values[values.length - 1];
  return `${label}: ${chars}  ${first}%${T.dim('\u2192')}${last}%  ${arrow}`;
}

/**
 * Context render — plain text trend.
 * @param {number[]} values
 * @param {Object} [opts]
 * @param {string} [opts.label]
 * @returns {string}
 */
function context(values, opts) {
  if (!values || values.length === 0) return '';
  const label = (opts && opts.label) || 'Trend';
  const trend = trendDirection(values);
  return `${label}: ${values.join('% → ')}% (${trend})`;
}

module.exports = { terminal, context, buildSparkChars, trendDirection };
