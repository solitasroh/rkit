# ui-enhancement Planning Document

> **Summary**: lib/ui Dual Output 분리 + 하드코딩 제거 + 도메인 특화 UI 컴포넌트 추가
>
> **Project**: mcukit
> **Version**: 0.7.0
> **Author**: soojang.roh
> **Date**: 2026-04-03
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | ANSI 색상 코드가 additionalContext에서 stripped되어 LLM 컨텍스트에서 무의미한 바이트 낭비. 임계값/컬럼폭 하드코딩. MCU/MPU/WPF 도메인 특화 UI 없음 |
| **Solution** | Dual Output 분리(stderr=ANSI 터미널, additionalContext=markdown), config 기반 파라미터화, 도메인별 예산 게이지/sparkline/MR 상태 컴포넌트 추가 |
| **Function/UX Effect** | 사용자는 터미널에서 색상 있는 대시보드를 보고, LLM은 깔끔한 markdown 컨텍스트를 받아 정확한 상황 인식 |
| **Core Value** | Hook 출력의 두 채널(터미널 시각화 + LLM 컨텍스트)을 각각 최적화하여 개발자 경험과 AI 정확도를 동시에 향상 |

---

## 1. Overview

### 1.1 Purpose

mcukit lib/ui 모듈을 세 방향으로 개선한다:
1. **Dual Output**: ANSI 터미널 표시(stderr)와 LLM 컨텍스트(additionalContext)를 분리
2. **Config 연동**: 하드코딩된 임계값/폭/단축키를 mcukit.config.json에서 로드
3. **도메인 UI**: MCU Flash/RAM 게이지, sparkline 트렌드, MR 상태 표시 추가

### 1.2 Background

- 3개 에이전트 병렬 조사 결과:
  - **UI 툴킷**: Ink/Blessed/Terminal Kit 모두 hook 모델과 비호환. 외부 라이브러리 추가 불필요
  - **UX 패턴**: sparkline(`▁▂▃▅▇`), phase-aware 정보, 요약/상세 토글 패턴 적용 가능
  - **현재 코드**: bkit 직접 포팅 (브랜딩 변경만), 하드코딩 다수, 도메인 특화 없음
- 핵심 발견: `additionalContext`에서 ANSI가 stripped됨 → 현재 ANSI 코드가 바이트만 낭비

### 1.3 현재 lib/ui 구조 (1,376 LOC, 7 모듈)

| 모듈 | LOC | 역할 | 문제점 |
|------|:---:|------|--------|
| ansi.js | 264 | ANSI escape + Unicode Box | ANSI가 context에서 무의미 |
| progress-bar.js | 228 | PDCA 진행률 | BAR_WIDTHS 하드코딩 |
| workflow-map.js | 234 | PDCA 흐름도 | 90% 임계값 하드코딩 |
| control-panel.js | 183 | 자동화 슬라이더 | SLIDER_WIDTH 22 고정, SHORTCUTS 하드코딩 |
| agent-panel.js | 184 | CTO Team 상태 | 컬럼폭 18/12/38 매직넘버 |
| impact-view.js | 263 | Match Rate + 파일 트리 | 90%/70% 임계값 하드코딩 |
| index.js | 20 | export hub | — |

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Priority | Requirement | Description |
|----|:--------:|-------------|-------------|
| FR-01 | P0 | Dual Output 엔진 | ansi.js에 `renderForTerminal()` + `renderForContext()` 두 모드 추가 |
| FR-02 | P0 | stderr 터미널 출력 | SessionStart hook에서 ANSI 대시보드를 stderr로 출력 |
| FR-03 | P0 | markdown context 출력 | additionalContext에 ANSI 없는 markdown/plain text 출력 |
| FR-04 | P1 | Config 파라미터화 | 임계값, 바 폭, 컬럼폭, 단축키를 mcukit.config.json ui 섹션에서 로드 |
| FR-05 | P1 | MCU 예산 게이지 | Flash/RAM 사용량 인라인 바 (`Flash 62%/85% ████████████░░░░`) |
| FR-06 | P1 | Sparkline 트렌드 | Match Rate 추이 (`▁▂▃▅▇ 60%→85%`) |
| FR-07 | P2 | MR 상태 컴포넌트 | `!42 ✓✓●○ feat: ... CI:●` 형식의 MR 요약 |
| FR-08 | P2 | Phase-aware 정보 | 현재 PDCA 단계에 따라 다른 정보 표시 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-01 | 외부 의존성 0 | 현재와 동일하게 순수 Node.js (chalk/ink 등 추가 금지) |
| NFR-02 | 하위 호환 | 기존 API (renderProgressBar 등) 시그니처 유지 |
| NFR-03 | NO_COLOR 준수 | 기존 NO_COLOR/ANSI_DISABLED 지원 유지 |
| NFR-04 | 성능 | hook 타임아웃 5000ms 내 렌더링 완료 |

