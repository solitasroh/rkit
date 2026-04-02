# ui-enhancement Design Document

> **Summary**: Option B (Clean) — TerminalRenderer/ContextRenderer 분리 + config-loader + 도메인 컴포넌트
>
> **Project**: mcukit
> **Version**: 0.7.0
> **Author**: soojang.roh
> **Date**: 2026-04-03
> **Status**: Draft
> **Planning Doc**: [ui-enhancement.plan.md](../01-plan/features/ui-enhancement.plan.md)

---

## 1. Architecture Overview

### 1.1 현재 구조 → 목표 구조

**현재 (단일 렌더러):**
```
lib/ui/
├── ansi.js              ← ANSI + Box Drawing (단일 모드)
├── progress-bar.js      ← ANSI 전용 렌더링
├── workflow-map.js      ← ANSI 전용 렌더링
├── control-panel.js     ← ANSI 전용 렌더링
├── agent-panel.js       ← ANSI 전용 렌더링
├── impact-view.js       ← ANSI 전용 렌더링
└── index.js             ← export hub
```

**목표 (Dual Renderer — Clean 분리):**
```
lib/ui/
├── engines/
│   ├── terminal.js      ← ANSI + Box Drawing 렌더링 엔진 (stderr용)
│   └── markdown.js      ← Markdown/plain text 렌더링 엔진 (context용)
├── components/
│   ├── progress-bar.js  ← { terminal(), context() } 두 메서드
│   ├── workflow-map.js  ← { terminal(), context() }
│   ├── control-panel.js ← { terminal(), context() }
│   ├── agent-panel.js   ← { terminal(), context() }
│   ├── impact-view.js   ← { terminal(), context() }
│   ├── budget-gauge.js  ← MCU Flash/RAM 게이지 (신규)
│   └── sparkline.js     ← 트렌드 차트 (신규)
├── config-loader.js     ← mcukit.config.json ui 섹션 로더
├── ansi.js              ← 기존 유지 (하위 호환, engines/terminal.js가 활용)
└── index.js             ← 신규 API + 하위 호환 API
```

### 1.2 Dual Output 데이터 흐름

```
Hook 실행 (session-start.js)
  │
  ├── components/*.terminal(data, config)
  │   → ANSI 색상 문자열 조합
  │   → process.stderr.write()         ← 사용자 터미널에 직접 표시
  │
  └── components/*.context(data, config)
      → markdown 문자열 조합
      → JSON.additionalContext          ← LLM 컨텍스트로 주입
```

### 1.3 컴포넌트 인터페이스 규약

모든 컴포넌트는 동일한 인터페이스를 따른다:

```javascript
// 컴포넌트 인터페이스
module.exports = {
  // 터미널용 (ANSI + Box Drawing) → stderr
  terminal(data, config) → string,
  
  // LLM 컨텍스트용 (markdown) → additionalContext
  context(data, config) → string,
  
  // 하위 호환 (기존 renderXxx API)
  renderXxx(pdcaStatus, agentState, opts) → string
};
```

---

## 2. Engines

### 2.1 `engines/terminal.js`

기존 ansi.js의 렌더링 함수를 엔진으로 재구성. ANSI escape + Unicode Box Drawing.

**API:**

```javascript
const T = require('./engines/terminal');

T.colorize(text, color)          // ANSI 색상 적용
T.bold(text)                     // 굵게
T.dim(text)                      // 흐리게
T.box(title, lines, width)       // ┌─ title ─┐ Box 렌더링
T.progressBar(percent, width)    // ████████░░░░ 바
T.hline(width)                   // ──────────── 수평선
T.statusSymbol(status)           // ✓ ▶ · ✗ 등
T.isColorDisabled()              // NO_COLOR 체크
T.getTermWidth()                 // 터미널 폭
T.getWidthBreakpoint()           // narrow/normal/wide/ultrawide
T.stripAnsi(str)                 // ANSI strip
T.boxLine(content, width)        // 박스 라인
T.truncate(text, maxLen)         // 말줄임
T.BOX                            // Box Drawing 상수
T.SYMBOLS                        // 상태 심볼 상수
T.COLORS                         // 색상 상수
```

**내부**: 기존 ansi.js 상수(COLORS, STYLES, BOX, SYMBOLS) + 함수를 그대로 활용.

### 2.2 `engines/markdown.js`

LLM 컨텍스트용 plain text/markdown 렌더링 엔진. ANSI 없음.

**API:**

