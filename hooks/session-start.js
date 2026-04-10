#!/usr/bin/env node
/**
 * rkit Embedded Dev Kit - SessionStart Hook (v0.1.0)
 *
 * Orchestrator delegates to startup modules:
 *   1. migration   - Legacy path migration
 *   2. restore     - PLUGIN_DATA backup restoration
 *   3. contextInit - Context Hierarchy, Memory Store, ensureMcukitDirs
 *   4. domainDetect- ★ Domain auto-detection (MCU/MPU/WPF)
 *   5. onboarding  - Onboarding message generation
 *  5.5. instinct   - Instinct profile load (converged patterns)
 *   6. sessionCtx  - additionalContext string building
 *   7. dashboard   - PDCA progress bar rendering
 *   8. workflowMap - Workflow map rendering
 *   9. controlPanel- Control panel rendering
 *  10. staleDetect - Stale feature detection
 */

const { MCUKIT_PLATFORM } = require('../lib/core/platform');
const { debugLog } = require('../lib/core/debug');

debugLog('SessionStart', 'Hook executed', {
  cwd: process.cwd(),
  platform: MCUKIT_PLATFORM
});

// --- 0. Required Plugins (devkit extensions) ---
try {
  const { execSync } = require('child_process');
  const fs = require('fs');
  const path = require('path');
  const configPath = path.join(process.env.CLAUDE_PLUGIN_ROOT || process.cwd(), 'rkit.config.json');
  if (fs.existsSync(configPath)) {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    const plugins = config.requiredPlugins || [];
    for (const pluginSpec of plugins) {
      try {
        const installed = execSync('claude plugin list 2>&1', { encoding: 'utf8', timeout: 5000 });
        if (installed.includes(pluginSpec.split('@')[0])) continue;
        execSync(`claude plugin install ${pluginSpec} 2>&1`, { encoding: 'utf8', timeout: 30000 });
        debugLog('SessionStart', `Installed plugin: ${pluginSpec}`);
      } catch (e) {
        debugLog('SessionStart', `Plugin install failed: ${pluginSpec}`, { error: e.message });
      }
    }
  }
} catch (e) {
  debugLog('SessionStart', 'RequiredPlugins check failed', { error: e.message });
}

// --- 1. Migration ---
try {
  const migration = require('./startup/migration');
  migration.run();
} catch (e) {
  debugLog('SessionStart', 'Migration failed', { error: e.message });
}

// --- 2. Restore ---
try {
  const restore = require('./startup/restore');
  restore.run();
} catch (e) {
  debugLog('SessionStart', 'Restore failed', { error: e.message });
}

// --- 3. Context Init ---
try {
  const contextInit = require('./startup/context-init');
  contextInit.run();
} catch (e) {
  debugLog('SessionStart', 'Context init failed', { error: e.message });
}

// --- 4. ★ Domain Detection (rkit-specific) ---
let domainResult = { domain: 'unknown', confidence: 0, markers: [] };
try {
  const { detectDomain, detectPlatform, saveDomainCache } = require('../lib/domain/detector');
  domainResult = detectDomain();

  if (domainResult.domain !== 'unknown') {
    domainResult.platform = detectPlatform(domainResult.domain);
    saveDomainCache(domainResult);
  }

  debugLog('SessionStart', 'Domain detected', domainResult);
} catch (e) {
  debugLog('SessionStart', 'Domain detection failed', { error: e.message });
}

// --- 5. Onboarding ---
let onboardingContext = { onboardingData: { type: 'new_user', hasExistingWork: false }, triggerTable: '' };
try {
  const onboarding = require('./startup/onboarding');
  onboardingContext = onboarding.run();
} catch (e) {
  debugLog('SessionStart', 'Onboarding failed', { error: e.message });
}

