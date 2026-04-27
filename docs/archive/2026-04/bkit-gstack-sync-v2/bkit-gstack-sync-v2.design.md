---
template: design
version: 1.2
---

# bkit-gstack-sync-v2 Design Document — Cycle 1

> **Summary**: bkit v2.1.0 S1 cleanup 패턴(`21d35d6`)을 rkit에 적용한다. 작업 단위는 **dead 파일 5개 삭제 + live 파일 3개 삭제 + `lib/context/index.js` facade 축소**다. 이 과정에서 드러난 `import-resolver.js` / `skill-orchestrator.js`의 잔여 broken bridge(`_common`/`core` 미정의 ReferenceError 위험)를 함께 수정한다. 추가로 audit-logger v2.1.10 PII redaction(`sanitizeDetails`) + CATEGORIES enum 확장을 도입한다.
>
> **Project**: rkit
> **Target Version**: v0.9.14
> **Author**: 노수장
> **Date**: 2026-04-27
> **Status**: Draft
> **Branch**: `feature/bkit-gstack-sync-v2`
> **Plan Doc**: [bkit-gstack-sync-v2.plan.md](../../01-plan/features/bkit-gstack-sync-v2.plan.md)

---

## 1. Overview

### 1.1 Design Goals

1. **bkit S1 cleanup 패턴 적용**: rkit의 dead 파일 5개와 live 파일 3개를 정리하고, `lib/context/index.js`는 bkit과 동일한 5 live 모듈 facade로 축소한다. rkit 도메인 분기(`.rkit/`, `.claude/rkit/`, `rkitVersion`)는 보존.
2. **잔여 broken bridge 동시 수정**: 정리 작업 중 발견된 `import-resolver.js:17-22` `_common` 미정의 결함과 `skill-orchestrator.js:23-28` 동일 결함을 단일 PR로 정리.
3. **audit log 위생 강화**: `validateAndNormalize` 파스스루를 PII redaction이 적용되는 sanitize 경로로 교체.
4. **회귀 0**: SessionStart hook 출력 byte-diff ≤ 5%, 단위/통합 테스트 PASS 유지, audit log schema 하위 호환.

### 1.2 Design Principles

- **추가-비파괴 정리**: 새 모듈은 신설하지 않고 기존 파일에 인라인 또는 default fallback으로 흡수.
- **명시적 분기 보존**: `.rkit/`, `.claude/rkit/`, `rkitVersion`, `MCUKIT_VERSION` 같은 rkit 분기는 sync 대상 아님(주석으로 명시).
- **Graceful Degradation**: lazy require + null 분기로 의존성 누락 시 기본값 fallback.
- **단일 PR 단위 감축**: 약 1,300 LOC 감소 + 결함 3건 정리를 하나의 feature 브랜치 안에서 단계 커밋.

### 1.3 Reference Commits

| 출처 | 커밋 | 본 Design 반영 |
|---|---|---|
| bkit | `21d35d6` (v2.1.0 S1 dead cleanup) | Group A/B 처리 패턴 |
| bkit | `0940fa5` (v2.1.10 audit-logger sanitize C2) | sanitizeDetails 함수 |
| bkit | v2.1.8 B2 commit (CATEGORIES extension) | CATEGORIES enum 확장 |
| bkit | `lib/permission-manager.js` (HEAD) | context-hierarchy 제거 패턴 참고. rkit은 안전 정책 보존을 위해 core config 병합 방식으로 분기 |
| bkit | `lib/import-resolver.js` (HEAD) | `getCore()` lazy + `getUserConfigDir()` 인라인 |

---

## 2. 현재 상태 진단

### 2.1 결함 인벤토리

