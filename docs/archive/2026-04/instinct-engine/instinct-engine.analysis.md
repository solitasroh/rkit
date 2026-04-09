# Design-Implementation Gap Analysis Report: instinct-engine

## Analysis Overview

| 항목 | 값 |
|------|-----|
| **분석 대상** | instinct-engine (v0.9.13) |
| **설계 문서** | `docs/02-design/features/instinct-engine.design.md` |
| **구현 경로** | `lib/instinct/{confidence,store,collector,loader}.js` |
| **분석 일자** | 2026-04-10 |

---

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 95.8% | [PASS] |
| Architecture Compliance | 100% | [PASS] |
| Convention Compliance | 100% | [PASS] |
| **Overall** | **96.6%** | **[PASS]** |

Match Rate = 46 / 48 = **95.8%**

---

## Detailed Comparison

### 1. confidence.js (Design Section 3)

| # | 검증 항목 | 설계 | 구현 | 결과 |
|---|----------|------|------|:----:|
| 1 | INITIAL_CONFIDENCE = 0.3 | Section 3.1 | line 19 | PASS |
| 2 | APPLY_FACTOR = 0.2 | Section 3.1 | line 20 | PASS |
| 3 | REJECT_FACTOR = 0.3 | Section 3.1 | line 21 | PASS |
| 4 | DECAY_FACTOR = 0.05 | Section 3.1 | line 22 | PASS |
| 5 | CONVERGENCE_THRESHOLD = 0.05 | Section 3.1 | line 23 | PASS |
| 6 | CONVERGENCE_SESSIONS = 3 | Section 3.1 | line 24 | PASS |
| 7 | DEACTIVATION_THRESHOLD = 0.1 | Section 3.1 | line 25 | PASS |
| 8 | updateConfidence applied 수식 | `+= APPLY_FACTOR * (1 - current)` | line 37 | PASS |
| 9 | updateConfidence rejected 수식 | `-= REJECT_FACTOR * current` | line 39 | PASS |
| 10 | updateConfidence decay 수식 | `-= DECAY_FACTOR * current` | line 41 | PASS |
| 11 | updateConfidence 반환값 | `{ score, delta }` | line 50 | PASS |
| 12 | isConverged(history) | 최근 N세션 delta < threshold | line 59-63 | PASS |
| 13 | isDeactivated(confidence) | < 0.1 | line 70-72 | PASS |
| 14 | isPromotable(confidence, projectCount) | >= 0.8 AND >= 3 | line 80-82 | PASS |
| 15 | module.exports (7상수 + 4함수) | Section 3.2 | line 84-96 | PASS |

**Subtotal: 15 / 15 (100%)**

---

### 2. store.js (Design Section 4)

| # | 검증 항목 | 설계 | 구현 | 결과 |
|---|----------|------|------|:----:|
| 16 | getProjectHash() git remote SHA-256 12자 | Section 4.1 | line 44-47 | PASS |
| 17 | getProjectHash() fallback 디렉토리 경로 | Section 4.1 | line 48-51 | PASS |
| 18 | loadPatterns(projectHash) 없으면 빈 구조 | Section 4.2 | line 144-148 | PASS |
| 19 | loadPatterns safeRead 사용 | Section 4.2 | line 147 | PASS |
| 20 | savePatterns 원자적 쓰기 (tmp -> rename) | Section 4.4 | line 79-89 | PASS |
| 21 | loadConfidence 동일 패턴 | Section 4.2 | line 167-171 | PASS |
| 22 | saveConfidence 동일 패턴 | Section 4.2 | line 178-181 | PASS |
| 23 | createEmptyPatterns 스키마 v1.0.0 | Section 4.5 | line 116-124 | PASS |
| 24 | createEmptyConfidence 스키마 v1.0.0 | Section 4.5 | line 126-133 | PASS |
| 25 | loadGlobalPatterns() v0.9.14 stub | Section 4.2 | line 187-189 | PASS |
| 26 | promoteToGlobal() throw | Section 4.2 | line 192-194 | PASS |
| 27 | 경로 `.rkit/instinct/{hash}/` | Section 4.3 | line 36-37 | PASS |
| 28 | 디렉토리 자동 생성 mkdirSync recursive | Section 8 | line 69-72 | PASS |
| 29 | JSON 파싱 실패 시 .bak 백업 + 빈 구조 반환 | Section 8 | line 103-109 | PASS |
| 30 | 원자적 쓰기 실패 시 .tmp 정리 | Section 8 | line 86 | PASS |
| 31 | patterns.json > 500KB 시 비활성 패턴 제거 | Section 8 | MAX_PATTERNS_SIZE 상수만 정의, 제거 로직 미구현 | **FAIL** |

