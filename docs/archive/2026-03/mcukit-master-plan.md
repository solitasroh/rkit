# mcukit - MCU 개발 지원 Kit 마스터 기획서

## Executive Summary

| 항목 | 내용 |
|------|------|
| **프로젝트명** | mcukit (MCU Development Kit for Claude Code) |
| **목표** | bkit-claude-code의 PDCA 기반 AI 네이티브 개발 방법론을 MCU 임베디드 개발에 특화하여 이식 |
| **타겟 MCU** | STM32 계열, NXP Kinetis (K Series) |
| **기반 분석** | bkit-claude-code v2.0.0 (Apache 2.0, popup-studio-ai) |
| **작성일** | 2026-03-22 |

---

## 1. bkit-claude-code 분석 요약

### 1.1 아키텍처 개요

bkit은 Claude Code CLI 플러그인으로, **Context Engineering** 기법을 통해 AI 에이전트의 개발 행위를 체계적으로 관리합니다.

```
┌─────────────────────────────────────────────────┐
│               bkit Architecture                  │
├─────────────────────────────────────────────────┤
│  Layer 1: Skills (36개)    - 도메인 지식          │
│  Layer 2: Agents (31개)    - 역할 기반 행동 규칙    │
│  Layer 3: Lib (~465 함수)  - PDCA 상태 머신/엔진    │
│  Layer 4: Hooks (18 이벤트) - 라이프사이클 제어      │
│  Layer 5: Templates        - 문서 표준화            │
│  Layer 6: MCP Servers (2개) - 외부 도구 통합        │
└─────────────────────────────────────────────────┘
```

### 1.2 핵심 컴포넌트 매핑

| bkit 컴포넌트 | 역할 | mcukit 대응 방향 |
|---------------|------|------------------|
| PDCA State Machine (20 전이) | 개발 흐름 제어 | **그대로 이식** - MCU 개발에도 Plan→Design→Do→Check→Act 적용 |
| 36 Skills (웹 개발 중심) | 도메인 지식 | **MCU 특화 재작성** - HAL, RTOS, 디바이스 드라이버, 통신 프로토콜 등 |
| 31 Agents (PM/CTO/QA 등) | AI 역할 분담 | **MCU 도메인 재구성** - HW 엔지니어, FW 엔지니어, 테스트 엔지니어 등 |
| 9-Stage Pipeline | 개발 파이프라인 | **MCU 파이프라인 재설계** - BSP→Driver→Middleware→Application |
| 3 Project Levels | 프로젝트 규모 | **MCU 레벨 재정의** - Bare-metal / RTOS / Multi-core |
| Templates | 문서 표준화 | **MCU 문서 템플릿** - HW 스펙, 레지스터 맵, 타이밍 다이어그램 참조 |
| Hooks (18 events) | 이벤트 기반 제어 | **그대로 이식** + 빌드/플래시 훅 추가 |
| Quality Gates | 품질 관리 | **MCU 특화** - MISRA C, 스택 사이즈, 메모리 맵 검증 추가 |

### 1.3 재사용 가능한 코어 모듈 (변경 불필요)

다음 bkit 모듈은 도메인 독립적이므로 거의 그대로 활용 가능합니다:

- `lib/core/` - config, cache, state-store, paths, errors, debug, platform
- `lib/pdca/state-machine.js` - 선언적 상태 전이 테이블
- `lib/pdca/workflow-engine.js` - 워크플로우 실행 엔진
- `lib/pdca/workflow-parser.js` - YAML 워크플로우 DSL 파서
- `lib/audit/` - 감사 로깅, 결정 추적
- `lib/control/` - 자동화 레벨, 체크포인트, 위험 탐지
- `lib/quality/` - 게이트 관리자, 메트릭 수집기
- `lib/ui/` - CLI 대시보드 (progress-bar, workflow-map)
- `hooks/hooks.json` 구조 - 이벤트 기반 훅 시스템

---

## 2. mcukit 설계 방향

### 2.1 핵심 철학

