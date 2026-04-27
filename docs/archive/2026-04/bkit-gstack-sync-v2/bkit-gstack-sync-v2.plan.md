---
template: plan
version: 1.2
---

# bkit-gstack-sync-v2 Planning Document — Cycle 1 (Cleanup + Existing Module Hardening)

> **Summary**: bkit v2.0.6 → v2.1.10 (62 commits), gstack 2026-04-02 → HEAD (70 commits) upstream 변경 중 회귀 위험이 낮은 P0/P1 항목을 정책 "**최대한 bkit upstream에 맞춘다(불명확 분기 sync, 동작 영향 없도록)**"에 따라 통합한다. Cycle 1은 cleanup + audit hardening으로 제한하고, 스킬 동작 의미가 바뀌는 gstack 후속 패치와 신규 대형 모듈(Clean Architecture, QA Phase, cc-regression)은 후속 Cycle로 분리한다.
>
> **Project**: rkit
> **Target Version**: v0.9.14 (current package.json: v0.9.13)
> **Author**: 노수장
> **Date**: 2026-04-27
> **Status**: Draft
> **Branch**: `feature/bkit-gstack-sync-v2`

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | rkit은 이전 bkit-sync (v2.0.6 시점, 2026-04-02)에서 멈춰있어 그 후 11개 마이너 버전(v2.0.7~v2.1.10) 분량의 upstream 변경이 미반영. 특히 ① bkit이 dead로 정리한 7 파일이 rkit에 잔존(약 1,700+ LOC), ② v2.1.10 audit-logger의 PII redaction 강화 미적용, ③ gstack의 `/investigate`·`/retro`·`cso`·`review` 후속 패치 미반영. 정책상 임베디드 도메인 분기가 명시적이지 않은 항목은 모두 sync 대상. |
| **Solution** | Cycle 1로 (a) 사용처 0인 dead 파일 정리, (b) 사용처가 있는 3 파일은 bkit 패턴(lazy try/catch + hook 블록 제거)을 따라 사용처를 먼저 정리한 뒤 삭제, (c) `lib/context/index.js`는 bkit 정합을 위해 5개 live 모듈 re-export로 보존, (d) `lib/import-resolver.js`의 기존 `_common`/`core` 잔여 브릿지 결함을 함께 수정, (e) `lib/audit/audit-logger.js`에 `sanitizeDetails()` + CATEGORIES 확장 도입. gstack 스킬 후속 패치는 Cycle 1.5로 분리. |
| **Function/UX Effect** | 코드베이스 약 1,500 LOC 감소(보수성↑, 빌드/탐색 속도↑), import resolver의 기존 런타임 결함 제거, audit log의 토큰/비밀번호 누출 차단. 스킬 동작 의미 변경은 본 Cycle에서 제외하여 cleanup PR의 회귀 표면을 낮춘다. |
| **Core Value** | "**bkit upstream과 잡음 없는 정합 + 임베디드 도메인 분기는 명시적으로만**" — 향후 모든 sync 사이클의 기준선이 되는 baseline 회복. |

---

## 1. Overview

### 1.1 Purpose

본 feature는 두 가지 정책을 코드에 새긴다:

1. **bkit upstream sync 우선**: 임베디드(MCU/MPU/WPF) 도메인 분기가 명시적인 항목을 제외하고는 bkit과 동일하게 둔다. 의도 불명확한 분기는 sync한다.
2. **동작 영향 없도록**: 모든 변경은 hook 출력 byte-diff와 단위 테스트 PASS로 검증한다.

이 정책에 따라 회귀 위험이 낮은 항목만 Cycle 1에 모아 단일 PR로 처리한다. 회귀 위험이 큰 항목(신규 모듈 도입, lib/pdca/status.js 분할 등)은 Cycle 2의 평가 단계로 미룬다.

### 1.2 Background

- 이전 sync(`docs/archive/2026-04/bkit-gstack-sync/`)는 bkit v2.0.3 → v2.0.6까지의 변경을 통합. 이후 132 commits 누적.
- 분석 결과 bkit이 v2.1.0 `21d35d6`에서 dead로 판정한 11 파일 중 **rkit이 7 파일 보유** (당초 추정 4보다 +3).
  - 검증 노트: `references/_analysis/s1-cleanup-impact-on-rkit.md`
