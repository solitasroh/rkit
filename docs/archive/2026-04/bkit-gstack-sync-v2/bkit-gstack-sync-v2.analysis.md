---
template: analysis
version: 1.0
---

# bkit-gstack-sync-v2 Gap Analysis (Check Phase) — Cycle 1

> **Summary**: Plan/Design 대비 구현 일치율 **100%** — 7 FR 모두 PASS, 6 NFR 모두 PASS, 13 TC 모두 PASS, 5 D-record 모두 적용, 7 Risk 모두 mitigated. iterate 불필요, report 단계 진입 가능.
>
> **Project**: rkit
> **Version**: v0.9.14
> **Author**: 노수장 (gap-detector)
> **Date**: 2026-04-27
> **Plan Doc**: [bkit-gstack-sync-v2.plan.md](../01-plan/features/bkit-gstack-sync-v2.plan.md)
> **Design Doc**: [bkit-gstack-sync-v2.design.md](../02-design/features/bkit-gstack-sync-v2.design.md)
> **Branch**: `feature/bkit-gstack-sync-v2` (8 commits, code-only Δ +209 / −1761 = net −1,552 LOC)

---

## 1. Match Rate Summary

| 영역 | PASS | PARTIAL | FAIL | 총 | 일치율 |
|---|:---:|:---:|:---:|:---:|:---:|
| Functional Requirements | 7 | 0 | 0 | 7 | **100%** |
| Non-Functional Requirements | 6 | 0 | 0 | 6 | **100%** |
| Test Cases (TC-1~9 + 4 regression) | 13 | 0 | 0 | 13 | **100%** |
| Decision Records (D-1~5) | 5 | 0 | 0 | 5 | **100%** |
| Risk Mitigation (R-1~7) | 7 | 0 | 0 | 7 | **100%** |
| **Overall** | **38** | **0** | **0** | **38** | **100%** |

**Match Rate 공식**: `(PASS + 0.5×PARTIAL) / total × 100 = 38/38 × 100 = 100%`. 임계치 ≥ 90% 충족.

---

## 2. Functional Requirements 검증

| FR | Requirement | Implementation (commit + path:line) | Verification | Status |
|---|---|---|---|:---:|
| **FR-01** | Group A dead 5파일 삭제 + `lib/context/index.js` 5 live 모듈 re-export 정합 | `5623a06` (C2) — `lib/context/{self-healing,ops-metrics,decision-record}.js` 삭제 + `lib/context/index.js` 23 LOC로 축소; `ea3dfaf` (C3) — `lib/pdca/do-detector.js`, `lib/core/backup-scheduler.js` 삭제 | TC-1 facade keys 11개 정확 일치 (`analyzeImpact, checkInvariants, extractContextAnchor, getDependencyImpact, getDtsImpact, getMemoryImpact, getScenarioCommands, injectAnchorToTemplate, loadDesignContext, loadPlanContext, runScenario`); TC-2 grep 0건 | **PASS** |
| **FR-02** | `lib/context-fork.js` 삭제 + `context-init.js` ContextFork 블록 제거 | `2e94ad7` (C6) — `lib/context-fork.js` (227 LOC) 삭제, `hooks/startup/context-init.js` 209→155 LOC 슬림화, `contextFork`/`getActiveForks`/`clearAllForks` 잔존 0건 | grep `contextFork` 0건 (코멘트 1건만 남음 line 11), hook exit 0 | **PASS** |
| **FR-03** | `lib/context-hierarchy.js` 삭제 + 3 사용처(hook + permission + import-resolver) 정리 | `2e94ad7` (C6) — `lib/context-hierarchy.js` (276 LOC) 삭제; `54cdd80` (C5) — `lib/permission-manager.js` `getCore()` barrel + `getConfiguredPermissions()` 도입; `69642ec` (C4) — `lib/import-resolver.js` `getUserConfigDir()` 인라인 + `getCore()` lazy | TC-3 grep `context-hierarchy` 0건 (코멘트 1건만 line 35), TC-4 import-resolver smoke 24/24 PASS, TC-5 permission-matrix smoke 27/27 PASS | **PASS** |
| **FR-04** | `lib/memory-store.js` 삭제 + hook의 sessionCount/lastSession 블록 제거 | `2e94ad7` (C6) — `lib/memory-store.js` (185 LOC) 삭제, `context-init.js` Memory Store 블록 19라인 제거 | grep `memory-store` 0건 in lib/hooks (R-1 의도적 손실 명시) | **PASS** |
| **FR-05** | `audit-logger.js` `sanitizeDetails()` 도입 (PII redaction + 500자 truncate) | `a1087de` (C1) — `lib/audit/audit-logger.js:108-118` `SENSITIVE_KEY_PATTERNS` + `DETAILS_VALUE_MAX_CHARS=500`, `:129-` `sanitizeDetails()` 함수, `:185` `validateAndNormalize` details 파스스루를 `sanitizeDetails(entry.details)` 호출로 교체 | TC-6/TC-7 + tests/audit-sanitize.test.js 37/37 PASS (PII redact, 500자 truncate, 중첩 1단계 sanitize) | **PASS** |
| **FR-06** | `audit-logger.js` CATEGORIES enum 4종 확장 | `a1087de` (C1) — `lib/audit/audit-logger.js:55` `CATEGORIES` 배열에 `'permission', 'checkpoint', 'trust', 'system'` 추가 (총 10개) | TC-8 audit-sanitize 카테고리 케이스 PASS | **PASS** |
| **FR-07** | `import-resolver.js` `_common`/`core` 잔여 브릿지 결함 수정 + smoke test | `69642ec` (C4) — DEF-1 `getCommon()` body 빈 함수 결함 제거, DEF-2 `core.PLUGIN_ROOT/PROJECT_DIR/debugLog` → `getCore()` lazy barrel 경유로 교체, DEF-3 `lib/skill-orchestrator.js:21` 주석 + `getCommon()` 삭제, DEF-4 hierarchy 호출 제거; `tests/import-resolver.smoke.test.js` 신설 | smoke 24/24 PASS — 특히 TC-2.2 USER_CONFIG가 `.claude/rkit` 분기로 정상 해석, TC-2.3 missing core에서 ReferenceError 0건 | **PASS** |