```
bkit의 "AI Native Web Development"
  → mcukit의 "AI Native Embedded Development"

핵심 차이점:
- 웹: 파일 저장 → 즉시 반영 (Hot Reload)
- MCU: 코드 수정 → 빌드 → 플래시 → 실행 → 디버그 (빌드 체인 필수)
```

### 2.2 MCU 개발의 고유 요구사항

| 영역 | 웹 개발 (bkit) | MCU 개발 (mcukit) |
|------|---------------|-------------------|
| **빌드 시스템** | npm/webpack | CMake, Makefile, IAR, Keil, arm-gcc |
| **실행 환경** | 브라우저/Node.js | 실제 MCU 하드웨어 or QEMU |
| **디버깅** | 브라우저 DevTools | J-Link, ST-Link, OpenOCD, GDB |
| **테스트** | Jest, Vitest | Unity (C), CppUTest, QEMU, HIL |
| **메모리 제약** | 사실상 무제한 | Flash/RAM 크기 제한 (KB~MB 단위) |
| **코딩 표준** | ESLint, Prettier | MISRA C, CERT C, BARR-C |
| **의존성** | npm packages | HAL, BSP, RTOS, Middleware 라이브러리 |
| **배포** | Vercel, Docker | OTA 펌웨어 업데이트, 플래싱 |
| **HW 인터페이스** | REST API | GPIO, SPI, I2C, UART, CAN, ADC, DMA |

### 2.3 타겟 MCU 플랫폼 상세

#### STM32 계열
- **SDK**: STM32CubeMX + STM32 HAL/LL
- **빌드**: CMake (STM32CubeIDE) 또는 arm-none-eabi-gcc
- **디버거**: ST-Link V2/V3, OpenOCD
- **RTOS**: FreeRTOS (STM32Cube 내장), ThreadX (Azure RTOS)

#### NXP Kinetis K Series
- **SDK**: MCUXpresso SDK
- **빌드**: CMake (MCUXpresso IDE) 또는 arm-none-eabi-gcc
- **디버거**: J-Link, MCU-Link, OpenOCD
- **RTOS**: FreeRTOS, Zephyr

---

## 3. mcukit 아키텍처 설계

### 3.1 전체 구조