- bkit `audit-logger`는 v2.1.10에서 PII redaction(`sanitizeDetails`)과 CATEGORIES enum 확장을 도입. 재귀 버그(`createDualSink`)는 rkit에 영향 없음(rkit `lib/infra/telemetry.js` 미보유).
- gstack은 동기화 시점 이후 `v0.14 → v1.0 → v1.15` 두 차례 메이저 롤. rkit 보유 5 스킬에 모두 후속 패치 존재(특히 `/investigate` 16건, `/retro` 16건, `cso/` +613 lines).

### 1.3 Related Documents

- 분석 노트(임시, gitignore):
  - `references/_analysis/bkit-changes.md` — bkit v2.0.6 → v2.1.10 전체 변경 인벤토리
  - `references/_analysis/gstack-changes.md` — gstack 변경 인벤토리
  - `references/_analysis/s1-cleanup-impact-on-rkit.md` — S1 cleanup 영향 매트릭스
- 이전 sync 사이클: `docs/archive/2026-04/bkit-gstack-sync/`
- bkit upstream: `https://github.com/popup-studio-ai/bkit-claude-code` (Apache 2.0)
- gstack upstream: `https://github.com/garrytan/gstack` (MIT)

### 1.4 Cycle 정의

| Cycle | 범위 | 회귀 위험 | 본 Plan |
|---|---|---|---|
| **Cycle 1 (본 Plan)** | Cleanup + 기존 모듈 강화 + audit hardening | Low | ✅ |
| Cycle 1.5 (별도 Plan 또는 별도 PR) | gstack 후속 패치 기반 기존 스킬 강화 (`/investigate`, `/retro`, `/security-review`, `/code-review`) | Low~Medium | 후속 |
| Cycle 2 (별도 Plan) | bkit 신규 대형 모듈 도입 평가 (Clean Arch, QA Phase, cc-regression, telemetry) | Medium~High | 후속 |
| Cycle 3 (필요 시) | gstack 신규 스킬 평가 (`/devex-review`, `/plan-tune`, `/pair-agent` 등) | Low~Medium | 후속 |

---

## 2. Scope

### 2.1 In Scope

#### 2.1.1 Group A — Dead 파일 정리 + context facade 정합

- [ ] `lib/pdca/do-detector.js` 삭제 (252 LOC)
- [ ] `lib/core/backup-scheduler.js` 삭제 (129 LOC)
- [ ] `lib/context/self-healing.js` 삭제 (179 LOC, `index.js`에서만 참조)
- [ ] `lib/context/ops-metrics.js` 삭제 (237 LOC, 동상)
- [ ] `lib/context/decision-record.js` 삭제 (동상)
- [ ] `lib/context/index.js`는 삭제하지 않고 bkit과 동일하게 5 live 모듈만 re-export하도록 축소
  - 보존 모듈: `context-loader`, `impact-analyzer`, `invariant-checker`, `scenario-runner`
  - 제거 export: `self-healing`, `ops-metrics`, `decision-record`
- [ ] `lib/context/` 디렉토리 정리 후 bkit과 동일하게 5 파일(`context-loader`, `impact-analyzer`, `index`, `invariant-checker`, `scenario-runner`) 정합

> 결정: `lib/context/index.js`는 보존한다. 현재 rkit 내부 사용처는 없지만, bkit upstream 정합과 외부 require 호환성을 우선한다.

#### 2.1.2 Group B — Live 파일 + 사용처 정리

