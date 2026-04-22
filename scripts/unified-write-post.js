#!/usr/bin/env node
/**
 * unified-write-post.js - Unified Write PostToolUse Handler (v1.4.4)
 *
 * GitHub Issue #9354 Workaround:
 * Consolidates Write PostToolUse hooks from:
 * - rkit-rules: pdca-post-write.js (always runs)
 * - phase-5-design-system: phase5-design-post.js
 * - phase-6-ui-integration: phase6-ui-post.js
 * - qa-monitor: qa-monitor-post.js
 */

const path = require('path');
const fs = require('fs');
const { readStdinSync, parseHookInput, outputAllow } = require('../lib/core/io');
const { debugLog } = require('../lib/core/debug');
const { getActiveSkill, getActiveAgent } = require('../lib/task/context');
const { validateDocument, formatValidationWarning } = require('../lib/pdca/template-validator.js');

// ============================================================
// Handler: pdca-post-write (always runs - core rkit-rules)
// ============================================================

/**
 * PDCA post-write handler - always runs for PDCA tracking
 * @param {Object} input - Hook input
 * @returns {boolean} True if executed
 */
function handlePdcaPostWrite(input) {
  try {
    // Call existing pdca-post-write.js
    const handlerPath = path.join(__dirname, 'pdca-post-write.js');
    const handler = require(handlerPath);

    if (typeof handler.run === 'function') {
      handler.run(input);
    }
    // If self-executing, it already ran when required
    return true;
  } catch (e) {
    debugLog('UnifiedWritePost', 'pdca-post-write failed', { error: e.message });
    return false;
  }
}

// ============================================================
// Handler: phase5-design-post
// ============================================================

/**
 * Phase 5 design system component tracking
 * @param {Object} input - Hook input
 * @param {string} filePath - Written file path
 * @returns {boolean} True if executed
 */
function handlePhase5DesignPost(input, filePath) {
  if (!filePath) return false;

  // Track component files for design system
  if (filePath.includes('components/') || filePath.includes('design-system/')) {
    debugLog('UnifiedWritePost', 'Design system component written', { filePath });

    // Additional phase-5 specific logic could go here:
    // - Update component registry
    // - Validate design token usage
    // - Check naming conventions
  }
  return true;
}

// ============================================================
// Handler: phase6-ui-post
// ============================================================

/**
 * Phase 6 UI integration tracking
 * @param {Object} input - Hook input
 * @param {string} filePath - Written file path
 * @returns {boolean} True if executed
 */
function handlePhase6UiPost(input, filePath) {
  if (!filePath) return false;

  // Track UI page/component files
  if (filePath.includes('pages/') || filePath.includes('app/') || filePath.includes('views/')) {
    debugLog('UnifiedWritePost', 'UI page written', { filePath });

    // Additional phase-6 specific logic could go here:
    // - Validate API integration patterns
    // - Check state management usage
    // - Verify error handling
  }
  return true;
}

// ============================================================
// Handler: qa-monitor-post (Write)
// ============================================================

/**
 * QA monitor write tracking
 * @param {Object} input - Hook input
 * @param {string} filePath - Written file path
 * @returns {boolean} True if executed
 */
function handleQaMonitorPost(input, filePath) {
  if (!filePath) return false;

  debugLog('UnifiedWritePost', 'QA monitor: file written', { filePath });

  // QA-specific tracking:
  // - Log file changes for test verification
  // - Track test file modifications
  return true;
}

// ============================================================
// Main Execution
// ============================================================

debugLog('UnifiedWritePost', 'Hook started');

// Read hook context
let input = {};
try {
  input = readStdinSync();
  if (typeof input === 'string') {
    input = JSON.parse(input);
  }
} catch (e) {
  debugLog('UnifiedWritePost', 'Failed to parse input', { error: e.message });
}

// Parse file path from input
const { filePath } = parseHookInput(input);

// Get current context
const activeSkill = getActiveSkill();
const activeAgent = getActiveAgent();

debugLog('UnifiedWritePost', 'Context', { activeSkill, activeAgent, filePath });

// Always run PDCA post-write (core rkit-rules functionality)
handlePdcaPostWrite(input);

// Conditional handlers based on active skill/agent
if (activeSkill === 'phase-5-design-system') {
  handlePhase5DesignPost(input, filePath);
}

if (activeSkill === 'phase-6-ui-integration') {
  handlePhase6UiPost(input, filePath);
}

if (activeAgent === 'qa-monitor') {
  handleQaMonitorPost(input, filePath);
}

// Code quality check on every code file write
try {
  const { handleCodeQuality } = require('./code-quality-hook');
  handleCodeQuality(input);
} catch (e) {
  debugLog('UnifiedWritePost', 'code-quality-hook failed', { error: e.message });
}

// C++ static analysis (cpp-static-analysis) — only fires for C/C++ extensions.
// Non-blocking: Python hook stderr is relayed, never outputs decision:block.
try {
  const { handleCppStaticAnalysis } = require('./cpp-static-analysis-hook');
  handleCppStaticAnalysis(input);
} catch (e) {
  debugLog('UnifiedWritePost', 'cpp-static-analysis-hook failed', { error: e.message });
}

// v1.6.0 ENH-103: PDCA template validation
if (filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const result = validateDocument(filePath, content);

    if (!result.valid && result.missing.length > 0) {
      const warning = formatValidationWarning(result);
      debugLog('UnifiedWritePost', 'Template validation failed', {
        filePath, type: result.type, missing: result.missing
      });
      outputAllow(warning, 'PostToolUse');
      debugLog('UnifiedWritePost', 'Hook completed with template warning');
      process.exit(0);
    }
  } catch (e) {
    debugLog('UnifiedWritePost', 'Template validation error', { error: e.message });
  }
}

// v2.0.0: Audit logging for file write
try {
  const toolInput = input.tool_input || {};
  const audit = require('../lib/audit/audit-logger');
  audit.writeAuditLog({
    actor: 'system', actorId: 'unified-write-post',
    action: toolInput.file_path ? 'file_modified' : 'file_created',
    category: 'file',
    target: toolInput.file_path || '', targetType: 'file',
    result: 'success', destructiveOperation: false
  });
} catch (_) {}

// v2.0.0: Loop detection for repeated file edits
try {
  const toolInput = input.tool_input || {};
  const lb = require('../lib/control/loop-breaker');
  lb.recordAction('file_edit', toolInput.file_path || 'unknown');
  const loopCheck = lb.checkLoop();
  if (loopCheck.detected) {
    debugLog('UnifiedWritePost', 'Loop detected in file edits', {
      target: toolInput.file_path, details: loopCheck
    });
  }
} catch (_) {}

// v2.0.0: Metrics update if PDCA feature is active
try {
  const { getPdcaStatusFull } = require('../lib/pdca/status');
  const pdcaStatus = getPdcaStatusFull();
  if (pdcaStatus && pdcaStatus.currentFeature) {
    const mc = require('../lib/quality/metrics-collector');
    mc.collectMetric('file_change_count', pdcaStatus.currentFeature, 1, 'unified-write-post');
  }
} catch (_) {}

// Output allow (PostToolUse doesn't block)
outputAllow('', 'PostToolUse');

debugLog('UnifiedWritePost', 'Hook completed');
