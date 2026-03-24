/**
 * Guard Mode - Combined safety mode orchestrating freeze + destructive detection + automation cap
 * @module lib/control/guard-mode
 * @version 1.0.0
 *
 * Inspired by gstack's /guard (careful + freeze).
 * When active: freezes domain preset, caps automation at L2, enhances Bash scrutiny.
 *
 * State persisted to `.mcukit/state/guard-mode.json`.
 */

const fs = require('fs');
const path = require('path');

const STATE_FILE = '.mcukit/state/guard-mode.json';

/**
 * Load guard mode state
 * @returns {{active: boolean, activatedAt: string|null, domain: string|null, previousLevel: number|null, reason: string|null}}
 */
function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return { active: false, activatedAt: null, domain: null, previousLevel: null, reason: null };
  }
}

/**
 * Save guard mode state
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
 * Activate guard mode
 * @param {string} domain - 'mcu', 'mpu', or 'wpf' (for freeze preset)
 * @param {number} currentLevel - Current automation level (to restore later)
 * @param {string} [reason] - Why guard mode is being activated
 * @returns {{activated: boolean, frozenCount: number, cappedLevel: number}}
 */
function activate(domain, currentLevel, reason) {
  const freezeManager = require('./freeze-manager');

  // Apply domain freeze preset
  const freezeResult = freezeManager.freezePreset(domain);
  const frozenCount = freezeResult ? freezeResult.added.length + (freezeResult.alreadyFrozen ? freezeResult.alreadyFrozen.length : 0) : 0;

  // Save state (previous level for restore)
  const state = {
    active: true,
    activatedAt: new Date().toISOString(),
    domain,
    previousLevel: currentLevel,
    reason: reason || `Guard mode activated for ${domain} domain`,
  };
  saveState(state);

  return {
    activated: true,
    frozenCount,
    cappedLevel: Math.min(currentLevel, 2),
  };
}

/**
 * Deactivate guard mode
 * @returns {{deactivated: boolean, previousLevel: number|null, unfrozenCount: number}}
 */
function deactivate() {
  const freezeManager = require('./freeze-manager');
  const state = loadState();

  if (!state.active) {
    return { deactivated: false, previousLevel: null, unfrozenCount: 0 };
  }

  // Unfreeze all (guard-applied freezes)
  const unfrozenCount = freezeManager.unfreezeAll();

  // Restore previous state
  const previousLevel = state.previousLevel;
  saveState({ active: false, activatedAt: null, domain: null, previousLevel: null, reason: null });

  return { deactivated: true, previousLevel, unfrozenCount };
}

/**
 * Check if guard mode is active
 * @returns {boolean}
 */
function isActive() {
  return loadState().active;
}

/**
 * Get guard mode status
 * @returns {{active: boolean, activatedAt: string|null, domain: string|null, previousLevel: number|null, reason: string|null}}
 */
function getStatus() {
  return loadState();
}

/**
 * Check if an automation level is allowed under guard mode
 * @param {number} requestedLevel - Requested automation level
 * @returns {{allowed: boolean, cappedLevel: number, reason: string|null}}
 */
function checkLevelCap(requestedLevel) {
  const state = loadState();
  if (!state.active) {
    return { allowed: true, cappedLevel: requestedLevel, reason: null };
  }

  if (requestedLevel > 2) {
    return {
      allowed: false,
      cappedLevel: 2,
      reason: `Guard mode caps automation at L2. Requested L${requestedLevel} denied. Deactivate guard mode first with /guard off.`,
    };
  }

  return { allowed: true, cappedLevel: requestedLevel, reason: null };
}

module.exports = {
  activate,
  deactivate,
  isActive,
  getStatus,
  checkLevelCap,
};
