/**
 * MCU Budget Gauge Component
 * @module lib/ui/components/budget-gauge
 *
 * Flash/RAM usage gauge for MCU domain projects.
 * Dual render: terminal (ANSI bar) / context (markdown text).
 */

const T = require('../engines/terminal');
const M = require('../engines/markdown');
const { loadUiConfig } = require('../config-loader');

/**
 * Get gauge color based on usage vs threshold.
 * @param {number} usage - Current usage percentage
 * @param {number} threshold - Warning threshold
 * @returns {string} color name
 */
function gaugeColor(usage, threshold) {
  if (usage >= threshold) return 'red';
  if (usage >= threshold * 0.9) return 'yellow';
  return 'green';
}

/**
 * Terminal render — ANSI colored budget gauges.
 * @param {Object} data
 * @param {number} [data.flashUsed] - Flash usage percentage
 * @param {number} [data.flashBudget] - Flash budget threshold
 * @param {number} [data.ramUsed] - RAM usage percentage
 * @param {number} [data.ramBudget] - RAM budget threshold
 * @param {Object} [config] - UI config (auto-loaded if omitted)
 * @returns {string}
 */
function terminal(data, config) {
  if (!data) return '';
  const cfg = config || loadUiConfig();
  const flashThreshold = (data.flashBudget || cfg.thresholds.flash.warn);
  const ramThreshold = (data.ramBudget || cfg.thresholds.ram.warn);
  const bp = T.getWidthBreakpoint();
  const barW = bp === 'narrow' ? 12 : 18;

  const parts = [];

  if (data.flashUsed != null) {
    const fc = gaugeColor(data.flashUsed, flashThreshold);
    const bar = T.progressBar(data.flashUsed, barW, fc);
    parts.push(`Flash ${data.flashUsed}%/${flashThreshold}% ${bar}`);
  }

  if (data.ramUsed != null) {
    const rc = gaugeColor(data.ramUsed, ramThreshold);
    const bar = T.progressBar(data.ramUsed, barW, rc);
    parts.push(`RAM ${data.ramUsed}%/${ramThreshold}% ${bar}`);
  }

  if (parts.length === 0) return '';
  return `  Budget  ${parts.join('  ')}`;
}

/**
 * Context render — markdown budget status.
 * @param {Object} data
 * @param {Object} [config]
 * @returns {string}
 */
function context(data, config) {
  if (!data) return '';
  const cfg = config || loadUiConfig();
  const flashThreshold = (data.flashBudget || cfg.thresholds.flash.warn);
  const ramThreshold = (data.ramBudget || cfg.thresholds.ram.warn);

  const lines = [];
  if (data.flashUsed != null) {
    const status = data.flashUsed >= flashThreshold ? 'OVER' : 'OK';
    const headroom = flashThreshold - data.flashUsed;
    lines.push(`Flash: ${data.flashUsed}%/${flashThreshold}% (${status}, ${headroom}% headroom)`);
  }
  if (data.ramUsed != null) {
    const status = data.ramUsed >= ramThreshold ? 'OVER' : 'OK';
    const headroom = ramThreshold - data.ramUsed;
    lines.push(`RAM: ${data.ramUsed}%/${ramThreshold}% (${status}, ${headroom}% headroom)`);
  }

  if (lines.length === 0) return '';
  return M.heading(3, 'MCU Budget') + '\n' + M.list(lines);
}

module.exports = { terminal, context, gaugeColor };
