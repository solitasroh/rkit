# ui-enhancement Completion Report

> **Feature**: ui-enhancement
> **Project**: mcukit v0.7.0
> **Date**: 2026-04-03
> **Author**: soojang.roh

---

## 1. Executive Summary

### 1.1 Overview

| Item | Detail |
|------|--------|
| Feature | lib/ui Dual Output 분리 + Config 연동 + 도메인 컴포넌트 |
| Duration | 2026-04-03 (단일 세션) |
| PDCA Phases | Plan → Design → Do → Check → Report |
| Match Rate | 97% → **100%** (1회 수정) |

### 1.2 Results

| Metric | Value |
|--------|-------|
| New Files | 10 (engines 2, components 7, config-loader 1) |
| Modified Files | 2 (index.js 재작성, session-start.js) |
| Total Lines | 1,796 |
| Architecture | Option B (Clean) — engines/ + components/ 분리 |
| Gap Iterations | 1 (session-start.js data 래핑 + Design 5건 역반영) |
| Tests | 4 컴포넌트 dual render + backward compat 통과 |

### 1.3 Value Delivered

| Perspective | Result |
|-------------|--------|
| **Problem** | ANSI가 additionalContext에서 stripped → 바이트 낭비. 임계값 하드코딩. 도메인 특화 UI 없음 |
| **Solution** | Dual Output(terminal→stderr ANSI, context→markdown) 엔진 분리 + config-loader + budget-gauge + sparkline |
| **Function/UX** | 사용자는 터미널에서 색상 대시보드, LLM은 깔끔한 markdown 테이블/리스트 컨텍스트 |
| **Core Value** | Hook 출력의 두 채널을 각각 최적화 — 개발자 시각 경험 + AI 컨텍스트 정확도 동시 향상 |

---

## 2. PDCA Cycle Summary

### 2.1 Plan

- 3개 에이전트 병렬 조사: UI 툴킷 (Ink/Blessed 비호환 확인), UX 패턴 (sparkline/phase-aware), 코드 분석 (bkit 직접 포팅 확인)
- 핵심 발견: additionalContext에서 ANSI stripped → dual output 필요
- 외부 라이브러리 추가 불필요 확인 (순수 Node.js 유지)

### 2.2 Design

- 3가지 옵션 → **Option B (Clean)** 선택: engines/ + components/ 완전 분리
- 컴포넌트 인터페이스: `{ terminal(), context(), renderXxx() }`
- config-loader: mcukit.config.json ui 섹션 로드 + 기본값 병합

### 2.3 Do

| Step | File | Lines |
|:----:|------|:-----:|
| 1 | `engines/terminal.js` | 103 |
| 2 | `engines/markdown.js` | 132 |
| 3 | `config-loader.js` | 108 |
| 4 | `components/sparkline.js` | 79 |
| 5 | `components/budget-gauge.js` | 89 |
| 6 | `components/progress-bar.js` | 242 |
| 7 | `components/workflow-map.js` | 267 |
| 8 | `components/control-panel.js` | 203 |
| 9 | `components/agent-panel.js` | 233 |
| 10 | `components/impact-view.js` | 286 |
| 11 | `index.js` (재작성) | 54 |
| 12 | `session-start.js` (수정) | ~35 |

### 2.4 Check

**1차 분석: 97%** — 6건 gap 발견

| # | 심각도 | 항목 | 조치 |
|---|:------:|------|------|
| 3 | High | session-start.js raw pdcaStatus → `{ pdcaStatus, feature }` 래핑 | 코드 수정 |
| 2 | Medium | renderImpactView 2-arg → 3-arg | Design 수정 |
| 6 | Low | symbol() → statusSymbol() | Design 수정 |
| 1 | Low | getThreshold/getBarWidth 추가 export | Design 수정 |
| 4 | Low | markdown.keyValue() 미문서화 | Design 수정 |
| 5 | Low | terminal.js 추가 re-export | Design 수정 |

**2차 (수정 후): 100%**