| ID | 파일 | 라인 | 결함 |
|---|---|---|---|
| **DEF-1** | `lib/import-resolver.js` | 17-22 | `_common` 변수 미정의. `getCommon()` 호출 시 `ReferenceError: _common is not defined`. body 비어있음(`if (!_common) { }`). |
| **DEF-2** | `lib/import-resolver.js` | 47-50, 85, 99, 128 | `core` 변수 미정의. `core.PLUGIN_ROOT/PROJECT_DIR/debugLog` 참조 시 `ReferenceError`. require 호출 부재. |
| **DEF-3** | `lib/skill-orchestrator.js` | 23-28 | `_common` 변수 미정의. `getCommon()` body 비어있음. import-resolver와 동일 패턴. |
| **DEF-4** | `lib/import-resolver.js` | 44 | `const hierarchy = getHierarchy()` 호출 후 50번 라인에서만 사용 — 변수가 제대로 사용되지만 hierarchy 의존성 자체가 정리 대상. |

> **현재 silent fail 메커니즘**: 위 결함은 호출 시점이 적기 때문에 표면화되지 않음. `hooks/startup/context-init.js:36, 98-121`에서 `safeRequire` + try/catch로 감싸져 있어 ReferenceError 발생 시 silent skip. 즉 **`startupImports` 기능은 사실상 동작하지 않는 상태**(R-7 식별).

### 2.2 모듈 의존 그래프 (현재)

```
hooks/startup/context-init.js
   ├─ safeRequire('lib/context-hierarchy.js') ─┐
   ├─ safeRequire('lib/memory-store.js')        │
   ├─ safeRequire('lib/import-resolver.js') ──┐ │
   └─ safeRequire('lib/context-fork.js') ─────┘ │
                                                │
lib/permission-manager.js                       │
   └─ require('./context-hierarchy.js') ────────┤
                                                │
lib/import-resolver.js (broken)                 │
   ├─ require('./context-hierarchy.js') ───────┘
   └─ uses `core.*` (미정의 ReferenceError)

lib/skill-orchestrator.js (broken)
   └─ getCommon() (미정의 ReferenceError)

lib/context/index.js (cascade dead)
   ├─ require('./self-healing')
   ├─ require('./ops-metrics')
   └─ require('./decision-record')
```

### 2.3 모듈 의존 그래프 (Cycle 1 완료 후)

```
hooks/startup/context-init.js (slim)
   └─ rkit core: paths/level/debug/config (직접 require)

lib/permission-manager.js (slim)
   ├─ core (lazy barrel) — getConfig + debugLog 단일 진입점
   ├─ DEFAULT_PERMISSIONS와 core.getConfig('permissions', {}) 병합
   └─ core.debugLog 안전 호출 (없으면 no-op)

lib/import-resolver.js (fixed)
   ├─ getCore() lazy → core.PLUGIN_ROOT/PROJECT_DIR/debugLog
   └─ getUserConfigDir() 인라인 (`.claude/rkit`)

lib/skill-orchestrator.js (fixed)
   └─ broken getCommon() 제거

lib/context/index.js (slim, 5 live re-export)
   ├─ context-loader / impact-analyzer
   ├─ invariant-checker / scenario-runner
   └─ (self-healing / ops-metrics / decision-record 제거)
```

---

## 3. 상세 설계 — FR별

### 3.1 FR-01 — Group A Dead 파일 정리 + context facade 정합

**대상 파일 (삭제)**:
- `lib/pdca/do-detector.js` (252 LOC, 사용처 0)
- `lib/core/backup-scheduler.js` (129 LOC, 사용처 0)
- `lib/context/self-healing.js` (179 LOC)
- `lib/context/ops-metrics.js` (237 LOC)
- `lib/context/decision-record.js` (사용처 0)

**대상 파일 (축소)**: `lib/context/index.js`

**변경 전 (rkit 현재)**:
```js
const selfHealing = require('./self-healing');
const opsMetrics = require('./ops-metrics');
const decisionRecord = require('./decision-record');

module.exports = {
  // context-loader / impact-analyzer / invariant-checker / scenario-runner ...
  diagnose: selfHealing.diagnose,
  collectMetrics: opsMetrics.collectMetrics,
  saveBenchmark: opsMetrics.saveBenchmark,
  loadBenchmarkHistory: opsMetrics.loadBenchmarkHistory,
  recordDecision: decisionRecord.recordDecision,
  listDecisions: decisionRecord.listDecisions,
};
```

