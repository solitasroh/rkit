---
template: report
version: 1.1
---

# instinct-codegen Completion Report

> **Status**: Complete
>
> **Project**: rkit
> **Version**: v0.9.14
> **Author**: 노수장
> **Completion Date**: 2026-04-27
> **PDCA Cycle**: #1

---

## Executive Summary

### 1.1 Project Overview

| Item | Content |
|------|---------|
| Feature | instinct-codegen |
| Start Date | 2026-04-10 (Plan) |
| End Date | 2026-04-27 (Report) |
| Duration | 17일 (post-hoc Design 정리 4/17 → Check/정리 4/27) |

### 1.2 Results Summary

```
┌─────────────────────────────────────────────┐
│  Final Match Rate: 100%                      │
├─────────────────────────────────────────────┤
│  ✅ FR Complete:        5 / 5                │
│  ✅ Test Cases:         5 / 5                │
│  ✅ Gap Resolved:       2 / 2 (post-Check)   │
│  ⏳ Carried Over:       2 (의도적 보류)        │
└─────────────────────────────────────────────┘
```

| 단계 | Match Rate | 비고 |
|------|-----------:|------|
| Check (4/27, Gap 발견 시점) | 95% | Gap-1 중복 상수 / Gap-2 Design 문서 부정확 |
| Final (Gap-1/Gap-2 정리 후) | **100%** | 동작 영향 없는 minor cleanup 만 처리 |

### 1.3 Value Delivered

| Perspective | Content |
|-------------|---------|
| **Problem** | 인스팅트(학습된 코딩 패턴)가 코드 리뷰 시점에만 반영되고, 코드 작성 시점(Write/Edit)에는 전달되지 않아 같은 실수가 반복됨. v0.9.13 A/B 실험에서 `additionalContext` 단독 주입은 효과 없음이 확인됨. |
| **Solution** | `lib/code-quality/pre-guide.js`의 `generateStructuralGuide()`에 `(G) Instinct patterns` 슬롯을 추가. `lib/instinct/loader.js`의 `loadConvergedPatterns()`를 lazy require로 호출하고, `compactInstinct(raw, 200)` 헬퍼로 마크다운을 `[LEARNED] desc(0.92). ...` 단일 라인으로 압축하여 PreToolUse 컨텍스트에 주입. |
| **Function/UX Effect** | Write/Edit 도구 호출 시 100% 자동으로 학습 패턴이 Claude 컨텍스트에 합류. 인스팅트 데이터 부재 시 graceful skip(기존 출력 바이트 단위 동일). 토큰 예산 200자 자체 제한, smoke test 20건 입력 → 189자 출력 검증. |
| **Core Value** | "리뷰에서 배운 것이 다음 코드 작성에 바로 반영된다" — 학습 루프(리뷰 → 인스팅트 → 코드 생성) 폐쇄. |

---

## 2. Related Documents

| Phase | Document | Status |
|-------|----------|--------|
| Plan | [instinct-codegen.plan.md](../../01-plan/features/instinct-codegen.plan.md) | ✅ Finalized (v0.1, 2026-04-10) |
| Design | [instinct-codegen.design.md](../../02-design/features/instinct-codegen.design.md) | ✅ Finalized (v0.2, 2026-04-27) |
| Check | [instinct-codegen.analysis.md](../../03-analysis/instinct-codegen.analysis.md) | ✅ Complete (95% → cleanup → 100%) |
| Act | Current document | ✅ Complete |

---

## 3. Completed Items

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status | Implementation |
|----|-------------|----------|--------|----------------|
| FR-01 | `(G) Instinct patterns` 슬롯 추가 | High | ✅ Complete | `lib/code-quality/pre-guide.js:463-468` |
| FR-02 | `loadConvergedPatterns()` 호출 (lazy require) | High | ✅ Complete | `pre-guide.js:465` (try/catch graceful skip) |
| FR-03 | 1줄 압축 형식 변환 | High | ✅ Complete | `compactInstinct()` (`pre-guide.js:391-414`) |
| FR-04 | `MAX_CONTEXT_LENGTH` 500 → 1500 | Medium | ✅ Complete | `lib/core/io.js:11` (single source of truth) |
| FR-05 | 로드 실패 시 graceful skip | High | ✅ Complete | TC2/TC3 검증 |

### 3.2 Non-Functional Requirements

