/**
 * Invariant Checker - Domain-specific invariant validation
 * @module lib/context/invariant-checker
 * @version 2.0.5
 *
 * Verifies domain invariants that must hold true at all times:
 * - MCU: MISRA C basic pattern checks (goto, malloc, etc.)
 * - MPU: Device Tree syntax validation via dtc
 * - WPF: .csproj UseWPF and TargetFramework validation
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Run all invariant checks for the given domain
 * @param {string} domain - Domain identifier (mcu/mpu/wpf)
 * @param {string} projectDir - Absolute path to project root
 * @returns {{ passed: boolean, checks: Object[], summary: string }}
 */
function checkInvariants(domain, projectDir) {
  var checks = [];

  if (domain === 'mcu') {
    checks = checks.concat(checkMcuInvariants(projectDir));
  } else if (domain === 'mpu') {
    checks = checks.concat(checkMpuInvariants(projectDir));
  } else if (domain === 'wpf') {
    checks = checks.concat(checkWpfInvariants(projectDir));
  }

  var failed = checks.filter(function (c) { return !c.passed; });
  var passed = failed.length === 0;
  var summary = passed
    ? 'All ' + checks.length + ' invariant(s) passed.'
    : failed.length + ' of ' + checks.length + ' invariant(s) failed.';

  return { passed: passed, checks: checks, summary: summary };
}

// ── MCU Invariants ────────────────────────────────────────────────

/**
 * MISRA C basic pattern checks
 * @param {string} projectDir
 * @returns {Object[]}
 */