**변경 후** (bkit `lib/context/index.js`와 동일한 5 모듈 export):
```js
const contextLoader = require('./context-loader');
const impactAnalyzer = require('./impact-analyzer');
const invariantChecker = require('./invariant-checker');
const scenarioRunner = require('./scenario-runner');

module.exports = {
  loadPlanContext: contextLoader.loadPlanContext,
  loadDesignContext: contextLoader.loadDesignContext,
  extractContextAnchor: contextLoader.extractContextAnchor,
  injectAnchorToTemplate: contextLoader.injectAnchorToTemplate,

  analyzeImpact: impactAnalyzer.analyzeImpact,
  getMemoryImpact: impactAnalyzer.getMemoryImpact,
  getDtsImpact: impactAnalyzer.getDtsImpact,
  getDependencyImpact: impactAnalyzer.getDependencyImpact,

  checkInvariants: invariantChecker.checkInvariants,

  runScenario: scenarioRunner.runScenario,
  getScenarioCommands: scenarioRunner.getScenarioCommands,
};
```

**Acceptance**:
- `node -e "const c=require('./lib/context'); console.log(Object.keys(c).sort())"` → `[analyzeImpact, checkInvariants, extractContextAnchor, getDependencyImpact, getDtsImpact, getMemoryImpact, getScenarioCommands, injectAnchorToTemplate, loadDesignContext, loadPlanContext, runScenario]` (11 keys, diagnose/collectMetrics/recordDecision 등 제거됨)
- 5 dead 파일 grep 후 사용처 0 재확인 후 삭제

---

### 3.2 FR-02 — `lib/context-fork.js` 삭제 + `context-init.js` ContextFork 블록 제거

**파일 삭제**: `lib/context-fork.js` (227 LOC)

**`hooks/startup/context-init.js` 변경**:

| 위치 | 변경 |
|---|---|
| L36 | `const contextFork = safeRequire('../../lib/context-fork.js');` 제거 |
| L123-134 | "Context Fork cleanup" 블록 12 라인 제거 (`if (contextFork) { ... contextFork.getActiveForks() ... clearAllForks() ... }`) |
| L199-206 | 반환 객체에서 `contextFork` 키 제거 |
| L30 | JSDoc `@returns`에서 `contextFork: object|null` 키 제거 |

**Acceptance**: hook 출력에 `Cleared stale forks` 라인 사라짐, 정상 종료.

---

### 3.3 FR-03 — `lib/context-hierarchy.js` 삭제 + 3 사용처 정리 (가장 큰 변경)

**파일 삭제**: `lib/context-hierarchy.js` (276 LOC)

#### 3.3.1 `hooks/startup/context-init.js`

| 위치 | 변경 |
|---|---|
| L33 | `const contextHierarchy = safeRequire('../../lib/context-hierarchy.js');` 제거 |
| L56-75 | "Context Hierarchy initialization" 블록 20 라인 제거 |
| L171-174 | `forkEnabledSkills`를 `contextHierarchy.setSessionContext`로 보존하던 코드 제거 (`forkEnabledSkills`는 반환 객체로만 노출) |
| L199-206 | 반환 객체에서 `contextHierarchy` 키 제거 |

#### 3.3.2 `lib/permission-manager.js` — context-hierarchy 제거 + rkit 권한 정책 보존

**핵심 결정 (D-2 적용)**: `context-hierarchy.js` 의존은 제거한다. 단, rkit은 `rkit.config.json`의 `permissions`가 MCU/MPU 안전 정책의 일부이므로 bkit HEAD처럼 `DEFAULT_PERMISSIONS` 단독으로 단순화하지 않는다. `lib/core` barrel의 `getConfig('permissions', {})`를 통해 프로젝트 설정을 읽고 `DEFAULT_PERMISSIONS`와 병합한다. require 진입점은 `import-resolver.js`와 동일하게 `./core` barrel로 통일한다(M-1).