### 2.5 Test

```
=== Progress Bar ===
terminal: ┌─── uart-dma ─── 58% ─┐ ... (ANSI Box + 색상 바)
context:  ### PDCA Progress: uart-dma (58%)\n| Phase | Status |...

=== Sparkline ===
terminal: Match Rate: ▁▃▆▇█  60%→96%  ↑
context:  Match Rate: 60% → 72% → 85% → 91% → 96% (improving)

=== Budget Gauge ===
terminal: Budget  Flash 62%/85% ███████████░░░░░░░  RAM 48%/75% ...
context:  ### MCU Budget\n- Flash: 62%/85% (OK, 23% headroom)

=== Backward Compat ===
renderPdcaProgressBar: function ✓
renderWorkflowMap: function ✓
colorize: function ✓ (ansi.js)
```

---

## 3. Deliverables

### 3.1 New Architecture

```
lib/ui/
├── engines/
│   ├── terminal.js      ← ANSI stderr 렌더링
│   └── markdown.js      ← markdown context 렌더링
├── components/
│   ├── progress-bar.js  ← { terminal(), context() }
│   ├── workflow-map.js
│   ├── control-panel.js
│   ├── agent-panel.js
│   ├── impact-view.js
│   ├── budget-gauge.js  ← MCU 전용 (신규)
│   └── sparkline.js     ← 트렌드 차트 (신규)
├── config-loader.js     ← config 로더
├── ansi.js              ← 기존 유지 (하위 호환)
└── index.js             ← 신규 + 하위 호환 API
```

### 3.2 Dual Output 흐름

```
session-start.js
  ├── component.terminal(data, config) → process.stderr.write() → 터미널
  └── component.context(data, config) → additionalContext → LLM
```

### 3.3 Config 파라미터화

| 이전 (하드코딩) | 이후 (config) |
|----------------|-------------|
| 90%/70% 색상 임계값 | `config.thresholds.matchRate` |
| BAR_WIDTHS {16,20,36,50} | `config.layout.barWidths` |
| SLIDER_WIDTH = 22 | `config.layout.sliderWidth` |
| 컬럼폭 18/12 | `config.layout.agentColumns` |

---

## 4. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Option B (Clean) | engines/ + components/ 분리 | 완전한 관심사 분리, 테스트 용이 |
| 외부 라이브러리 0개 | 순수 Node.js 유지 | 조사 결과 Ink/Blessed 등 hook 모델과 비호환 |
| ansi.js 유지 | 삭제하지 않고 보존 | 하위 호환 + engines/terminal.js가 활용 |
| config-loader 캐싱 | 첫 로드 후 캐시 | hook 타임아웃 5000ms 성능 보장 |
| stderr + additionalContext | 이중 출력 | ANSI는 터미널, markdown은 LLM 최적 |

---

## 5. Research Summary

3개 에이전트 병렬 조사 결과:

| 조사 | 핵심 발견 |
|------|----------|
| UI 툴킷 | Ink/Blessed/Terminal Kit 전부 hook 비호환. cli-table3만 고려 가치 있으나 불필요 |
| UX 패턴 | sparkline(`▁▂▃▅▇`), phase-aware 정보, 요약/상세 토글, Terraform plan 스타일 |
| 코드 분석 | bkit 직접 포팅 (브랜딩만 변경), 하드코딩 다수, 품질 8.5/10 |

---

## 6. Lessons Learned

| 항목 | 교훈 |
|------|------|
| additionalContext ANSI strip | Hook 출력 채널의 실제 동작을 먼저 파악해야 설계 방향이 맞음 |
| Clean 분리 규모 | Option B는 파일 수 2배 이상이지만 테스트/유지보수 이점이 큼 |
| 병렬 에이전트 조사 | 3개 관점(도구/패턴/코드) 동시 조사로 종합적 판단 가능 |
| data 래핑 버그 | 컴포넌트 인터페이스와 호출부의 데이터 형태 불일치는 테스트로 발견 |
