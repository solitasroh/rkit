# mcukit-mcu-domain Design Document

> **Summary**: STM32/NXP K MCU 도메인 모듈, Skills, Agents, Hooks의 상세 기술 설계
>
> **Project**: mcukit
> **Version**: 0.2.0
> **Author**: Rootech
> **Date**: 2026-03-22
> **Status**: Draft
> **Plan Reference**: `docs/01-plan/features/mcukit-mcu-domain.plan.md`

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | MCU 빌드 후 메모리 분석, .ioc 핀/클럭 검증이 수동이며, AI가 STM32 HAL/NXP SDK 패턴을 정확히 모름 |
| **Solution** | 4개 lib/mcu 모듈(파서/검증기) + 6 Skills(도메인 지식) + 3 Agents(역할 분담) + 2 Hooks(자동 트리거) |
| **Function/UX Effect** | `make` → 자동 메모리 대시보드, `.ioc` 저장 → 핀 충돌 경고, 코드 작성 → HAL 패턴 자동 가이드 |
| **Core Value** | 빌드 결과 분석/HW 설정 검증의 100% 자동화 |

---

## 1. Design Goals

| # | 목표 | 측정 |
|---|------|------|
| G1 | .map 파일 파싱 정확도 | Flash/RAM 계산 vs arm-none-eabi-size 오차 < 1% |
| G2 | .ioc 핀 파싱 완전성 | CubeMX 6.x 생성 .ioc 100% 파싱 |
| G3 | 빌드 후 자동 분석 | PostToolUse(Bash) Hook에서 make/cmake 감지 → 자동 실행 |
| G4 | 기존 코어 무침투 | lib/mcu/는 lib/core에만 의존, PDCA 엔진 수정 없음 |

---

## 2. Module Design

### 2.1 lib/mcu/toolchain.js

```javascript
/**
 * @module lib/mcu/toolchain
 * @version 0.2.0
 * @dependencies lib/core/config, lib/core/debug
 */

// ── Exports ──

/**
 * 설치된 ARM 크로스 컴파일러 탐지
 * @returns {{ found: boolean, path: string, version: string, type: 'gcc'|'iar'|'keil' }}
 *
 * 탐색 순서:
 * 1. mcukit.config.json → mcu.toolchain 값 (명시적 경로)
 * 2. 환경변수: $ARM_GCC_PATH, $ARMGCC_DIR
 * 3. PATH에서 arm-none-eabi-gcc 검색 (which/where 실행)
 * 4. 기본 설치 경로:
 *    Windows: C:/ST/STM32CubeIDE/*/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.*/tools/bin/
 *             C:/NXP/MCUXpressoIDE_*/ide/tools/bin/
 *             C:/Program Files (x86)/GNU Arm Embedded Toolchain/*/bin/
 *    Linux:   /usr/bin/arm-none-eabi-gcc
 *             /opt/gcc-arm-none-eabi-*/bin/
 *    macOS:   /usr/local/bin/arm-none-eabi-gcc
 *             /Applications/ARM/bin/
 *
 * 버전 확인: arm-none-eabi-gcc --version 파싱
 */
function detectToolchain() {}

/**
 * 빌드 시스템 탐지
 * @returns {{ type: 'cmake'|'makefile'|'keil'|'iar'|'unknown', configFile: string|null }}
 *
 * 감지 우선순위:
 * 1. CMakeLists.txt → 'cmake' (arm-none-eabi.cmake 툴체인 파일 확인)
 * 2. Makefile → 'makefile' (arm-none-eabi- 접두사 포함 여부)
 * 3. *.uvprojx → 'keil' (Keil uVision 프로젝트)
 * 4. *.ewp → 'iar' (IAR Embedded Workbench 프로젝트)
 */
function detectBuildSystem() {}

/**
 * arm-none-eabi-size 실행하여 ELF 크기 반환
 * @param {string} elfPath
 * @returns {Promise<{ text: number, data: number, bss: number }>}
 */
function runArmSize(elfPath) {}
```

