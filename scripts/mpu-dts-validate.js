#!/usr/bin/env node
/**
 * MPU DTS Validation Hook - PostToolUse(Write) for .dts/.dtsi files
 * @version 0.3.0
 */
try {
  const { readStdinSync, outputAllow } = require('../lib/core/io');
  const { debugLog } = require('../lib/core/debug');
  const input = readStdinSync();
  if (!input) { outputAllow(); process.exit(0); }

  const parsed = typeof input === 'string' ? JSON.parse(input) : input;
  const filePath = (parsed.tool_input || {}).file_path || '';

  if (!filePath.endsWith('.dts') && !filePath.endsWith('.dtsi')) {
    outputAllow(); process.exit(0);
  }

  debugLog('MPU-DTS', 'Validating', { file: filePath });
  const { validateDeviceTree } = require('../lib/mpu/device-tree');
  const result = validateDeviceTree(filePath);

  let ctx = '';
  if (!result.valid) {
    ctx = 'DTS Validation FAILED:\n' + result.errors.map(e => '  ' + e).join('\n');
  } else if (result.warnings.length > 0) {
    ctx = 'DTS Warnings:\n' + result.warnings.map(w => '  ' + w).join('\n');
  }

  if (ctx) { console.log(JSON.stringify({ additionalContext: ctx })); }
  else { outputAllow(); }
  process.exit(0);
} catch (_) {
  try { require('../lib/core/io').outputAllow(); } catch (__) { console.log('{}'); }
  process.exit(0);
}
