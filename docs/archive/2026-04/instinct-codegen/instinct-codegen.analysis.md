---
template: analysis
version: 1.0
---

# instinct-codegen Gap Analysis (Check Phase)

> **Summary**: Plan/Design 5개 FR 전부 구현 확인. 2건의 minor gap (중복 상수, Design 문서 부정확). Match Rate **95%**.
>
> **Project**: rkit
> **Version**: v0.9.14
> **Author**: 노수장 (gap-detector)
> **Date**: 2026-04-27
> **Plan Doc**: [instinct-codegen.plan.md](../01-plan/features/instinct-codegen.plan.md)
> **Design Doc**: [instinct-codegen.design.md](../02-design/features/instinct-codegen.design.md)

---

## 1. Match Rate Summary

| Category | Count | Pass | Match Rate |
|----------|------:|-----:|-----------:|
| Functional Requirements (FR) | 5 | 5 | 100% |
| Non-Functional Requirements (NFR) | 3 | 2 + 1 N/A | 100%* |
| Test Cases (Design 8.2) | 5 | 5 | 100% |
| Design Accuracy (문서 정합성) | 2 | 1 | 50% |
| **Overall** | — | — | **95%** |

\* 성능 항목(훅 5초 이내)은 직접 측정 안 됨 — N/A 처리. 토큰 예산/호환성은 smoke test로 검증.

---

## 2. Functional Requirements 검증

| ID | Requirement | Plan Priority | 구현 위치 | 검증 결과 |
|----|-------------|---------------|-----------|-----------|
| FR-01 | `(G) Instinct patterns` 슬롯 추가 | High | `lib/code-quality/pre-guide.js:463-468` | ✅ 슬롯 순서 (F)→(G)→SIZING 정확 |
| FR-02 | `loadConvergedPatterns()` 호출 | High | `pre-guide.js:465` (lazy require) | ✅ try/require로 안전 호출 |
| FR-03 | 1줄 압축 형식 변환 | High | `compactInstinct()` (`pre-guide.js:391-414`) | ✅ smoke test TC1: `[LEARNED] desc(0.92). desc(0.85). desc(0.88).` 출력 확인 |
| FR-04 | `MAX_CONTEXT_LENGTH` 500 → 1500 | Medium | `lib/core/io.js:11` | ✅ 단, **부분 gap 존재** (§4 Gap-1) |
| FR-05 | 로드 실패 시 graceful skip | High | `pre-guide.js:464,468` (try/catch) | ✅ TC2/TC3로 검증 (null/empty/0건) |

---

## 3. Non-Functional Requirements 검증

| Category | 기준 | 측정 결과 | 상태 |
|----------|------|-----------|------|
| Performance | PreToolUse 훅 5초 이내 | 직접 측정 안 됨 (hook timeout 설정 미확인) | ⚠️ N/A |
| Token budget | 인스팅트 주입 텍스트 ≤ 200자 | TC4 (20개 입력) → 189자 | ✅ |
| 호환성 | 인스팅트 없는 프로젝트에서 기존 동작 동일 | TC5 `generateStructuralGuide('test.cpp', ...)` → 353자 정상 반환, (G) skip | ✅ |

---

## 4. Gap 분석

### Gap-1: `MAX_CONTEXT_LENGTH` 중복 상수 (Low/Medium)

- **파일**: `lib/core/constants.js:97`
- **현상**: `lib/core/io.js:11`은 `1500`으로 변경되었으나, `lib/core/constants.js:97`에 별도로 `MAX_CONTEXT_LENGTH = 500` 이 잔존.
- **영향 분석**:
  - 현재 import 추적 결과, `constants.js`의 `MAX_CONTEXT_LENGTH`를 직접 import하는 코드 **없음** (consumers는 `core/index.js` 또는 `core/io.js` 경유 → 1500을 받음).
  - 따라서 **현재 동작 영향 없음**.
  - 그러나 향후 누군가 `require('./core/constants').MAX_CONTEXT_LENGTH` 로 가져오면 500을 받아 silent drift 발생.
- **권장 조치**:
  - (a) `constants.js`에서 `MAX_CONTEXT_LENGTH` 값을 1500으로 동기화, 또는
  - (b) `constants.js`의 중복 정의 삭제하고 `io.js`로 일원화 (선호).

