#!/usr/bin/env node
/**
 * Smoke test for audit-logger v2.1.10 / v2.1.8 hardening.
 * Verifies sanitizeDetails behavior (FR-05) and CATEGORIES enum extension (FR-06).
 *
 * Run: node tests/audit-sanitize.test.js
 */

const { sanitizeDetails, CATEGORIES } = require('../lib/audit/audit-logger');

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
// TC-6: PII / token / secret redaction
// ============================================================
{
  const result = sanitizeDetails({
    password: 'p1',
    token: 't1',
    api_key: 'k1',
    'api-key': 'k2',
    secret: 's1',
    authorization: 'Bearer abc',
    cookie: 'sid=xyz',
    session_key: 'sk',
    private_key: 'pk',
    name: 'ok',
    count: 42,
  });
  check('TC-6.1 password redacted',       result.password === '[REDACTED]');
  check('TC-6.2 token redacted',          result.token === '[REDACTED]');
  check('TC-6.3 api_key redacted',        result.api_key === '[REDACTED]');
  check('TC-6.4 api-key redacted',        result['api-key'] === '[REDACTED]');
  check('TC-6.5 secret redacted',         result.secret === '[REDACTED]');
  check('TC-6.6 authorization redacted',  result.authorization === '[REDACTED]');
  check('TC-6.7 cookie redacted',         result.cookie === '[REDACTED]');
  check('TC-6.8 session_key redacted',    result.session_key === '[REDACTED]');
  check('TC-6.9 private_key redacted',    result.private_key === '[REDACTED]');
  check('TC-6.10 non-sensitive preserved', result.name === 'ok');
  check('TC-6.11 numeric preserved',       result.count === 42);
}

// ============================================================
// TC-7: long string truncation (>500 chars)
// ============================================================
{
  const result = sanitizeDetails({
    long: 'x'.repeat(600),
    exact: 'y'.repeat(500),
    boundary: 'z'.repeat(501),
  });
  check('TC-7.1 600-char string truncated',
    result.long.startsWith('x'.repeat(500)) && result.long.endsWith('…[truncated]'));
  check('TC-7.2 500-char string preserved (boundary)', result.exact === 'y'.repeat(500));
  check('TC-7.3 501-char string truncated',
    result.boundary.startsWith('z'.repeat(500)) && result.boundary.endsWith('…[truncated]'));
}

// ============================================================
// TC-8: CATEGORIES enum extension (4 new categories)
// ============================================================
{
  const required = ['pdca', 'file', 'config', 'control', 'team', 'quality',
                    'permission', 'checkpoint', 'trust', 'system'];
  for (const cat of required) {
    check(`TC-8 CATEGORIES includes "${cat}"`, CATEGORIES.includes(cat));
  }
  check('TC-8 CATEGORIES length is 10', CATEGORIES.length === 10);
}

// ============================================================
// TC-9: graceful handling of bad input
// ============================================================
{
  check('TC-9.1 null  → {}',       JSON.stringify(sanitizeDetails(null)) === '{}');
  check('TC-9.2 undef → {}',       JSON.stringify(sanitizeDetails(undefined)) === '{}');
  check('TC-9.3 array → {}',       JSON.stringify(sanitizeDetails([1, 2, 3])) === '{}');
  check('TC-9.4 num   → {}',       JSON.stringify(sanitizeDetails(123)) === '{}');
  check('TC-9.5 str   → {}',       JSON.stringify(sanitizeDetails('hi')) === '{}');
  check('TC-9.6 empty → {}',       JSON.stringify(sanitizeDetails({})) === '{}');
}

// ============================================================
// TC-10: nested object redaction (one level)
// ============================================================
{
  const result = sanitizeDetails({
    user: { name: 'kim', token: 'jwt-xyz', note: 'ok' },
    payload: { long: 'a'.repeat(600), api_key: 'k', n: 7 },
  });
  check('TC-10.1 nested.token redacted',  result.user.token === '[REDACTED]');
  check('TC-10.2 nested.name preserved',  result.user.name === 'kim');
  check('TC-10.3 nested.note preserved',  result.user.note === 'ok');
  check('TC-10.4 nested long truncated',
    result.payload.long.startsWith('a'.repeat(500)) && result.payload.long.endsWith('…[truncated]'));
  check('TC-10.5 nested.api_key redacted', result.payload.api_key === '[REDACTED]');
  check('TC-10.6 nested numeric preserved', result.payload.n === 7);
}

// ============================================================
// Summary
// ============================================================
console.log(`\nResult: ${pass} passed, ${fail} failed`);
if (fail > 0) {
  process.exitCode = 1;
} else {
  console.log('OK: audit-sanitize smoke test passed');
}