- [ ] `hooks/startup/context-init.js`: Context Hierarchy 초기화 블록(L57-75), Memory Store 블록(L77-95), Context Fork cleanup 블록(L123-134) 제거
- [ ] `lib/permission-manager.js:11-19`: `_hierarchy = require('./context-hierarchy.js')` lazy 호출 제거 또는 try/catch graceful (bkit 패턴)
- [ ] `lib/import-resolver.js:14-29`: `_hierarchy` 처리 정리
- [ ] `lib/import-resolver.js`: 기존 `_common`/`core` 잔여 브릿지 결함 수정
  - `_common` 미정의 `getCommon()` 제거
  - `core.PLUGIN_ROOT`, `core.PROJECT_DIR`, `core.debugLog` 참조를 명시적 `require('./core')` 또는 필요한 core 모듈 직접 import로 교체
  - `resolveVariables()`/`loadImportedContent()` 단위 smoke test 추가
- [ ] `lib/context-fork.js` 삭제 (227 LOC)
- [ ] `lib/context-hierarchy.js` 삭제 (276 LOC)
- [ ] `lib/memory-store.js` 삭제 (185 LOC)
- [ ] `lib/skill-orchestrator.js`의 lazy require 1곳도 동시 점검 (bkit S1에서 함께 정리됨)

#### 2.1.3 audit-logger 강화 (rkit에 직접 가치)

- [ ] `lib/audit/audit-logger.js`에 `sanitizeDetails()` 함수 도입 (v2.1.10 C2 fix)
  - PII/token redaction: `password|secret|token|api_key|authorization|cookie|session_key|private_key`
  - 문자열 값 500자 truncate
  - 1단계 nested 객체 sanitize
- [ ] `CATEGORIES` enum에 `'permission', 'checkpoint', 'trust', 'system'` 추가 (v2.1.8 B2 fix)
- [ ] `validateAndNormalize()`의 `details` 패스스루를 `sanitizeDetails(entry.details)`로 교체
- [ ] **rkit 분기 보존**: `getAuditDir()`의 `.rkit/audit/` 경로, `rkitVersion` 키, MCUKIT_VERSION 상수는 그대로 유지 (의도적 분기)

> **OOS**: bkit v2.1.10의 `getTelemetrySink()` + `createOtelSink()` mirror는 `lib/infra/telemetry.js` 의존성이 있어 Cycle 2로 이월.

#### 2.1.4 gstack 후속 패치 — Cycle 1.5로 분리

- [ ] 본 Cycle에서는 코드 cleanup/audit hardening만 수행하고, 아래 4개 스킬 강화는 별도 Cycle 1.5 Plan 또는 별도 PR로 처리
  - `skills/investigate/SKILL.md`: gstack `b805aa01` Confusion Protocol + `a81be536`/`69733e26` Pros/Cons + RECOMMENDATION 포맷 이식
  - `skills/retro/SKILL.md`: gstack `dbd7aee5` repeat-user adaptation + `c6e6a21d` AI slop reduction 이식
  - `skills/security-review/SKILL.md`: gstack `cso/` BLOCK/WARN/LOG_ONLY threshold + `combineVerdict` 앙상블 패턴 이식
  - `skills/code-review/SKILL.md`: gstack `review/` `9ca8f1d7` adaptive gating + cross-review dedup + `31943b2f` anti-skip rule 이식

> Cycle 1.5 진입 조건: 각 스킬별 before/after eval 또는 최소 수용 기준을 먼저 정의한다. 임베디드 도메인 어구(`HardFault`, `Device Tree`, `XAML`, `MISRA` 등)는 삭제하지 않고 유지한다.

### 2.2 Out of Scope (Cycle 2/3 또는 영구 OOS)

#### Cycle 2로 이월 (신규 대형 모듈, 평가 후 결정)

- bkit `lib/domain/{ports,guards,rules}/` Hexagonal Clean Architecture
- bkit `lib/orchestrator/` 3-Layer Orchestration (Intent/NextAction/Team/WorkflowSM)
- bkit `lib/qa/` (15+ 파일) + qa-* 에이전트 4종 + `qa-phase` 스킬
- bkit `lib/cc-regression/` (CC 회귀 attribution + 토큰 ledger)
- bkit `lib/infra/{telemetry,cc-bridge,docs-code-scanner}/` (OTEL dual sink 등)
- bkit `lib/core/{version,context-budget,worktree-detector,session-ctx-fp,session-title-cache}/` 신규 5 모듈
- bkit `lib/pdca/status.js` 분할(status-{core,cleanup,migration}) — 분기 vs 채택 결정