function checkMcuInvariants(projectDir) {
  var checks = [];
  var cFiles = findFilesByExtension(projectDir, ['.c', '.h'], ['build', 'node_modules', '.git', 'Drivers']);

  // Rule: no goto usage (MISRA C:2012 Rule 15.1)
  var gotoViolations = [];
  // Rule: no malloc/free in safety-critical code (MISRA C:2012 Rule 21.3)
  var mallocViolations = [];

  for (var i = 0; i < cFiles.length; i++) {
    try {
      var content = fs.readFileSync(cFiles[i], 'utf8');
      var lines = content.split('\n');

      for (var ln = 0; ln < lines.length; ln++) {
        var line = lines[ln];
        // Skip comments (simple heuristic)
        var trimmed = line.trim();
        if (trimmed.startsWith('//') || trimmed.startsWith('*') || trimmed.startsWith('/*')) continue;

        if (/\bgoto\b/.test(line)) {
          gotoViolations.push({ file: cFiles[i], line: ln + 1 });
        }
        if (/\b(malloc|calloc|realloc|free)\s*\(/.test(line)) {
          mallocViolations.push({ file: cFiles[i], line: ln + 1 });
        }
      }
    } catch (e) {
      // Skip unreadable files
    }
  }

  checks.push({
    name: 'MISRA-15.1-no-goto',
    passed: gotoViolations.length === 0,
    violations: gotoViolations,
    description: 'goto usage detected in ' + gotoViolations.length + ' location(s).',
  });

  checks.push({
    name: 'MISRA-21.3-no-dynamic-alloc',
    passed: mallocViolations.length === 0,
    violations: mallocViolations,
    description: 'Dynamic memory allocation detected in ' + mallocViolations.length + ' location(s).',
  });

  return checks;
}

// ── MPU Invariants ────────────────────────────────────────────────

/**
 * Device Tree validation via dtc
 * @param {string} projectDir
 * @returns {Object[]}
 */
function checkMpuInvariants(projectDir) {
  var checks = [];
  var dtsFiles = findFilesByExtension(projectDir, ['.dts'], ['build', 'node_modules', '.git']);

  // Check if dtc is available
  var dtcAvailable = false;
  var whichCmd = process.platform === 'win32' ? 'where' : 'which';
  try {
    execSync(whichCmd + ' dtc', { stdio: 'pipe' });
    dtcAvailable = true;
  } catch (e) {
    // dtc not installed
  }

  if (!dtcAvailable) {
    checks.push({
      name: 'dtc-available',
      passed: true,
      violations: [],
      description: 'dtc not found — DTS syntax validation skipped.',
      skipped: true,
    });
    return checks;
  }

  var nullDev = process.platform === 'win32' ? 'NUL' : '/dev/null';
  var dtcViolations = [];
  for (var i = 0; i < dtsFiles.length; i++) {
    try {
      execSync('dtc -I dts -O dtb -o ' + nullDev + ' "' + dtsFiles[i] + '" 2>&1', {
        stdio: 'pipe',
        timeout: 10000,
      });
    } catch (e) {
      var errMsg = e.stderr ? e.stderr.toString().trim() : (e.message || 'unknown error');
      dtcViolations.push({ file: dtsFiles[i], error: errMsg });
    }
  }

  checks.push({
    name: 'dts-syntax-valid',
    passed: dtcViolations.length === 0,
    violations: dtcViolations,
    description: dtcViolations.length === 0
      ? 'All ' + dtsFiles.length + ' DTS file(s) passed dtc validation.'
      : dtcViolations.length + ' DTS file(s) failed dtc validation.',
  });

  return checks;
}

// ── WPF Invariants ────────────────────────────────────────────────

/**
 * .csproj UseWPF and TargetFramework validation
 * @param {string} projectDir
 * @returns {Object[]}
 */
function checkWpfInvariants(projectDir) {
  var checks = [];
  var csprojFiles = findFilesByExtension(projectDir, ['.csproj'], ['build', 'node_modules', '.git', 'bin', 'obj']);

  var useWpfViolations = [];
  var frameworkViolations = [];

  for (var i = 0; i < csprojFiles.length; i++) {
    try {
      var content = fs.readFileSync(csprojFiles[i], 'utf8');

      // Check UseWPF
      if (!/<UseWPF>true<\/UseWPF>/i.test(content)) {
        useWpfViolations.push({ file: csprojFiles[i], reason: 'Missing <UseWPF>true</UseWPF>' });
      }

      // Check TargetFramework (should be net8.0-windows or similar)
      var tfMatch = content.match(/<TargetFramework>(.*?)<\/TargetFramework>/);
      if (tfMatch) {
        var tf = tfMatch[1];
        if (!/^net\d+\.\d+-windows/.test(tf)) {
          frameworkViolations.push({ file: csprojFiles[i], framework: tf, reason: 'Expected net*-windows target' });
        }
      } else {
        frameworkViolations.push({ file: csprojFiles[i], reason: 'No <TargetFramework> found' });
      }
    } catch (e) {
      // Skip unreadable files
    }
  }

  checks.push({
    name: 'wpf-use-wpf-enabled',
    passed: useWpfViolations.length === 0,
    violations: useWpfViolations,
    description: useWpfViolations.length === 0
      ? 'All .csproj files have UseWPF enabled.'
      : useWpfViolations.length + ' .csproj file(s) missing UseWPF.',
  });

  checks.push({
    name: 'wpf-target-framework',
    passed: frameworkViolations.length === 0,
    violations: frameworkViolations,
    description: frameworkViolations.length === 0
      ? 'All .csproj files target net*-windows.'
      : frameworkViolations.length + ' .csproj file(s) have unexpected TargetFramework.',
  });

  return checks;
}

// ── Helpers ───────────────────────────────────────────────────────

/**
 * Simple recursive file finder by extension (shallow scan, max 3 levels)
 * @param {string} dir - Directory to scan
 * @param {string[]} extensions - File extensions to match
 * @param {string[]} excludeDirs - Directory names to skip
 * @param {number} [depth=0] - Current depth
 * @returns {string[]}
 */
function findFilesByExtension(dir, extensions, excludeDirs, depth) {
  if (depth === undefined) depth = 0;
  if (depth > 3) return [];

  var results = [];

  try {
    var entries = fs.readdirSync(dir, { withFileTypes: true });
    for (var i = 0; i < entries.length; i++) {
      var entry = entries[i];
      var fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        if (excludeDirs.indexOf(entry.name) === -1) {
          results = results.concat(findFilesByExtension(fullPath, extensions, excludeDirs, depth + 1));
        }
      } else if (entry.isFile()) {
        var ext = path.extname(entry.name).toLowerCase();
        if (extensions.indexOf(ext) !== -1) {
          results.push(fullPath);
        }
      }
    }
  } catch (e) {
    // Directory unreadable — skip
  }

  return results;
}

module.exports = {
  checkInvariants,
};
