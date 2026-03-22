#!/usr/bin/env node
/**
 * WPF XAML Binding Check Hook - PostToolUse(Write) for .xaml files
 * @version 0.4.0
 */
try {
  const { readStdinSync, outputAllow } = require('../lib/core/io');
  const { debugLog } = require('../lib/core/debug');
  const input = readStdinSync();
  if (!input) { outputAllow(); process.exit(0); }

  const parsed = typeof input === 'string' ? JSON.parse(input) : input;
  const filePath = (parsed.tool_input || {}).file_path || '';
  if (!filePath.endsWith('.xaml')) { outputAllow(); process.exit(0); }

  debugLog('WPF-XAML', 'Checking bindings', { file: filePath });
  const { extractBindings } = require('../lib/wpf/xaml-analyzer');
  const bindings = extractBindings(filePath);

  if (bindings.length > 0) {
    const summary = `XAML: ${bindings.length} bindings found (${bindings.filter(b => b.type === 'Binding').length} Binding, ${bindings.filter(b => b.type === 'TemplateBinding').length} TemplateBinding)`;
    console.log(JSON.stringify({ additionalContext: summary }));
  } else { outputAllow(); }
  process.exit(0);
} catch (_) {
  try { require('../lib/core/io').outputAllow(); } catch (__) { console.log('{}'); }
  process.exit(0);
}