#### Cycle 3 후보 (gstack 신규 스킬, 임베디드 적합성 평가 후)

- gstack 후속 패치 기반 기존 스킬 강화: `/investigate`, `/retro`, `/security-review`, `/code-review` (Cycle 1.5 우선 후보)
- gstack 신규 스킬: `/devex-review`, `/plan-devex-review`, `/plan-tune`, `/pair-agent`, `/context-save`+`/context-restore`, `/benchmark-models`

#### 영구 OOS (임베디드 도메인 무관)

- gstack `browse/`, `extension/` 브라우저 자동화 스택
- gstack `make-pdf/` 발행 PDF 생성기
- gstack `gbrain` family (15 shell binaries, Supabase schema)
- gstack `hosts/*.ts` (Cursor/OpenCode/Slate/Kiro/OpenClaw 등)
- gstack `model-overlays/` (Opus 4.7/GPT-5.4/Gemini)
- gstack mobile/web canary/landing-report 등
- bkit Sentry observability stack (v2.0.7)
- bkit Enterprise infra 템플릿 (ArgoCD, Terraform)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-01 | Group A dead 파일 삭제 + `lib/context/index.js` 5 live 모듈 re-export 정합 | P0-High | bkit `21d35d6` |
| FR-02 | Group B `lib/context-fork.js` 삭제 + `context-init.js` ContextFork 블록 제거 | P0-High | bkit S1 |
| FR-03 | Group B `lib/context-hierarchy.js` 삭제 + 3 사용처(hook + permission + import-resolver) 정리 | P0-High | bkit S1 |
| FR-04 | Group B `lib/memory-store.js` 삭제 + hook의 sessionCount/lastSession 블록 제거 | P0-Medium | bkit S1 |
| FR-05 | `audit-logger.js`에 `sanitizeDetails()` 도입 (PII redaction + 500자 truncate) | P1-High | bkit `v2.1.10 C2` |
| FR-06 | `audit-logger.js` CATEGORIES enum 확장 (permission/checkpoint/trust/system) | P1-Medium | bkit `v2.1.8 B2` |
| FR-07 | `lib/import-resolver.js`의 `_common`/`core` 잔여 브릿지 결함 수정 + smoke test | P0-High | current rkit defect |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement |
|----------|----------|-------------|
| Code reduction | Cycle 1 net LOC 감소 ≥ 1,300 LOC | `git diff --shortstat` |
| 동작 등가성 | SessionStart hook 출력 byte-diff ≤ 5% (정보성 라인 변경 허용) | hook 직접 실행 비교 |
| 테스트 회귀 | 전 단위/통합 테스트 PASS 유지 | `node test-all.js`, `node tests/instinct-integration.test.js`, `node tests/test-architecture-e2e.js` |
| audit-logger 호환 | 기존 audit log 라인 schema 하위 호환 (새 필드만 추가) | 기존 `.rkit/audit/*.jsonl` 샘플 검증 |
| PII redaction 효과 | password/token/secret 키 → `[REDACTED]`, 500자 초과 → `…[truncated]` | TC 추가 |
| context facade 정합성 | `require('./lib/context')`가 5 live 모듈 export만 제공 | node smoke test |

---

## 4. Risks