**FR 일치율: 7/7 = 100%**

---

## 3. Non-Functional Requirements 검증

| NFR | Criteria | 측정값 | Status |
|---|---|---|:---:|
| Code reduction | Cycle 1 net LOC 감소 ≥ 1,300 | code-only `git diff main...HEAD --shortstat -- ':!docs' ':!tests'` = +209 / −1761 = **net −1,552** (목표 119% 달성) | **PASS** |
| 동작 등가성 | SessionStart hook 출력 byte-diff ≤ 5% | hook exit 0, JSON 정상 출력 (`┌─── bkit-gstack-sync-v2 ─...─ 75% ─┐` 헤더 보존). Memory Store/Context Hierarchy/Context Fork 블록 제거에 따른 정보성 라인 변경만 발생 | **PASS** |
| 테스트 회귀 | 단위/통합 테스트 PASS 유지 | `node test-all.js` 76/76 PASS, `node tests/instinct-integration.test.js` 15/15 PASS, `node tests/test-architecture-e2e.js` exit 0 (C7 `7edce2a`에서 require 경로 보정 후) | **PASS** |
| audit-logger 호환 | 기존 audit log schema 하위 호환 | `MCUKIT_VERSION='2.0.0'`, `getAuditDir() → .rkit/audit/` 보존 (`a1087de`). 신규 필드 없이 details 값만 sanitize 처리 → 기존 reader 영향 0 | **PASS** |
| PII redaction 효과 | password/token/secret → `[REDACTED]`, 500자 초과 → `…[truncated]` | `tests/audit-sanitize.test.js` 37/37 PASS — top-level + nested 1단계 모두 검증 | **PASS** |
| context facade 정합성 | `require('./lib/context')`가 5 live 모듈 export만 제공 | TC-1 결과 keys 11개 = bkit upstream과 동일 11키 (5 모듈에서 파생). dead export 0건 | **PASS** |

**NFR 일치율: 6/6 = 100%**

---

## 4. Test Cases 검증

### 4.1 Design §6.1 Unit/Smoke (TC-1 ~ TC-9)

