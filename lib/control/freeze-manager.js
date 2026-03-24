/**
 * Freeze Manager - User-invocable file/directory freeze protection
 * @module lib/control/freeze-manager
 * @version 1.0.0
 *
 * Protects critical files from accidental modification during PDCA Do phase.
 * Domain-specific presets for MCU, MPU (Kernel/Driver/App), and WPF.
 *
 * State persisted to `.mcukit/state/freeze-list.json`.
 */

const fs = require('fs');
const path = require('path');
const { matchesPattern } = require('./scope-limiter');

const STATE_FILE = '.mcukit/state/freeze-list.json';

/**
 * Domain-specific freeze presets
 * @type {Object<string, {patterns: string[], description: string}>}
 */
const DOMAIN_PRESETS = {
  mcu: {
    patterns: [
      '*.ld',
      'startup_*.s',
      '*.ioc',
      'system_*.c',
      'stm32*_hal_conf.h',
      '**/Core/Startup/**',
    ],
    description: 'MCU critical: linker scripts, startup assembly, HAL config, CubeMX project',
  },
  mpu: {
    patterns: [
      '*.dts',
      '*.dtsi',
      '**/Kconfig',
      '**/Makefile.kernel',
      'include/linux/*.h',
      'include/dt-bindings/**',
    ],
    description: 'MPU critical: Device Tree, kernel config, kernel public headers',
  },
  wpf: {
    patterns: [
      'App.xaml',
      'App.xaml.cs',
      '*.csproj',
      'AssemblyInfo.cs',
      'app.manifest',
      '**/Properties/launchSettings.json',
    ],
    description: 'WPF critical: project config, app entry point, assembly info',
  },
};

/**
 * Load freeze state from disk
 * @returns {{frozen: Array<{pattern: string, reason: string, frozenAt: string, frozenBy: string}>}}
 */
function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return { frozen: [] };
  }
}

/**
 * Save freeze state to disk
 * @param {Object} state
 */
function saveState(state) {
  const dir = path.dirname(STATE_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
}

/**
 * Freeze file patterns with a reason
 * @param {string[]} patterns - Glob patterns to freeze
 * @param {string} reason - Why these files are frozen
 * @param {string} [frozenBy='user'] - Who froze them
 * @returns {{added: string[], alreadyFrozen: string[]}}
 */
function freeze(patterns, reason, frozenBy = 'user') {
  const state = loadState();
  const existingPatterns = new Set(state.frozen.map(f => f.pattern));
  const added = [];
  const alreadyFrozen = [];

  for (const pattern of patterns) {
    if (existingPatterns.has(pattern)) {
      alreadyFrozen.push(pattern);
    } else {
      state.frozen.push({
        pattern,
        reason: reason || 'User-requested freeze',
        frozenAt: new Date().toISOString(),
        frozenBy,
      });
      added.push(pattern);
    }
  }

  saveState(state);
  return { added, alreadyFrozen };
}

/**
 * Freeze a domain preset
 * @param {string} domain - 'mcu', 'mpu', or 'wpf'
 * @returns {{added: string[], alreadyFrozen: string[], preset: Object}|null}
 */
function freezePreset(domain) {
  const preset = DOMAIN_PRESETS[domain.toLowerCase()];
  if (!preset) return null;

  const result = freeze(preset.patterns, preset.description, `preset:${domain}`);
  return { ...result, preset };
}

/**
 * Unfreeze specific patterns
 * @param {string[]} patterns - Patterns to unfreeze (exact match)
 * @returns {{removed: string[], notFound: string[]}}
 */
function unfreeze(patterns) {
  const state = loadState();
  const removed = [];
  const notFound = [];

  for (const pattern of patterns) {
    const idx = state.frozen.findIndex(f => f.pattern === pattern);
    if (idx >= 0) {
      state.frozen.splice(idx, 1);
      removed.push(pattern);
    } else {
      notFound.push(pattern);
    }
  }

  saveState(state);
  return { removed, notFound };
}

/**
 * Unfreeze all patterns
 * @returns {number} Number of patterns unfrozen
 */
function unfreezeAll() {
  const state = loadState();
  const count = state.frozen.length;
  state.frozen = [];
  saveState(state);
  return count;
}

/**
 * List all frozen patterns
 * @returns {Array<{pattern: string, reason: string, frozenAt: string, frozenBy: string}>}
 */
function listFrozen() {
  return loadState().frozen;
}

/**
 * Check if a file path is frozen
 * @param {string} filePath - File path to check (relative or absolute)
 * @returns {{frozen: boolean, matchedPattern: string|null, reason: string|null}}
 */
function isFrozen(filePath) {
  const state = loadState();
  if (state.frozen.length === 0) {
    return { frozen: false, matchedPattern: null, reason: null };
  }

  const patterns = state.frozen.map(f => f.pattern);
  if (matchesPattern(filePath, patterns)) {
    const matched = state.frozen.find(f => matchesPattern(filePath, [f.pattern]));
    return {
      frozen: true,
      matchedPattern: matched ? matched.pattern : null,
      reason: matched ? matched.reason : null,
    };
  }

  return { frozen: false, matchedPattern: null, reason: null };
}

/**
 * Get available domain presets
 * @returns {Object<string, {patterns: string[], description: string}>}
 */
function getPresets() {
  return { ...DOMAIN_PRESETS };
}

/**
 * Get freeze status summary for /control status integration
 * @returns {{active: boolean, count: number, presets: string[]}}
 */
function getStatus() {
  const state = loadState();
  const presets = [...new Set(
    state.frozen
      .filter(f => f.frozenBy && f.frozenBy.startsWith('preset:'))
      .map(f => f.frozenBy.replace('preset:', ''))
  )];

  return {
    active: state.frozen.length > 0,
    count: state.frozen.length,
    presets,
  };
}

module.exports = {
  DOMAIN_PRESETS,
  freeze,
  freezePreset,
  unfreeze,
  unfreezeAll,
  listFrozen,
  isFrozen,
  getPresets,
  getStatus,
};