**변경 전**:
```js
let _hierarchy = null;
function getHierarchy() {
  if (!_hierarchy) { _hierarchy = require('./context-hierarchy.js'); }
  return _hierarchy;
}

function checkPermission(toolName, toolInput = '') {
  const hierarchy = getHierarchy();
  const permissions = hierarchy.getHierarchicalConfig('permissions', DEFAULT_PERMISSIONS);
  // ...
}
```

**변경 후** (rkit 분기: config permissions 보존, `./core` barrel 단일 진입점):
```js
// NOTE: context-hierarchy.js was removed in bkit-gstack-sync-v2.
// rkit keeps project/user permission policy via core config (barrel).
let _core = null;
function getCore() {
  if (!_core) {
    try { _core = require('./core'); } catch (_) { _core = null; }
  }
  return _core;
}

function debugLog(message, meta) {
  const core = getCore();
  if (core && core.debugLog) {
    core.debugLog('Permission', message, meta);
  }
}

function getConfiguredPermissions() {
  const core = getCore();
  const configured = core && core.getConfig ? core.getConfig('permissions', {}) : {};
  return { ...DEFAULT_PERMISSIONS, ...(configured || {}) };
}

function checkPermission(toolName, toolInput = '') {
  const permissions = getConfiguredPermissions();
  // ... (이하 매칭 로직 동일)
}
```

→ `getHierarchy()` 제거. `getDebug()` 호출(L82)은 `debugLog(...)` helper로 교체. `getToolPermissions()`와 `getAllPermissions()`도 `getConfiguredPermissions()`를 사용한다. `_core`/`getCore()` 명명은 §3.3.3 `import-resolver.js`와 동일하여 두 파일이 같은 진입 패턴을 공유한다.

**보존해야 하는 rkit 설정 예시**:
```json
{
  "Bash(dd if=*)": "ask",
  "Bash(mkfs*)": "ask",
  "Bash(st-flash erase*)": "ask",
  "Bash(STM32_Programmer_CLI*-e all*)": "ask",
  "Bash(git push --force*)": "deny"
}
```

**영구 회귀 가드 (M-2)**: 위 안전 정책 매트릭스는 §5 C5 커밋에서 [tests/permission-matrix.smoke.test.js](../../../tests/permission-matrix.smoke.test.js)로 신설하여 PR과 함께 머지된다. §6.1 TC-5는 그 smoke test를 호출만 한다.

#### 3.3.3 `lib/import-resolver.js` — DEF-1, DEF-2, DEF-4 동시 수정

**bkit HEAD 패턴 적용**:

```js
const fs = require('fs');
const path = require('path');
const os = require('os');

// NOTE: context-hierarchy.js / common.js were removed in bkit-gstack-sync-v2.
// getUserConfigDir() inlined here; PLUGIN_ROOT/PROJECT_DIR/debugLog migrate to lib/core.
let _core = null;
function getCore() {
  if (!_core) {
    try { _core = require('./core'); } catch (_) { _core = null; }
  }
  return _core;
}

/**
 * Get user config directory (was in context-hierarchy.js, now inlined).
 * rkit branch: `.claude/rkit` (bkit upstream uses `.claude/bkit`).
 * @returns {string}
 */
function getUserConfigDir() {
  return path.join(os.homedir(), '.claude', 'rkit');
}
```

**`resolveVariables()` 수정**:
```js
function resolveVariables(importPath) {
  const core = getCore();
  return importPath
    .replace(/\$\{PLUGIN_ROOT\}/g, core ? core.PLUGIN_ROOT : '')
    .replace(/\$\{PROJECT\}/g,    core ? core.PROJECT_DIR : '')
    .replace(/\$\{USER_CONFIG\}/g, getUserConfigDir());
}
```

**`loadImportedContent`/`resolveImports` 수정**: `core.debugLog(...)` → `(getCore()?.debugLog ?? (() => {}))(...)`로 안전 호출. 또는 `const core = getCore(); if (core) core.debugLog(...)` 형태.

**rkit 분기 보존**: `getUserConfigDir()`은 `.claude/rkit/` (bkit은 `.claude/bkit`).

#### 3.3.4 `lib/skill-orchestrator.js` — DEF-3 정리