| ID | Risk | Mitigation |
|----|------|------------|
| R-1 | Group B `lib/memory-store.js` 삭제로 sessionCount/lastSession 추적 손실 | bkit도 동일 hook 그대로 두고 파일만 지움(graceful no-op). 추적 자체가 의도적으로 사라진 기능. 의도적 손실로 명시. |
| R-2 | `lib/context-hierarchy.js`가 permission-manager/import-resolver의 핵심 동작에 사용되고 있을 가능성 | 사용 코드 정독 후, getHierarchy() 호출 결과를 사용하는 함수에서 null 분기 추가. 단위 테스트 PASS 확인 후 삭제. |
| R-3 | `lib/context/index.js` 보존 시 삭제된 3 모듈 export가 남아 require 실패를 유발 | `index.js`를 5 live 모듈 re-export로 축소하고 node smoke test 수행. |
| R-4 | gstack 후속 패치가 cleanup PR의 회귀 표면을 넓힘 | 본 Cycle에서 제외하고 Cycle 1.5에서 스킬별 eval 기준 수립 후 진행. |
| R-5 | audit-logger sanitizeDetails 도입 시 기존 audit 호출 측에서 의도적으로 password/token을 details에 넣는 경우 | 호출처 grep: `audit-logger`로 sensitive 키 전송하는 곳 없음 확인. 도입 무영향. |
| R-6 | 본 Plan 작업 중 main에 다른 변경 머지될 경우 rebase 충돌 | `feature/bkit-gstack-sync-v2` 브랜치에서 작업, 단발 PR로 main에 머지. |

---

## 5. Verification Plan

### 5.1 단위 검증 (Group A/B 정리 후)

| 검증 항목 | 명령 | 기대 |
|---|---|---|
| `require('./lib/context')` facade smoke | `node -e "const c=require('./lib/context'); console.log(Object.keys(c).sort().join('\\n'))"` | 삭제 모듈 export 없음 |
| Group A 파일 사용처 0건 재확인 | `grep -rn "do-detector\\|backup-scheduler\\|context/self-healing\\|context/ops-metrics\\|context/decision-record"` | 0건 |
| hook safeRequire 잔존 0건 | `grep -n "context-fork\\|context-hierarchy\\|memory-store" hooks/` | 0건 |
| permission/import-resolver의 getHierarchy 호출 처리 | 파일 직접 read + null 분기 검증 | 명시적 처리 |
| import-resolver smoke | `node -e "const r=require('./lib/import-resolver'); console.log(typeof r.resolveImports)"` | `function` |

### 5.2 동작 검증

| 검증 항목 | 방법 |
|---|---|
| SessionStart hook 정상 종료 | `node hooks/session-start.js` 실행 후 exit code 0 및 JSON 출력 |
| 단위/통합 테스트 PASS | `node test-all.js`, `node tests/instinct-integration.test.js`, `node tests/test-architecture-e2e.js` |
| audit-logger 신규 TC | `password/token/api_key/secret` → `[REDACTED]`, 600자 string → `…[truncated]` |
| audit-logger CATEGORIES TC | `category: 'permission'` 등 새 4 카테고리 통과, 무효 카테고리는 기존대로 fallback |

### 5.3 회귀 검증

| 검증 항목 | 방법 |
|---|---|
| 기존 audit log 호환 | `.rkit/audit/2026-04-*.jsonl` 샘플을 v2 schema로 파싱 → 모든 필드 정상 |
| Hook 출력 byte-diff | 정리 전후 SessionStart additionalContext 비교 (≤5% 변동) |
| `lib/permission-manager` 권한 결정 등가성 | 명시 단위 smoke + 기존 통합 테스트 PASS |
| `lib/import-resolver` import 해결 등가성 | 신규 smoke + 기존 통합 테스트 PASS |

---

## 6. 결정 필요 항목 (Design 단계 진입 전)

| ID | 결정 항목 | 옵션 | 본 Plan 권고 |
|----|-----------|------|--------------|
| **D-1** | `lib/context/index.js` 처리 | (a) 완전 삭제 / (b) bkit과 동일하게 5 모듈만 re-export로 보존 | **결정: (b)** — 정책 "bkit upstream 정합" 우선 |
| **D-2** | Group B `permission-manager`/`import-resolver`의 `_hierarchy` 처리 | (a) lazy try/catch (bkit 패턴) / (b) 호출처 함수 자체 제거 | **(a)** — 최소 변경, bkit과 동일 패턴 |
| **D-3** | `lib/skill-orchestrator.js`의 lazy require 동시 점검 범위 | (a) Cycle 1 포함 / (b) 별도 PR | **(a)** — bkit S1과 동일하게 함께 처리 |
| **D-4** | gstack 4 스킬 강화 시 기존 임베디드 어구 보존 정책 | (a) Cycle 1.5에서 추가 병합 / (b) Cycle 1에 포함 | **결정: (a)** — cleanup PR과 분리 |
| **D-5** | audit-logger `MCUKIT_VERSION` 상수 처리 | (a) 유지 / (b) bkit `BKIT_VERSION` SoT 패턴 도입 | **(a)** — `lib/core/version.js` 미보유, Cycle 2 이월 |

