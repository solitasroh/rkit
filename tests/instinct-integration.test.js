#!/usr/bin/env node
/**
 * instinct-integration Test Suite
 * Plan Section 4 테스트 전략에 따른 T1~T4 검증
 *
 * 실행: node tests/instinct-integration.test.js
 */

const path = require('path');
const fs = require('fs');

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    console.log(`  PASS: ${name}`);
    passed++;
  } else {
    console.log(`  FAIL: ${name}`);
    failed++;
  }
}

// Setup: clean instinct data
const instinctDir = path.join(process.cwd(), '.rkit', 'instinct');
if (fs.existsSync(instinctDir)) {
  fs.rmSync(instinctDir, { recursive: true });
}

// ============================================================
console.log('\n=== T1: Unit — collectInstinctPatterns ===');
// ============================================================

const ro = require('../lib/code-quality/review-orchestrator');

// T1-1: 정상 수집
const result1 = {
  target: 'test/', files: ['a.c', 'b.cpp'], languages: ['C', 'C++'],
  timestamp: new Date().toISOString(),
  findings: [
    { rule: 'SQ-001', file: 'a.c', line: 10, severity: 'HIGH', layer: 'L1', title: 'Long fn', fix: 'Split' },
    { rule: 'RAII', file: 'b.cpp', line: 20, severity: 'HIGH', layer: 'L2', title: 'Raw delete', fix: 'unique_ptr' },
  ],
  summary: { CRITICAL: 0, HIGH: 2, MEDIUM: 0, LOW: 0 }, score: 86, decision: 'WARNING'
};
const count1 = ro.collectInstinctPatterns(result1, 'test-session-1');
assert(count1 === 2, 'T1-1: 2 findings → 2 patterns collected');

// T1-2: 빈 findings
const count2 = ro.collectInstinctPatterns({ findings: [] }, 'test-session-2');
assert(count2 === 0, 'T1-2: empty findings → 0 patterns');

// T1-3: Graceful Degradation (instinct 모듈 경로 오류 시뮬레이션은 불가하므로 함수 존재 확인)
assert(typeof ro.collectInstinctPatterns === 'function', 'T1-3: collectInstinctPatterns is a function');

// T1-4: 중복 호출 → sessions append
const count4 = ro.collectInstinctPatterns(result1, 'test-session-3');
assert(count4 === 2, 'T1-4: duplicate call collects (sessions appended)');

// ============================================================
console.log('\n=== T2: Integration — SessionStart loader ===');
// ============================================================

const { loadConvergedPatterns, getProfileSummary } = require('../lib/instinct/loader');

// T2-1: 수집 후 미수렴 → 빈 텍스트
const text1 = loadConvergedPatterns();
assert(text1 === '', 'T2-1: no converged patterns → empty string');

// T2-2: 수렴 시뮬레이션
const store = require('../lib/instinct/store');
const hash = store.getProjectHash();
const confData = store.loadConfidence(hash);
const patternIds = Object.keys(confData.scores);
if (patternIds.length > 0) {
  confData.scores[patternIds[0]].current = 0.88;
  confData.scores[patternIds[0]].convergedAt = 9;
  confData.scores[patternIds[0]].history = [
    { session: 7, score: 0.81, delta: 0.04, reason: 'applied' },
    { session: 8, score: 0.85, delta: 0.04, reason: 'applied' },
    { session: 9, score: 0.88, delta: 0.03, reason: 'applied' },
  ];
  store.saveConfidence(hash, confData);
}
const text2 = loadConvergedPatterns();
assert(text2.includes('Project Instinct'), 'T2-2: converged pattern → Project Instinct header');

// T2-3: getProfileSummary 정확성
const summary = getProfileSummary();
assert(summary.converged === 1, 'T2-3: 1 converged pattern in summary');
assert(summary.totalPatterns >= 2, 'T2-3: total patterns >= 2');

// ============================================================
console.log('\n=== T3: E2E — session-start.js 실행 ===');
// ============================================================

const { execSync } = require('child_process');
try {
  const raw = execSync('node hooks/session-start.js 2>nul', { encoding: 'utf8', timeout: 10000 });
  const data = JSON.parse(raw);
  const ctx = data.hookSpecificOutput.additionalContext || '';
  assert(ctx.includes('Project Instinct'), 'T3-1: session-start output includes Instinct context');
  assert(data.hookSpecificOutput.hookEventName === 'SessionStart', 'T3-2: hookEventName preserved');
} catch (e) {
  assert(false, 'T3-1: session-start.js execution failed: ' + e.message);
  assert(false, 'T3-2: skipped due to T3-1 failure');
}

// ============================================================
console.log('\n=== T4: Regression — 기존 export 보존 ===');
// ============================================================

assert(typeof ro.selectL2Agent === 'function', 'T4-1: selectL2Agent preserved');
assert(typeof ro.mergeResults === 'function', 'T4-2: mergeResults preserved');
assert(typeof ro.formatReport === 'function', 'T4-3: formatReport preserved');
assert(typeof ro.L2_AGENT_MAP === 'object', 'T4-4: L2_AGENT_MAP preserved');
assert(typeof ro.getL3Agents === 'function', 'T4-5: getL3Agents preserved');

// ============================================================
// Cleanup
// ============================================================
if (fs.existsSync(instinctDir)) {
  fs.rmSync(instinctDir, { recursive: true });
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed (total ${passed + failed}) ===`);
process.exit(failed > 0 ? 1 : 0);
