/**
 * UI Config Loader
 * @module lib/ui/config-loader
 *
 * Loads UI configuration from mcukit.config.json ui section.
 * Falls back to sensible defaults when config is missing.
 */

const fs = require('fs');
const path = require('path');

const DEFAULTS = Object.freeze({
  thresholds: {
    matchRate: { good: 90, warn: 70 },
    flash: { warn: 85 },
    ram: { warn: 75 },
  },
  layout: {
    barWidths: { narrow: 16, normal: 20, wide: 36, ultrawide: 50 },
    agentColumns: { name: 18, status: 12 },
    sliderWidth: 22,
    maxTreeFiles: 10,
    maxTreeDepth: 3,
  },
  display: {
    compactMode: 'auto',
    showShortcuts: true,
    maxRecentMessages: 5,
  },
});

let _cache = null;

/**
 * Deep merge source into target (non-destructive).
 */
function deepMerge(target, source) {
  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (
      source[key] && typeof source[key] === 'object' && !Array.isArray(source[key]) &&
      target[key] && typeof target[key] === 'object' && !Array.isArray(target[key])
    ) {
      result[key] = deepMerge(target[key], source[key]);
    } else {
      result[key] = source[key];
    }
  }
  return result;
}

/**
 * Load UI config from mcukit.config.json, merged with defaults.
 * Caches result after first load.
 * @param {boolean} [forceReload] - Skip cache
 * @returns {Object} UI config
 */
function loadUiConfig(forceReload) {
  if (_cache && !forceReload) return _cache;

  let fileConfig = {};
  const configPaths = [
    path.join(process.cwd(), 'mcukit.config.json'),
    path.join(process.cwd(), '.mcukit', 'config.json'),
  ];

  for (const p of configPaths) {
    try {
      if (fs.existsSync(p)) {
        const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
        if (raw.ui) {
          fileConfig = raw.ui;
          break;
        }
      }
    } catch (_) { /* ignore parse errors, use defaults */ }
  }

  _cache = deepMerge(DEFAULTS, fileConfig);
  return _cache;
}

/**
 * Get a specific threshold value.
 * @param {string} metric - 'matchRate' | 'flash' | 'ram'
 * @returns {Object} { good?: number, warn: number }
 */
function getThreshold(metric) {
  const config = loadUiConfig();
  return config.thresholds[metric] || {};
}

/**
 * Get bar width for current terminal breakpoint.
 * @param {string} breakpoint - 'narrow' | 'normal' | 'wide' | 'ultrawide'
 * @returns {number}
 */
function getBarWidth(breakpoint) {
  const config = loadUiConfig();
  return config.layout.barWidths[breakpoint] || 20;
}

module.exports = {
  loadUiConfig,
  getThreshold,
  getBarWidth,
  DEFAULTS,
};