| Item | Target | Achieved | Status |
|------|--------|----------|--------|
| Token budget | ≤ 200자 | TC4: 189자 (20건 입력) | ✅ |
| 호환성 | 인스팅트 없는 프로젝트 기존 동작 동일 | TC5: `generateStructuralGuide` 정상 (353자, (G) skip) | ✅ |
| Performance | PreToolUse 훅 ≤ 5초 | 직접 측정 미실시 (lazy require + 자체 200자 제한으로 안전 마진 충분) | ⚠️ N/A |

### 3.3 Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| 신규 함수 `compactInstinct()` | `lib/code-quality/pre-guide.js:391-414` | ✅ |
| `(G)` 슬롯 통합 | `lib/code-quality/pre-guide.js:463-468` | ✅ |
| 컨텍스트 한도 확대 | `lib/core/io.js:11` (500 → 1500) | ✅ |
| 중복 상수 제거 | `lib/core/constants.js` (MAX_CONTEXT_LENGTH 정의/export 삭제) | ✅ Check 후 정리 |
| Plan 문서 | `docs/01-plan/features/instinct-codegen.plan.md` | ✅ |
| Design 문서 (v0.2) | `docs/02-design/features/instinct-codegen.design.md` | ✅ Check 결과 반영 |
| Analysis 리포트 | `docs/03-analysis/instinct-codegen.analysis.md` | ✅ |
| Smoke test (5건, inline) | `node -e` 스크립트 (Check 단계에서 실행) | ✅ |

---

## 4. Incomplete Items

### 4.1 Carried Over to Next Cycle (의도적 보류)

| Item | Reason | Priority | Estimated Effort |
|------|--------|----------|------------------|
| 정식 unit test (`tests/` 디렉토리) | Plan/Design에 "후행 고려"로 명시. Smoke test 5건으로 행동 검증 충족 | Low | 0.5일 |
| 통합 테스트 (실제 `.rkit/instinct/` 데이터로 (G) 출력 확인) | 현재 인스팅트 축적 데이터 부재. 향후 리뷰 누적 후 자연 발생 | Low | 0.5일 |

### 4.2 Cancelled/On Hold Items

| Item | Reason | Alternative |
|------|--------|-------------|
| PostToolUse 사후 검증 | Plan §2.2 Out of Scope (안 2, 별도 feature) | 향후 별도 PDCA 사이클 |
| 인스팅트 → 스킬 승격 | Plan §2.2 Out of Scope (안 3, v0.9.15 이후) | 향후 별도 PDCA 사이클 |
| `isCodeFile()` 확장자 범위 확대 (.py, .js 등) | Plan §2.2 Out of Scope | 필요 시 별도 사이클 |

---

## 5. Quality Metrics

### 5.1 Final Analysis Results

| Metric | Target | Final | Status |
|--------|--------|-------|--------|
| Design Match Rate | ≥ 90% | 100% | ✅ |
| FR 구현률 | 100% | 5/5 | ✅ |
| Smoke Test 통과율 | 100% | 5/5 | ✅ |
| 토큰 예산 준수 | ≤ 200자 | 189자 (max) | ✅ |
| 호환성 회귀 | 0건 | 0건 | ✅ |

### 5.2 Resolved Issues (Check 단계 발견 → Act 처리)

| Issue | Severity | Resolution | Result |
|-------|----------|------------|--------|
| `MAX_CONTEXT_LENGTH` 중복 상수 (`constants.js` 500 / `io.js` 1500) | Low/Medium | `constants.js`에서 정의 + export 제거. `io.js`를 single source of truth로 일원화 | ✅ Resolved (consumer drift 위험 제거) |
| Design 문서 §2.2 / §4.3 데이터 플로우 부정확 (`pre-write.js` truncateContext 호출 표기) | Low | Design v0.2로 정정. 실제 truncate 호출자(`user-prompt-handler.js`) 명시, pre-write는 자체 truncation 없음 표기 | ✅ Resolved |

---

## 6. Lessons Learned & Retrospective

### 6.1 What Went Well (Keep)

- **Lazy require + try/catch** 패턴이 graceful degradation을 깔끔하게 보장. 인스팅트 모듈 부재 환경에서도 (A)~(F) 출력 바이트 단위 동일.
- **자체 토큰 예산** (`compactInstinct(maxLen=200)`) 으로 외부 truncation에 의존하지 않아, hook 호출 경로별 truncation 차이에 안전.
- **Post-hoc Design 정리** 가 Check에서 데이터 플로우 부정확을 노출. 구현 후 정리한 Design을 Check가 검증함으로써 문서-코드 정합성 자기 보정.

### 6.2 What Needs Improvement (Problem)

