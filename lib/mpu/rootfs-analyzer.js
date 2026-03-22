/**
 * Root Filesystem Analyzer
 * @module lib/mpu/rootfs-analyzer
 * @version 0.3.0
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Analyze rootfs directory size
 * @param {string} rootfsPath
 * @returns {{ totalMB: number, topDirs: Array<{name: string, sizeMB: number}> }}
 */
function analyzeRootfsSize(rootfsPath) {
  if (!fs.existsSync(rootfsPath)) {
    return { totalMB: 0, topDirs: [] };
  }

  try {
    const output = execSync(`du -sm "${rootfsPath}"/*/ 2>/dev/null || echo ""`, {
      encoding: 'utf-8', timeout: 10000,
    });

    const topDirs = [];
    let totalMB = 0;

    for (const line of output.split('\n')) {
      const match = line.match(/^(\d+)\s+(.+)$/);
      if (match) {
        const sizeMB = parseInt(match[1], 10);
        const name = path.basename(match[2]);
        topDirs.push({ name, sizeMB });
        totalMB += sizeMB;
      }
    }

    topDirs.sort((a, b) => b.sizeMB - a.sizeMB);
    return { totalMB, topDirs: topDirs.slice(0, 10) };
  } catch (_) {
    return { totalMB: 0, topDirs: [] };
  }
}

/**
 * List installed packages from Yocto manifest
 * @param {string} manifestPath - *.manifest file
 * @returns {Array<{name: string, version: string}>}
 */
function listInstalledPackages(manifestPath) {
  if (!fs.existsSync(manifestPath)) return [];

  const content = fs.readFileSync(manifestPath, 'utf-8');
  const packages = [];

  for (const line of content.split('\n')) {
    const parts = line.trim().split(/\s+/);
    if (parts.length >= 2) {
      packages.push({ name: parts[0], version: parts[2] || parts[1] });
    }
  }

  return packages;
}

module.exports = { analyzeRootfsSize, listInstalledPackages };
