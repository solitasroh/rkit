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
    if (process.platform === 'win32') {
      // Windows: use Node.js fs to calculate directory sizes
      const topDirs = [];
      let totalMB = 0;
      const entries = fs.readdirSync(rootfsPath, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const dirPath = path.join(rootfsPath, entry.name);
        const sizeMB = Math.round(getDirSizeBytes(dirPath) / (1024 * 1024));
        topDirs.push({ name: entry.name, sizeMB });
        totalMB += sizeMB;
      }
      topDirs.sort((a, b) => b.sizeMB - a.sizeMB);
      return { totalMB, topDirs: topDirs.slice(0, 10) };
    }

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
  } catch (_e) {
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

/**
 * Calculate directory size in bytes (recursive, Windows fallback)
 * @param {string} dirPath
 * @returns {number}
 */
function getDirSizeBytes(dirPath) {
  let total = 0;
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
        total += getDirSizeBytes(fullPath);
      } else if (entry.isFile()) {
        total += fs.statSync(fullPath).size;
      }
    }
  } catch (_e) { /* skip inaccessible */ }
  return total;
}

module.exports = { analyzeRootfsSize, listInstalledPackages };