### 2.2 lib/mcu/memory-analyzer.js

```javascript
/**
 * @module lib/mcu/memory-analyzer
 * @version 0.2.0
 * @dependencies lib/core/debug, lib/mcu/build-history, lib/core/config
 */

// ── GCC ARM .map 파일 파서 ──

/**
 * .map 파일에서 메모리 사용량 추출
 * @param {string} mapFilePath
 * @returns {{
 *   flash: { used: number, total: number, percent: number },
 *   ram:   { used: number, total: number, percent: number },
 *   sections: Array<{ name: string, address: number, size: number }>,
 *   symbols: Array<{ name: string, size: number, section: string }>,
 *   topSymbols: Array<{ name: string, size: number }>
 * }}
 *
 * 파싱 전략:
 * 1. "Memory Configuration" 섹션에서 FLASH/RAM origin, length 추출
 *    정규식: /^(\w+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)/gm
 *    예시: "FLASH  0x08000000  0x00100000  xr"
 *          "RAM    0x20000000  0x00020000  xrw"
 *
 * 2. 섹션 크기 추출 (.text, .rodata, .data, .bss)
 *    정규식: /^\.(\w+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)/gm
 *
 * 3. 심볼별 크기 추출
 *    정규식: /^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+)/gm
 *    Top 20 심볼 크기순 정렬
 *
 * Flash = .text size + .rodata size + .data size
 * RAM   = .data size + .bss size
 */
function parseMapFile(mapFilePath) {}

/**
 * arm-none-eabi-size stdout 문자열 파싱
 * @param {string} sizeOutput - "   text    data     bss     dec     hex filename\n  12345   678   234 ..."
 * @returns {{ text: number, data: number, bss: number, total: number }}
 */
function parseSizeOutput(sizeOutput) {}

/**
 * 이전 빌드와 메모리 비교
 * @param {Object} current - parseMapFile 결과
 * @returns {{ flashDelta: number, ramDelta: number, newSymbols: string[], removedSymbols: string[] }}
 */
function compareBuildMemory(current) {}

/**
 * 메모리 예산 검증
 * @param {Object} usage - { flash: { used, total }, ram: { used, total } }
 * @returns {{ passed: boolean, violations: string[] }}
 *
 * 기준: mcukit.config.json → mcu.memoryBudget
 *   flashWarningPercent: 85
 *   ramWarningPercent: 75
 *   stackMarginPercent: 20
 */
function checkMemoryBudget(usage) {}

/**
 * CLI 대시보드용 메모리 리포트 문자열
 * @param {Object} analysis - parseMapFile 결과
 * @param {Object|null} delta - compareBuildMemory 결과
 * @returns {string} ANSI 색상 포함 리포트
 *
 * 출력 형식:
 * ┌─── Build Report ─────────────────────────────────────────────┐
 * │  Target: STM32F407VGT6    Toolchain: arm-none-eabi-gcc 13.2  │
 * │                                                               │
 * │  Flash: ████████████████░░░░  78.3% (800KB / 1024KB)         │
 * │  RAM:   ███████████░░░░░░░░░  56.1% (71.8KB / 128KB)        │
 * │                                                               │
 * │  Δ Flash: +1.2KB (+0.1%)  Δ RAM: -0.3KB (-0.2%)             │
 * │                                                               │
 * │  Top 5 Symbols (Flash):                                       │
 * │    1. USB_CDC_Handler    4,128 bytes                          │
 * │    2. lwip_init          3,856 bytes                          │
 * └───────────────────────────────────────────────────────────────┘
 */
function formatMemoryReport(analysis, delta) {}

/**
 * 빌드 디렉토리에서 .map 파일 자동 탐색
 * @param {string} projectDir
 * @returns {string|null} 가장 최근 .map 파일 경로
 *
 * 탐색 경로: build/, Debug/, Release/, output/, cmake-build-*/
 */
function findMapFile(projectDir) {}

/**
 * 빌드 디렉토리에서 .elf 파일 자동 탐색
 * @param {string} projectDir
 * @returns {string|null}
 */
function findElfFile(projectDir) {}
```

