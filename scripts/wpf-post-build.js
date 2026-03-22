#!/usr/bin/env node
/**
 * WPF Post-Build Analysis Hook - PostToolUse(Bash) for dotnet build/msbuild
 * @version 0.4.0
 */
try {
  const { readStdinSync, outputAllow } = require('../lib/core/io');
  const input = readStdinSync();
  if (!input) { outputAllow(); process.exit(0); }

  const parsed = typeof input === 'string' ? JSON.parse(input) : input;
  const command = (parsed.tool_input || {}).command || '';
  const stdout = (parsed.tool_output || {}).stdout || '';
  const exitCode = (parsed.tool_output || {}).exit_code;

  if (!command.includes('dotnet build') && !command.includes('msbuild')) {
    outputAllow(); process.exit(0);
  }

  // Parse warnings and errors from build output
  const warnings = (stdout.match(/warning \w+\d+:/g) || []).length;
  const errors = (stdout.match(/error \w+\d+:/g) || []).length;

  if (warnings > 0 || errors > 0 || exitCode !== 0) {
    const ctx = `WPF Build: ${errors} error(s), ${warnings} warning(s)` +
      (exitCode !== 0 ? ' [BUILD FAILED]' : '');
    console.log(JSON.stringify({ additionalContext: ctx }));
  } else { outputAllow(); }
  process.exit(0);
} catch (_) {
  try { require('../lib/core/io').outputAllow(); } catch (__) { console.log('{}'); }
  process.exit(0);
}
