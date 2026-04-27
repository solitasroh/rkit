#!/usr/bin/env node
/**
 * Smoke test for lib/permission-manager after Cycle 1 / C5 cleanup.
 *
 * Goal: verify the embedded MCU/MPU/WPF safety policy survived the migration
 * from `context-hierarchy.getHierarchicalConfig()` to the new
 * `getConfiguredPermissions()` (DEFAULT_PERMISSIONS ∪ rkit.config.json).
 *
 * Run: node tests/permission-matrix.smoke.test.js
 */

const p = require('../lib/permission-manager');

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
// TC-1: public API surface preserved
// ============================================================
check('TC-1.1 checkPermission exported',       typeof p.checkPermission === 'function');
check('TC-1.2 getToolPermissions exported',    typeof p.getToolPermissions === 'function');
check('TC-1.3 getAllPermissions exported',     typeof p.getAllPermissions === 'function');
check('TC-1.4 shouldBlock exported',           typeof p.shouldBlock === 'function');
check('TC-1.5 requiresConfirmation exported',  typeof p.requiresConfirmation === 'function');
check('TC-1.6 PERMISSION_LEVELS exported',     typeof p.PERMISSION_LEVELS === 'object');
check('TC-1.7 DEFAULT_PERMISSIONS exported',   typeof p.DEFAULT_PERMISSIONS === 'object');

// ============================================================
// TC-2: embedded safety matrix (DEFAULT ∪ rkit.config.json#permissions)
// ============================================================
const matrix = [
  // DEFAULT_PERMISSIONS
  ['rm -rf /',                                    'deny',  'rm -rf must be DENY'],
  ['rm -r /tmp/foo',                              'ask',   'rm -r must ASK'],
  ['git push --force origin main',                'deny',  'git push --force must DENY'],
  ['git reset --hard HEAD',                       'ask',   'git reset --hard must ASK'],
  // rkit.config.json — embedded safety
  ['dd if=src of=/dev/sda',                       'ask',   'dd if= must ASK (MPU storage safety)'],
  ['mkfs.ext4 /dev/sda',                          'ask',   'mkfs must ASK (MPU storage safety)'],
  ['st-flash erase',                              'ask',   'st-flash erase must ASK (MCU flash safety)'],
  ['STM32_Programmer_CLI -c port=SWD -e all',     'ask',   'STM32_Programmer_CLI -e all must ASK (MCU flash safety)'],
  // Tool-level fallback
  ['echo hello',                                  'allow', 'plain echo must ALLOW (Bash default)'],
];

for (const [cmd, expected, label] of matrix) {
  const got = p.checkPermission('Bash', cmd);
  check(`TC-2 ${label}`, got === expected, `cmd=${cmd} expected=${expected} got=${got}`);
}

// ============================================================
// TC-3: getAllPermissions returns merged map (rkit.config keys present)
// ============================================================
{
  const all = p.getAllPermissions();
  check('TC-3.1 returns object',                  typeof all === 'object' && all !== null);
  check('TC-3.2 contains DEFAULT key (rm -rf*)',  all['Bash(rm -rf*)'] === 'deny');
  check('TC-3.3 contains rkit.config key (dd if=*)', all['Bash(dd if=*)'] === 'ask');
  check('TC-3.4 contains rkit.config key (st-flash erase*)', all['Bash(st-flash erase*)'] === 'ask');
  check('TC-3.5 contains rkit.config key (mkfs*)', all['Bash(mkfs*)'] === 'ask');
}

// ============================================================
// TC-4: shouldBlock + requiresConfirmation parity
// ============================================================
{
  const block1 = p.shouldBlock('Bash', 'rm -rf /');
  check('TC-4.1 rm -rf blocked',           block1.blocked === true && block1.permission === 'deny');

  const block2 = p.shouldBlock('Bash', 'echo hi');
  check('TC-4.2 echo not blocked',         block2.blocked === false && block2.permission === 'allow');

  const conf1 = p.requiresConfirmation('Bash', 'dd if=x of=/dev/sda');
  check('TC-4.3 dd requires confirmation', conf1.requiresConfirmation === true && conf1.permission === 'ask');
}

// ============================================================
// TC-5: missing core barrel — graceful (DEFAULT only, no throw)
// ============================================================
//   We don't unload the cache here; just verify that DEFAULT_PERMISSIONS itself
//   covers the most critical case even without config merge.
{
  const def = p.DEFAULT_PERMISSIONS;
  check('TC-5.1 DEFAULT contains rm -rf deny',          def['Bash(rm -rf*)'] === 'deny');
  check('TC-5.2 DEFAULT contains git push --force deny', def['Bash(git push --force*)'] === 'deny');
  check('TC-5.3 DEFAULT covers basic tools',            def.Write === 'allow' && def.Edit === 'allow' && def.Read === 'allow' && def.Bash === 'allow');
}

// ============================================================
// Summary
// ============================================================
console.log(`\nResult: ${pass} passed, ${fail} failed`);
if (fail > 0) {
  process.exitCode = 1;
} else {
  console.log('OK: permission-matrix smoke test passed');
}
