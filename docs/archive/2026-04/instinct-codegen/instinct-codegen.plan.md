# instinct-codegen Planning Document

> **Summary**: 인스팅트 학습 패턴을 코드 작성 시점(PreToolUse)에 주입하여 코드 생성 품질 향상
>
> **Project**: rkit
> **Version**: v0.9.14
> **Author**: 노수장
> **Date**: 2026-04-10
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 인스팅트(학습된 코딩 패턴)가 코드 리뷰 시에만 반영되고, 코드 작성 시에는 반영되지 않아 같은 실수가 반복됨 |
| **Solution** | PreToolUse 훅(pre-guide.js)의 `generateStructuralGuide()`에 인스팅트 패턴 주입 슬롯 추가 |
| **Function/UX Effect** | 사용자 개입 없이 Write/Edit 시 자동으로 학습된 패턴이 Claude에게 전달됨 |
| **Core Value** | "리뷰에서 배운 것이 다음 코드 작성에 바로 반영된다" — 학습 루프 완성 |

---

## 1. Overview

### 1.1 Purpose

v0.9.13에서 구현된 인스팅트 학습 엔진이 리뷰 에이전트(code-analyzer, c-cpp-reviewer 등)에만 연결되어 있다. 코드 작성 시점에는 SessionStart의 `additionalContext`에만 약하게 주입되는데, A/B 실험에서 이 방식은 효과가 없음이 확인되었다.

본 feature는 PreToolUse 훅(`pre-guide.js`)에 인스팅트 패턴을 주입하여, Claude가 C/C++/C# 코드를 작성할 때 학습된 패턴을 참고하도록 한다.

### 1.2 Background

- v0.9.13 instinct-prompt-injection A/B 실험 결과:
  - `additionalContext`만: 효과 없음 (X)
  - `profile.md` + 명시적 지시: 효과 있음 (O)
- 현재 `profile.md`를 import하는 건 리뷰 에이전트 4개뿐
- PreToolUse 훅(`pre-write.js` → `pre-guide.js`)은 모든 Write/Edit에 100% 실행됨
- `isCodeFile()` 범위: `.c, .h, .cpp, .hpp, .cs, .dts, .dtsi` — 대상 언어 포함

### 1.3 Related Documents

- 인스팅트 엔진: `docs/archive/2026-04/instinct-engine/`
- 인스팅트 프롬프트 주입 A/B: `docs/archive/2026-04/instinct-prompt-injection/`
- ECC 비교 분석: `docs/03-analysis/everything-claude-code-comparison.analysis.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] `pre-guide.js`의 `generateStructuralGuide()`에 인스팅트 슬롯 `(G)` 추가
- [ ] `MAX_CONTEXT_LENGTH` 확대 (500 → 1500)
- [ ] 인스팅트 패턴을 COMPACT_RULES와 동일한 1줄 압축 형식으로 변환
- [ ] 인스팅트가 없거나 로드 실패 시 graceful skip

### 2.2 Out of Scope

- PostToolUse 사후 검증 (안 2, 별도 feature)
- 인스팅트 → 스킬 승격 (안 3, v0.9.15 이후)
- `isCodeFile()` 확장자 범위 확대 (.py, .js 등)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `generateStructuralGuide()`에 `(G) Instinct patterns` 슬롯 추가 | High | Pending |
| FR-02 | `loader.js`의 `loadConvergedPatterns()`를 pre-guide.js에서 호출 | High | Pending |
| FR-03 | 수렴된 패턴을 1줄 압축 형식으로 변환 (COMPACT_RULES 스타일) | High | Pending |
| FR-04 | `MAX_CONTEXT_LENGTH`를 500 → 1500으로 확대 | Medium | Pending |
| FR-05 | 인스팅트 로드 실패 시 에러 없이 기존 동작 유지 | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | PreToolUse 훅 총 실행시간 5초 이내 유지 | timeout 설정 확인 |
| Token budget | 인스팅트 주입 텍스트 200자 이내 | 문자열 길이 측정 |
| 호환성 | 인스팅트 없는 프로젝트에서 기존 동작 변화 없음 | 기존 테스트 통과 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] `pre-guide.js`에 인스팅트 로드 + 압축 + 주입 코드 추가
- [ ] `io.js`의 `MAX_CONTEXT_LENGTH` 1500으로 변경
- [ ] 인스팅트 있는 프로젝트에서 Write/Edit 시 패턴 텍스트가 출력에 포함됨
- [ ] 인스팅트 없는 프로젝트에서 기존 동작 동일

### 4.2 Quality Criteria

- [ ] 기존 pre-guide.js 테스트 통과
- [ ] 훅 실행시간 5초 미초과
- [ ] `(A)~(F)` 기존 슬롯 출력 변화 없음

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| MAX_CONTEXT_LENGTH 확대로 토큰 비용 증가 | Low | Medium | 인스팅트 부분을 200자로 제한 |
| pre-guide.js에서 instinct 모듈 require 실패 | Medium | Low | try/catch + graceful skip |
| 인스팅트 텍스트가 다른 contextParts와 잘림 | Medium | Medium | 인스팅트 우선순위 조정 또는 별도 출력 |

---

## 6. Implementation Approach

### 6.1 수정 대상 파일

| File | Change |
|------|--------|
| `lib/code-quality/pre-guide.js` | `(G)` 슬롯 추가: 인스팅트 로드 + 압축 |
| `lib/core/io.js` | `MAX_CONTEXT_LENGTH` 500 → 1500 |

### 6.2 인스팅트 압축 형식

기존 COMPACT_RULES 패턴을 따름:

```javascript
// 현재 COMPACT_RULES 예시
cpp: 'C/C++: RAII (unique_ptr), no raw new/delete. ranges/algorithms...'

// 인스팅트 압축 예시
instinct: '[LEARNED] RAII for all resources(0.92). No magic numbers(0.85). Functions<=30 lines(0.88).'
```

### 6.3 코드 변경 개요

```javascript
// pre-guide.js generateStructuralGuide() 에 추가
// (G) Instinct patterns (learned from previous reviews)
try {
  const { loadConvergedPatterns } = require('../instinct/loader');
  const raw = loadConvergedPatterns();
  if (raw) {
    const compact = compactInstinct(raw, 200); // 200자 제한
    parts.push(compact);
  }
} catch (e) {
  // graceful skip - instinct not available
}
```

---

## 7. Next Steps

1. [ ] Design 문서 작성 (`/pdca design instinct-codegen`)
2. [ ] 구현 (pre-guide.js, io.js 수정)
3. [ ] Gap 분석 (`/pdca analyze instinct-codegen`)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-10 | Initial draft | 노수장 |