### 2.3 lib/mcu/pin-config.js

```javascript
/**
 * @module lib/mcu/pin-config
 * @version 0.2.0
 * @dependencies lib/core/debug
 */

/**
 * CubeMX .ioc 파일 전체 파싱
 * @param {string} iocFilePath
 * @returns {Map<string, string>} 모든 key=value 쌍
 *
 * .ioc 포맷: Java Properties (flat key=value, # 주석, 섹션 없음)
 */
function parseIocFile(iocFilePath) {}

/**
 * 핀 할당 정보 추출
 * @param {Map<string, string>} iocData - parseIocFile 결과
 * @returns {Array<{
 *   pin: string,        // 'PA9'
 *   signal: string,     // 'USART1_TX'
 *   mode: string,       // 'Asynchronous'
 *   label: string|null, // 'DEBUG_TX'
 *   locked: boolean,    // true
 *   gpio: {             // GPIO 설정 (GPIO 모드일 때)
 *     pull: string|null,   // 'GPIO_PULLUP'
 *     speed: string|null,  // 'GPIO_SPEED_FREQ_HIGH'
 *     output: string|null  // 'GPIO_MODE_OUTPUT_PP'
 *   }|null
 * }>}
 *
 * 키 패턴:
 *   {PIN}.Signal={SIGNAL}     → pin, signal
 *   {PIN}.Mode={MODE}         → mode
 *   {PIN}.GPIO_Label={LABEL}  → label
 *   {PIN}.Locked=true         → locked
 *   {PIN}.GPIO_PuPd={VALUE}   → gpio.pull
 *   {PIN}.GPIO_Speed={VALUE}  → gpio.speed
 *   {PIN}.GPIO_ModeDefaultOutputPP={VALUE} → gpio.output
 *
 * 핀 목록: Mcu.Pin0={PIN}, Mcu.PinsNb={COUNT}
 */
function extractPinAssignments(iocData) {}

/**
 * 핀 충돌 검출
 * @param {Array} pinAssignments - extractPinAssignments 결과
 * @returns {Array<{
 *   pin: string,
 *   conflicts: Array<{ signal: string, source: string }>
 * }>}
 *
 * 충돌 조건:
 * - 동일 핀에 2개 이상 Signal이 할당된 경우
 * - 일반적으로 CubeMX가 방지하지만, 수동 수정 시 발생 가능
 * - AF(Alternate Function) 레벨 충돌도 체크
 */
function detectPinConflicts(pinAssignments) {}

/**
 * MCU 칩 이름 추출
 * @param {Map<string, string>} iocData
 * @returns {string|null} 예: 'STM32F407VGTx'
 *
 * 키: Mcu.UserName
 */
function extractChipName(iocData) {}

/**
 * IP(페리페럴) 목록 추출
 * @param {Map<string, string>} iocData
 * @returns {Array<{name: string, instance: string}>}
 *
 * 키 패턴: Mcu.IP{N}={IP_NAME}
 * 예: Mcu.IP0=USART1, Mcu.IP1=SPI2
 */
function extractPeripheralList(iocData) {}

/**
 * 핀 할당 리포트 포맷
 * @param {Array} assignments
 * @param {Array} conflicts
 * @returns {string}
 */
function formatPinReport(assignments, conflicts) {}
```

### 2.4 lib/mcu/clock-tree.js

