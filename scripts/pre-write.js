#!/usr/bin/env node
/**
 * pre-write.js - Unified PreToolUse hook for Write|Edit operations (v2.0.0)
 *
 * Purpose: PDCA check, task classification, convention hints, permission check,
 *          destructive detection, blast radius, scope limiting, audit logging
 * Hook: PreToolUse (Claude Code)
 * Philosophy: Automation First - Guide, don't block
 *
 * v2.0.0 Changes:
 * - Added destructive detector integration (control module)
 * - Added blast radius check (control module)
 * - Added scope limiter check (control module)
 * - Added audit logging for all write operations
 *
 * v1.4.2 Changes:
 * - Added permission check integration (FR-05)
 *
 * v1.4.0 Changes:
 * - Added debug logging for hook verification
 * - Added PDCA status update for "do" phase
 *
 * Converted from: scripts/pre-write.sh
 */

const { readStdinSync, parseHookInput, outputAllow, outputBlock, outputEmpty } = require('../lib/core/io');
const { debugLog } = require('../lib/core/debug');
const { isSourceFile, isCodeFile, isEnvFile, extractFeature } = require('../lib/core/file');
const { findDesignDoc, findPlanDoc } = require('../lib/pdca/phase');
const { updatePdcaStatus } = require('../lib/pdca/status');
const { classifyTaskByLines, getPdcaLevel } = require('../lib/task/classification');
const { generateTaskGuidance } = require('../lib/task/creator');

// v1.4.2: Permission Manager (FR-05)
let permissionManager;
try {
  permissionManager = require('../lib/permission-manager.js');
} catch (e) {
  // Fallback if module not available
  permissionManager = null;
}

// v1.0.0: Freeze Manager (gstack-inspired)
let freezeManager;
try {
  freezeManager = require('../lib/control/freeze-manager');
} catch (e) {
  freezeManager = null;
}

// Read input from stdin
const input = readStdinSync();
const { filePath, content } = parseHookInput(input);

// Debug log hook execution
debugLog('PreToolUse', 'Hook started', { filePath: filePath || 'none' });

// Skip if no file path
if (!filePath) {
  debugLog('PreToolUse', 'Skipped - no file path');
  outputEmpty();
  process.exit(0);
}

// Collect context messages
const contextParts = [];

// ============================================================
// 0. Permission Check (v1.4.2 - FR-05)
// ============================================================
if (permissionManager) {
  const toolName = input.tool_name || 'Write';  // Write or Edit
  const permission = permissionManager.checkPermission(toolName, filePath);

  if (permission === 'deny') {
    debugLog('PreToolUse', 'Permission denied', { filePath, tool: toolName });
    outputBlock(`${toolName} to ${filePath} is denied by permission policy.`);
    process.exit(2);
  }

  if (permission === 'ask') {
    contextParts.push(`${toolName} to ${filePath} requires confirmation.`);
    debugLog('PreToolUse', 'Permission requires confirmation', { filePath, tool: toolName });
  }
}

// ============================================================
// 0.5. Freeze Check (gstack-inspired file protection)
// ============================================================
if (freezeManager) {
  const freezeResult = freezeManager.isFrozen(filePath);
  if (freezeResult.frozen) {
    debugLog('PreToolUse', 'File is frozen', { filePath, pattern: freezeResult.matchedPattern });
    outputBlock(
      `🔒 File "${filePath}" is frozen (pattern: ${freezeResult.matchedPattern}).\n` +
      `Reason: ${freezeResult.reason}\n` +
      `Use /freeze unfreeze ${freezeResult.matchedPattern} to allow modification.`
    );
    process.exit(2);
  }
}

// ============================================================
// 0.6. Arch-Lock Check (gstack-inspired architecture boundary enforcement)
// ============================================================
try {
  const archLock = require('../lib/control/arch-lock');
  if (archLock.isLocked()) {
    const violation = archLock.checkViolation(filePath);
    if (violation.violation) {
      const ids = violation.decisions.map(d => `${d.id} (${d.title})`).join(', ');
      contextParts.push(
        `Architecture decision applies: ${ids}. ` +
        `Ensure changes comply with locked architecture. Use /arch-lock unlock to modify.`
      );
      debugLog('PreToolUse', 'Arch-lock boundary warning', { filePath, decisions: violation.decisions.map(d => d.id) });
    }
  }
} catch (_) {}

// ============================================================
// 1. Task Classification (v1.3.0 - Line-based, Automation First)
// ============================================================
let classification = 'quick_fix';
let pdcaLevel = 'none';
let lineCount = 0;

if (content) {
  lineCount = content.split('\n').length;
  classification = classifyTaskByLines(content);
  pdcaLevel = getPdcaLevel(classification);
}

// ============================================================
// 2. PDCA Document Check (for source files)
// ============================================================
let feature = '';
let designDoc = '';
let planDoc = '';

if (isSourceFile(filePath)) {
  feature = extractFeature(filePath);

  if (feature) {
    designDoc = findDesignDoc(feature);
    planDoc = findPlanDoc(feature);

    // Update PDCA status to "do" phase when source file is being written
    updatePdcaStatus(feature, 'do', {
      lastFile: filePath
    });

    debugLog('PreToolUse', 'PDCA status updated', {
      feature,
      phase: 'do',
      hasDesignDoc: !!designDoc
    });
  }
}

