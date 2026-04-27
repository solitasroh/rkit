/**
 * rkit Embedded Dev Kit - SessionStart: Context Initialization Module
 *
 * Loads startup imports via lib/import-resolver, scans SKILL.md frontmatter
 * for `context: fork` configuration, and surfaces a UserPromptSubmit
 * compatibility warning when relevant.
 *
 * NOTE (bkit-gstack-sync-v2 / Cycle 1, C6):
 *   The previous Context Hierarchy / Memory Store / Context Fork
 *   initialization blocks were removed alongside their backing modules
 *   (lib/context-hierarchy.js, lib/memory-store.js, lib/context-fork.js).
 *   Those blocks were already silent no-ops in practice (loaded via
 *   safeRequire and broken at the call site by undefined `core.*`
 *   identifiers — see DEF-1/2/3 fixed in C4). Removing them simply
 *   makes the silent skip explicit and matches bkit upstream.
 */

const fs = require('fs');
const path = require('path');
const { initPdcaStatusIfNotExists, getPdcaStatusFull } = require('../../lib/pdca/status');
const { getMcukitConfig } = require('../../lib/core/config');
const { debugLog } = require('../../lib/core/debug');

// Lazy-load optional modules with graceful fallback
function safeRequire(modulePath) {
  try {
    return require(modulePath);
  } catch (e) {
    return null;
  }
}

/**
 * Run context initialization.
 * Loads startup imports and scans skills for context:fork configuration.
 * @param {object} _input - Hook input (unused, reserved for future use)
 * @returns {{ importResolver: object|null, forkEnabledSkills: Array, userPromptBugWarning: string|null }}
 */
function run(_input) {
  const importResolver = safeRequire('../../lib/import-resolver.js');

  // v2.0.0: Ensure all rkit directories exist (audit/, checkpoints/, decisions/, workflows/, etc.)
  try {
    const { ensureMcukitDirs } = require('../../lib/core/paths');
    ensureMcukitDirs();
  } catch (e) {
    debugLog('SessionStart', 'ensureMcukitDirs failed', { error: e.message });
  }

  // Initialize PDCA status file if not exists
  initPdcaStatusIfNotExists();

  // v2.0.0: Trigger pdca-status auto-migration (v2 → v3 schema) if needed
  try {
    getPdcaStatusFull();
  } catch (e) {
    debugLog('SessionStart', 'PDCA status migration check failed', { error: e.message });
  }

  // Import Resolver - Load startup context (FR-02)
  if (importResolver) {
    try {
      const config = getMcukitConfig();
      const startupImports = config.startupImports || [];
      if (startupImports.length > 0) {
        const { CONFIG_PATHS } = require('../../lib/core/paths');
        const { content, errors } = importResolver.resolveImports(
          { imports: startupImports },
          CONFIG_PATHS.rkitConfig()
        );
        if (errors.length > 0) {
          debugLog('SessionStart', 'Startup import errors', { errors });
        }
        if (content) {
          debugLog('SessionStart', 'Startup imports loaded', {
            importCount: startupImports.length,
            contentLength: content.length
          });
        }
      }
    } catch (e) {
      debugLog('SessionStart', 'Failed to load startup imports', { error: e.message });
    }
  }

  // UserPromptSubmit bug detection (FIX-03)
  let userPromptBugWarning = null;
  try {
    const hooksJsonPath = path.join(__dirname, '..', 'hooks.json');
    if (fs.existsSync(hooksJsonPath)) {
      const hooksConfig = JSON.parse(fs.readFileSync(hooksJsonPath, 'utf8'));
      if (hooksConfig.hooks?.UserPromptSubmit) {
        userPromptBugWarning = `Warning: UserPromptSubmit hook in plugins may not trigger (GitHub #20659). Workaround: Add to ~/.claude/settings.json. See docs/TROUBLESHOOTING.md`;
      }
    }
  } catch (e) {
    debugLog('SessionStart', 'UserPromptSubmit bug check failed', { error: e.message });
  }

  // Scan skills for context:fork configuration (FIX-04)
  const forkEnabledSkills = [];
  try {
    const skillsDir = path.join(__dirname, '../../skills');
    if (fs.existsSync(skillsDir)) {
      const skills = fs.readdirSync(skillsDir);
      for (const skill of skills) {
        const skillMdPath = path.join(skillsDir, skill, 'SKILL.md');
        if (fs.existsSync(skillMdPath)) {
          const content = fs.readFileSync(skillMdPath, 'utf8');
          const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
          if (frontmatterMatch) {
            const frontmatter = frontmatterMatch[1];
            if (frontmatter.includes('context: fork') || frontmatter.includes('context:fork')) {
              const mergeResult = !frontmatter.includes('mergeResult: false');
              forkEnabledSkills.push({ name: skill, mergeResult });
            }
          }
        }
      }
    }
    if (forkEnabledSkills.length > 0) {
      debugLog('SessionStart', 'Fork-enabled skills detected', { skills: forkEnabledSkills });
    }
  } catch (e) {
    debugLog('SessionStart', 'Skill fork scan failed', { error: e.message });
  }

  // Preload common imports (FIX-05)
  if (importResolver) {
    const commonImports = [
      '${PLUGIN_ROOT}/templates/shared/api-patterns.md',
      '${PLUGIN_ROOT}/templates/shared/error-handling.md'
    ];
    let loadedCount = 0;
    for (const importPath of commonImports) {
      try {
        const resolved = importPath.replace('${PLUGIN_ROOT}', path.join(__dirname, '../..'));
        if (fs.existsSync(resolved)) {
          loadedCount++;
        }
      } catch (e) {
        // Ignore individual import errors
      }
    }
    debugLog('SessionStart', 'Import preload check', { available: loadedCount, total: commonImports.length });
  }

  return {
    importResolver,
    forkEnabledSkills,
    userPromptBugWarning
  };
}

module.exports = { run };