---

## 7. Schedule (예상)

| 단계 | 산출물 | 예상 소요 |
|---|---|---|
| Plan 승인 | 본 문서 사용자 검토 | 즉시 |
| Design | `docs/02-design/features/bkit-gstack-sync-v2.design.md` (FR별 변경 위치/방법 상세) | 1 세션 |
| Do | 단계별 커밋 (Group A → Group B/import-resolver → audit-logger) | 1~2 세션 |
| Check | Gap 분석, FR/NFR 충족율 | 1 세션 |
| Iterate (필요 시) | 미충족 항목 보강 | 0~1 세션 |
| Report | `docs/04-report/features/bkit-gstack-sync-v2.report.md` + PR | 1 세션 |
| Cycle 1.5 Plan 시작 | 별도 Plan 문서 또는 PR (gstack 4 스킬 강화 + eval 기준) | 후속 |
| Cycle 2 Plan 시작 | 별도 Plan 문서 (신규 모듈 평가) | 후속 |

---

## 8. Approval

| Stakeholder | Decision | Notes |
|-------------|----------|-------|
| 노수장 (사용자) | Pending | 본 Plan + 결정 항목 D-1~D-5 검토 후 Design 진입 |

---

## Appendix A — 분석 노트 위치 (gitignore 영역)

| 파일 | 내용 |
|---|---|
| `references/bkit-claude-code/` | bkit upstream full clone (HEAD `f2c17f3`, 2026-04-22) |
| `references/gstack/` | gstack upstream full clone (HEAD `dde55103`, 2026-04-26, v1.15.0.0) |
| `references/_analysis/bkit-changes.md` | bkit v2.0.6 → v2.1.10 변경 인벤토리 |
| `references/_analysis/gstack-changes.md` | gstack 변경 인벤토리 |
| `references/_analysis/s1-cleanup-impact-on-rkit.md` | S1 cleanup 영향 매트릭스 |

## Appendix B — bkit 변경 분류 (참고)

| 카테고리 | 본 Cycle | Cycle 2 | OOS |
|---|---|---|---|
| Architecture/Refactor | — | ✅ Clean Arch | — |
| New Modules (lib/qa, lib/cc-regression 등) | — | ✅ | — |
| Hooks (CwdChanged, TaskCreated) | — | ✅ | — |
| MCP (`_meta`) | — | ✅ | — |
| Skills (qa-phase 신규) | — | ✅ | — |
| Agents (qa-* 4종) | — | ✅ | — |
| Library (lib/audit sanitize, CATEGORIES) | ✅ | — | — |
| 기존 스킬 후속 패치 | — | — | Cycle 1.5 |
| Tests/QA scanner | — | ✅ | — |
| CI/CD | — | ✅ | — |
| Bug fixes (audit-logger 재귀 등) | — (rkit 영향 없음) | — | — |
| CC Compat | — | ✅ engines 갱신 | — |

## Appendix C — gstack 변경 분류 (참고)

| 카테고리 | 본 Cycle | Cycle 3 | OOS |
|---|---|---|---|
| 기존 ported 스킬 후속 패치 (`/investigate`, `/retro`, `cso`, `review`) | — | ✅ Cycle 1.5 | — |
| 신규 스킬 (`/devex-review`, `/plan-tune`, `/pair-agent` 등) | — | ✅ 평가 | — |
| `make-pdf/`, `gbrain`, `browse/`, `extension/` | — | — | ✅ |
| Model overlays (Opus/GPT-5.4/Gemini) | — | — | ✅ |
| `hosts/*.ts` (Cursor/OpenCode/Kiro 등) | — | — | ✅ |