// ============================================================
// 3. Generate PDCA Guidance (v1.3.0 - No blocking, guide only)
// ============================================================
switch (pdcaLevel) {
  case 'none':
    // Quick Fix - no guidance needed
    break;
  case 'light':
    // Minor Change - light mention
    contextParts.push(`Minor change (${lineCount} lines). PDCA optional.`);
    break;
  case 'recommended':
    // Feature - recommend design doc
    if (designDoc) {
      contextParts.push(`Feature (${lineCount} lines). Design doc exists: ${designDoc}`);
    } else if (feature) {
      contextParts.push(`Feature (${lineCount} lines). Design doc recommended for '${feature}'. Consider /pdca-design ${feature}`);
    } else {
      contextParts.push(`Feature-level change (${lineCount} lines). Design doc recommended.`);
    }
    break;
  case 'required':
    // Major Feature - strongly recommend (but don't block)
    if (designDoc) {
      contextParts.push(`Major feature (${lineCount} lines). Design doc exists: ${designDoc}. Refer during implementation.`);
    } else if (feature) {
      contextParts.push(`Major feature (${lineCount} lines) without design doc. Strongly recommend /pdca-design ${feature} first.`);
    } else {
      contextParts.push(`Major feature (${lineCount} lines). Design doc strongly recommended before implementation.`);
    }
    break;
}

// Add reference to existing PDCA docs if not already mentioned
if (planDoc && !designDoc && pdcaLevel !== 'none' && pdcaLevel !== 'light') {
  contextParts.push(`Plan exists at ${planDoc}. Design doc not yet created.`);
}

// ============================================================
// 4. Convention Hints (for code files)
// ============================================================
if (isCodeFile(filePath)) {
  // Only add convention hints for larger changes
  if (pdcaLevel === 'recommended' || pdcaLevel === 'required') {
    contextParts.push('Conventions: Components=PascalCase, Functions=camelCase, Constants=UPPER_SNAKE_CASE');
  }
} else if (isEnvFile(filePath)) {
  contextParts.push('Env naming: NEXT_PUBLIC_* (client), DB_* (database), API_* (external), AUTH_* (auth)');
}

// ============================================================
// 5. Task System Guidance (v1.3.1 - FR-02)
// ============================================================
if (feature && (pdcaLevel === 'recommended' || pdcaLevel === 'required')) {
  const taskHint = generateTaskGuidance('do', feature, 'design');
  contextParts.push(taskHint);
}

// ============================================================
// 6. Destructive Detector (v2.0.0 - Control Module)
// ============================================================
try {
  const dd = require('../lib/control/destructive-detector');
  const toolInput = { file_path: filePath, content };
  const result = dd.detect('Write', toolInput);
  if (result.detected) {
    const audit = require('../lib/audit/audit-logger');
    audit.writeAuditLog({
      actor: 'hook', actorId: 'pre-write',
      action: 'destructive_blocked', category: 'control',
      target: toolInput.file_path || '', targetType: 'file',
      details: { rules: result.rules },
      result: 'blocked', destructiveOperation: true,
      blastRadius: 'medium'
    });
    contextParts.push(`Destructive operation detected: ${result.rules.map(r => r.id || r.reason).join(', ')}`);
  }
} catch (_) {}

// ============================================================
// 7. Blast Radius Check (v2.0.0 - Control Module)
// ============================================================
try {
  const br = require('../lib/control/blast-radius');
  const check = br.checkSingleFile(filePath, content?.length || 0);
  if (check.warning) {
    contextParts.push(`Blast radius warning: ${check.warning}`);
  }
} catch (_) {}

// ============================================================
// 8. Scope Limiter Check (v2.0.0 - Control Module)
// ============================================================
try {
  const sl = require('../lib/control/scope-limiter');
  const ac = require('../lib/control/automation-controller');
  const level = ac.getCurrentLevel();
  const scopeCheck = sl.checkPathScope(filePath, level);
  if (!scopeCheck.allowed) {
    contextParts.push(`Scope limit: ${scopeCheck.reason || 'Path not allowed at current automation level'}`);
  }
} catch (_) {}

// ============================================================
// 9. Audit Log (v2.0.0 - All Write Operations)
// ============================================================
try {
  const audit = require('../lib/audit/audit-logger');
  audit.writeAuditLog({
    actor: 'hook', actorId: 'pre-write',
    action: 'file_modified', category: 'file',
    target: filePath || '', targetType: 'file',
    result: 'success', destructiveOperation: false
  });
} catch (_) {}

// ============================================================
// Output combined context
// ============================================================
debugLog('PreToolUse', 'Hook completed', {
  classification,
  pdcaLevel,
  feature: feature || 'none',
  contextCount: contextParts.length
});

if (contextParts.length > 0) {
  // v1.4.0: PreToolUse hook에 맞는 스키마 사용
  outputAllow(contextParts.join(' | '), 'PreToolUse');
} else {
  outputEmpty();
}
