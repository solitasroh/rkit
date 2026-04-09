# instinct-engine Planning Document

> **Summary**: rkit 인스팅트 학습 엔진 — 코드 리뷰 패턴 자동 누적 및 세션 간 일관성 보장
>
> **Project**: rkit
> **Version**: v0.9.13
> **Author**: 노수장
> **Date**: 2026-04-10
> **Status**: Draft
> **Prior Design**: `docs/archive/2026-04/ecc-insights-integration/ecc-insights-integration.design.md` Section 7

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 코드 리뷰 결과가 세션마다 리셋되어 동일한 교정을 반복 지시해야 하고, 프로젝트별 코딩 관습이 축적되지 않는다 |
| **Solution** | 인스팅트 학습 엔진 4개 모듈(collector, store, confidence, loader)로 L1/L2 리뷰 패턴을 자동 수집하고, 신뢰도 수렴 알고리즘으로 검증된 패턴만 세션 시작 시 자동 주입 |
| **Function/UX Effect** | 3세션 후 반복 교정 70% 감소. SessionStart 훅에서 프로파일 자동 로드, `/code-review` 시 수렴된 패턴 자동 적용 |
| **Core Value** | "AI가 프로젝트의 코딩 관습을 기억한다" — 세션 간 학습 연속성으로 개발자 교정 피로를 제거 |

---

## 1. Overview

### 1.1 Purpose

ecc-insights-integration의 Phase 3으로, 3-Layer 코드 리뷰 시스템(v0.9.11~v0.9.12)에서 생산된 리뷰 결과를 세션 간 누적하는 인스팅트 학습 엔진을 구현한다.

### 1.2 Background

- **선행 작업**: v0.9.11(L1 code-analyzer) + v0.9.12(L2 리뷰어 + orchestrator) 완료, Match Rate 97.1%
- **설계 기반**: `ecc-insights-integration.design.md` Section 7 (JSON 스키마, 수렴 알고리즘, 모듈 인터페이스 확정)
- **ECC 참조**: Everything Claude Code의 세션 간 패턴 학습 철학 계승

### 1.3 Related Documents

- 아카이브된 Design: `docs/archive/2026-04/ecc-insights-integration/ecc-insights-integration.design.md` Section 7
- review-orchestrator: `lib/code-quality/review-orchestrator.js` (인스팅트 수집 연동점)
- code-analyzer: `agents/code-analyzer.md` (L1, memory: project)

---

## 2. Scope

### 2.1 In Scope (v0.9.13)

| # | 작업 | 파일 | 설명 |
|---|------|------|------|
| 1 | 신뢰도 알고리즘 | `lib/instinct/confidence.js` (NEW) | 패턴 신뢰도 업데이트, 수렴 판정, 승격 후보 판별 |
| 2 | 저장소 관리 | `lib/instinct/store.js` (NEW) | patterns.json/confidence.json CRUD, 프로젝트 해시 생성 |
| 3 | 패턴 수집기 | `lib/instinct/collector.js` (NEW) | L1/L2 리뷰 결과에서 패턴 추출, 사용자 교정 이벤트 처리 |
| 4 | 세션 로더 | `lib/instinct/loader.js` (NEW) | SessionStart 시 수렴 패턴 로드, 프롬프트 주입 텍스트 생성 |

### 2.2 Out of Scope

- **v0.9.14**: 크로스 프로젝트 글로벌 승격, 팀 공유 (`scope: "global"`, `scope: "team"`)
  - 데이터 구조에 `scope`, `origin` 필드 미리 포함하되 구현은 v0.9.14에서
- **1.0.0**: Go, Rust, Java 언어 확장
- review-orchestrator.js의 인스팅트 호출 코드 추가는 모듈 완성 후 통합 단계에서 진행

### 2.3 Constraints

- `.rkit/instinct/{project-hash}/` 디렉토리에 JSON 파일로 저장 (DB 없음)
- patterns.json 최대 크기: 500KB (패턴 수 제한으로 관리)
- 수렴된 패턴만 프롬프트에 주입 (토큰 절약)
- 기존 `.rkit/state/` 경로 체계와 일관성 유지

---

## 3. Implementation Strategy

### 3.1 구현 순서

```
confidence.js (의존성 없음)
    ↓
store.js (confidence.js 참조)
    ↓
collector.js (store.js 참조)
    ↓
loader.js (store.js + confidence.js 참조)
    ↓
통합: review-orchestrator.js에 collector 연동
```

### 3.2 핵심 데이터 구조

**patterns.json**: Design Section 7.3 확정 스키마 사용
- `scope` 필드: `"project"` (v0.9.13), `"global"` / `"team"` (v0.9.14 확장점)
- `origin` 필드: 패턴 출처 추적 (review/correction/manual/promoted)

**confidence.json**: Design Section 7.4 확정 스키마 사용
- `promotable` 필드: v0.9.14 글로벌 승격 후보 플래그

### 3.3 수렴 알고리즘 (Design Section 7.5 확정)

```
초기: 0.3
적용(applied):  +0.2 × (1 - current)
거부(rejected): -0.3 × current
미관찰(decay):  -0.05 × current

수렴: 3연속 delta < 0.05 → converged
비활성화: confidence < 0.1
```

### 3.4 SessionStart 훅 연동

`loader.js`는 SessionStart 훅에서 호출되어:
1. 프로젝트 해시 계산
2. 수렴된 패턴 필터링 (converged = true)
3. 컴팩트 텍스트로 변환 (토큰 절약)
4. 세션 컨텍스트에 주입

---

## 4. Success Criteria

| 기준 | 목표 |
|------|------|
| 모듈 로드 | 4개 모듈 모두 `require()` 에러 없음 |
| 신뢰도 계산 | 수렴 시각화 예시와 동일한 결과 산출 |
| 패턴 저장/로드 | `.rkit/instinct/{hash}/patterns.json` 정상 CRUD |
| 프로파일 로드 | 수렴 패턴만 필터링하여 프롬프트 텍스트 생성 |
| Design 일치도 | Gap Analysis >= 90% |

---

## 5. Risks

| 리스크 | 영향 | 대응 |
|--------|------|------|
| patterns.json 용량 증가 | 세션 시작 지연 | 500KB 제한, 오래된 패턴 비활성화 |
| 잘못된 패턴 수렴 | 잘못된 교정 자동 적용 | confidence < 0.1 비활성화, 수동 제거 CLI |
| git remote 없는 프로젝트 | 프로젝트 해시 불일치 | 디렉토리 경로 fallback |

---

## 6. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-10 | Design Section 7 기반 초안 작성 | 노수장 |