```javascript
/**
 * @module lib/mcu/clock-tree
 * @version 0.2.0
 * @dependencies lib/core/debug
 */

/**
 * .ioc 파일에서 클럭 설정 추출
 * @param {Map<string, string>} iocData - parseIocFile 결과
 * @returns {{
 *   hse: { enabled: boolean, frequency: number|null },
 *   hsi: { enabled: boolean, frequency: 16000000 },
 *   pll: { source: string, m: number, n: number, p: number, q: number },
 *   sysclk: { source: string, frequency: number },
 *   ahb: { divider: number, frequency: number },
 *   apb1: { divider: number, frequency: number, maxFrequency: number },
 *   apb2: { divider: number, frequency: number, maxFrequency: number }
 * }}
 *
 * 키 패턴:
 *   RCC.HSEState=RCC_HSE_ON
 *   RCC.PLLSource=RCC_PLLSOURCE_HSE
 *   RCC.PLLM={value}
 *   RCC.PLLN={value}
 *   RCC.PLLP=RCC_PLLP_DIV{value}
 *   RCC.PLLQ={value}
 *   RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK
 *   RCC.AHBCLKDivider=RCC_SYSCLK_DIV{value}
 *   RCC.APB1CLKDivider=RCC_HCLK_DIV{value}
 *   RCC.APB2CLKDivider=RCC_HCLK_DIV{value}
 *
 * SYSCLK 계산 (HSE + PLL):
 *   PLL_VCO = (HSE / PLLM) * PLLN
 *   SYSCLK  = PLL_VCO / PLLP
 *   AHB     = SYSCLK / AHBDiv
 *   APB1    = AHB / APB1Div
 *   APB2    = AHB / APB2Div
 */
function extractClockConfig(iocData) {}

/**
 * APB 클럭이 최대 허용 주파수를 초과하는지 검증
 * @param {Object} clockConfig - extractClockConfig 결과
 * @returns {{ valid: boolean, issues: string[] }}
 *
 * STM32F4 제한:
 *   APB1 max: 42 MHz
 *   APB2 max: 84 MHz
 *   SYSCLK max: 168 MHz (STM32F407)
 */
function validateClockLimits(clockConfig) {}

/**
 * 클럭 트리 리포트 포맷
 * @param {Object} clockConfig
 * @returns {string}
 */
function formatClockReport(clockConfig) {}
```

### 2.5 lib/mcu/index.js

```javascript
/**
 * @mcukit/mcu - MCU Domain Module Entry Point
 * @module lib/mcu
 * @version 0.2.0
 */
module.exports = {
  ...require('./toolchain'),
  ...require('./memory-analyzer'),
  ...require('./pin-config'),
  ...require('./clock-tree'),
  ...require('./build-history'),   // MVP-1에서 구현됨
};
```

---

## 3. Hook Script Design

### 3.1 scripts/mcu-post-build.js

```javascript
/**
 * MCU Post-Build Analysis Hook
 * Trigger: PostToolUse(Bash) - make, cmake --build, ninja 감지
 *
 * 동작 흐름:
 * 1. Bash 명령이 빌드 명령인지 판별 (BUILD_COMMAND_PATTERNS.mcu)
 * 2. exit code = 0 (성공) 확인
 * 3. 프로젝트에서 최신 .map 파일 탐색 (findMapFile)
 * 4. .map 파일 파싱 (parseMapFile)
 * 5. 이전 빌드와 비교 (compareBuildMemory)
 * 6. 메모리 예산 검증 (checkMemoryBudget)
 * 7. build-history에 기록 (addBuildRecord)
 * 8. 리포트 출력 (formatMemoryReport → additionalContext)
 *
 * 입력: { tool_name: "Bash", tool_input: { command: "make -j4" }, tool_output: { exit_code: 0 } }
 * 출력: { additionalContext: "┌─── Build Report ─────..." }
 * 타임아웃: 5초
 */
```

### 3.2 scripts/mcu-pre-flash.js

```javascript
/**
 * MCU Pre-Flash Safety Check Hook
 * Trigger: PreToolUse(Bash) - st-flash, STM32_Programmer_CLI, JLinkExe 감지
 *
 * 동작 흐름:
 * 1. 명령에 flash 도구 패턴이 포함되는지 확인
 * 2. 바이너리 파일 존재 여부 확인
 * 3. 바이너리 크기 vs Flash 총 크기 비교 (초과 시 차단)
 * 4. 올바른 타겟 주소 확인 (STM32: 0x08000000)
 * 5. erase 명령 시 사용자 확인 요구 (outputBlock)
 *
 * 입력: { tool_name: "Bash", tool_input: { command: "st-flash write firmware.bin 0x08000000" } }
 * 출력: outputAllow() 또는 outputBlock("reason")
 * 타임아웃: 3초
 */
```

