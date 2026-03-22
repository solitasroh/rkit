/**
 * MPU Cross-Compiler Detection
 * @module lib/mpu/cross-compile
 * @version 0.3.0
 *
 * Platform-specific toolchain (verified):
 *   i.MX6 (Cortex-A9, ARMv7-A):     arm-linux-gnueabihf-gcc (hard float)
 *   i.MX6ULL (Cortex-A7, ARMv7-A):  arm-linux-gnueabihf-gcc (hard float)
 *   i.MX28 (ARM926EJ-S, ARMv5TEJ):  arm-linux-gnueabi-gcc (soft float)
 *     i.MX28 has NO VFP/NEON → hard float binary CANNOT run
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Detect cross-compiler for MPU target
 * @returns {{ found: boolean, path: string|null, arch: string|null, sysroot: string|null, floatAbi: string }}
 */
function detectCrossCompiler() {
  // 1. Yocto SDK environment variables
  if (process.env.CC && process.env.CC.includes('arm-linux')) {
    return {
      found: true,
      path: process.env.CC.split(' ')[0],
      arch: detectArch(process.env.CC),
      sysroot: process.env.SDKTARGETSYSROOT || process.env.OECORE_TARGET_SYSROOT || null,
      floatAbi: process.env.CC.includes('gnueabihf') ? 'hard' : 'soft',
    };
  }

  if (process.env.CROSS_COMPILE) {
    const gcc = process.env.CROSS_COMPILE + 'gcc';
    return {
      found: true,
      path: gcc,
      arch: detectArch(gcc),
      sysroot: null,
      floatAbi: gcc.includes('gnueabihf') ? 'hard' : 'soft',
    };
  }

  // 2. Try platform-specific detection
  const { domain } = getDomainInfo();

  // i.MX28 needs soft float
  if (domain === 'mpu') {
    const platform = getPlatformInfo();
    if (platform && platform.platform === 'imx28') {
      return findCompiler('arm-linux-gnueabi-gcc', 'soft');
    }
  }

  // Default: try hard float first (i.MX6/6ULL)
  const hf = findCompiler('arm-linux-gnueabihf-gcc', 'hard');
  if (hf.found) return hf;

  // Fallback: soft float
  return findCompiler('arm-linux-gnueabi-gcc', 'soft');
}

/**
 * Detect Yocto SDK environment
 * @returns {{ sdkPath: string|null, targetSysroot: string|null, envVars: Object }}
 */
function detectSdkEnvironment() {
  const result = {
    sdkPath: null,
    targetSysroot: process.env.SDKTARGETSYSROOT || null,
    envVars: {},
  };

  // Check standard SDK paths
  const sdkPaths = ['/opt/poky', '/opt/fsl-imx-xwayland', '/opt/fsl-imx-fb', '/opt/imx-'];
  for (const base of sdkPaths) {
    try {
      if (fs.existsSync(base)) {
        result.sdkPath = base;
        break;
      }
      // Try glob-like
      const parent = path.dirname(base);
      const prefix = path.basename(base);
      if (fs.existsSync(parent)) {
        const dirs = fs.readdirSync(parent).filter(d => d.startsWith(prefix));
        if (dirs.length > 0) {
          result.sdkPath = path.join(parent, dirs[0]);
          break;
        }
      }
    } catch (_) {}
  }

  // Capture relevant env vars
  for (const key of ['CC', 'CXX', 'LD', 'CROSS_COMPILE', 'SDKTARGETSYSROOT', 'ARCH', 'CFLAGS', 'LDFLAGS']) {
    if (process.env[key]) result.envVars[key] = process.env[key];
  }

  return result;
}

// ── Helpers ──

function findCompiler(name, floatAbi) {
  const whichCmd = process.platform === 'win32' ? 'where' : 'which';
  try {
    const result = execSync(`${whichCmd} ${name}`, { encoding: 'utf-8', timeout: 3000, stdio: 'pipe' }).trim();
    const gccPath = result.split('\n')[0].trim();
    if (gccPath) {
      return { found: true, path: gccPath, arch: detectArch(gccPath), sysroot: null, floatAbi };
    }
  } catch (_) {}

  return { found: false, path: null, arch: null, sysroot: null, floatAbi };
}

function detectArch(gccPath) {
  if (gccPath.includes('gnueabihf')) return 'armv7-a-hf';
  if (gccPath.includes('gnueabi')) return 'armv5te-sf';
  if (gccPath.includes('aarch64')) return 'aarch64';
  return 'arm';
}

function getDomainInfo() {
  try { return require('../domain/detector').getCachedDomainInfo(); }
  catch (_) { return { domain: 'unknown' }; }
}

function getPlatformInfo() {
  try {
    const info = require('../domain/detector').getCachedDomainInfo();
    return info ? info.platform || null : null;
  } catch (_) { return null; }
}

module.exports = { detectCrossCompiler, detectSdkEnvironment };
