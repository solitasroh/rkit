/**
 * Architecture Lock - Freeze architectural decisions from Design documents
 * @module lib/control/arch-lock
 * @version 1.0.0
 *
 * Locks architecture decisions (layers, interfaces, memory maps) defined in Design docs.
 * Prevents scope creep by enforcing boundaries during Do phase.
 *
 * State persisted to `.mcukit/state/arch-lock.json`.
 */

const fs = require('fs');
const path = require('path');

const STATE_FILE = '.mcukit/state/arch-lock.json';

/**
 * @typedef {Object} ArchDecision
 * @property {string} id - Decision identifier (e.g., 'AD-001')
 * @property {string} title - Decision title
 * @property {string} category - 'layer'|'interface'|'memory'|'pattern'|'dependency'
 * @property {string} description - What was decided
 * @property {string[]} affectedPaths - File paths/patterns affected by this decision
 * @property {string} lockedAt - ISO timestamp
 * @property {string} lockedBy - Who locked it
 * @property {string} designDoc - Source design document path
 */

/**
 * Load arch-lock state from disk
 * @returns {{locked: boolean, decisions: ArchDecision[], lockedAt: string|null, domain: string|null, feature: string|null}}
 */
function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return { locked: false, decisions: [], lockedAt: null, domain: null, feature: null };
  }
}

/**
 * Save arch-lock state to disk
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
 * Lock architecture decisions
 * @param {string} feature - Feature name
 * @param {string} domain - 'mcu'|'mpu'|'wpf'
 * @param {ArchDecision[]} decisions - Architecture decisions to lock
 * @param {string} designDoc - Path to design document
 * @returns {{locked: boolean, count: number}}
 */
function lock(feature, domain, decisions, designDoc) {
  const state = loadState();

  const newDecisions = decisions.map((d, i) => ({
    id: d.id || `AD-${String(state.decisions.length + i + 1).padStart(3, '0')}`,
    title: d.title,
    category: d.category || 'pattern',
    description: d.description,
    affectedPaths: d.affectedPaths || [],
    lockedAt: new Date().toISOString(),
    lockedBy: d.lockedBy || 'user',
    designDoc: designDoc || d.designDoc || '',
  }));

  state.locked = true;
  state.lockedAt = new Date().toISOString();
  state.domain = domain;
  state.feature = feature;
  state.decisions = [...state.decisions, ...newDecisions];

  saveState(state);

  return { locked: true, count: newDecisions.length };
}

/**
 * Unlock all architecture decisions
 * @returns {{unlocked: boolean, removedCount: number}}
 */
function unlock() {
  const state = loadState();
  const count = state.decisions.length;

  saveState({ locked: false, decisions: [], lockedAt: null, domain: null, feature: null });

  return { unlocked: true, removedCount: count };
}

/**
 * Unlock specific decisions by ID
 * @param {string[]} ids - Decision IDs to unlock
 * @returns {{removed: string[], notFound: string[]}}
 */
function unlockDecisions(ids) {
  const state = loadState();
  const removed = [];
  const notFound = [];

  for (const id of ids) {
    const idx = state.decisions.findIndex(d => d.id === id);
    if (idx >= 0) {
      state.decisions.splice(idx, 1);
      removed.push(id);
    } else {
      notFound.push(id);
    }
  }

  if (state.decisions.length === 0) {
    state.locked = false;
  }

  saveState(state);
  return { removed, notFound };
}

/**
 * Check if a file path violates any locked architecture decision
 * @param {string} filePath - File path to check
 * @returns {{violation: boolean, decisions: ArchDecision[]}}
 */
function checkViolation(filePath) {
  const state = loadState();
  if (!state.locked || state.decisions.length === 0) {
    return { violation: false, decisions: [] };
  }

  const violated = state.decisions.filter(d => {
    if (!d.affectedPaths || d.affectedPaths.length === 0) return false;
    try {
      const { matchesPattern } = require('./scope-limiter');
      return matchesPattern(filePath, d.affectedPaths);
    } catch {
      // Fallback: simple string inclusion check
      return d.affectedPaths.some(p => filePath.includes(p.replace(/\*/g, '')));
    }
  });

  return { violation: violated.length > 0, decisions: violated };
}

/**
 * Check if arch-lock is active
 * @returns {boolean}
 */
function isLocked() {
  return loadState().locked;
}

/**
 * Get arch-lock status summary
 * @returns {{locked: boolean, count: number, domain: string|null, feature: string|null, categories: Object<string, number>}}
 */
function getStatus() {
  const state = loadState();
  const categories = {};
  for (const d of state.decisions) {
    categories[d.category] = (categories[d.category] || 0) + 1;
  }

  return {
    locked: state.locked,
    count: state.decisions.length,
    domain: state.domain,
    feature: state.feature,
    categories,
  };
}

/**
 * List all locked decisions
 * @returns {ArchDecision[]}
 */
function listDecisions() {
  return loadState().decisions;
}

/**
 * Domain-specific architecture decision templates
 * @type {Object<string, Array<{title: string, category: string, description: string}>>}
 */
const DOMAIN_TEMPLATES = {
  mcu: [
    { title: 'Software Layer Structure', category: 'layer', description: 'Application → Driver → HAL layering. No direct register access from application layer.' },
    { title: 'Memory Map', category: 'memory', description: 'Flash/RAM section allocation as defined in linker script.' },
    { title: 'Interrupt Priority Map', category: 'interface', description: 'ISR priority assignments. Higher priority = lower latency requirement.' },
    { title: 'Peripheral Allocation', category: 'interface', description: 'Which peripherals are assigned to which functions.' },
  ],
  mpu: [
    { title: 'Software Stack', category: 'layer', description: 'Kernel → Driver → Library → Application stack. Clear user/kernel boundary.' },
    { title: 'Driver Interface', category: 'interface', description: 'ioctl/sysfs/netlink interface selection per driver.' },
    { title: 'DT Node Structure', category: 'pattern', description: 'Device Tree node hierarchy and binding contracts.' },
    { title: 'IPC Architecture', category: 'interface', description: 'Inter-process communication method (socket/shared memory/D-Bus).' },
  ],
  wpf: [
    { title: 'MVVM Structure', category: 'layer', description: 'View → ViewModel → Model. ViewModel must not reference View types.' },
    { title: 'DI Container', category: 'pattern', description: 'Service registration and lifetime management (Singleton/Transient/Scoped).' },
    { title: 'Navigation Pattern', category: 'pattern', description: 'Page/Window navigation strategy and parameter passing.' },
    { title: 'Communication Architecture', category: 'interface', description: 'Serial/network communication layer isolation from business logic.' },
  ],
};

module.exports = {
  DOMAIN_TEMPLATES,
  lock,
  unlock,
  unlockDecisions,
  checkViolation,
  isLocked,
  getStatus,
  listDecisions,
};