**현재 (broken)**:
```js
let _importResolver = null;
function getCommon() {
  if (!_common) {  // ReferenceError
    
  }
  return _common;
}
function getImportResolver() { /* OK */ }
```

**변경 후**:
```js
// NOTE: common.js was removed in bkit-gstack-sync-v2; getCommon() removed.
let _importResolver = null;
function getImportResolver() {
  if (!_importResolver) {
    try { _importResolver = require('./import-resolver.js'); } catch (_) { _importResolver = null; }
  }
  return _importResolver;
}
```

→ `getCommon()` 함수 자체 삭제. 호출자 grep 후 0건 확인 (현재 broken이라 호출 자체가 안 됐을 것).

---

### 3.4 FR-04 — `lib/memory-store.js` 삭제

**파일 삭제**: `lib/memory-store.js` (185 LOC)

**`hooks/startup/context-init.js` 변경**:

| 위치 | 변경 |
|---|---|
| L34 | `const memoryStore = safeRequire('../../lib/memory-store.js');` 제거 |
| L77-95 | "Memory Store initialization" 블록 19 라인 제거 (sessionCount/lastSession persistence) |
| L199-206 | 반환 객체에서 `memoryStore` 키 제거 |

**의도적 손실**: sessionCount/lastSession 추적 사라짐. R-1로 명시. bkit도 동일하게 hook 그대로 두고 파일만 지웠으나(graceful no-op) rkit은 hook까지 함께 정리해 더 깨끗한 상태로 갈 수 있음.

---

### 3.5 FR-05 — `audit-logger.js` `sanitizeDetails()` 도입

**대상 파일**: `lib/audit/audit-logger.js`

**추가 상수** (헤더 영역):
```js
// v2.1.10 (C2 fix): Sensitive key blacklist + value length cap.
// Prevents accidental PII/token leakage into .rkit/audit/*.jsonl.
const SENSITIVE_KEY_PATTERNS = [
  /password/i,
  /secret/i,
  /token/i,
  /api[_-]?key/i,
  /authorization/i,
  /cookie/i,
  /session[_-]?key/i,
  /private[_-]?key/i,
];
const DETAILS_VALUE_MAX_CHARS = 500;
```

**추가 함수** (`validateAndNormalize` 위에 배치):
```js
function sanitizeDetails(details) {
  if (!details || typeof details !== 'object' || Array.isArray(details)) return {};
  const out = {};
  for (const [key, value] of Object.entries(details)) {
    if (SENSITIVE_KEY_PATTERNS.some((re) => re.test(key))) {
      out[key] = '[REDACTED]';
      continue;
    }
    if (typeof value === 'string' && value.length > DETAILS_VALUE_MAX_CHARS) {
      out[key] = value.slice(0, DETAILS_VALUE_MAX_CHARS) + '…[truncated]';
      continue;
    }
    if (
      value === null ||
      typeof value === 'number' ||
      typeof value === 'boolean' ||
      typeof value === 'string'
    ) {
      out[key] = value;
    } else if (typeof value === 'object') {
      try {
        const nested = {};
        for (const [nk, nv] of Object.entries(value)) {
          if (SENSITIVE_KEY_PATTERNS.some((re) => re.test(nk))) {
            nested[nk] = '[REDACTED]';
          } else if (typeof nv === 'string' && nv.length > DETAILS_VALUE_MAX_CHARS) {
            nested[nk] = nv.slice(0, DETAILS_VALUE_MAX_CHARS) + '…[truncated]';
          } else {
            nested[nk] = nv;
          }
        }
        out[key] = nested;
      } catch {
        out[key] = '[non-serializable]';
      }
    }
  }
  return out;
}
```

**`validateAndNormalize` 수정**: `details` 패스스루 라인을 sanitize 호출로 교체.

**변경 전**:
```js
details: entry.details && typeof entry.details === 'object' ? entry.details : {},
```

**변경 후**:
```js
details: sanitizeDetails(entry.details),
```

---

### 3.6 FR-06 — CATEGORIES enum 확장

