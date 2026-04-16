#!/usr/bin/env node
/**
 * Code Quality PostToolUse Hook — 3-Stage Pipeline
 * @version 0.1.0
 *
 * Runs after Write/Edit on code files.
 * Stage 1: Linter (external tool, optional)
 * Stage 2: Structure Check (built-in metrics)
 * Stage 3: Metrics Storage
 *
 * Can be called standalone (Edit matcher) or via unified-write-post.js
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Lazy requires for rkit modules
function getIo() { return require('../lib/core/io'); }
function getDebug() { return require('../lib/core/debug'); }
function getMetrics() { return require('../lib/code-quality/metrics-collector'); }

/** Code file extensions to check */
const CODE_EXTENSIONS = new Set([
  '.c', '.cpp', '.h', '.hpp', '.cc',
  '.cs',
  '.ts', '.tsx', '.js', '.jsx',
  '.py',
]);

const _suppress = process.platform === 'win32' ? '2>NUL' : '2>/dev/null';

/** Linter commands by extension */
const LINTER_COMMANDS = {
  '.c':   'cppcheck --enable=style --quiet --template="{file}:{line}: {severity}: {message}" {file}',
  '.cpp': 'cppcheck --enable=style --quiet --template="{file}:{line}: {severity}: {message}" {file}',
  '.h':   'cppcheck --enable=style --quiet --template="{file}:{line}: {severity}: {message}" {file}',
  '.hpp': 'cppcheck --enable=style --quiet --template="{file}:{line}: {severity}: {message}" {file}',
  '.cs':  'dotnet format --verify-no-changes --include {file} 2>&1 || true',
  '.ts':  `npx --no-install eslint --no-fix --format compact {file} ${_suppress} || npx --no-install biome check {file} ${_suppress} || true`,
  '.tsx': `npx --no-install eslint --no-fix --format compact {file} ${_suppress} || npx --no-install biome check {file} ${_suppress} || true`,
  '.js':  `npx --no-install eslint --no-fix --format compact {file} ${_suppress} || true`,
  '.jsx': `npx --no-install eslint --no-fix --format compact {file} ${_suppress} || true`,
  '.py':  `ruff check --no-fix --output-format text {file} ${_suppress} || true`,
};

/**
 * Stage 1: Run language-appropriate linter
 * @param {string} filePath
 * @returns {{output: string, skipped: boolean}}
 */
function runLinter(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const cmdTemplate = LINTER_COMMANDS[ext];
  if (!cmdTemplate) return { output: '', skipped: true };

  const cmd = cmdTemplate.replace(/\{file\}/g, filePath);
  const tool = cmd.split(' ')[0];

  // Check if tool exists
  const whichCmd = process.platform === 'win32' ? 'where' : 'which';
  try {
    execSync(`${whichCmd} ${tool}`, { stdio: 'pipe' });
  } catch {
    return { output: '', skipped: true };
  }

  try {
    const output = execSync(cmd, {
      encoding: 'utf-8',
      timeout: 10000,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { output: (output || '').trim(), skipped: false };
  } catch (e) {
    // Some linters exit non-zero on findings
    const stderr = e.stderr ? e.stderr.toString().trim() : '';
    const stdout = e.stdout ? e.stdout.toString().trim() : '';
    return { output: stdout || stderr, skipped: false };
  }
}

/**
 * Main handler — called from unified-write-post.js or standalone
 * @param {Object} input - Hook input with tool_input.file_path
 * @returns {boolean} true if executed
 */
function handleCodeQuality(input) {
  const filePath = input?.tool_input?.file_path;
  if (!filePath) return false;

  const ext = path.extname(filePath).toLowerCase();
  if (!CODE_EXTENSIONS.has(ext)) return false;

  // Check file exists
  if (!fs.existsSync(filePath)) return false;

  const { debugLog } = getDebug();
  const { checkStructure, saveMetrics, formatViolations } = getMetrics();

  debugLog('CodeQuality', 'checking', { file: filePath });

  const messages = [];

  // Stage 1: Linter
  const lintResult = runLinter(filePath);
  if (!lintResult.skipped && lintResult.output) {
    messages.push(`[Linter] ${lintResult.output}`);
  }

  // Stage 2: Structure Check
  const content = fs.readFileSync(filePath, 'utf-8');
  const { violations, metrics } = checkStructure(filePath, content);

  if (violations.length > 0) {
    messages.push(formatViolations(filePath, violations));
  }

  // Stage 3: Metrics Storage
  saveMetrics(filePath, metrics);

  // Output feedback to stderr (Claude receives this)
  if (messages.length > 0) {
    process.stderr.write(messages.join('\n'));
  }

  debugLog('CodeQuality', 'done', {
    file: filePath,
    violations: violations.length,
    linterSkipped: lintResult.skipped,
  });

  return true;
}

// Standalone execution (for Edit matcher in hooks.json)
if (require.main === module) {
  try {
    const { readStdinSync, outputAllow } = getIo();
    const input = readStdinSync();
    handleCodeQuality(input);
    outputAllow();
  } catch (e) {
    // Non-blocking — never prevent tool execution
    try {
      const { outputAllow } = getIo();
      outputAllow();
    } catch { /* last resort */ }
  }
}

module.exports = { handleCodeQuality, runLinter };