---

## 4. Agent Design

### 4.1 agents/fw-architect.md

```yaml
---
name: fw-architect
description: |
  펌웨어 아키텍처 설계 전문가. 임베디드 시스템의 소프트웨어 레이어 구조,
  인터럽트 우선순위 맵, 메모리 레이아웃, RTOS 태스크 설계를 수행합니다.
  Triggers: firmware architecture, 펌웨어 아키텍처, FW 설계, レイヤー設計
model: opus
effort: high
maxTurns: 30
permissionMode: acceptEdits
memory: project
context: fork
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task(Explore)
skills: [pdca, mcukit-rules]
imports:
  - ${PLUGIN_ROOT}/refs/stm32/hal-patterns.md
  - ${PLUGIN_ROOT}/templates/mcu-driver-spec.template.md
disallowedTools:
  - "Bash(rm -rf*)"
  - "Bash(st-flash erase*)"
  - "Bash(STM32_Programmer_CLI*-e all*)"
---
```

**역할 범위**:
- FW 레이어 구조 설계 (HAL → Driver → Service → Application)
- 인터럽트 우선순위 맵 설계 (NVIC 그룹/서브 프라이오리티)
- 메모리 레이아웃 설계 (링커 스크립트 섹션 배치)
- RTOS 태스크 분리 기준 및 스택 사이징
- 부팅 시퀀스 설계 (SystemInit → HAL_Init → ClockConfig → Periph_Init → main_loop/RTOS)

### 4.2 agents/hw-interface-expert.md

```yaml
---
name: hw-interface-expert
description: |
  하드웨어 인터페이스 전문가. GPIO, SPI, I2C, UART, CAN, ADC, DMA 등
  MCU 페리페럴 설정 및 드라이버 구현을 담당합니다.
  Triggers: peripheral, GPIO, SPI, I2C, UART, CAN, 페리페럴 설정
model: sonnet
effort: medium
maxTurns: 20
permissionMode: acceptEdits
memory: project
context: fork
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
skills: [pdca, mcukit-rules, stm32-hal, communication]
imports:
  - ${PLUGIN_ROOT}/refs/stm32/hal-patterns.md
  - ${PLUGIN_ROOT}/refs/stm32/peripheral-map.md
---
```

### 4.3 agents/safety-auditor.md

```yaml
---
name: safety-auditor
description: |
  MISRA C / 기능안전 감사자. MISRA C:2012 코딩 표준 준수 여부를 검증하고,
  스택 오버플로 위험, 미초기화 변수, 무한 루프 위험을 분석합니다.
  Triggers: MISRA, safety, 코딩 표준, 안전 검증
model: opus
effort: high
maxTurns: 20
permissionMode: plan
memory: project
context: fork
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Task(Explore)
skills: [pdca, mcukit-rules, misra-c]
imports:
  - ${PLUGIN_ROOT}/refs/misra-c/rules-summary.md
---
```

---

## 5. Skill Design

### 5.1 Skill Frontmatter 공통 구조

모든 MCU Skill은 다음 필드를 포함:

```yaml
domain: mcu                    # 도메인 라우팅용
platforms: [stm32, nxp-k]     # 또는 개별 플랫폼
classification: capability     # workflow | capability
pdca-phase: do                # 주로 사용되는 PDCA 단계
```

### 5.2 Skills 요약