---

## 3. Dual Output 설계 (핵심)

### 3.1 현재 문제

```
Hook stdout → JSON { additionalContext: "┌─── \x1b[32m✓\x1b[0m ───┐" }
  → Claude Code가 ANSI strip → LLM은 "┌─── ✓ ───┐" 만 봄
  → ANSI 바이트 낭비 + Box Drawing이 LLM 토큰 소모
```

### 3.2 개선 구조

```
Hook 실행
  ├── stderr → ANSI 터미널 표시 (사용자가 직접 봄)
  │   ┌─── mcukit ── uart-dma ── [MCU/STM32F4] ──────
  │   │ ✓ Plan  ✓ Design  ● Do  ○ Check  ○ Act
  │   │ Budget  Flash 62%/85% ████████████░░░░
  │   └─────────────────────────────────────────────
  │
  └── stdout → JSON { additionalContext: markdown }
      ```
      ## PDCA Status: uart-dma [MCU/STM32F4]
      | Phase | Status |
      |-------|--------|
      | Plan | Done |
      | Design | Done |
      | Do | In Progress (2/3) |
      | Check | Pending |
      
      Flash: 62%/85%, RAM: 48%/75%
      Next: /pdca analyze uart-dma
      ```
```

### 3.3 ansi.js 확장

```javascript
// 기존 API 유지
module.exports.colorize = colorize;
module.exports.bold = bold;
module.exports.boxLine = boxLine;

// 신규: 렌더링 모드
module.exports.setRenderMode = setRenderMode; // 'terminal' | 'context'
module.exports.getRenderMode = getRenderMode;

// 신규: context 모드 헬퍼
module.exports.markdownTable = markdownTable;  // 2D array → markdown table
module.exports.markdownList = markdownList;    // items → bullet list
module.exports.markdownHeading = markdownHeading; // level + text → ## text
```

### 3.4 각 컴포넌트의 dual render

| 컴포넌트 | Terminal (stderr) | Context (additionalContext) |
|----------|-------------------|---------------------------|
| progress-bar | ANSI 색상 + Box Drawing + Unicode bar | markdown table + plain text |
| workflow-map | ANSI 색상 + 화살표 + 분기 | markdown phase list |
| control-panel | ANSI 슬라이더 + Box | markdown level + approvals |
| agent-panel | ANSI 로스터 + Box | markdown team status |
| impact-view | ANSI 트리 + 색상 bar | markdown file list + rate |

---

## 4. Config 파라미터화

### 4.1 mcukit.config.json ui 섹션 (신규)

```json
{
  "ui": {
    "thresholds": {
      "matchRate": { "good": 90, "warn": 70 },
      "flash": { "warn": 85 },
      "ram": { "warn": 75 }
    },
    "layout": {
      "barWidths": { "narrow": 16, "normal": 20, "wide": 36, "ultrawide": 50 },
      "agentColumns": { "name": 18, "status": 12 },
      "maxTreeFiles": 10,
      "maxTreeDepth": 3,
      "sliderWidth": 22
    },
    "display": {
      "compactMode": "auto",
      "showShortcuts": true,
      "maxRecentMessages": 5
    }
  }
}
```

### 4.2 하드코딩 제거 대상

| 현재 하드코딩 | 위치 | config 경로 |
|-------------|------|------------|
| 90% (green), 70% (yellow) | impact-view.js:49, workflow-map.js | `ui.thresholds.matchRate` |
| BAR_WIDTHS {16,20,36,50} | progress-bar.js:43 | `ui.layout.barWidths` |
| SLIDER_WIDTH = 22 | control-panel.js:37 | `ui.layout.sliderWidth` |
| 컬럼폭 18, 12, 38 | agent-panel.js:123 | `ui.layout.agentColumns` |
| SHORTCUTS [7개] | control-panel.js:39 | `ui.display.showShortcuts` |
| maxFiles=10, depth=3 | impact-view.js | `ui.layout.maxTreeFiles/Depth` |