**Subtotal: 15 / 16 (93.8%)**

---

### 3. collector.js (Design Section 5)

| # | 검증 항목 | 설계 | 구현 | 결과 |
|---|----------|------|------|:----:|
| 32 | extractPatterns(reviewResult, sessionId) | Section 5.1 | line 80-121 | PASS |
| 33 | findings -> 패턴 배열 변환 | Section 5.2 | line 95-118 | PASS |
| 34 | extractCorrectionPattern(correctionEvent, sessionId) | Section 5.1 | line 129-156 | PASS |
| 35 | before/after -> 패턴 변환 | Section 5.1 | line 133-155 | PASS |
| 36 | saveExtractedPatterns(patterns, sessionId) | Section 5.1 | line 163-201 | PASS |
| 37 | store 저장 + confidence 업데이트 | Section 5.1 | line 197-200 | PASS |
| 38 | findSimilarPattern: category + language + description | Section 5.3 | line 66-72 | PASS |
| 39 | 유사 패턴 발견 시 sessions 배열에 append | Section 5.2 | line 176 | PASS |
| 40 | 신규 패턴 UUID v4 + INITIAL_CONFIDENCE | Section 5.2 | line 96, 107 | PASS |
| 41 | 신규 패턴 scope = "project" | Section 5.2 | line 109 | PASS |
| 42 | 중복 감지 로직 | Section 5.3 | line 88-91, 173 | PASS |

**Subtotal: 11 / 11 (100%)**

---

### 4. loader.js (Design Section 6)

| # | 검증 항목 | 설계 | 구현 | 결과 |
|---|----------|------|------|:----:|
| 43 | loadConvergedPatterns() 수렴 패턴 필터링 | Section 6.1 | line 28-34 | PASS |
| 44 | 컴팩트 텍스트 변환 | Section 6.2 | line 42-49 | PASS |
| 45 | MAX_CONVERGED_PATTERNS = 20 | Section 6.2 | line 13 | PASS |
| 46 | getProfileSummary() 5개 필드 | Section 6.1 | line 84-90 | PASS |
| 47 | Graceful degradation (try/catch) | Section 6.1 | line 52-55, 91-93 | PASS |
| 48 | 500 토큰 제한 로직 | Section 6.2 "총 500 토큰 이내" | 토큰 카운트/제한 로직 미구현 | **FAIL** |

**Subtotal: 5 / 6 (83.3%)**

---

## Summary

### [MISSING] 설계 O, 구현 X (2건)

| # | 항목 | 설계 위치 | 설명 | 영향도 |
|---|------|----------|------|:------:|
| 1 | 패턴 크기 제한 퍼지 | Section 8 row 5 | `patterns.json > 500KB` 시 가장 오래된 비활성 패턴 제거 로직. `MAX_PATTERNS_SIZE` 상수만 정의됨 (store.js:29), 실제 제거 로직 없음 | Medium |
| 2 | 토큰 제한 | Section 6.2 | "총 500 토큰 이내" 텍스트 생성 제한. MAX_CONVERGED_PATTERNS=20 상수로 간접 제한만 존재, 명시적 토큰 카운트 없음 | Low |

### [ADDED] 설계 X, 구현 O (5건)

| # | 항목 | 구현 위치 | 설명 | 영향도 |
|---|------|----------|------|:------:|
| 1 | clamp + 반올림 | confidence.js:48-50 | score를 0~1 범위로 clamp하고 소수점 3자리 반올림. 수치 안정성 확보 | None (합리적 추가) |
| 2 | 유틸리티 export | store.js:198-200 | `getInstinctBase()`, `getProjectDir()`, `MAX_PATTERNS_SIZE` 추가 export | None (유틸리티) |
| 3 | 구현 상세 export | collector.js:204-207 | `CATEGORIES`, `RULE_CATEGORY_MAP`, `detectLanguageFromFile` 추가 export | None (테스트 편의) |
| 4 | loadGlobalPatterns 실구현 | store.js:187-189 | 설계는 단순 stub이지만 구현은 safeRead로 실제 파일 읽기 수행 | None (설계보다 진보) |
| 5 | 컴팩트 텍스트 Fix 라인 | loader.js:48-49 | correction.description이 있으면 `Fix:` 라인 추가. 설계 예시에 없음 | None (유용한 추가) |

