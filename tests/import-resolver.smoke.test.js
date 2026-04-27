#!/usr/bin/env node
/**
 * Smoke test for lib/import-resolver after Cycle 1 / C4 cleanup.
 * Verifies broken `_common` / `core` ReferenceError shims are gone and
 * `${USER_CONFIG}` resolves to rkit's `.claude/rkit/` branch.
 *
 * Run: node tests/import-resolver.smoke.test.js
 */

const path = require('path');
const os = require('os');
const r = require('../lib/import-resolver');

let pass = 0;
let fail = 0;

function check(name, cond, info) {
  if (cond) {
    pass++;
    console.log(`  PASS ${name}`);
  } else {
    fail++;
    console.error(`  FAIL ${name}${info ? ' — ' + info : ''}`);
  }
}

// ============================================================
// TC-1: public API surface
// ============================================================
check('TC-1.1 resolveVariables exported',          typeof r.resolveVariables === 'function');
check('TC-1.2 resolveImportPath exported',         typeof r.resolveImportPath === 'function');
check('TC-1.3 loadImportedContent exported',       typeof r.loadImportedContent === 'function');
check('TC-1.4 detectCircularImport exported',      typeof r.detectCircularImport === 'function');
check('TC-1.5 resolveImports exported',            typeof r.resolveImports === 'function');
check('TC-1.6 parseFrontmatter exported',          typeof r.parseFrontmatter === 'function');
check('TC-1.7 processMarkdownWithImports exported', typeof r.processMarkdownWithImports === 'function');
check('TC-1.8 clearImportCache exported',          typeof r.clearImportCache === 'function');
check('TC-1.9 getCacheStats exported',             typeof r.getCacheStats === 'function');
check('TC-1.10 IMPORT_CACHE_TTL exported',         typeof r.IMPORT_CACHE_TTL === 'number');

// ============================================================
// TC-2: resolveVariables — no more ReferenceError, USER_CONFIG inlined
// ============================================================
{
  const out = r.resolveVariables('${PLUGIN_ROOT}/foo/${USER_CONFIG}/bar/${PROJECT}/baz');
  check('TC-2.1 resolveVariables returns string', typeof out === 'string');

  const expectedUserConfig = path.join(os.homedir(), '.claude', 'rkit');
  // path separator depends on OS; check for both unix + win
  const userPart = out.split('/foo/')[1].split('/bar/')[0]; // platform-portable enough
  check(`TC-2.2 USER_CONFIG resolves to rkit branch (${expectedUserConfig})`,
    out.includes(expectedUserConfig) || out.includes(expectedUserConfig.replace(/\\/g, '/')),
    `got userPart=${userPart}`);

  // PLUGIN_ROOT/PROJECT may be empty when core barrel is unavailable in this run, but no throw.
  check('TC-2.3 no ReferenceError on missing core', out.length > 0);
}

// ============================================================
// TC-3: resolveImports — empty imports array yields empty result
// ============================================================
{
  const empty = r.resolveImports({}, __filename);
  check('TC-3.1 empty frontmatter → empty content',  empty.content === '');
  check('TC-3.2 empty frontmatter → empty errors',   Array.isArray(empty.errors) && empty.errors.length === 0);

  const noArr = r.resolveImports({ imports: 'not-array' }, __filename);
  check('TC-3.3 imports non-array → empty content',  noArr.content === '');

  const emptyArr = r.resolveImports({ imports: [] }, __filename);
  check('TC-3.4 imports empty array → empty content', emptyArr.content === '');
}

// ============================================================
// TC-4: parseFrontmatter — basic shape
// ============================================================
{
  const md = '---\nname: foo\nimports:\n  - ./a.md\n  - ./b.md\n---\nbody';
  const { frontmatter, body } = r.parseFrontmatter(md);
  check('TC-4.1 frontmatter parsed',          typeof frontmatter === 'object');
  check('TC-4.2 imports parsed as array',     Array.isArray(frontmatter.imports) && frontmatter.imports.length === 2);
  check('TC-4.3 imports[0] === "./a.md"',     frontmatter.imports[0] === './a.md');
  check('TC-4.4 body separated',              body.trim() === 'body');

  const noFm = r.parseFrontmatter('plain markdown without frontmatter');
  check('TC-4.5 missing frontmatter → empty fm', Object.keys(noFm.frontmatter).length === 0);
  check('TC-4.6 missing frontmatter → body untouched', noFm.body === 'plain markdown without frontmatter');
}

// ============================================================
// TC-5: cache primitives
// ============================================================
{
  r.clearImportCache();
  const stats0 = r.getCacheStats();
  check('TC-5.1 clearImportCache → size 0', stats0.size === 0);
}

// ============================================================
// Summary
// ============================================================
console.log(`\nResult: ${pass} passed, ${fail} failed`);
if (fail > 0) {
  process.exitCode = 1;
} else {
  console.log('OK: import-resolver smoke test passed');
}