```javascript
const M = require('./engines/markdown');

M.table(headers, rows)           // | H1 | H2 |\n|---|---| 마크다운 테이블
M.heading(level, text)           // ## text
M.list(items)                    // - item1\n- item2
M.bold(text)                     // **text**
M.status(phase, state)           // "Plan: Done" (plain text)
M.progressText(percent)          // "67% (2/3)"
M.sparkline(values)              // "▁▂▃▅▇ 60%→96%"
M.separator()                    // ---
M.keyValue(kvPairs)              // key-value → bullet list
```

---

## 3. Components

### 3.1 `components/progress-bar.js`

**terminal()** 출력:
```
┌─── pdca ── uart-dma ── 58% ──────────────────┐
│  PM✓  PLAN✓  DESIGN▶  DO·  CHECK·  REPORT·   │
│  ████████████████░░░░░░░░░░░░  58%            │
└─ design • last: 3h ago • iter: 2 ────────────┘
```

**context()** 출력:
```markdown
## PDCA: uart-dma (58%)
| Phase | Status |
|-------|--------|
| PM | Done |
| Plan | Done |
| Design | In Progress |
| Do | Pending |
| Check | Pending |
| Report | Pending |

Phase: design, Last: 3h ago, Iterations: 2
```

### 3.2 `components/workflow-map.js`

**terminal()**: 기존 ANSI Box Drawing 흐름도 (화살표, 분기, 팀 로스터)

**context()** 출력:
```markdown
## Workflow: uart-dma
PM(Done) → Plan(Done) → Design(Active) → Do → Check → Report
- Check: ≥90% → Report, <90% → Act
- Iteration: 2, Match Rate: 75%
```

### 3.3 `components/control-panel.js`

**terminal()**: ANSI 슬라이더 + 승인 목록

**context()** 출력:
```markdown
## Control
- Automation: L2 Semi-Auto
- Pending Approvals: 0
```

### 3.4 `components/agent-panel.js`

**terminal()**: ANSI 팀 로스터 Box

**context()** 출력:
```markdown
## Agent Team (parallel)
| Agent | Status | Task |
|-------|--------|------|
| Developer | Working | implement logic |
| Frontend | Idle | — |
| QA | Pending | — |
```

### 3.5 `components/impact-view.js`

**terminal()**: ANSI Match Rate 바 + 파일 트리 + sparkline

**context()** 출력:
```markdown
## Impact
- Match Rate: 85%
- Trend: 60% → 72% → 85% (improving)
- Changed: 3 files (+142, -28)
```

### 3.6 `components/budget-gauge.js` (신규)

MCU Flash/RAM 예산 게이지. MCU 도메인에서만 표시.

**terminal()** 출력:
```
  Budget  Flash 62%/85% ████████████░░░░░░  RAM 48%/75% █████████░░░░░░░░░░
```

**context()** 출력:
```markdown
## MCU Budget
- Flash: 62%/85% (OK, 23% headroom)
- RAM: 48%/75% (OK, 27% headroom)
```

**데이터 소스**: `arm-none-eabi-size` 출력 또는 .map 파일 파싱 (가능한 경우)

### 3.7 `components/sparkline.js` (신규)

Unicode block elements를 사용한 트렌드 차트.

**API:**
```javascript
const { sparkline } = require('./components/sparkline');

sparkline.terminal([60, 72, 85, 91, 96])
// → "▁▂▅▇█  60%→96%  trend: ↑"

sparkline.context([60, 72, 85, 91, 96])
// → "Trend: 60% → 72% → 85% → 91% → 96% (improving)"
```

**블록 문자**: `▁▂▃▄▅▆▇█` (8 levels, U+2581~U+2588)

---

## 4. Config Loader

### 4.1 `config-loader.js`

mcukit.config.json의 `ui` 섹션을 로드하고 기본값과 병합.

```javascript
const { loadUiConfig } = require('./config-loader');
const config = loadUiConfig(); // 파일 없으면 기본값 반환

// config.thresholds.matchRate.good → 90
// config.layout.barWidths.normal → 20
// config.display.compactMode → 'auto'
```

**기본값 (파일 없을 때):**
```javascript
const DEFAULTS = {
  thresholds: {
    matchRate: { good: 90, warn: 70 },
    flash: { warn: 85 },
    ram: { warn: 75 }
  },
  layout: {
    barWidths: { narrow: 16, normal: 20, wide: 36, ultrawide: 50 },
    agentColumns: { name: 18, status: 12 },
    sliderWidth: 22,
    maxTreeFiles: 10,
    maxTreeDepth: 3
  },
  display: {
    compactMode: 'auto',
    showShortcuts: true,
    maxRecentMessages: 5
  }
};
```

---

## 5. Session Start Hook 수정

### 5.1 `hooks/session-start.js` 변경