### [CHANGED] 설계 != 구현 (0건)

해당 없음. 모든 인터페이스, 수식, 반환값이 설계와 일치합니다.

---

## Data Schema Compliance (Design Section 7)

| 스키마 항목 | 설계 | 구현 확인 위치 | 결과 |
|------------|------|---------------|:----:|
| patterns.json: version | "1.0.0" | store.js:118 | PASS |
| patterns.json: projectId | projectHash | store.js:119 | PASS |
| patterns.json: projectMeta | remoteUrl, domain, languages | store.js:120 | PASS |
| patterns.json: patterns[] | 배열 | store.js:121 | PASS |
| patterns.json: metadata | totalSessions, lastUpdated, schemaVersion | store.js:122 | PASS |
| confidence.json: version | "1.0.0" | store.js:128 | PASS |
| confidence.json: projectId | projectHash | store.js:129 | PASS |
| confidence.json: scores{} | Object | store.js:130 | PASS |
| confidence.json: globalCandidates[] | Array | store.js:131 | PASS |
| 패턴 필드: id | UUID v4 | collector.js:96 (crypto.randomUUID) | PASS |
| 패턴 필드: category | 6종 enum | collector.js:17 | PASS |
| 패턴 필드: pattern | description, example, language | collector.js:98-102 | PASS |
| 패턴 필드: correction | description, example | collector.js:104-106 | PASS |
| 패턴 필드: confidence | 0-1 | collector.js:107 | PASS |
| 패턴 필드: scope | project/global/team | collector.js:109 | PASS |
| 패턴 필드: origin | projectId, sessionId, timestamp, source | collector.js:110-114 | PASS |
| 패턴 필드: sessions[] | sessionId, timestamp, action | collector.js:115 | PASS |
| 패턴 필드: tags | Array | collector.js:117 | PASS |

**Schema Compliance: 18 / 18 (100%)**

---

## Error Handling Compliance (Design Section 8)

| 에러 상황 | 설계 처리 | 구현 | 결과 |
|----------|----------|------|:----:|
| 디렉토리 없음 | mkdirSync recursive | store.js:69-72 ensureDir() | PASS |
| JSON 파싱 실패 | .bak 백업 + 빈 구조 | store.js:103-109 safeRead() | PASS |
| confidence.json 파싱 실패 | 경고 로그 + 빈 구조 | store.js:97-109 safeRead() (동일 함수) | PASS |
| git remote 없음 | 디렉토리 경로 fallback | store.js:48-51 catch block | PASS |
| patterns.json > 500KB | 비활성 패턴 제거 | MAX_PATTERNS_SIZE 상수만 존재, 로직 없음 | **FAIL** |
| 원자적 쓰기 실패 | .tmp 제거 + 기존 파일 보존 | store.js:85-88 catch block | PASS |

**Error Handling: 5 / 6 (83.3%)**

---

## Recommended Actions

### Immediate (FAIL 항목)

1. **패턴 크기 제한 구현** (store.js): `savePatterns()` 내에 `MAX_PATTERNS_SIZE` 초과 시 `isDeactivated()` 패턴을 오래된 순으로 제거하는 로직 추가. 또는 설계 문서에서 "v0.9.14 이후 구현" 으로 스코프 조정.

2. **토큰 제한 구현** (loader.js): `loadConvergedPatterns()` 에서 생성 텍스트의 대략적 토큰 수를 산정하여 500 토큰 초과 시 패턴 수를 줄이는 로직 추가. 또는 MAX_CONVERGED_PATTERNS=20 이 사실상 500토큰 이내를 보장한다면 설계 문서에 그 근거를 명시.

### Documentation Update (ADDED 항목)

설계에 없는 구현 5건은 모두 합리적 추가(defensive coding, 테스트 편의)이므로 설계 문서를 구현에 맞게 업데이트 권장:
- Section 3.3에 "score는 0~1 범위로 clamp, 소수점 3자리 반올림" 추가
- Section 6.2에 "correction이 있으면 Fix: 라인 추가" 명시

---

## Final Match Rate

```
총 검증 항목: 48
충족 항목:    46
미충족 항목:   2

Match Rate = 46 / 48 = 95.8%
```

> Match Rate >= 90%: 설계와 구현이 잘 일치합니다. 미충족 2건은 방어적 상한 제한 로직으로 기능 동작에는 영향이 없으나 장기 운용 시 필요한 항목입니다.
