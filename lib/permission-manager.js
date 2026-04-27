#!/usr/bin/env node
/**
 * Permission Hierarchy Manager (FR-05)
 * Implements deny → ask → allow permission chain
 *
 * @version 1.6.0
 * @module lib/permission-manager
 */

// Import from other modules (lazy to avoid circular dependency).
// NOTE (bkit-gstack-sync-v2 / Cycle 1, C5): context-hierarchy.js was removed
// in bkit v2.1.0 S1 cleanup. We migrate to a lazy `core` barrel for getConfig
// + debugLog (same pattern as lib/import-resolver.js, see C4 commit).
//
// rkit branch: unlike bkit HEAD which uses DEFAULT_PERMISSIONS only, rkit
// merges DEFAULT_PERMISSIONS with `rkit.config.json#permissions` so MCU/MPU
// safety policies (e.g. `Bash(dd if=*)` ask) survive the migration.
let _core = null;
function getCore() {
  if (!_core) {
    try { _core = require('./core'); } catch (_) { _core = null; }
  }
  return _core;
}

function debugLog(message, meta) {
  const core = getCore();
  if (core && core.debugLog) {
    core.debugLog('Permission', message, meta);
  }
}

function getConfiguredPermissions() {
  const core = getCore();
  const configured = core && core.getConfig ? core.getConfig('permissions', {}) : {};
  return { ...DEFAULT_PERMISSIONS, ...(configured || {}) };
}

/**
 * Permission levels
 */
const PERMISSION_LEVELS = {
  deny: 0,
  ask: 1,
  allow: 2
};

/**
 * Default permissions (when no config is provided)
 */
const DEFAULT_PERMISSIONS = {
  Write: 'allow',
  Edit: 'allow',
  Read: 'allow',
  Bash: 'allow',
  'Bash(rm -rf*)': 'deny',
  'Bash(rm -r*)': 'ask',
  'Bash(git push --force*)': 'deny',
  'Bash(git reset --hard*)': 'ask'
};

/**
 * Check permission for a tool
 * @param {string} toolName - Tool name (e.g., "Write", "Bash")
 * @param {string} toolInput - Tool input/command for pattern matching
 * @returns {'deny' | 'ask' | 'allow'}
 */
function checkPermission(toolName, toolInput = '') {
  const permissions = getConfiguredPermissions();

  // Check specific pattern first (most restrictive wins)
  const patterns = Object.keys(permissions).filter(p =>
    p.startsWith(`${toolName}(`) && p.endsWith(')')
  );

  // Sort patterns by specificity (longer = more specific)
  patterns.sort((a, b) => b.length - a.length);

  for (const pattern of patterns) {
    // Extract pattern inside parentheses
    const patternContent = pattern.slice(toolName.length + 1, -1);

    // Convert glob-like pattern to regex
    const regexStr = patternContent
      .replace(/[.+^${}()|[\]\\]/g, '\\$&')  // Escape special chars except *
      .replace(/\*/g, '.*');  // Convert * to .*

    const matcher = new RegExp(`^${regexStr}$`, 'i');

    if (matcher.test(toolInput)) {
      debugLog('Pattern matched', { pattern, toolInput, permission: permissions[pattern] });
      return permissions[pattern];
    }
  }

  // Check tool-level permission
  if (toolName in permissions) {
    return permissions[toolName];
  }

  // Default: allow
  return 'allow';
}

/**
 * Get all permissions for a tool
 * @param {string} toolName - Tool name
 * @returns {Object} Permission rules for the tool
 */
function getToolPermissions(toolName) {
  const permissions = getConfiguredPermissions();
  const toolPermissions = {};

  for (const [key, value] of Object.entries(permissions)) {
    if (key === toolName || key.startsWith(`${toolName}(`)) {
      toolPermissions[key] = value;
    }
  }

  return toolPermissions;
}

/**
 * Validate permission action
 * @param {string} permission - Permission string
 * @returns {boolean}
 */
function isValidPermission(permission) {
  return permission in PERMISSION_LEVELS;
}

/**
 * Get permission level as number for comparison
 * @param {string} permission - Permission string
 * @returns {number}
 */
function getPermissionLevel(permission) {
  return PERMISSION_LEVELS[permission] ?? PERMISSION_LEVELS.allow;
}

/**
 * Check if permission A is more restrictive than permission B
 * @param {string} permA - First permission
 * @param {string} permB - Second permission
 * @returns {boolean}
 */
function isMoreRestrictive(permA, permB) {
  return getPermissionLevel(permA) < getPermissionLevel(permB);
}

/**
 * Get all configured permissions
 * @returns {Object}
 */
function getAllPermissions() {
  return getConfiguredPermissions();
}

/**
 * Check if tool action should be blocked
 * @param {string} toolName - Tool name
 * @param {string} toolInput - Tool input
 * @returns {{ blocked: boolean, permission: string, reason: string }}
 */
function shouldBlock(toolName, toolInput = '') {
  const permission = checkPermission(toolName, toolInput);

  if (permission === 'deny') {
    return {
      blocked: true,
      permission,
      reason: `${toolName} action is denied by permission policy`
    };
  }

  return {
    blocked: false,
    permission,
    reason: null
  };
}

/**
 * Check if tool action requires confirmation
 * @param {string} toolName - Tool name
 * @param {string} toolInput - Tool input
 * @returns {{ requiresConfirmation: boolean, permission: string }}
 */
function requiresConfirmation(toolName, toolInput = '') {
  const permission = checkPermission(toolName, toolInput);

  return {
    requiresConfirmation: permission === 'ask',
    permission
  };
}

module.exports = {
  checkPermission,
  getToolPermissions,
  isValidPermission,
  getPermissionLevel,
  isMoreRestrictive,
  getAllPermissions,
  shouldBlock,
  requiresConfirmation,
  PERMISSION_LEVELS,
  DEFAULT_PERMISSIONS
};