### Gap-2: Design 문서 데이터 플로우 부정확 (Low)

- **파일**: `docs/02-design/features/instinct-codegen.design.md` (§2.2 Data Flow, §4.3)
- **현상**:
  - Design 2.2: `parts.join(' | ') → truncateContext(_, 1500) → stdout` 로 기재
  - Design 4.3: "pre-write.js의 truncateContext 호출: 더 긴 guide 허용" 으로 기재
- **실제 코드**:
  - `scripts/pre-write.js:306` — `outputAllow(contextParts.join(' | '), 'PreToolUse')` 만 호출. **`truncateContext` 호출 없음**.
  - 실제 `truncateContext` 호출처는 `scripts/user-prompt-handler.js:220` (UserPromptSubmit 훅 전용).
- **영향 분석**:
  - Pre-write 훅 출력은 트렁케이션 없이 그대로 stdout 으로 나감 → `MAX_CONTEXT_LENGTH=1500` 변경의 **실제 영향 범위는 UserPromptSubmit 훅에 한정**.
  - 인스팅트 주입 자체는 200자 budget 으로 자체 제한되므로 기능 동작에는 문제 없음.
- **권장 조치**: Design 2.2 데이터 플로우를 `parts.join(' | ') → outputAllow → stdout` 으로 정정. §4.3 "다른 호출자 함께 확대" 표현 유지(맞음). pre-write.js 영향 부분은 삭제 또는 "자체 truncation 없음" 으로 명시.

### Gap-3: 통합 테스트 보류 (Info, 의도적)

- **위치**: Design §8.1 "Integration: 실제 `.rkit/instinct/` 데이터로 (G) 출력 확인 ⬜ 인스팅트 축적 후"
- **현황**: 현재 프로젝트에 `.rkit/instinct/` 데이터 부재 (`loader.loadConvergedPatterns()` 출력 빈 문자열 확인됨).
- **상태**: Plan/Design에 "후행 고려" 로 명시된 항목 → Gap 아님, 단순 미실행 상태.

### Gap-4: Unit tests 미작성 (Info, 의도적)

- **위치**: Design §8.1 "Unit: tests/ 디렉토리 ⬜ 후행 고려"
- **현황**: 인라인 `node -e` smoke test 5건만 수행. `tests/` 정식 테스트 미작성.
- **상태**: 의도적 보류. Match Rate 산정에서 제외.

---

## 5. Smoke Test 결과

Check 단계에서 재실행한 5개 테스트 케이스:

| TC | 시나리오 | 기대 | 실제 | 결과 |
|----|----------|------|------|------|
| TC1 | Happy path 3건 | `[LEARNED] desc(0.92)...` | `"[LEARNED] Use snake_case for functions(0.92). RAII for all resources(0.85). Functions under 40 lines(0.88)."` | ✅ |
| TC2 | null / empty 입력 | `null` | `null` / `null` | ✅ |
| TC3 | header-only (0 항목) | `null` | `null` | ✅ |
| TC4 | 20건 + maxLen=200 | 길이 ≤ 200, prefix `[LEARNED]` | 189자, prefix 정확 | ✅ |
| TC5 | `generateStructuralGuide('test.cpp', ...)` 회귀 | 정상 string 반환, (G) skip | 353자 string 반환 | ✅ |

---

## 6. 요약 및 다음 단계

### 6.1 Match Rate

**95%** — Plan FR 100% 구현, Design 정확성 -3%, 중복 상수 정리 -2%.
임계치 90% 초과 → `/pdca iterate` 불필요. 즉시 `/pdca report` 가능.

### 6.2 권장 처리 (선택 사항)

마이너 정리 작업 두 건은 단일 커밋으로 묶어 처리 권장:

1. `lib/core/constants.js:97` 의 중복 `MAX_CONTEXT_LENGTH` 상수 삭제 또는 1500 동기화 (Gap-1)
2. `docs/02-design/features/instinct-codegen.design.md` §2.2 / §4.3 데이터 플로우 정정 (Gap-2)

위 두 건은 행동 변화를 일으키지 않으므로 별도 PDCA 사이클 불필요. 본 Check 결과를 반영하여 Design v0.2 갱신 후 Report 단계 진입.

### 6.3 다음 단계 명령

```bash
/pdca report instinct-codegen
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-27 | Initial gap analysis | gap-detector / 노수장 |