**현재**:
```js
const CATEGORIES = ['pdca', 'file', 'config', 'control', 'team', 'quality'];
```

**변경 후** (bkit v2.1.8 B2):
```js
// v2.1.8 (B2 fix): extended CATEGORIES enum to preserve convenience logger categories
const CATEGORIES = ['pdca', 'file', 'config', 'control', 'team', 'quality', 'permission', 'checkpoint', 'trust', 'system'];
```

→ rkit이 permission-manager / checkpoint-manager / trust 관련 audit를 남길 때 무효 카테고리 폴백되지 않고 정확히 분류됨.

---

### 3.7 FR-07 — import-resolver `_common`/`core` 결함 수정 + smoke test

FR-03의 §3.3.3에서 함께 처리 (위 변경에 흡수).

**추가 산출물**: smoke test (Do 단계 산출물)

```js
// tests/import-resolver.smoke.test.js (신규)
const r = require('../lib/import-resolver');

console.assert(typeof r.resolveVariables === 'function', 'resolveVariables 함수 존재');
console.assert(typeof r.resolveImportPath === 'function', 'resolveImportPath 함수 존재');
console.assert(typeof r.resolveImports === 'function', 'resolveImports 함수 존재');

// resolveVariables: getCore null이어도 throw 없이 빈 문자열 치환
const out = r.resolveVariables('${PLUGIN_ROOT}/foo/${USER_CONFIG}/bar');
console.assert(typeof out === 'string', 'resolveVariables는 string 반환');
console.assert(out.includes('.claude/rkit') || out.includes('.claude\\rkit'), 'USER_CONFIG는 .claude/rkit 경로');

// resolveImports: imports 없는 frontmatter는 빈 결과
const empty = r.resolveImports({}, __filename);
console.assert(empty.content === '', '빈 imports → 빈 content');
console.assert(Array.isArray(empty.errors) && empty.errors.length === 0, '빈 imports → 빈 errors');

console.log('OK: import-resolver smoke test passed');
```

---

## 4. 모듈 의존성 변경 매트릭스

| 항목 | 변경 전 의존 | 변경 후 의존 |
|---|---|---|
| `hooks/startup/context-init.js` | context-hierarchy, memory-store, import-resolver, context-fork (4 safeRequire) | import-resolver만 유지(common imports preload). 나머지 3 제거. |
| `lib/permission-manager.js` | context-hierarchy (lazy), core/debug (lazy) | core (lazy barrel). context-hierarchy 제거, rkit.config permissions 병합 유지. import-resolver와 동일 진입 패턴(`getCore()`). |
| `lib/import-resolver.js` | context-hierarchy (lazy), undefined `core`(broken) | core (lazy), `getUserConfigDir` 인라인 |
| `lib/skill-orchestrator.js` | undefined `_common`(broken), import-resolver (lazy) | import-resolver (lazy) only |
| `lib/context/index.js` | 7 모듈 re-export | 4 live 모듈 re-export |
| `lib/audit/audit-logger.js` | (외부 의존 없음) | (변경 없음) — 함수 내부 강화 |

---

## 5. Implementation Order (Do 단계 커밋 시퀀스)

bkit 정합 우선 + 회귀 위험 최소화 순서로 6 커밋 단위로 진행:

