---
template: design
version: 1.2
---

# instinct-codegen Design Document

> **Summary**: PreToolUse 훅(`pre-guide.js`)에 인스팅트 수렴 패턴을 압축 주입하여 Write/Edit 시점에 학습된 패턴이 Claude에 자동 전달되도록 한다.
>
> **Project**: rkit
> **Version**: v0.9.14
> **Author**: 노수장
> **Date**: 2026-04-17
> **Status**: Draft (post-hoc, 구현 완료 후 정리)
> **Planning Doc**: [instinct-codegen.plan.md](../../01-plan/features/instinct-codegen.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- 인스팅트(학습된 코딩 패턴)를 코드 작성 시점(PreToolUse)에 주입하여 같은 실수의 반복을 차단
- 기존 PreToolUse 출력 슬롯 `(A)~(F)`의 의미와 순서를 깨지 않고 `(G)` 슬롯으로 확장
- 인스팅트 모듈/데이터가 없는 프로젝트에서 기존 동작 불변(graceful degradation)

### 1.2 Design Principles

- **비침투적 확장**: 기존 슬롯/테스트/계약을 건드리지 않는 추가형(Append-only) 슬롯
- **Graceful Degradation**: 로드 실패/빈 패턴/포맷 불일치 시 `null` 반환 → parts에 push 하지 않음 → 기존 출력 유지
- **토큰 예산 준수**: 인스팅트 주입 텍스트 ≤ 200자, 전체 컨텍스트 `MAX_CONTEXT_LENGTH`=1500자로 기존 3배 확대하되 compact 형식 유지

---

## 2. Architecture

### 2.1 Component Diagram

```
┌──────────────────────────┐
│ Claude Code PreToolUse   │
│  (Write / Edit tool)     │
└───────────┬──────────────┘
            │ stdin (JSON)
            ▼
┌──────────────────────────┐      ┌────────────────────────┐
│ scripts/pre-write.js     │─────▶│ lib/core/io.js         │
│  (hook entrypoint)       │      │  MAX_CONTEXT_LENGTH    │
└───────────┬──────────────┘      │  truncateContext()     │
            │ calls                └────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────┐
│ lib/code-quality/pre-guide.js                             │
│   generateStructuralGuide(filePath, content)              │
│   ┌──────────────────────────────────────────────────┐   │
│   │ (A) Layer detection                              │   │
│   │ (B) Anti-pattern detection                       │   │
│   │ (C) Design pattern suggestion                    │   │
│   │ (D) Structural risk (loops/branches)             │   │
│   │ (E) Compact language rules                       │   │
│   │ (F) Existing pattern consistency                 │   │
│   │ (G) Instinct patterns      ◀── NEW SLOT          │   │
│   │ SIZING base rule                                 │   │
│   └──────────────────────────────────────────────────┘   │
└───────────┬──────────────────────────────────────────────┘
            │ lazy require (try/catch)
            ▼
┌──────────────────────────────────────────────────────────┐
│ lib/instinct/loader.js                                    │
│   loadConvergedPatterns() → markdown text                 │
│   └─ reads .rkit/instinct/patterns.json + confidence.json │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
Write/Edit tool call
   │
   ▼
pre-write.js (hook)
   │ filePath, content
   ▼
pre-guide.generateStructuralGuide()
   │
   ├── (A)~(F) existing parts
   │
   └── (G) try {
            raw = loader.loadConvergedPatterns()    // '' on fail
            compact = compactInstinct(raw, 200)      // null on empty/fail
            if (compact) parts.push(compact)
        } catch { /* skip */ }
   │
   ▼
parts.join(' | ') → outputAllow(...) → stdout
   (pre-write.js는 자체 truncation 없음. MAX_CONTEXT_LENGTH는
    user-prompt-handler.js의 truncateContext에서만 사용됨)
   │
   ▼
Claude context injection
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `pre-guide.js` | `lib/instinct/loader.js` (lazy require) | Converged pattern 로드 |
| `pre-guide.js` | `lib/core/io.js` (indirect via pre-write.js) | 컨텍스트 트렁케이션 상수 공유 |
| `loader.js` | `lib/instinct/store.js`, `confidence.js` | 패턴/신뢰도 저장소 접근 |

---

## 3. Data Model

### 3.1 loader.js 출력 형식 (입력 계약)

`loadConvergedPatterns()`는 아래 마크다운 문자열을 반환하거나 `''`을 반환한다.

```markdown
## Project Instinct (auto-learned patterns)
- [category] [lang] description (confidence: 0.92)
  Fix: correction description
- [category] description (confidence: 0.85)
```

- `[lang]` 블록은 선택적(C#/TS 등 언어 정보 있을 때만)
- `Fix:` 라인은 선택적
- 각 항목 라인: `^- \[카테고리\]( \[언어\])? 설명 \(confidence: 숫자\)$`

### 3.2 compactInstinct 출력 형식 (출력 계약)

```
[LEARNED] desc1(0.92). desc2(0.85). desc3(0.88).
```

- 접두사 `[LEARNED] ` 고정 (Claude가 인스팅트 영역임을 식별)
- 각 항목 `설명(신뢰도)` 뒤에 `. ` 구분자
- 마지막 항목 뒤에도 `.` 추가
- 총 길이 ≤ `maxLen` (기본 200자)
- 항목이 0개면 `null` 반환

---

## 4. API Specification

### 4.1 compactInstinct(raw, maxLen)

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `raw` | `string \| null` | loader.js 출력 마크다운 |
| `maxLen` | `number` (default 200) | 출력 문자열 최대 길이 |

**반환**: `string | null`

- 정상: `[LEARNED] ...` 형식의 단일 라인
- 빈 입력/파싱 실패/0 항목: `null`

**Side effects**: 없음 (pure function)

### 4.2 generateStructuralGuide 확장

기존 시그니처 불변: `(filePath: string, content: string|null) → string|null`.
반환 문자열 내부 순서: `(A) → ... → (F) → (G) → SIZING`.
`(G)`가 `null`이면 parts에 추가되지 않음 → 기존 출력과 바이트 단위로 동일.

### 4.3 MAX_CONTEXT_LENGTH 확대

`lib/core/io.js`의 `MAX_CONTEXT_LENGTH: 500 → 1500`. (`lib/core/constants.js`의 중복 상수는 v0.9.14 Check 단계에서 제거되어 `io.js`가 single source of truth)
영향 범위:
- `scripts/user-prompt-handler.js:220`의 `truncateContext` 호출: 더 긴 컨텍스트 허용 (UserPromptSubmit 훅)
- `scripts/pre-write.js`(PreToolUse 훅)는 truncate를 호출하지 않으므로 본 상수의 직접 영향 없음. 인스팅트 자체는 `compactInstinct(maxLen=200)`으로 자체 제한.

---

## 5. UI/UX Design

N/A — CLI/Hook 내부 동작. 사용자 직접 UI 없음.

---

## 6. Error Handling

### 6.1 실패 지점 및 처리

| 실패 지점 | 처리 전략 | 결과 |
|-----------|-----------|------|
| `require('../instinct/loader')` 실패 | `try/catch`로 감싸고 skip | `(G)` 부재, 나머지 출력 유지 |
| `loadConvergedPatterns()` 내부 예외 | loader 자체가 try/catch → `''` 반환 | compactInstinct가 null 반환 → skip |
| `compactInstinct` 파싱 0건 | `null` 반환 | parts push 안 함 |
| `maxLen` 초과 | 루프 중 조기 break, 마지막 유효 항목까지만 포함 | 잘린 형식 유지 |

### 6.2 에러 전파 금지 원칙

- `(G)` 슬롯의 어떠한 실패도 전체 `generateStructuralGuide` 실패로 번지면 안 됨
- 빈 파서 결과, 예외, 모듈 부재 모두 **조용히** skip (사용자에게 에러 노출 안 함)

---

## 7. Security Considerations

- 인스팅트 파일(`.rkit/instinct/*.json`)은 로컬 파일로, 외부 입력 없음
- compactInstinct는 `raw` 문자열을 파싱만 할 뿐 `eval`/`exec` 등 동적 실행 경로 없음
- 출력 텍스트는 Claude 컨텍스트로 주입되며, 사용자 기밀 데이터는 포함하지 않음 (loader가 description/confidence만 노출)

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Tool | 상태 |
|------|--------|------|------|
| Smoke | `compactInstinct`, `generateStructuralGuide` | `node -e` 인라인 | ✅ Do 단계에서 수행 |
| Unit | 엣지 케이스 (빈/null/0건/초과) | 기존 방식 유지 (tests/ 디렉토리) | ⬜ 후행 고려 |
| Integration | 실제 `.rkit/instinct/` 데이터로 (G) 출력 확인 | 수동 실행 | ⬜ 인스팅트 축적 후 |

### 8.2 Test Cases (완료됨)

- [x] Happy path: 샘플 마크다운 3건 → `[LEARNED] desc1(0.92). desc2(0.85). desc3(0.88).` (90자)
- [x] Empty/null: `null` 반환
- [x] 0 항목(마크다운 헤더만): `null` 반환
- [x] 예산 초과: 20건 입력 시 200자 이내 앞쪽 항목만 포함
- [x] 기존 동작 불변: 인스팅트 없을 때 (A)~(F) + SIZING 출력 동일

---

## 9. Clean Architecture

### 9.1 Layer Assignment (본 feature)

| Component | Layer | Location |
|-----------|-------|----------|
| `pre-write.js` | Presentation (hook entry) | `scripts/` |
| `pre-guide.js` | Application (orchestration) | `lib/code-quality/` |
| `loader.js` | Application (instinct service) | `lib/instinct/` |
| `io.js` | Infrastructure (shared util) | `lib/core/` |

### 9.2 Dependency Rules 준수

- `pre-guide.js`가 `loader.js`를 **lazy require**로 호출 → 순환 참조/초기화 문제 회피
- `loader.js`는 `pre-guide.js`에 역의존하지 않음 (단방향)

---

## 10. Coding Convention Reference

### 10.1 본 feature의 컨벤션 적용

| 항목 | 컨벤션 |
|------|--------|
| 함수 길이 | `compactInstinct` ≤ 40 lines 준수 |
| 에러 처리 | try/catch graceful skip (기존 패턴 준수) |
| 상수 | `MAX_CONVERGED_PATTERNS`(loader), `maxLen` 기본값(compactInstinct) 명시 |
| JSDoc | 신규 함수에 `@param`/`@returns` 작성 |
| 정규표현식 | 단일 라인 매칭, 주석으로 포맷 명시 |

---

## 11. Implementation Guide

### 11.1 File Changes

```
lib/
├── core/io.js                    ── MAX_CONTEXT_LENGTH 500→1500
└── code-quality/pre-guide.js     ── compactInstinct() 신규 + (G) slot + export
```

### 11.2 Implementation Order

1. [x] `io.js` 상수 변경 (파급 영향 먼저 확인)
2. [x] `pre-guide.js`에 `compactInstinct()` 헬퍼 추가 (Section G 블록)
3. [x] `generateStructuralGuide()` 내부에 `(G)` 슬롯 삽입 (F 뒤, SIZING 앞)
4. [x] `module.exports`에 `compactInstinct` 추가 (테스트/재사용 목적)
5. [x] 스모크 테스트 5건 수행
6. [ ] Gap 분석 → Plan FR 대비 100% 매칭 확인
7. [ ] 커밋 (의도적으로 분리: (a) io.js, (b) pre-guide.js)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-17 | Post-hoc design doc (Do 이후 정리) | 노수장 |
| 0.2 | 2026-04-27 | Check 결과 반영: §2.2 데이터 플로우 / §4.3 영향 범위 정정 | 노수장 |
