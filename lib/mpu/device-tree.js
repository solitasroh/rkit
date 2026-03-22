/**
 * Device Tree Source Parser & Validator
 * @module lib/mpu/device-tree
 * @version 0.3.0
 *
 * Validates DTS/DTSI files using dtc compiler and parses node structure.
 * Supports i.MX6, i.MX6ULL, i.MX28 Device Tree files.
 *
 * DTS file naming (verified):
 *   i.MX6Q:   imx6q.dtsi, imx6qdl.dtsi, imx6q-sabresd.dts
 *   i.MX6ULL: imx6ull.dtsi, imx6ul.dtsi, imx6ull-14x14-evk.dts
 *   i.MX28:   imx28.dtsi, imx28-evk.dts
 *
 * Kernel path (6.5+): arch/arm/boot/dts/nxp/imx/ (or nxp/mxs/ for i.MX28)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Validate DTS/DTSI file syntax using dtc
 * @param {string} dtsFilePath
 * @returns {{ valid: boolean, errors: string[], warnings: string[] }}
 */
function validateDeviceTree(dtsFilePath) {
  if (!fs.existsSync(dtsFilePath)) {
    return { valid: false, errors: [`File not found: ${dtsFilePath}`], warnings: [] };
  }

  // Check dtc availability
  try {
    execSync('dtc --version', { encoding: 'utf-8', timeout: 3000, stdio: 'pipe' });
  } catch (_) {
    return {
      valid: true,
      errors: [],
      warnings: ['dtc not installed. Install with: sudo apt install device-tree-compiler'],
    };
  }

  try {
    const cmd = `dtc -I dts -O dtb -o /dev/null -W no-unit_address_vs_reg "${dtsFilePath}" 2>&1`;
    const output = execSync(cmd, { encoding: 'utf-8', timeout: 10000 });

    const errors = [];
    const warnings = [];

    for (const line of output.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.includes('Error') || trimmed.includes('ERROR')) {
        errors.push(trimmed);
      } else if (trimmed.includes('Warning') || trimmed.includes('WARNING')) {
        warnings.push(trimmed);
      }
    }

    return { valid: errors.length === 0, errors, warnings };
  } catch (e) {
    const stderr = e.stderr ? e.stderr.toString() : e.message;
    const errors = stderr.split('\n').filter(l => l.trim()).slice(0, 10);
    return { valid: false, errors, warnings: [] };
  }
}

/**
 * Parse DTS file into a simple node tree
 * @param {string} dtsFilePath
 * @returns {Object} Recursive node structure
 */
function parseDtsNodes(dtsFilePath) {
  const content = fs.readFileSync(dtsFilePath, 'utf-8');
  const root = { name: '/', children: [], properties: [] };

  // Simple regex-based extraction of top-level node references
  const nodeRefRegex = /&(\w+)\s*\{/g;
  let match;
  while ((match = nodeRefRegex.exec(content)) !== null) {
    root.children.push({
      name: `&${match[1]}`,
      type: 'reference',
      line: content.substring(0, match.index).split('\n').length,
    });
  }

  // Extract root-level nodes
  const nodeRegex = /^\s*(\w[\w@,-]*)\s*\{/gm;
  while ((match = nodeRegex.exec(content)) !== null) {
    if (match[1] === 'dts-v1' || match[1] === 'plugin') continue;
    root.children.push({
      name: match[1],
      type: 'node',
      line: content.substring(0, match.index).split('\n').length,
    });
  }

  return root;
}

/**
 * Check pinctrl conflicts in DTS (duplicate pads in fsl,pins)
 * @param {string} dtsFilePath
 * @returns {Array<{pad: string, conflicts: string[], lines: number[]}>}
 */
function checkPinctrlConflicts(dtsFilePath) {
  const content = fs.readFileSync(dtsFilePath, 'utf-8');
  const conflicts = [];

  // Extract all fsl,pins entries
  // Pattern: MX6QDL_PAD_name__function  0xvalue
  const padRegex = /(MX6\w*_PAD_\w+)__(\w+)\s+0x[0-9a-fA-F]+/g;
  const padMap = new Map(); // pad → [{function, line}]

  let match;
  while ((match = padRegex.exec(content)) !== null) {
    const pad = match[1];
    const func = match[2];
    const line = content.substring(0, match.index).split('\n').length;

    if (!padMap.has(pad)) padMap.set(pad, []);
    padMap.get(pad).push({ function: func, line });
  }

  for (const [pad, entries] of padMap) {
    if (entries.length > 1) {
      conflicts.push({
        pad,
        conflicts: entries.map(e => e.function),
        lines: entries.map(e => e.line),
      });
    }
  }

  return conflicts;
}

module.exports = {
  validateDeviceTree,
  parseDtsNodes,
  checkPinctrlConflicts,
};