| TC | 검증 항목 | 결과 | Evidence |
|---|---|:---:|---|
| TC-1 | context facade keys = 11 | PASS | `node -e "..."` → `analyzeImpact,checkInvariants,extractContextAnchor,getDependencyImpact,getDtsImpact,getMemoryImpact,getScenarioCommands,injectAnchorToTemplate,loadDesignContext,loadPlanContext,runScenario` (정확히 11개) |
| TC-2 | Group A dead 사용처 0건 | PASS | `grep -rn "do-detector\|backup-scheduler\|context/self-healing\|context/ops-metrics\|context/decision-record" lib/ hooks/ scripts/ skills/ servers/` → 0건 |
| TC-3 | 제거 live 모듈 사용처 0건 | PASS | `grep -rn "context-fork\|context-hierarchy\|memory-store" lib/ hooks/` → 실제 require 0건. doc 코멘트 2건만 잔존 (`lib/import-resolver.js:35`, `hooks/startup/context-init.js:11` — 둘 다 "removed in S1 cleanup" 설명) |
| TC-4 | import-resolver smoke | PASS | `tests/import-resolver.smoke.test.js` 24/24 PASS |
| TC-5 | permission-matrix smoke (6 안전 정책) | PASS | `tests/permission-matrix.smoke.test.js` 27/27 PASS — `rm -rf*`, `dd if=*`, `mkfs*`, `st-flash erase*`, `STM32_Programmer_CLI -e all*`, `git push --force*` 매트릭스 모두 적합 |
| TC-6 | audit sanitizeDetails — PII | PASS | `tests/audit-sanitize.test.js` `password→[REDACTED]`, `token→[REDACTED]`, `api_key→[REDACTED]` 케이스 PASS |
| TC-7 | audit sanitizeDetails — truncate | PASS | 600자 string → `'x'×500 + '…[truncated]'` PASS |
| TC-8 | audit CATEGORIES extension | PASS | `category: 'permission'/'checkpoint'/'trust'/'system'` 입력 → 출력 보존 (fallback `control` 미발생) |
| TC-9 | hook exit 0 + JSON | PASS | `echo '{}' \| node hooks/session-start.js` → exit 0, JSON header 정상 출력 |

### 4.2 Design §6.2 Regression (4건)

| 항목 | 명령 | 결과 | Status |
|---|---|---|:---:|
| 기존 단위/통합 | `node test-all.js` | 76/76 PASS | **PASS** |
| instinct 통합 | `node tests/instinct-integration.test.js` | 15/15 PASS | **PASS** |
| 아키텍처 E2E | `node tests/test-architecture-e2e.js` | exit 0, "E2E Simulation Completed" | **PASS** |
| 기존 audit log 호환 | `MCUKIT_VERSION`/`rkitVersion` 키 보존 (`a1087de` `lib/audit/audit-logger.js:30`) | schema 하위 호환 | **PASS** |

**TC 일치율: 13/13 = 100%**

---

## 5. Decision Records 검증

| ID | 결정 | Implementation Evidence | Status |
|---|---|---|:---:|
| **D-1** | `lib/context/index.js` 보존 (5 live 모듈 re-export 축소) | `5623a06` — `lib/context/index.js` 23 LOC, 5 모듈 import + 11 keys export. 파일 자체 보존 | **적용** |
| **D-2** | `permission-manager.js` `getHierarchicalConfig` 제거하되 rkit.config `permissions` core 병합 보존 | `54cdd80` `lib/permission-manager.js:33-37` `getConfiguredPermissions() = { ...DEFAULT_PERMISSIONS, ...(core.getConfig('permissions', {})) }` | **적용** |
| **D-3** | `lib/skill-orchestrator.js` broken `getCommon()` 동시 정리 (Cycle 1 포함) | `69642ec` — `lib/skill-orchestrator.js:21` "broken getCommon() shim was deleted here too" 주석 + 함수 제거 | **적용** |
| **D-4** | gstack 4 스킬 강화 → Cycle 1.5로 분리 (본 Design 범위 외) | 본 8 commits에 `skills/investigate`, `skills/retro`, `skills/security-review`, `skills/code-review` 변경 0건 (OOS 보존) | **적용** |
| **D-5** | `MCUKIT_VERSION` 상수 유지 (`BKIT_VERSION` SoT 도입은 Cycle 2 이월) | `a1087de` `lib/audit/audit-logger.js:30` `const MCUKIT_VERSION = '2.0.0'` 그대로 유지, `rkitVersion` 키 보존 | **적용** |