```
mcukit/
├── agents/                    # MCU 특화 AI 에이전트 (15~20개)
│   ├── fw-architect.md        # 펌웨어 아키텍트
│   ├── hw-interface-expert.md # HW 인터페이스 전문가
│   ├── driver-developer.md    # 디바이스 드라이버 개발자
│   ├── rtos-expert.md         # RTOS 전문가
│   ├── memory-optimizer.md    # 메모리 최적화 전문가
│   ├── protocol-expert.md     # 통신 프로토콜 전문가
│   ├── safety-auditor.md      # MISRA/기능안전 감사자
│   ├── test-engineer.md       # 임베디드 테스트 엔지니어
│   ├── build-expert.md        # 빌드 시스템/툴체인 전문가
│   ├── debug-expert.md        # 디버깅/트레이스 전문가
│   ├── power-optimizer.md     # 저전력 최적화 전문가
│   ├── bootloader-expert.md   # 부트로더/OTA 전문가
│   ├── gap-detector.md        # 설계-구현 갭 분석 (bkit 이식)
│   ├── code-analyzer.md       # 코드 품질 분석 (MISRA 특화)
│   ├── report-generator.md    # PDCA 보고서 생성 (bkit 이식)
│   └── cto-lead.md            # 팀 오케스트레이션 (bkit 이식)
│
├── skills/                    # MCU 특화 스킬 (25~30개)
│   ├── pdca/                  # PDCA 관리 (bkit 이식)
│   ├── mcukit-rules/          # 핵심 규칙
│   ├── mcukit-templates/      # 문서 템플릿
│   │
│   ├── # ── Phase Skills (MCU 개발 파이프라인) ──
│   ├── phase-1-hw-spec/       # HW 스펙/핀맵/클럭 설정
│   ├── phase-2-bsp-init/      # BSP 초기화/스타트업 코드
│   ├── phase-3-driver/        # 디바이스 드라이버 개발
│   ├── phase-4-middleware/    # 미들웨어/프로토콜 스택
│   ├── phase-5-rtos/          # RTOS 태스크 설계/구현
│   ├── phase-6-application/   # 애플리케이션 로직
│   ├── phase-7-test/          # 테스트/검증
│   ├── phase-8-optimization/  # 메모리/성능/전력 최적화
│   ├── phase-9-production/    # 양산/OTA/플래싱
│   │
│   ├── # ── Platform Skills ──
│   ├── stm32-hal/             # STM32 HAL 전문 지식
│   ├── stm32-ll/              # STM32 LL (Low-Layer) API
│   ├── stm32-cubemx/          # CubeMX 코드 생성/설정
│   ├── nxp-mcuxpresso/        # NXP MCUXpresso SDK
│   ├── nxp-kinetis/           # NXP Kinetis K Series 전문
│   │
│   ├── # ── Domain Skills ──
│   ├── freertos/              # FreeRTOS 태스크/동기화
│   ├── communication/         # UART/SPI/I2C/CAN/USB
│   ├── misra-c/               # MISRA C:2012 코딩 표준
│   ├── memory-management/     # 링커 스크립트/메모리 맵
│   ├── interrupt-design/      # 인터럽트/DMA 설계
│   ├── bootloader/            # 부트로더/펌웨어 업데이트
│   ├── low-power/             # 저전력 모드 설계
│   ├── cmake-embedded/        # 임베디드 CMake 빌드
│   └── debug-trace/           # 디버깅/SWO 트레이스
│
├── lib/                       # 코어 라이브러리
│   ├── core/                  # bkit에서 이식 (config, state, paths 등)
│   ├── pdca/                  # bkit에서 이식 (state-machine, workflow 등)
│   ├── audit/                 # bkit에서 이식
│   ├── control/               # bkit에서 이식
│   ├── quality/               # bkit에서 이식 + MCU 확장
│   ├── mcu/                   # ★ MCU 고유 모듈 (신규)
│   │   ├── toolchain.js       # 크로스 컴파일러 탐지/설정
│   │   ├── flash.js           # 플래싱 유틸리티 (ST-Link, J-Link)
│   │   ├── debug.js           # 디버거 연결 관리
│   │   ├── memory-analyzer.js # 빌드 결과 메모리 사용량 분석
│   │   ├── register-map.js    # 레지스터 맵 파서/검증
│   │   ├── pin-config.js      # 핀 할당 충돌 검출
│   │   ├── clock-tree.js      # 클럭 트리 설정 검증
│   │   └── linker-analyzer.js # 링커 스크립트/맵 파일 분석
│   ├── intent/                # bkit에서 이식
│   ├── task/                  # bkit에서 이식
│   ├── team/                  # bkit에서 이식
│   └── ui/                    # bkit에서 이식
│
├── hooks/                     # 이벤트 훅 (bkit 구조 이식 + MCU 확장)
│   ├── hooks.json
│   ├── session-start.js
│   └── scripts/
│       ├── pre-build.js       # 빌드 전 검증 (메모리 예산, MISRA 사전검사)
│       ├── post-build.js      # 빌드 후 분석 (맵 파일 파싱, 메모리 리포트)
│       ├── pre-flash.js       # 플래싱 전 안전 검사
│       └── post-flash.js      # 플래싱 후 검증
│
├── templates/                 # MCU 문서 템플릿
│   ├── plan.template.md       # 기획서 (bkit 이식)
│   ├── design.template.md     # 설계서 (MCU 특화 섹션 추가)
│   ├── hw-spec.template.md    # ★ HW 스펙 문서
│   ├── driver-spec.template.md# ★ 드라이버 스펙
│   ├── memory-budget.template.md # ★ 메모리 예산 문서
│   ├── test-plan.template.md  # ★ MCU 테스트 계획
│   └── analysis.template.md   # 갭 분석 (bkit 이식)
│
├── servers/                   # MCP 서버
│   ├── mcukit-pdca-server/    # PDCA 관리 (bkit 이식)
│   └── mcukit-analysis-server/# 분석 도구 (MCU 특화 확장)
│
├── refs/                      # 레퍼런스 데이터
│   ├── stm32/                 # STM32 칩 데이터 (핀맵, 클럭, 페리페럴)
│   ├── nxp-k/                 # NXP K Series 칩 데이터
│   ├── misra-c/               # MISRA C:2012 규칙 레퍼런스
│   └── freertos/              # FreeRTOS API 레퍼런스
│
├── mcukit.config.json         # 설정 파일
└── CLAUDE.md                  # Claude Code 연동 설정
```

