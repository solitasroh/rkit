#!/usr/bin/env node
/**
 * MPU Post-Build Analysis Hook - PostToolUse(Bash) for bitbake/make
 * @version 0.3.0
 */
try {
  const { readStdinSync, outputAllow } = require('../lib/core/io');
  const { debugLog } = require('../lib/core/debug');
  const input = readStdinSync();
  if (!input) { outputAllow(); process.exit(0); }

  const parsed = typeof input === 'string' ? JSON.parse(input) : input;
  const command = (parsed.tool_input || {}).command || '';
  const exitCode = (parsed.tool_output || {}).exit_code;

  const mpuBuildPatterns = ['bitbake', 'buildroot'];
  const isMpuBuild = mpuBuildPatterns.some(p => command.includes(p));
  if (!isMpuBuild || exitCode !== 0) { outputAllow(); process.exit(0); }

  debugLog('MPU-PostBuild', 'Build detected', { command });

  // Try to find deploy directory
  const fs = require('fs');
  const path = require('path');
  const cwd = process.cwd();
  const deployDirs = ['tmp/deploy/images', 'build/tmp/deploy/images', 'output/images'];

  let deployDir = null;
  for (const d of deployDirs) {
    const full = path.join(cwd, d);
    if (fs.existsSync(full)) {
      // Find machine subdirectory
      const subs = fs.readdirSync(full, { withFileTypes: true }).filter(e => e.isDirectory());
      if (subs.length > 0) { deployDir = path.join(full, subs[0].name); }
      else { deployDir = full; }
      break;
    }
  }

  if (!deployDir) { outputAllow(); process.exit(0); }

  const { analyzeImageSize, formatImageReport } = require('../lib/mpu/yocto-analyzer');
  const sizes = analyzeImageSize(deployDir);
  if (sizes.total > 0) {
    console.log(JSON.stringify({ additionalContext: formatImageReport(sizes) }));
  } else { outputAllow(); }
  process.exit(0);
} catch (_) {
  try { require('../lib/core/io').outputAllow(); } catch (__) { console.log('{}'); }
  process.exit(0);
}
