#!/usr/bin/env node
/**
 * Multi-Level Context Hierarchy (FR-01)
 * Manages 4-level context: Plugin → User → Project → Session
 *
 * @version 1.6.0
 * @module lib/context-hierarchy
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// Lazy require to avoid circular dependency (restored after c389514)
let _platform = null;
function getPlatform() {
  if (!_platform) { _platform = require('./core/platform'); }
  return _platform;
}

let _debug = null;
function getDebug() {
  if (!_debug) { _debug = require('./core/debug'); }
  return _debug;
}

// Context level priorities (higher = more specific)
const LEVEL_PRIORITY = {
  plugin: 1,
  user: 2,
  project: 3,
  session: 4
};

// Session context (in-memory)
let _sessionContext = {};

// Local cache for context hierarchy
const _hierarchyCache = {
  data: null,
  timestamp: 0,
  ttl: 5000  // 5 seconds
};

/**
 * Get user config directory (Claude Code only)
 * @returns {string} User config path
 */
function getUserConfigDir() {
  const homeDir = os.homedir();
  return path.join(homeDir, '.claude', 'rkit');
}

/**
 * Load context from a specific level
 * @param {'plugin' | 'user' | 'project' | 'session'} level
 * @returns {Object|null} ContextLevel object or null
 */
function loadContextLevel(level) {
  const now = new Date().toISOString();

  switch (level) {
    case 'plugin': {
      const pluginConfigPath = path.join(getPlatform().PLUGIN_ROOT, 'rkit.config.json');
      if (fs.existsSync(pluginConfigPath)) {
        try {
          return {
            level: 'plugin',
            priority: LEVEL_PRIORITY.plugin,
            source: pluginConfigPath,
            data: JSON.parse(fs.readFileSync(pluginConfigPath, 'utf8')),
            loadedAt: now
          };
        } catch (e) {
          getDebug().debugLog('ContextHierarchy', 'Failed to load plugin config', { error: e.message });
        }
      }
      return null;
    }

    case 'user': {
      const userConfigPath = path.join(getUserConfigDir(), 'user-config.json');
      if (fs.existsSync(userConfigPath)) {
        try {
          return {
            level: 'user',
            priority: LEVEL_PRIORITY.user,
            source: userConfigPath,
            data: JSON.parse(fs.readFileSync(userConfigPath, 'utf8')),
            loadedAt: now
          };
        } catch (e) {
          getDebug().debugLog('ContextHierarchy', 'Failed to load user config', { error: e.message });
        }
      }
      return null;
    }

    case 'project': {
      const projectConfigPath = path.join(getPlatform().PROJECT_DIR, 'rkit.config.json');
      if (fs.existsSync(projectConfigPath)) {
        try {
          return {
            level: 'project',
            priority: LEVEL_PRIORITY.project,
            source: projectConfigPath,
            data: JSON.parse(fs.readFileSync(projectConfigPath, 'utf8')),
            loadedAt: now
          };
        } catch (e) {
          getDebug().debugLog('ContextHierarchy', 'Failed to load project config', { error: e.message });
        }
      }
      return null;
    }

    case 'session': {
      return {
        level: 'session',
        priority: LEVEL_PRIORITY.session,
        source: 'memory',
        data: _sessionContext,
        loadedAt: now
      };
    }

    default:
      return null;
  }
}

/**
 * Get full context hierarchy with merging
 * @param {boolean} forceRefresh - Skip cache
 * @returns {Object} ContextHierarchy object
 */
function getContextHierarchy(forceRefresh = false) {
  // Check local cache
  if (!forceRefresh && _hierarchyCache.data) {
    if (Date.now() - _hierarchyCache.timestamp < _hierarchyCache.ttl) {
      return _hierarchyCache.data;
    }
  }

  const levels = [];
  const conflicts = [];

  // Load all levels
  for (const levelName of ['plugin', 'user', 'project', 'session']) {
    const level = loadContextLevel(levelName);
    if (level) {
      levels.push(level);
    }
  }

  // Sort by priority (ascending, so later ones override)
  levels.sort((a, b) => a.priority - b.priority);

  // Merge with conflict detection
  const merged = {};
  const keyHistory = {};  // Track which level set each key

  for (const level of levels) {
    for (const [key, value] of Object.entries(level.data || {})) {
      if (key in merged && JSON.stringify(merged[key]) !== JSON.stringify(value)) {
        // Conflict detected
        if (!keyHistory[key]) {
          keyHistory[key] = [];
        }
        keyHistory[key].push({ level: level.level, value: merged[key] });
        conflicts.push({
          key,
          values: [...keyHistory[key], { level: level.level, value }],
          resolved: value  // Higher priority wins
        });
      }
      merged[key] = value;
      keyHistory[key] = keyHistory[key] || [];
      keyHistory[key].push({ level: level.level, value });
    }
  }

  const result = { levels, merged, conflicts };

  // Cache result
  _hierarchyCache.data = result;
  _hierarchyCache.timestamp = Date.now();

  getDebug().debugLog('ContextHierarchy', 'Hierarchy loaded', {
    levelCount: levels.length,
    conflictCount: conflicts.length
  });

  return result;
}

/**
 * Get merged config value with hierarchy
 * @param {string} keyPath - Dot-separated path (e.g., "pdca.matchRateThreshold")
 * @param {*} defaultValue - Default if not found
 * @returns {*}
 */
function getHierarchicalConfig(keyPath, defaultValue = null) {
  const hierarchy = getContextHierarchy();
  const keys = keyPath.split('.');
  let value = hierarchy.merged;

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      return defaultValue;
    }
  }

  return value ?? defaultValue;
}

/**
 * Set session-level context (in-memory)
 * @param {string} key - Config key
 * @param {*} value - Value to set
 */
function setSessionContext(key, value) {
  _sessionContext[key] = value;
  // Invalidate cache
  _hierarchyCache.data = null;
  getDebug().debugLog('ContextHierarchy', 'Session context set', { key });
}

/**
 * Get session-level context
 * @param {string} key - Config key
 * @param {*} defaultValue - Default if not found
 * @returns {*}
 */
function getSessionContext(key, defaultValue = null) {
  return key in _sessionContext ? _sessionContext[key] : defaultValue;
}

/**
 * Clear session context
 */
function clearSessionContext() {
  _sessionContext = {};
  _hierarchyCache.data = null;
  getDebug().debugLog('ContextHierarchy', 'Session context cleared');
}

/**
 * Get all session context
 * @returns {Object}
 */
function getAllSessionContext() {
  return { ..._sessionContext };
}

/**
 * Invalidate hierarchy cache
 */
function invalidateCache() {
  _hierarchyCache.data = null;
}

module.exports = {
  getContextHierarchy,
  getHierarchicalConfig,
  loadContextLevel,
  setSessionContext,
  getSessionContext,
  clearSessionContext,
  getAllSessionContext,
  getUserConfigDir,
  invalidateCache,
  LEVEL_PRIORITY
};