| # | 커밋 | 파일 | 검증 |
|---|---|---|---|
| **C1** | `refactor(audit): add sanitizeDetails + extend CATEGORIES (bkit v2.1.10/v2.1.8 sync)` | `lib/audit/audit-logger.js` (+~80 LOC, -2 LOC) | 신규 audit TC 4건 PASS |
| **C2** | `refactor(context): trim lib/context/index.js to 5 live re-exports + delete 3 dead modules` | `lib/context/index.js` 축소, `self-healing.js`/`ops-metrics.js`/`decision-record.js` 삭제 | `node -e "require('./lib/context')"` smoke + grep 0건 |
| **C3** | `refactor(orphan): delete dead modules do-detector + backup-scheduler` | `lib/pdca/do-detector.js`, `lib/core/backup-scheduler.js` 삭제 | grep 0건 + test-all.js PASS |
| **C4** | `refactor(import-resolver): fix broken _common/core bridges + inline getUserConfigDir (bkit S1 sync)` | `lib/import-resolver.js`, `lib/skill-orchestrator.js` (broken `getCommon` 제거) | smoke test 신규, 기존 통합 테스트 PASS |
| **C5** | `refactor(permission-manager): remove context-hierarchy dependency, preserve rkit config permissions via core barrel` | `lib/permission-manager.js`, `tests/permission-matrix.smoke.test.js` (신규) | 권한 매트릭스 smoke test PASS (TC-5) |
| **C6** | `refactor(hooks): slim context-init.js + delete context-fork/context-hierarchy/memory-store` | `hooks/startup/context-init.js` 정리, 3 lib 파일 삭제 | hook 실행 exit 0 + JSON 출력, byte-diff ≤5%, test-all.js PASS |

> 순서 이유: C1(독립), C2(읽기 전용 facade), C3(완전 dead), C4(broken 수정으로 안정화), C5(permission), C6(가장 큰 표면 — 마지막). 각 커밋이 독립적으로 회귀 검증 가능.

---

## 6. Verification

### 6.1 Unit / Smoke Tests

| TC ID | 대상 | 명령 | 기대 |
|---|---|---|---|
| TC-1 | context facade | `node -e "console.log(Object.keys(require('./lib/context')).sort())"` | 11 keys, dead 모듈 export 부재 |
| TC-2 | grep dead 사용처 | `grep -rn "do-detector\|backup-scheduler\|context/self-healing\|context/ops-metrics\|context/decision-record" lib/ hooks/ scripts/ skills/ servers/ scripts/` | 0건 |
| TC-3 | runtime references to removed live modules | `grep -rnE "require\\(.+(context-fork\|context-hierarchy\|memory-store)" lib/ hooks/` (require 기반 런타임 참조만) | 0건. NOTE 주석은 의도적 잔존이므로 검증 패턴에서 제외. plain `grep "context-fork\|..."`는 이 NOTE 주석이 매치되므로 사용하지 않음. |
| TC-4 | import-resolver smoke | `node tests/import-resolver.smoke.test.js` | OK |
| TC-5 | permission-manager config matrix | `node tests/permission-matrix.smoke.test.js` (C5에서 신설) — 6 안전 정책 케이스(`rm -rf`, `dd if=`, `mkfs`, `st-flash erase`, `STM32_Programmer_CLI -e all`, `git push --force`) 일괄 검증. `rkit.config.json`의 permissions 병합 결과까지 포함. | exit 0, "OK" 출력 |
| TC-6 | audit sanitizeDetails — PII | `audit.writeAuditLog({action:'control_action', target:'x', details:{password:'p1', token:'t1', name:'ok'}})` → 파일 마지막 라인 JSON parse → `details.password === '[REDACTED]'` | PASS |
| TC-7 | audit sanitizeDetails — truncate | `details:{long: 'x'.repeat(600)}` → `details.long.startsWith('x'.repeat(500)) && details.long.endsWith('…[truncated]')` | PASS |
| TC-8 | audit CATEGORIES | `category: 'permission'` 입력 → 출력에 `category: 'permission'` 보존 | PASS |
| TC-9 | hook exit 0 | `node hooks/session-start.js` 또는 PowerShell에서 `'{}' | node hooks/session-start.js` | exit 0, JSON 정상 출력 |

### 6.2 Regression Tests

| 항목 | 명령 |
|---|---|
| 기존 단위/통합 | `node test-all.js` |
| instinct 통합 | `node tests/instinct-integration.test.js` |
| 아키텍처 E2E | `node tests/test-architecture-e2e.js` |
| 기존 audit log 호환 | `.rkit/audit/2026-04-*.jsonl` 샘플 라인을 v2 schema(rkitVersion 키 포함)로 파싱 → 모든 필드 정상 |

### 6.3 Hook Output Byte-Diff