---

## 5. 도메인 특화 UI 컴포넌트

### 5.1 MCU 예산 게이지 (신규 컴포넌트)

```
Budget  Flash 62%/85% ████████████░░░░░░  RAM 48%/75% █████████░░░░░░░░░░
        ↑ green (< 85%)                    ↑ green (< 75%)
```

- `arm-none-eabi-size` 출력이 있으면 자동 파싱
- 임계값 초과 시 yellow/red 색상
- context 모드: `Flash: 62%/85% (OK), RAM: 48%/75% (OK)`

### 5.2 Sparkline 트렌드 (신규 헬퍼)

```
Match Rate: ▁▂▃▅▇  60% → 72% → 85% → 91% → 96%  trend: ↑
```

- Unicode block elements `▁▂▃▄▅▆▇█` (8 levels)
- PDCA iteration history에서 데이터 추출
- context 모드: `Match Rate trend: 60% → 72% → 85% → 91% → 96% (improving)`

### 5.3 MR 상태 컴포넌트 (신규)

```
Open MRs (2)
 !42  ✓✓●○  [OP#123] feat: SPI driver    SR  2h ago  CI:●
 !39  ✓✓✓   [OP#456] fix: UART buffer    SR  1d ago  CI:✓  → ready
```

- glab CLI로 MR 데이터 조회 (`/mr status`와 연동)
- 리뷰어 승인 상태를 이니셜로 표시
- context 모드: markdown table

### 5.4 Phase-Aware 정보 표시

현재 PDCA 단계에 따라 가장 관련 있는 정보를 표시:

| Phase | 표시 내용 |
|-------|----------|
| Plan/Design | 요구사항 요약, 설계 옵션 |
| Do | MCU: Flash/RAM 예산, 빌드 상태 |
| Check | Match Rate, gap 요약, sparkline |
| Report 이후 | MR 상태, OP 태스크 상태 |

---

## 6. Scope

### 6.1 Modified Files (7개 — 기존 lib/ui 전체)

| File | 변경 내용 |
|------|----------|
| `lib/ui/ansi.js` | dual mode 엔진 + markdown 헬퍼 추가 |
| `lib/ui/progress-bar.js` | dual render + config 연동 |
| `lib/ui/workflow-map.js` | dual render + config 연동 |
| `lib/ui/control-panel.js` | dual render + config 연동 + 동적 슬라이더 |
| `lib/ui/agent-panel.js` | dual render + config 연동 + 동적 컬럼폭 |
| `lib/ui/impact-view.js` | dual render + config 연동 + sparkline |
| `lib/ui/index.js` | 신규 export 추가 |

### 6.2 New Files (2개)

| File | 역할 |
|------|------|
| `lib/ui/budget-gauge.js` | MCU Flash/RAM 예산 게이지 컴포넌트 |
| `lib/ui/sparkline.js` | sparkline 트렌드 차트 헬퍼 |

### 6.3 Modified Files (기타)

| File | 변경 내용 |
|------|----------|
| `hooks/session-start.js` | stderr 출력 + context markdown 분리 |

### 6.4 Out of Scope

| Item | Reason |
|------|--------|
| 외부 UI 라이브러리 추가 | 조사 결과 불필요 확인 |
| 인터랙티브 TUI | hook 모델과 비호환 |
| MR 상태 컴포넌트 실제 glab 연동 | `/mr status` skill에서 처리 |
| Nerd Font 아이콘 | 호환성 리스크 |

---

## 7. Success Criteria

| Criteria | Priority |
|----------|:--------:|
| stderr에 ANSI 색상 대시보드 표시 | P0 |
| additionalContext에 ANSI 없는 markdown 출력 | P0 |
| 기존 API 시그니처 하위 호환 | P0 |
| config에서 임계값/폭 로드 | P1 |
| MCU 프로젝트에서 Flash/RAM 게이지 표시 | P1 |
| sparkline 트렌드 표시 | P1 |
| NO_COLOR 환경에서 정상 동작 | P0 |
| hook 타임아웃 5000ms 이내 | P0 |