// --- 5.5. Instinct Profile Load ---
let instinctContext = '';
try {
  const { loadConvergedPatterns, getProfileSummary, writeProfileFile } = require('../lib/instinct/loader');
  instinctContext = loadConvergedPatterns();
  writeProfileFile(); // Write profile.md for agent imports
  if (instinctContext) {
    const summary = getProfileSummary();
    debugLog('SessionStart', 'Instinct loaded', summary);
  }
} catch (e) {
  debugLog('SessionStart', 'Instinct load skipped', { error: e.message });
}

// --- 6. Session Context ---
let additionalContext = '';
try {
  const sessionContext = require('./startup/session-context');
  additionalContext = sessionContext.build(null, onboardingContext);
} catch (e) {
  debugLog('SessionStart', 'Session context failed', { error: e.message });
}

// --- 6.5. Instinct context injection ---
if (instinctContext) {
  additionalContext += '\n' + instinctContext + '\n';
}

// --- 7-9. PDCA Dashboard (Dual Output: terminal → stderr, context → additionalContext) ---
let pdcaStatus = null;
try {
  const ui = require('../lib/ui');
  const { loadUiConfig } = require('../lib/ui/config-loader');
  const { getPdcaStatusFull } = require('../lib/pdca/status');
  const config = loadUiConfig();
  pdcaStatus = getPdcaStatusFull();

  if (pdcaStatus && pdcaStatus.primaryFeature) {
    const data = { pdcaStatus, feature: pdcaStatus.primaryFeature };

    // Terminal output (ANSI → stderr → user sees colored dashboard)
    const terminalParts = [
      ui.progressBar.terminal(data, config),
      ui.workflowMap.terminal(data, config),
      ui.controlPanel.terminal(data, config),
    ].filter(Boolean);

    if (terminalParts.length > 0) {
      process.stderr.write(terminalParts.join('\n') + '\n');
    }

    // Context output (markdown → additionalContext → LLM reads clean text)
    const contextParts = [
      ui.progressBar.context(data, config),
      ui.workflowMap.context(data, config),
      ui.controlPanel.context(data, config),
    ].filter(Boolean);

    if (contextParts.length > 0) {
      additionalContext = contextParts.join('\n\n') + '\n\n' + additionalContext;
    }
  }
} catch (e) {
  debugLog('SessionStart', 'PDCA dashboard failed', { error: e.message });
}

// --- 10. Stale Feature Detection ---
try {
  const { detectStaleFeatures } = require('../lib/pdca/lifecycle');
  const stale = detectStaleFeatures();
  if (stale.length > 0) {
    let warning = '\n## Stale Feature Warning\n\n';
    for (const s of stale) {
      warning += `- **${s.feature}**: idle ${s.daysIdle} days (phase: ${s.phase})\n`;
    }
    additionalContext += warning;
  }
} catch (e) {
  debugLog('SessionStart', 'Stale detection failed', { error: e.message });
}

// --- Domain info in context ---
if (domainResult.domain !== 'unknown') {
  const domainInfo = `\n## Detected Domain: ${domainResult.domain.toUpperCase()}\n` +
    `- Platform: ${domainResult.platform ? domainResult.platform.platform : 'unknown'}\n` +
    `- SDK: ${domainResult.platform ? domainResult.platform.sdk : 'unknown'}\n` +
    `- Confidence: ${(domainResult.confidence * 100).toFixed(0)}%\n`;
  additionalContext += domainInfo;
}

// --- Output ---
const response = {
  systemMessage: `rkit Embedded Dev Kit v${require('../package.json').version} activated (Claude Code)`,
  hookSpecificOutput: {
    hookEventName: 'SessionStart',
    onboardingType: onboardingContext.onboardingData.type,
    hasExistingWork: onboardingContext.onboardingData.hasExistingWork,
    primaryFeature: onboardingContext.onboardingData.primaryFeature || null,
    currentPhase: onboardingContext.onboardingData.phase || null,
    detectedDomain: domainResult.domain,
    additionalContext: additionalContext,
  },
};

console.log(JSON.stringify(response));
process.exit(0);