```powershell
# Windows/PowerShell 기준. checkout 없이 현재 브랜치에서 baseline을 먼저 저장한다.
$before = Join-Path $env:TEMP "rkit-hook-before.json"
$after = Join-Path $env:TEMP "rkit-hook-after.json"

# Do 시작 전 1회 실행
node hooks/session-start.js > $before

# 변경 적용 후 실행
node hooks/session-start.js > $after

# PowerShell 내장 diff
Compare-Object (Get-Content $before) (Get-Content $after)
```

기대: `additionalContext` 본문 byte-diff ≤ 5%(정보성 차이만), JSON schema 동일.

---

## 7. Decision Records

| ID | 결정 | 적용 |
|----|------|------|
| **D-1** | `lib/context/index.js` 보존 (5 live 모듈 re-export로 축소) | §3.1 적용 |
| **D-2** | `permission-manager.js`에서 `getHierarchicalConfig` 호출 제거. 단, rkit.config `permissions`는 core config 병합으로 보존 | §3.3.2 적용 |
| **D-3** | `lib/skill-orchestrator.js` broken `getCommon()` 동시 정리 (Cycle 1 포함) | §3.3.4 적용 |
| **D-4** | gstack 4 스킬 강화 → Cycle 1.5로 분리 (본 Design 범위 외) | OOS 명시 |
| **D-5** | `MCUKIT_VERSION` 상수 유지 (`BKIT_VERSION` SoT 도입은 Cycle 2) | §3.5/§3.6에서 `rkitVersion` 키도 그대로 유지 |

---

## 8. Risks (Plan §4 보강)

| ID | Risk | Design 대응 |
|----|------|-------------|
| R-1 | sessionCount/lastSession 추적 손실 | §3.4 — 의도적 손실로 README/CHANGELOG에 기록 |
| R-2 | context-hierarchy 의존 동작 회귀 | §3.3.2에서 permission 설정은 core config 병합으로 보존. 다른 사용처는 §3.3.3 인라인. TC-5 매트릭스로 검증. |
| R-3 | `lib/context/index.js` 재 참조 | TC-1 smoke. `git grep "require.*'./context'\|require.*'../context'"` 0건 확인 |
| R-4 | gstack 패치 cleanup PR 회귀 | Cycle 1.5 분리 — 본 Design 범위 외 |
| R-5 | sanitizeDetails 도입 부작용 | `git grep "writeAuditLog.*password\|writeAuditLog.*token"` 호출처 0건 확인 |
| R-6 | rebase 충돌 | feature/bkit-gstack-sync-v2 단발 PR |
| **R-7** (신규) | DEF-1~3 결함이 silent하게 startupImports 기능을 무력화 중 | C4 커밋 후 startupImports 정상 동작 확인 (`rkit.config.json`에 `startupImports` 설정 후 hook 출력 확인) |

---

## 9. Out of Scope (재확인)

- gstack 4 스킬 후속 패치 → Cycle 1.5
- bkit `lib/domain/`, `lib/orchestrator/`, `lib/qa/`, `lib/cc-regression/`, `lib/infra/telemetry` → Cycle 2
- bkit `lib/core/{version,context-budget,worktree-detector,session-ctx-fp,session-title-cache}` → Cycle 2
- bkit `lib/pdca/status.js` 분할 → Cycle 2
- audit-logger OTEL mirror (`getTelemetrySink` + `createOtelSink`) → Cycle 2 (telemetry 의존)

---

## 10. Approval

| Stakeholder | Decision | Notes |
|-------------|----------|-------|
| 노수장 (사용자) | Pending | Design 검토 후 Do 단계(C1 커밋부터) 진입 |

---

## Appendix — Reference 파일 위치

- bkit `21d35d6` (S1 cleanup): `references/bkit-claude-code/` 에서 `git -C ... show 21d35d6`
- bkit `0940fa5` (audit-logger v2.1.10 sanitize): 동상
- bkit HEAD `lib/import-resolver.js` / `lib/permission-manager.js`: 마이그레이션 패턴 참조 원본
- 분석 노트: `references/_analysis/{bkit-changes,gstack-changes,s1-cleanup-impact-on-rkit}.md`
