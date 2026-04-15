/**
 * External Tool Integration Bridge
 * @module lib/mcu/tool-bridge
 * @version 0.1.0
 *
 * Integrates with external analysis tools (cppcheck, GCC stack usage).
 * All tools are OPTIONAL — functions return empty results gracefully
 * when tools are not installed or files are not available.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Check if a command is available in PATH
 * @param {string} cmd
 * @returns {boolean}
 */
function isCommandAvailable(cmd) {
  const whichCmd = process.platform === 'win32' ? 'where' : 'which';
  try {
    execSync(`${whichCmd} ${cmd}`, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

/**
 * Run cppcheck with threadsafety addon and parse results
 * @param {string} srcDir - source directory
 * @param {Object} [options] - {cppcheckPath: string, extraArgs: string[]}
 * @returns {{findings: Array<{id: string, severity: string, message: string, file: string, line: number}>, available: boolean}}
 */
function runCppcheckThreadsafety(srcDir, options) {
  const cppcheckCmd = (options && options.cppcheckPath) || 'cppcheck';

  if (!isCommandAvailable(cppcheckCmd)) {
    return { findings: [], available: false };
  }

  try {
    const extraArgs = (options && options.extraArgs) || [];
    const args = [
      '--addon=threadsafety',
      '--template={id};;{severity};;{file};;{line};;{message}',
      '--quiet',
      '--force',
      ...extraArgs,
      srcDir,
    ].join(' ');

    const output = execSync(`${cppcheckCmd} ${args}`, {
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 120000, // 2 min timeout
      encoding: 'utf-8',
    });

    // cppcheck outputs to stderr
    const stderr = output || '';
    const findings = [];

    for (const line of stderr.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const parts = trimmed.split(';;');
      if (parts.length >= 5) {
        findings.push({
          id: parts[0],
          severity: parts[1],
          file: path.relative(srcDir, parts[2]),
          line: parseInt(parts[3], 10) || 0,
          message: parts[4],
        });
      }
    }

    return { findings, available: true };

  } catch (e) {
    // cppcheck may output findings to stderr and return non-zero
    const stderr = e.stderr ? e.stderr.toString() : '';
    const findings = [];

    for (const line of stderr.split('\n')) {
      const parts = line.trim().split(';;');
      if (parts.length >= 5) {
        findings.push({
          id: parts[0],
          severity: parts[1],
          file: path.relative(srcDir, parts[2]),
          line: parseInt(parts[3], 10) || 0,
          message: parts[4],
        });
      }
    }

    return { findings, available: true };
  }
}

/**
 * Extract per-function stack usage from GCC .su files
 * Requires build with -fstack-usage flag
 * @param {string} buildDir - build directory (.su file search)
 * @param {string|null} mapPath - .map file path (optional, for symbol matching)
 * @returns {{entries: Array<{function: string, stackBytes: number, qualifier: string, file: string}>, available: boolean}}
 */
function extractStackUsage(buildDir, mapPath) {
  // Find .su files
  let suFiles = [];
  try {
    suFiles = findFilesRecursive(buildDir, '.su');
  } catch {
    return { entries: [], available: false };
  }

  if (suFiles.length === 0) {
    return { entries: [], available: false };
  }

  const entries = [];

  for (const suFile of suFiles) {
    const content = fs.readFileSync(suFile, 'utf-8');

    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      // Format: file:line:col:function_name\tsize\tqualifier
      // e.g., src/main.c:42:6:main	256	static
      const match = trimmed.match(/^(.+?):(\d+):\d+:(\w+)\t(\d+)\t(\w+)/);
      if (match) {
        entries.push({
          function: match[3],
          stackBytes: parseInt(match[4], 10),
          qualifier: match[5], // "static", "dynamic", "bounded"
          file: match[1],
          line: parseInt(match[2], 10),
        });
      }
    }
  }

  // Sort by stack usage descending
  entries.sort((a, b) => b.stackBytes - a.stackBytes);

  return { entries, available: true };
}

/**
 * Recursively find files with given extension
 * @param {string} dir
 * @param {string} ext
 * @returns {string[]}
 */
function findFilesRecursive(dir, ext) {
  const files = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith('.')) {
        files.push(...findFilesRecursive(fullPath, ext));
      } else if (entry.isFile() && entry.name.endsWith(ext)) {
        files.push(fullPath);
      }
    }
  } catch {
    // Skip inaccessible directories
  }
  return files;
}

module.exports = {
  runCppcheckThreadsafety,
  extractStackUsage,
};