### 3.2 MCU 특화 PDCA 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│                    mcukit PDCA Workflow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [PM] → [PLAN] → [DESIGN] → [DO] → [CHECK] → [ACT] → [REPORT] │
│                                                                  │
│  PM:     요구사항 분석, HW 제약 파악                               │
│  PLAN:   MCU 선정, 페리페럴 할당, 메모리 예산                       │
│  DESIGN: 아키텍처, 레이어 구조, 인터럽트 설계, 태스크 설계           │
│  DO:     BSP → Driver → Middleware → App 순서 구현                │
│  CHECK:  빌드 검증, MISRA 준수, 메모리 사용량, 스택 분석            │
│  ACT:    최적화, 리팩토링, 이슈 수정                               │
│  REPORT: 완료 보고서 + 메모리/성능 메트릭                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 MCU 3-Level 프로젝트 분류

| 레벨 | bkit 대응 | 설명 | 특징 |
|------|-----------|------|------|
| **Bare-metal** | Starter | RTOS 없이 폴링/인터럽트 기반 | 단순 제어, 소규모 Flash/RAM |
| **RTOS** | Dynamic | FreeRTOS/Zephyr 기반 멀티태스크 | 태스크 분리, 동기화, 미들웨어 |
| **Multi-core / Safety** | Enterprise | 멀티코어 or 기능안전 등급 | ASIL, 리던던시, 파티셔닝 |

---

## 4. MCU 특화 Quality Gates

### 4.1 빌드 후 자동 검증 항목

```javascript
// mcukit Quality Gate 예시
const MCU_QUALITY_THRESHOLDS = {
  // 메모리 검증
  flashUsagePercent: 85,      // Flash 사용률 상한 (%)
  ramUsagePercent: 75,        // RAM 사용률 상한 (%)
  maxStackDepth: null,        // 칩별 동적 설정

  // 코딩 표준
  misraCViolations: 0,        // MISRA C 필수 규칙 위반 수
  misraAdvisoryMax: 10,       // MISRA C 권고 규칙 위반 상한

  // 성능
  interruptLatencyUs: null,   // 인터럽트 응답 시간 상한 (칩별)
  taskStackMargin: 20,        // 태스크 스택 여유 마진 (%)

  // 코드 품질 (bkit 이식)
  matchRate: 90,              // 설계-구현 일치율
  codeQualityScore: 70,
  conventionCompliance: 90,
};
```

### 4.2 빌드 결과 자동 분석

```
Post-Build Hook이 자동 수행:
1. .map 파일 파싱 → Flash/RAM 사용량 리포트
2. 스택 사용량 정적 분석 (arm-none-eabi-size, puncover)
3. 심볼 크기 Top-N 리스트
4. 이전 빌드 대비 증감 비교
5. 메모리 예산 초과 시 경고
```

---

## 5. 개발 로드맵

### Phase 1: 코어 이식 (1~2주)