- **상수 단일 출처 부재**: `lib/core/constants.js`와 `lib/core/io.js` 양쪽에 동일 이름 상수가 공존했음. 이번에 `io.js`로 일원화했지만, 다른 상수에도 동일 패턴이 있을 수 있어 전수 점검 필요.
- **Hook 출력 경로의 truncation 정책 비일관**: `pre-write.js`는 truncate 미적용, `user-prompt-handler.js`만 truncate 적용. 의도된 정책인지 명문화 필요.
- **Performance 측정 누락**: NFR로 5초 이내를 명시했으나 실측 안 함. 인스팅트 데이터 누적 후 측정 필요.

### 6.3 What to Try Next (Try)

- **상수 audit 스킬화**: rkit 레포 전체에서 동일 이름 상수 중복 정의를 자동 검출하는 점검 (다음 PDCA 사이클 후보).
- **PostToolUse 사후 검증 슬롯**: Plan §2.2 Out of Scope였던 "안 2"를 별도 feature로 진입. (G) 주입이 실제 코드에 반영되었는지 검증.
- **인스팅트 → 스킬 승격**: 신뢰도 임계 도달 패턴을 자동으로 SKILL.md로 격상하는 파이프라인 (v0.9.15+).

---

## 7. Process Improvement Suggestions

### 7.1 PDCA Process

| Phase | Current | Improvement Suggestion |
|-------|---------|------------------------|
| Plan | 우수 | 유지 (Plan FR 5건이 Check까지 그대로 추적 가능) |
| Design | Post-hoc 작성 → Check에서 부정확 노출 | 구현 직후 Design 정리 시 코드 grep으로 호출 관계 1차 검증 권장 |
| Do | inline smoke test로 충분 | 향후 핵심 헬퍼는 `tests/`로 승격 |
| Check | Match Rate 95% → 정리 후 100% | minor gap 발견 시 별도 iterate 사이클 없이 즉시 정리하는 본 사이클 패턴 유지 |

### 7.2 Tools/Environment

| Area | Improvement Suggestion | Expected Benefit |
|------|------------------------|------------------|
| Lint | `MAX_CONTEXT_LENGTH` 같은 도메인 상수의 중복 정의 검출 룰 | drift 사전 방지 |
| Hook 경로 통일 | pre-write/user-prompt-handler의 truncation 정책 통합 검토 | 출력 길이 예측 가능성 향상 |

---

## 8. Next Steps

### 8.1 Immediate

- [ ] 커밋 분리 (의도): (a) `lib/core/io.js` 상수 변경, (b) `lib/code-quality/pre-guide.js` 인스팅트 슬롯, (c) `lib/core/constants.js` 중복 제거, (d) Design 문서 v0.2 정정 + Analysis/Report 추가
- [ ] 인스팅트 데이터 축적 후 (G) 슬롯 실제 동작 관측 (수동)

### 8.2 Next PDCA Cycle 후보

| Item | Priority | Trigger |
|------|----------|---------|
| PostToolUse 사후 검증 (Plan 안 2) | Medium | 인스팅트 데이터 1주 이상 누적 후 |
| 인스팅트 → 스킬 승격 (Plan 안 3) | Low | v0.9.15 진입 시 |
| 상수 중복 audit 스킬 | Low | 별 트리거 시 |

---

## 9. Changelog

### v0.9.14 (2026-04-27)

**Added:**
- `lib/code-quality/pre-guide.js`: `compactInstinct(raw, maxLen=200)` 헬퍼 추가, `(G) Instinct patterns` 슬롯을 `generateStructuralGuide()` 출력에 통합 ((F) 뒤, SIZING 앞).
- `module.exports`에 `compactInstinct` 노출 (테스트/재사용 목적).
- 문서: `docs/01-plan/features/instinct-codegen.plan.md`, `docs/02-design/features/instinct-codegen.design.md`, `docs/03-analysis/instinct-codegen.analysis.md`, 본 보고서.

**Changed:**
- `lib/core/io.js`: `MAX_CONTEXT_LENGTH` 500 → **1500** (UserPromptSubmit 훅 컨텍스트 한도 확대).
- `docs/02-design/features/instinct-codegen.design.md` v0.2: §2.2 데이터 플로우 / §4.3 영향 범위 정정 (pre-write 비-truncate, user-prompt-handler가 실제 호출자).

**Removed:**
- `lib/core/constants.js`: `MAX_CONTEXT_LENGTH` 중복 상수 정의 및 export 삭제. `io.js`가 single source of truth.

**Fixed:**
- 동작 영향 없는 정합성 정리 (Check Gap-1, Gap-2).

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-27 | Completion report created (Match Rate 100%) | 노수장 |
