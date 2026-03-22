/**
 * Yocto/Buildroot Build Analyzer
 * @module lib/mpu/yocto-analyzer
 * @version 0.3.0
 *
 * Parses Yocto conf files and analyzes build output sizes.
 * Supports meta-freescale (community) and meta-imx (NXP official).
 *
 * Key paths:
 *   local.conf:    build/conf/local.conf
 *   bblayers.conf: build/conf/bblayers.conf
 *   Deploy dir:    build/tmp/deploy/images/<MACHINE>/
 *
 * Image naming:
 *   Latest BSP: imx-image-full, imx-image-multimedia
 *   Legacy BSP: fsl-image-gui (deprecated)
 *   Common:     core-image-minimal, core-image-base
 */

const fs = require('fs');
const path = require('path');

/**
 * Parse Yocto local.conf
 * @param {string} confPath - Path to local.conf
 * @returns {{ machine: string|null, distro: string|null, imageFeatures: string[] }}
 */
function parseLocalConf(confPath) {
  const content = fs.readFileSync(confPath, 'utf-8');
  const result = { machine: null, distro: null, imageFeatures: [] };

  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    // MACHINE ??= "imx6qsabresd"
    const machineMatch = trimmed.match(/^MACHINE\s*\??=\s*"([^"]+)"/);
    if (machineMatch) result.machine = machineMatch[1];

    // DISTRO ?= "poky"
    const distroMatch = trimmed.match(/^DISTRO\s*\??=\s*"([^"]+)"/);
    if (distroMatch) result.distro = distroMatch[1];

    // IMAGE_FEATURES += "ssh-server-openssh"
    const featMatch = trimmed.match(/^(?:EXTRA_)?IMAGE_FEATURES\s*\+?=\s*"([^"]+)"/);
    if (featMatch) {
      result.imageFeatures.push(...featMatch[1].split(/\s+/).filter(Boolean));
    }
  }

  return result;
}

/**
 * Parse bblayers.conf for layer paths
 * @param {string} confPath - Path to bblayers.conf
 * @returns {string[]}
 */
function parseBbLayers(confPath) {
  const content = fs.readFileSync(confPath, 'utf-8');
  const layers = [];

  // BBLAYERS can span multiple lines with \
  const bblayersMatch = content.match(/BBLAYERS\s*\??=\s*"([\s\S]*?)"/);
  if (bblayersMatch) {
    const raw = bblayersMatch[1].replace(/\\\n/g, ' ');
    for (const layer of raw.split(/\s+/)) {
      const trimmed = layer.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        // Expand ${BSPDIR} etc. as-is (can't resolve without env)
        layers.push(trimmed);
      }
    }
  }

  return layers;
}

/**
 * Analyze Yocto/Buildroot image sizes from deploy directory
 * @param {string} deployDir - tmp/deploy/images/<MACHINE>/ or output/images/
 * @returns {{ rootfs: number, kernel: number, dtb: number, uboot: number, total: number }}
 */
function analyzeImageSize(deployDir) {
  const result = { rootfs: 0, kernel: 0, dtb: 0, uboot: 0, total: 0 };

  if (!fs.existsSync(deployDir)) return result;

  try {
    const files = fs.readdirSync(deployDir);

    for (const f of files) {
      const fullPath = path.join(deployDir, f);
      let stat;
      try { stat = fs.lstatSync(fullPath); } catch (_) { continue; }
      if (!stat.isFile()) continue;

      const size = stat.size;
      const lower = f.toLowerCase();

      if (lower.match(/rootfs\.(ext[234]|squashfs|ubifs|tar)/)) {
        result.rootfs = Math.max(result.rootfs, size);
      } else if (lower.match(/^(z|u)?image$/i) || lower === 'vmlinuz') {
        result.kernel = Math.max(result.kernel, size);
      } else if (lower.endsWith('.dtb')) {
        result.dtb = Math.max(result.dtb, size);
      } else if (lower.startsWith('u-boot') && !lower.endsWith('.dtb')) {
        result.uboot = Math.max(result.uboot, size);
      }
    }
  } catch (_) {}

  result.total = result.rootfs + result.kernel + result.dtb + result.uboot;
  return result;
}

/**
 * Detect if project uses Yocto or Buildroot
 * @param {string} projectDir
 * @returns {'yocto'|'buildroot'|'unknown'}
 */
function detectBuildSystem(projectDir) {
  // Yocto markers
  const yoctoMarkers = ['conf/local.conf', 'build/conf/local.conf', 'conf/bblayers.conf'];
  for (const m of yoctoMarkers) {
    if (fs.existsSync(path.join(projectDir, m))) return 'yocto';
  }

  // Buildroot markers
  const brMarkers = ['.config', 'Config.in', 'output/images'];
  const hasBr = brMarkers.some(m => fs.existsSync(path.join(projectDir, m)));
  if (hasBr) return 'buildroot';

  return 'unknown';
}

/**
 * Format image size report
 * @param {Object} sizes - analyzeImageSize result
 * @returns {string}
 */
function formatImageReport(sizes) {
  const fmt = (bytes) => {
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  let report = '+----- Image Size Report -------------------------------------------+\n';
  report += `|  Rootfs:  ${fmt(sizes.rootfs).padEnd(12)} |\n`;
  report += `|  Kernel:  ${fmt(sizes.kernel).padEnd(12)} |\n`;
  report += `|  DTB:     ${fmt(sizes.dtb).padEnd(12)} |\n`;
  report += `|  U-Boot:  ${fmt(sizes.uboot).padEnd(12)} |\n`;
  report += `|  Total:   ${fmt(sizes.total).padEnd(12)} |\n`;
  report += '+------------------------------------------------------------------+\n';
  return report;
}

module.exports = {
  parseLocalConf,
  parseBbLayers,
  analyzeImageSize,
  detectBuildSystem,
  formatImageReport,
};