**bkit에서 변경 없이 이식할 모듈:**
- [ ] `lib/core/` 전체 (config, state-store, paths, cache, errors, debug, platform)
- [ ] `lib/pdca/state-machine.js` (PDCA 상태 머신)
- [ ] `lib/pdca/workflow-engine.js`, `workflow-parser.js`
- [ ] `lib/pdca/feature-manager.js`, `status.js`, `phase.js`
- [ ] `lib/audit/` 전체
- [ ] `lib/control/` 전체
- [ ] `lib/quality/` 전체
- [ ] `lib/ui/` 전체
- [ ] `lib/intent/`, `lib/task/`, `lib/team/`
- [ ] `hooks/hooks.json` 구조 + `session-start.js`
- [ ] `mcukit.config.json` (bkit.config.json 기반 커스터마이즈)
- [ ] 기본 PDCA 스킬 (`skills/pdca/`)

### Phase 2: MCU 기반 인프라 (2~3주)

**신규 개발:**
- [ ] `lib/mcu/toolchain.js` - arm-none-eabi-gcc, IAR, Keil 탐지
- [ ] `lib/mcu/flash.js` - ST-Link, J-Link, OpenOCD 연동
- [ ] `lib/mcu/memory-analyzer.js` - .map 파일 파서, 메모리 리포트
- [ ] `lib/mcu/linker-analyzer.js` - 링커 스크립트 분석
- [ ] `lib/mcu/pin-config.js` - 핀 멀티플렉싱 충돌 검출
- [ ] `lib/mcu/clock-tree.js` - 클럭 설정 검증
- [ ] `hooks/scripts/post-build.js` - 빌드 후 자동 분석
- [ ] `hooks/scripts/pre-flash.js` - 플래싱 전 안전 검사

### Phase 3: Platform Skills (2~3주)

**STM32 특화:**
- [ ] `skills/stm32-hal/` - HAL API 사용 가이드 + 베스트 프랙티스
- [ ] `skills/stm32-cubemx/` - CubeMX 코드 생성 패턴
- [ ] `skills/stm32-ll/` - LL API 직접 레지스터 접근 가이드

**NXP K Series 특화:**
- [ ] `skills/nxp-mcuxpresso/` - MCUXpresso SDK 가이드
- [ ] `skills/nxp-kinetis/` - K Series 특화 지식

**공통:**
- [ ] `skills/cmake-embedded/` - 임베디드 CMake 빌드 시스템
- [ ] `skills/freertos/` - FreeRTOS 태스크/큐/세마포어 설계
- [ ] `skills/communication/` - UART/SPI/I2C/CAN 드라이버 패턴

### Phase 4: Domain Skills (2~3주)

- [ ] `skills/misra-c/` - MISRA C:2012 규칙 + 자동 검사
- [ ] `skills/interrupt-design/` - 인터럽트 우선순위/네스팅 설계
- [ ] `skills/memory-management/` - 링커 스크립트, 메모리 레이아웃
- [ ] `skills/bootloader/` - 부트로더 + OTA 업데이트 설계
- [ ] `skills/low-power/` - 저전력 모드 (Sleep/Stop/Standby)
- [ ] `skills/debug-trace/` - SWD/SWO/ITM 디버깅

### Phase 5: MCU 에이전트 (1~2주)

- [ ] `agents/fw-architect.md` - 펌웨어 아키텍처 설계
- [ ] `agents/hw-interface-expert.md` - HW 인터페이스 설계
- [ ] `agents/driver-developer.md` - 디바이스 드라이버 구현
- [ ] `agents/rtos-expert.md` - RTOS 태스크 설계/최적화
- [ ] `agents/safety-auditor.md` - MISRA/기능안전 검증
- [ ] `agents/memory-optimizer.md` - 메모리/성능 최적화
- [ ] `agents/build-expert.md` - 빌드 시스템/툴체인 관리

### Phase 6: 템플릿 & 레퍼런스 (1~2주)

- [ ] MCU 특화 Plan/Design/Analysis 템플릿
- [ ] STM32 칩별 레퍼런스 데이터 (핀맵, 클럭)
- [ ] NXP K Series 레퍼런스 데이터
- [ ] MISRA C:2012 규칙 레퍼런스