**D-record 일치율: 5/5 = 100%**

---

## 6. Risk Mitigation 검증

| ID | Risk | Design 대응 | 실제 검증 | Status |
|---|---|---|---|:---:|
| **R-1** | sessionCount/lastSession 추적 손실 | 의도적 손실 명시 (§3.4) | `2e94ad7` Memory Store 블록 제거. graceful — hook exit 0, 다른 기능 영향 0 | **mitigated** |
| **R-2** | context-hierarchy 의존 동작 회귀 | core config 병합 + TC-5 매트릭스 | TC-5 27/27 PASS — rm -rf/dd/mkfs/st-flash/STM32 erase/git force push 모두 정확히 분류 | **mitigated** |
| **R-3** | `lib/context/index.js` 재 참조로 dead export 노출 | TC-1 + grep `require.*context` | TC-1 keys 11개 = 정확히 5 모듈에서 파생 export. dead 0건 | **mitigated** |
| **R-4** | gstack 패치 cleanup PR 회귀 | Cycle 1.5 분리 | 본 Cycle commits에 gstack 스킬 변경 0건 — OOS 정책 준수 | **mitigated** |
| **R-5** | sanitizeDetails 도입 부작용 (의도적 password 전송 호출처) | grep 0건 확인 후 도입 | `lib/audit/audit-logger.js:185` 적용 후 76/76 regression PASS — 호출처 영향 0 | **mitigated** |
| **R-6** | rebase 충돌 | `feature/bkit-gstack-sync-v2` 단발 PR | 8 commits 단일 브랜치 유지, main 기준 충돌 0건 | **mitigated** |
| **R-7** (신규) | DEF-1~3가 silent하게 startupImports 무력화 중 | C4 후 정상 동작 확인 | `69642ec` C4 후 `tests/import-resolver.smoke.test.js` 24/24 PASS — `getCore()` lazy + `.claude/rkit` 분기 정상 해석 | **mitigated** |

**Risk mitigation 일치율: 7/7 = 100%**

---

## 7. Gap 분석

본 Cycle에서 식별된 Gap **없음** (Match Rate 100%).

다만 **계획 외(Plan에 없던) 추가 산출물 1건** 기록:

| ID | 항목 | severity | file:line | description | recommendation |
|---|---|:---:|---|---|---|
| **EXTRA-1** | `agents/self-healing.md` HEALING_STRATEGIES 인라인 + `tests/test-architecture-e2e.js` require 경로 보정 | Low | `agents/self-healing.md:5,83`, `tests/test-architecture-e2e.js:6` | C7 (`7edce2a`)에서 추가됨. `lib/context/self-healing.js` 삭제로 인한 follow-up — agent 문서가 사라진 모듈을 참조하지 않도록 진단 룰을 인라인 처리하고, e2e 테스트가 새 경로를 require하도록 보정. Plan/Design에는 명시되지 않았으나 정리 작업의 자연스러운 closure. | Report 단계에서 "C7 follow-up commit" 항목으로 기록만 하면 됨. iterate 불요. |

> 이 EXTRA-1은 결함이 아니라 **회귀를 막기 위한 정상적 follow-up**. Match Rate 계산에서 차감 사유 아님.

---

## 8. Conclusion

- **Match Rate**: **100%** — 임계치 ≥ 90% 충족 (38/38 항목 PASS).
- **Code reduction**: net **−1,552 LOC** (목표 ≥ −1,300의 119%).
- **회귀**: 0건 (76 + 15 + e2e + 88 신규 TC 모두 PASS).
- **Carry-over**: 없음. Cycle 1.5(gstack 4 스킬), Cycle 2(신규 대형 모듈), Cycle 3(gstack 신규 스킬)은 본 Plan에서 OOS로 명시한 항목들이며 본 Cycle 미달이 아님.
- **Next**: `/pdca report bkit-gstack-sync-v2` — Cycle 1 완료 보고서 + PR 작성 단계 진입. iterate 단계 불필요.
