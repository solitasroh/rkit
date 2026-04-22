#!/usr/bin/env node
/**
 * C++ Static Analysis PostToolUse Hook — Node bridge to Python.
 *
 * Invoked from `unified-write-post.js::handleCppStaticAnalysis(input)`.
 * Spawns `hooks/cpp-post-edit.py` as child process with stdin JSON.
 *
 * rkit policy: non-blocking. Never outputs `decision: block`.
 * Python hook stderr is relayed to this process stderr (Claude sees it).
 *
 * Timeout: 10 seconds (design spec §4.7).
 */

const path = require('path');
const { execFileSync } = require('child_process');

const CPP_EXTENSIONS = new Set([
  '.c', '.cpp', '.cc', '.cxx',
  '.h', '.hpp',
]);

const HOOK_TIMEOUT_MS = 10000;

function getDebug() { return require('../lib/core/debug'); }

/**
 * Resolve plugin root. Prefer CLAUDE_PLUGIN_ROOT env var, fall back to relative.
 * @returns {string}
 */
function resolvePluginRoot() {
  return process.env.CLAUDE_PLUGIN_ROOT || path.resolve(__dirname, '..');
}

/**
 * PostToolUse entry point. Called from unified-write-post.js / code-quality-hook.js.
 * @param {Object} input - Claude Code hook input (tool_input.file_path available)
 * @returns {boolean} true if processed, false if skipped
 */
function handleCppStaticAnalysis(input) {
  const filePath = input?.tool_input?.file_path;
  if (!filePath) return false;

  const ext = path.extname(filePath).toLowerCase();
  if (!CPP_EXTENSIONS.has(ext)) return false;

  const pluginRoot = resolvePluginRoot();
  const hookPath = path.join(pluginRoot, 'hooks', 'cpp-post-edit.py');
  const { debugLog } = getDebug();

  try {
    execFileSync('python', [hookPath], {
      input: JSON.stringify(input),
      encoding: 'utf-8',
      timeout: HOOK_TIMEOUT_MS,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
      },
      stdio: ['pipe', 'pipe', 'inherit'], // stderr -> parent stderr (Claude sees)
    });
  } catch (e) {
    // Python hook is non-blocking by policy — any error is silent degradation.
    // Log to rkit debug, do not propagate.
    debugLog('CppStaticAnalysis', 'python hook failed', {
      file: filePath,
      error: e.message,
      code: e.code,
    });
  }

  return true;
}

module.exports = { handleCppStaticAnalysis, CPP_EXTENSIONS };