```javascript
// 기존: ANSI → additionalContext
// 변경: terminal → stderr, context → additionalContext

const components = require('../lib/ui');
const { loadUiConfig } = require('../lib/ui/config-loader');
const config = loadUiConfig();
pdcaStatus = getPdcaStatusFull();
const data = { pdcaStatus, feature: pdcaStatus.primaryFeature };

// Terminal 출력 (stderr → 사용자 직접 봄)
const terminalOutput = [
  components.progressBar.terminal(data, config),
  components.workflowMap.terminal(data, config),
  components.controlPanel.terminal(data, config),
].filter(Boolean).join('\n');

if (terminalOutput) {
  process.stderr.write(terminalOutput + '\n');
}

// Context 출력 (additionalContext → LLM)
const contextOutput = [
  components.progressBar.context(data, config),
  components.workflowMap.context(data, config),
  components.controlPanel.context(data, config),
].filter(Boolean).join('\n\n');

// additionalContext에 markdown 주입
additionalContext = contextOutput + '\n\n' + additionalContext;
```

---

## 6. 하위 호환

기존 `renderPdcaProgressBar(pdcaStatus, opts)` 등 API를 유지:

```javascript
// index.js — 하위 호환 API
module.exports = {
  // 신규 API (권장)
  progressBar: require('./components/progress-bar'),
  workflowMap: require('./components/workflow-map'),
  controlPanel: require('./components/control-panel'),
  agentPanel: require('./components/agent-panel'),
  impactView: require('./components/impact-view'),
  budgetGauge: require('./components/budget-gauge'),
  sparkline: require('./components/sparkline'),
  
  // 엔진
  terminal: require('./engines/terminal'),
  markdown: require('./engines/markdown'),
  
  // Config
  loadUiConfig: require('./config-loader').loadUiConfig,
  getThreshold: require('./config-loader').getThreshold,
  getBarWidth: require('./config-loader').getBarWidth,
  
  // 하위 호환 (기존 API — 내부적으로 terminal() 호출)
  renderPdcaProgressBar: (s, o) => require('./components/progress-bar').terminal(s, o),
  renderWorkflowMap:     (s, a, o) => require('./components/workflow-map').terminal(s, o),
  renderControlPanel:    (s, a, o) => require('./components/control-panel').terminal(s, o),
  renderAgentPanel:      (s, a, o) => require('./components/agent-panel').terminal(s, o),
  renderImpactView:      (s, g, o) => require('./components/impact-view').renderImpactView(s, g, o),
  
  // ANSI utilities (하위 호환)
  ...require('./ansi'),
};
```

---

## 7. Implementation Order

| Step | File | 의존 | 설명 |
|:----:|------|:----:|------|
| 1 | `lib/ui/engines/terminal.js` | ansi.js | ANSI 렌더링 엔진 |
| 2 | `lib/ui/engines/markdown.js` | — | Markdown 렌더링 엔진 |
| 3 | `lib/ui/config-loader.js` | — | UI config 로더 |
| 4 | `lib/ui/components/sparkline.js` | Step 1,2 | 트렌드 차트 |
| 5 | `lib/ui/components/budget-gauge.js` | Step 1,2,3 | MCU 예산 게이지 |
| 6 | `lib/ui/components/progress-bar.js` | Step 1,2,3 | dual render 리팩토링 |
| 7 | `lib/ui/components/workflow-map.js` | Step 1,2,3 | dual render 리팩토링 |
| 8 | `lib/ui/components/control-panel.js` | Step 1,2,3 | dual render 리팩토링 |
| 9 | `lib/ui/components/agent-panel.js` | Step 1,2,3 | dual render 리팩토링 |
| 10 | `lib/ui/components/impact-view.js` | Step 1,2,3,4 | dual render + sparkline |
| 11 | `lib/ui/index.js` | Step 1-10 | 신규 + 하위 호환 API |
| 12 | `hooks/session-start.js` | Step 11 | stderr/context 분리 |

---

## 8. 케이스별 검증 시나리오

| Case | 시나리오 | 기대 결과 |
|:----:|---------|----------|
| T1 | SessionStart (터미널) | stderr에 ANSI 색상 대시보드 표시 |
| T2 | SessionStart (context) | additionalContext에 markdown (ANSI 없음) |
| T3 | NO_COLOR=1 환경 | stderr에 plain text (색상 없음), context 동일 |
| T4 | config 임계값 변경 (80%) | 80% 이상이면 green 표시 |
| T5 | MCU 프로젝트 | budget-gauge 표시 |
| T6 | sparkline 데이터 [60,72,85,91,96] | `▁▂▅▇█ 60%→96%` |
| T7 | 기존 API renderPdcaProgressBar() | 정상 동작 (하위 호환) |
| T8 | config 파일 없음 | 기본값으로 동작 |
| T9 | primaryFeature 없음 | 대시보드 미표시, 에러 없음 |