| Skill | 핵심 내용 | 크기 (예상) |
|-------|----------|:-----------:|
| **stm32-hal/** | HAL_Init 시퀀스, HAL_UART/SPI/I2C/TIM 패턴, CubeMX 코드 수정 가이드, LL API 전환 기준 | ~300줄 |
| **nxp-mcuxpresso/** | fsl_* 드라이버 패턴, board.h/pin_mux.h 구조, clock_config.h 설정, SDK Builder 가이드 | ~250줄 |
| **cmake-embedded/** | arm-none-eabi 툴체인 파일, 링커 스크립트 연동, CTest 설정, 멀티타겟 빌드 | ~200줄 |
| **communication/** | UART DMA TX/RX, SPI 풀듀플렉스 패턴, I2C 마스터/슬레이브, CAN 필터/메일박스 | ~350줄 |
| **freertos/** | xTaskCreate 패턴, Queue/Semaphore/Mutex, 스택 사이징 공식, 우선순위 설계 원칙 | ~300줄 |
| **misra-c/** | Required/Advisory/Documented 분류, 자주 위반되는 규칙 Top 20, cppcheck --addon=misra 연동 | ~250줄 |

---

## 6. Template Design

### 6.1 templates/mcu-hw-spec.template.md

```markdown
# {feature} HW Specification

## 1. MCU Selection
| Item | Value |
|------|-------|
| MCU | {chip_name} |
| Core | {core_type} |
| Flash | {flash_size} |
| RAM | {ram_size} |
| Package | {package_type} |

## 2. Pin Assignment Table
| Pin | Signal | Mode | Label | AF |
|-----|--------|------|-------|----|
| {pin} | {signal} | {mode} | {label} | {af_number} |

## 3. Clock Configuration
| Clock | Frequency | Source |
|-------|-----------|--------|
| SYSCLK | {sysclk_freq} | {sysclk_source} |
| AHB | {ahb_freq} | SYSCLK/{ahb_div} |
| APB1 | {apb1_freq} | AHB/{apb1_div} |
| APB2 | {apb2_freq} | AHB/{apb2_div} |

## 4. Peripheral Allocation
| Peripheral | Purpose | Pins | DMA |
|-----------|---------|------|-----|
| {periph} | {purpose} | {pins} | {dma_channel} |

## 5. Power Budget (if applicable)
| Mode | Current | Duration |
|------|---------|----------|
```

### 6.2 templates/mcu-memory-budget.template.md

```markdown
# {feature} Memory Budget

## Target
| Item | Value |
|------|-------|
| MCU | {chip_name} |
| Flash Total | {flash_total} |
| RAM Total | {ram_total} |

## Flash Budget
| Component | Size | Percent | Notes |
|-----------|------|---------|-------|
| Bootloader | {size} | {pct}% | {notes} |
| Application | {size} | {pct}% | |
| OTA Reserve | {size} | {pct}% | |
| Config/NVM | {size} | {pct}% | |
| **Total** | **{total}** | **{pct}%** | |

## RAM Budget
| Component | Size | Percent | Notes |
|-----------|------|---------|-------|
| Stack (main) | {size} | {pct}% | |
| Heap | {size} | {pct}% | |
| RTOS Tasks | {size} | {pct}% | {task_count} tasks |
| Buffers | {size} | {pct}% | DMA, UART, etc. |
| Global/Static | {size} | {pct}% | |
| **Total** | **{total}** | **{pct}%** | |

## Warning Thresholds
- Flash: {flash_warning}% (mcukit.config.json)
- RAM: {ram_warning}%
```

---

## 7. Reference Data Design

### 7.1 refs/stm32/hal-patterns.md

STM32 HAL 코드 패턴 레퍼런스 (~200줄):
- HAL_Init() / SystemClock_Config() 시퀀스
- HAL_UART_Transmit / HAL_UART_Receive / HAL_UART_Transmit_DMA 패턴
- HAL_SPI_TransmitReceive / HAL_SPI_TransmitReceive_DMA
- HAL_I2C_Master_Transmit / HAL_I2C_Mem_Read
- HAL_TIM_PWM_Start / HAL_TIM_Base_Start_IT
- HAL_ADC_Start_DMA
- Callback 패턴 (HAL_UART_TxCpltCallback 등)
- 에러 처리 (HAL_StatusTypeDef 체크)

### 7.2 refs/stm32/peripheral-map.md

주요 STM32 칩별 페리페럴 매핑 (~150줄):
- STM32F407: USART1/2/3/6, SPI1/2/3, I2C1/2/3, TIM1-14, CAN1/2, USB_OTG
- STM32F103: USART1/2/3, SPI1/2, I2C1/2, TIM1-4
- 핀별 AF(Alternate Function) 매핑 요약

### 7.3 refs/nxp-k/sdk-patterns.md

NXP MCUXpresso SDK 패턴 (~150줄):
- BOARD_InitPins() / BOARD_InitBootClocks() 시퀀스
- UART_Init / UART_WriteBlocking / UART_ReadBlocking
- SPI_MasterTransferBlocking
- I2C_MasterTransferBlocking
- fsl_debug_console (PRINTF)

---

## 8. Integration with Existing Modules

### 8.1 router.js 연동

`lib/domain/router.js`의 `routePostToolAnalysis()`가 빌드 감지 시 lib/mcu 모듈을 호출:

```
PostToolUse(Bash) "make -j4"
  → router.routePostToolAnalysis('Bash', input)
  → domain='mcu', type='build-complete'
  → mcu-post-build.js 실행
    → memory-analyzer.findMapFile()
    → memory-analyzer.parseMapFile()
    → memory-analyzer.compareBuildMemory()
    → memory-analyzer.checkMemoryBudget()
    → build-history.addBuildRecord()
    → memory-analyzer.formatMemoryReport()
    → additionalContext에 리포트 출력
```

### 8.2 detector.js 연동

`lib/domain/detector.js`의 `detectPlatform('mcu')`가 .ioc 파일에서 칩 이름 추출:

```
detectPlatform('mcu')
  → pin-config.parseIocFile()
  → pin-config.extractChipName()
  → { platform: 'stm32f4', chip: 'STM32F407VGTx', sdk: 'STM32CubeF4' }
```

---

## 9. Implementation Order

```
Step 1: lib/mcu/pin-config.js (의존성 없음, .ioc 파서)
Step 2: lib/mcu/clock-tree.js (pin-config.js의 parseIocFile 사용)
Step 3: lib/mcu/toolchain.js (의존성 없음, 툴체인 탐지)
Step 4: lib/mcu/memory-analyzer.js (build-history.js 의존)
Step 5: lib/mcu/index.js (전체 re-export)
Step 6: scripts/mcu-post-build.js (memory-analyzer 의존)
Step 7: scripts/mcu-pre-flash.js (toolchain 의존)
Step 8: agents/ 3개 (독립 작성)
Step 9: skills/ 6개 (독립 작성)
Step 10: templates/ 3개 + refs/ 3개 (독립 작성)
```

---

## 10. Test Plan

| # | 테스트 | 입력 | 기대 결과 |
|---|--------|------|-----------|
| T1 | .ioc 핀 파싱 | STM32F407 .ioc 파일 | PA9=USART1_TX 등 정확히 추출 |
| T2 | 핀 충돌 검출 | 동일 핀에 2개 Signal | 충돌 경고 출력 |
| T3 | 클럭 계산 | HSE=8MHz, PLLM=8, PLLN=336, PLLP=2 | SYSCLK=168MHz |
| T4 | .map 파싱 | GCC ARM .map 파일 | Flash/RAM 사용량 ±1% 이내 |
| T5 | 메모리 리포트 | parseMapFile 결과 | 프로그레스바 포함 리포트 |
| T6 | 빌드 후 자동 분석 | `make -j4` 실행 | additionalContext에 리포트 |
| T7 | 플래시 전 검사 | `st-flash erase` | outputBlock 실행 |
| T8 | 툴체인 탐지 | PATH에 arm-none-eabi-gcc | found=true, version 추출 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-22 | 초기 설계: 4 모듈 + 2 Hooks + 3 Agents + 6 Skills + 3 Templates | Rootech |