---

## 6. 핵심 차별화 기능

### 6.1 빌드 결과 자동 대시보드

```
┌─── Build Report ────────────────────────────────────────────┐
│  Target: STM32F407VGT6    Toolchain: arm-none-eabi-gcc 13.2 │
│                                                              │
│  Flash: ████████████████░░░░  78.3% (800KB / 1024KB)        │
│  RAM:   ███████████░░░░░░░░░  56.1% (71.8KB / 128KB)       │
│  Stack: ██████░░░░░░░░░░░░░░  32.4% (used/allocated)       │
│                                                              │
│  MISRA C: 0 Required | 3 Advisory | 12 Documented           │
│  Δ Flash: +1.2KB (+0.1%)  Δ RAM: -0.3KB (-0.2%)            │
│                                                              │
│  Top 5 Symbols (Flash):                                      │
│    1. USB_CDC_Handler    4,128 bytes                         │
│    2. lwip_init          3,856 bytes                         │
│    3. HAL_TIM_IRQHandler 2,944 bytes                         │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 핀 충돌 자동 검출

```
⚠️  Pin Conflict Detected!
  PA9 is assigned to both:
    - USART1_TX (communication skill)
    - TIM1_CH2  (motor control)

  Suggestion: Move TIM1_CH2 to PE11 (AF1, available)
```

### 6.3 메모리 예산 관리

PDCA Plan 단계에서 메모리 예산을 설정하고, Check 단계에서 자동 검증:

```yaml
# memory-budget.yaml
target:
  chip: STM32F407VGT6
  flash_total: 1048576  # 1MB
  ram_total: 131072     # 128KB

budget:
  bootloader:
    flash: 65536       # 64KB
    ram: 8192          # 8KB
  application:
    flash: 786432      # 768KB
    ram: 98304         # 96KB
  reserve:
    flash: 196608      # 192KB (OTA용)
    ram: 24576         # 24KB (여유)
```

---

## 7. 기술적 리스크 및 대응

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| Claude Code가 MCU 레지스터 수준 코드를 정확히 생성하지 못할 수 있음 | 높음 | refs/ 에 칩별 레지스터 맵 데이터 사전 적재, Skills에 HAL/LL 패턴 코드 포함 |
| 크로스 컴파일 환경이 사용자마다 다름 | 중간 | toolchain.js에서 자동 탐지 + 수동 설정 fallback |
| 실제 HW 없이 테스트 어려움 | 중간 | QEMU 기반 에뮬레이션 + Unit Test (Host PC) 이중 전략 |
| MISRA C 분석 도구 라이선스 문제 | 낮음 | cppcheck --addon=misra (오픈소스) 기본 지원, 상용 도구는 선택적 연동 |
| bkit 업데이트 시 코어 모듈 동기화 | 중간 | bkit core를 git subtree로 관리, 업데이트 시 merge |

---

## 8. 우선순위 및 MVP 정의

### MVP (Minimum Viable Product)

**목표**: STM32 Bare-metal 프로젝트를 PDCA 사이클로 개발할 수 있는 최소 kit

1. PDCA 코어 이식 (state-machine, workflow, hooks)
2. STM32 HAL 스킬 1개
3. CMake 빌드 스킬 1개
4. post-build 메모리 분석 훅
5. fw-architect 에이전트 1개
6. MCU Plan/Design 템플릿
7. gap-detector 에이전트 (bkit 이식)

**MVP 예상 규모**: ~15 파일, ~3,000 LOC

---

## 9. 참고 자료

- **bkit 원본**: https://github.com/popup-studio-ai/bkit-claude-code (Apache 2.0)
- **STM32 HAL**: STM32Cube MCU Packages
- **NXP MCUXpresso SDK**: MCUXpresso SDK Builder
- **MISRA C:2012**: Guidelines for the use of the C language in critical systems
- **FreeRTOS**: https://www.freertos.org/
- **Claude Code Plugin API**: Skills 2.0, Hooks, Agents specification
