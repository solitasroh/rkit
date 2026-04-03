# mcukit-core Design Document

> **Summary**: bkit PDCA 코어 이식 + 3-Domain(MCU/MPU/WPF) 라우팅 시스템의 기술 설계
>
> **Project**: mcukit
> **Version**: 0.1.0
> **Author**: Rootech
> **Date**: 2026-03-22
> **Status**: Draft
> **Plan Reference**: `docs/01-plan/features/mcukit-core.plan.md` v0.3

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | bkit v2.0.0의 ~465 함수/76 모듈/18 Hook을 MCU/MPU/WPF 도메인에 맞게 이식하려면 변경 범위를 정밀하게 정의해야 함 |
| **Solution** | 5개 계층(Core/PDCA/Domain/Hooks/Skills)으로 분리하여, Domain 계층만 신규 개발하고 나머지는 이름 변경 수준으로 이식 |
| **Function/UX Effect** | `/pdca plan` 실행 시 도메인이 자동 감지되어 MCU/MPU/WPF 각각에 적합한 템플릿, 에이전트, 검증 로직이 활성화 |
| **Core Value** | 이식 공수 최소화(코어 80% 재사용) + 도메인 특화 가치 극대화(20% 신규 개발에 집중) |

---

## 1. Design Goals & Principles

### 1.1 설계 목표

| # | 목표 | 측정 기준 |
|---|------|-----------|
| G1 | bkit 코어 최대 재사용 | 변경률 < 20% (lib/core, lib/pdca) |
| G2 | 도메인 분리 | 도메인 코드가 코어에 침투하지 않음 |
| G3 | 확장 용이성 | 새 MCU 플랫폼 추가 시 Skill 1개 + refs 데이터만 추가 |
| G4 | 점진적 구현 | Phase별 독립 동작 가능 (MVP-1 → MVP-2 → MVP-3) |
| G5 | 안전성 | MCU/MPU 위험 명령(flash erase, dd) 자동 차단 |

### 1.2 설계 원칙

1. **Thin Adaptation Layer**: bkit 코어는 이름 변경 + 최소 수정만. 로직 변경 금지.
2. **Domain as Plugin**: 도메인 모듈(lib/mcu, lib/mpu, lib/wpf)은 코어에 의존하되, 코어는 도메인에 의존하지 않음.
3. **Domain Router Pattern**: `lib/domain/router.js`가 감지된 도메인에 따라 스킬/에이전트/훅을 분기.
4. **Lazy Loading**: 감지된 도메인의 모듈만 로드하여 startup 시간 5초 이내 유지.
5. **Fail-Safe Porting**: bkit 모듈 로드 실패 시 graceful fallback (기존 bkit 패턴 유지).

---

## 2. Architecture

### 2.1 5-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layer 5: Skills & Agents                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ pdca/    │ │ stm32-   │ │ imx-bsp/ │ │ wpf-     │  ... (30개)   │
│  │ mcukit-  │ │ hal/     │ │ yocto-   │ │ mvvm/    │               │
│  │ rules/   │ │ misra-c/ │ │ build/   │ │ xaml/    │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│                         Layer 4: Hooks & Scripts                     │
│  hooks.json → session-start.js → unified-*.js → domain-*.js        │
├─────────────────────────────────────────────────────────────────────┤
│                         Layer 3: Domain (★ 신규)                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ lib/domain/  │ │ lib/mcu/     │ │ lib/mpu/     │                │
│  │  detector.js │ │  toolchain   │ │  device-tree │                │
│  │  router.js   │ │  flash       │ │  yocto       │                │
│  │  cross.js    │ │  memory-     │ │  kernel-cfg  │                │
│  │              │ │  analyzer    │ │  cross-      │                │
│  │              │ │  pin-config  │ │  compile     │                │
│  │              │ │  clock-tree  │ │              │                │
│  │              │ └──────────────┘ └──────────────┘                │
│  │              │ ┌──────────────┐                                  │
│  │              │ │ lib/wpf/     │                                  │
│  │              │ │  xaml-       │                                  │
│  │              │ │  analyzer    │                                  │
│  │              │ │  mvvm-       │                                  │
│  │              │ │  validator   │                                  │
│  └──────────────┘ └──────────────┘                                  │
├─────────────────────────────────────────────────────────────────────┤
│                         Layer 2: PDCA Engine (bkit 이식)              │
│  state-machine │ workflow-engine │ feature-manager │ automation      │
│  status │ phase │ level │ tier │ lifecycle │ batch-orchestrator      │
├─────────────────────────────────────────────────────────────────────┤
│                         Layer 1: Core Infrastructure (bkit 이식)      │
│  platform │ config │ paths │ state-store │ cache │ errors            │
│  constants │ debug │ io │ file │ hook-io                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ audit/ │ control/ │ quality/ │ intent/ │ task/ │ team/ │ ui/ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 의존성 규칙 (Dependency Rules)

```
Layer 5 (Skills/Agents) → Layer 4, 3, 2, 1 (모두 참조 가능)
Layer 4 (Hooks)         → Layer 3, 2, 1
Layer 3 (Domain)        → Layer 2, 1 (★ Layer 3 내 도메인 간 참조 금지)
Layer 2 (PDCA)          → Layer 1
Layer 1 (Core)          → 외부 의존성 없음 (Node.js 내장 모듈만)
```

**금지 규칙**:
- Layer 1, 2는 Layer 3을 직접 require 하지 않음
- lib/mcu/는 lib/mpu/를 require 하지 않음 (cross-domain은 lib/domain/cross.js 경유)
- lib/domain/detector.js는 코어에 의존하되 도메인 모듈에는 의존하지 않음

### 2.3 Component Diagram

```
┌─ SessionStart Flow ─────────────────────────────────────────────┐
│                                                                  │
│  session-start.js                                                │
│       │                                                          │
│       ├─ migration.js ──→ paths.js (.mcukit/ 경로)               │
│       ├─ restore.js   ──→ state-store.js (백업 복원)              │
│       ├─ context-init.js → config.js (mcukit.config.json 로드)   │
│       ├─ domain-detect.js → detector.js (★ 도메인 감지)          │
│       │      │                                                   │
│       │      ├─ MCU 감지 → .ioc, .ld, startup_*.s, stm32*.h 발견  │
│       │      ├─ MPU 감지 → .dts, bblayers.conf, *.bb 발견        │
│       │      └─ WPF 감지 → .csproj+<UseWPF>true 발견             │
│       │                                                          │
│       ├─ onboarding.js ──→ 도메인별 트리거 테이블 생성             │
│       ├─ session-context.js → additionalContext 빌드             │
│       ├─ progress-bar ──→ PDCA 진행률                            │
│       ├─ workflow-map ──→ 단계 시각화                             │
│       ├─ control-panel ──→ 자동화 레벨                            │
│       └─ stale-detect ──→ 오래된 Feature 경고                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌─ PDCA Workflow ─────────────────────────────────────────────────┐
│                                                                  │
│  /pdca plan {feature}                                            │
│       │                                                          │
│       ├─ skill-orchestrator.js → SKILL.md frontmatter 파싱       │
│       ├─ import-resolver.js → 도메인별 템플릿 로드               │
│       ├─ router.js → 도메인에 맞는 Plan 템플릿 선택              │
│       │      │                                                   │
│       │      ├─ MCU → mcu-hw-spec + memory-budget 섹션 포함      │
│       │      ├─ MPU → mpu-bsp-spec + dts-spec 섹션 포함          │
│       │      └─ WPF → wpf-mvvm-spec + ui-spec 섹션 포함          │
│       │                                                          │
│       ├─ state-machine.js → IDLE→PLAN 전이                       │
│       ├─ status.js → pdca-status.json 업데이트                   │
│       └─ audit-logger.js → 감사 기록                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Design

### 3.1 lib/domain/ — Domain Detection & Routing (★ 신규 핵심)

#### 3.1.1 detector.js — 도메인 자동 감지

```javascript
/**
 * @module lib/domain/detector
 * @description 프로젝트 디렉토리의 마커 파일을 분석하여 도메인(MCU/MPU/WPF)과 레벨을 감지
 * @dependencies lib/core/config, lib/core/cache, lib/core/debug
 */

// ── Exports ──

/**
 * 프로젝트 도메인 감지
 * @returns {{ domain: 'mcu'|'mpu'|'wpf'|'unknown', confidence: number, markers: string[] }}
 */
function detectDomain() {}

/**
 * 도메인 내 레벨 감지
 * @param {'mcu'|'mpu'|'wpf'} domain
 * @returns {{ level: 'L1_Basic'|'L2_Standard'|'L3_Advanced', markers: string[] }}
 */
function detectDomainLevel(domain) {}

/**
 * 도메인 내 세부 플랫폼 감지
 * @param {'mcu'|'mpu'|'wpf'} domain
 * @returns {{ platform: string, sdk: string }}
 * @example { platform: 'stm32f4', sdk: 'STM32CubeF4' }
 * @example { platform: 'imx6ull', sdk: 'yocto-kirkstone' }
 * @example { platform: 'wpf-net8', sdk: '.NET 8.0' }
 */
function detectPlatform(domain) {}

/**
 * 캐시된 도메인 결과 반환 (SessionStart 이후)
 * @returns {{ domain, level, platform, sdk }}
 */
function getCachedDomainInfo() {}
```

**감지 알고리즘**:

```
1. mcukit.config.json의 domain.override 확인 → 있으면 즉시 반환
2. 프로젝트 루트에서 마커 파일 스캔 (glob 패턴, maxDepth: 3)
3. 매치된 마커 수 기반 confidence 점수 계산
   - MCU 마커: *.ioc, *.ld, startup_*.s, stm32*.h, fsl_*.h,
               fsl_device_registers.h, board.h, FreeRTOSConfig.h
     (주의: sdk_config.h는 Nordic nRF 전용 → MCU 마커에서 제외)
   - MPU 마커: *.dts, *.dtsi, bblayers.conf, *.bb, *.bbappend,
               imx*.dtsi, local.conf (build/conf/ 하위)
   - WPF 마커: *.csproj 내부에 <UseWPF>true</UseWPF> 포함 (파싱 필요),
               App.xaml (강력 힌트, 필수 아님), *.sln
     (주의: MainWindow.xaml은 기본 템플릿명일 뿐 → 감지 기준에서 제외)
     (주의: .csproj 존재만으로는 WPF 판별 불가 → UseWPF 태그 확인 필수)
4. 최고 confidence 도메인 반환 (동점 시 파일 수가 많은 쪽)
5. 결과를 cache에 저장 (TTL: 세션 동안 유지)
```

**복수 도메인 프로젝트 대응**:
```
프로젝트에 .ioc와 .csproj가 동시 존재 시:
→ MCU+WPF Cross-Domain으로 감지
→ primaryDomain: 더 많은 소스 파일이 있는 쪽
→ secondaryDomain: 나머지
→ cross-domain skills 활성화 (serial-bridge 등)
```

#### 3.1.2 router.js — 도메인별 라우팅

```javascript
/**
 * @module lib/domain/router
 * @description 감지된 도메인에 따라 적절한 스킬, 에이전트, 템플릿, 검증 로직을 라우팅
 * @dependencies lib/domain/detector, lib/core/config
 */

// ── Exports ──

/**
 * 도메인에 맞는 PDCA 템플릿 경로 반환
 * @param {string} phase - 'plan' | 'design' | 'analysis' | 'report'
 * @returns {string[]} 사용할 템플릿 파일 경로 배열 (공통 + 도메인 특화)
 */
function getTemplatesForPhase(phase) {}

/**
 * 도메인에 맞는 Quality Gate thresholds 반환
 * @returns {Object} 도메인별 + 공통 threshold 병합 객체
 */
function getQualityThresholds() {}

/**
 * 도메인에 맞는 destructive 명령 패턴 반환
 * @returns {Array<{pattern: string, reason: string}>}
 */
function getDestructivePatterns() {}

/**
 * 도메인에 맞는 Phase 파이프라인 반환
 * @returns {Object} phase별 도메인 특화 가이드
 */
function getPipelineGuide() {}

/**
 * PostToolUse에서 도메인별 분석 로직 호출
 * @param {string} toolName - 'Write' | 'Bash'
 * @param {Object} input - Hook 입력
 * @returns {Object|null} 분석 결과 (없으면 null)
 */
function routePostToolAnalysis(toolName, input) {}
```

#### 3.1.3 cross.js — Cross-Domain 연동

```javascript
/**
 * @module lib/domain/cross
 * @description MCU↔WPF 등 도메인 간 연동 유틸리티
 * @dependencies lib/domain/detector
 */

/**
 * 시리얼 통신 프로토콜 일관성 검증
 * MCU 측 UART 프로토콜 정의와 WPF 측 SerialPort 설정 비교
 * @param {string} mcuProtocolFile - MCU 프로토콜 정의 파일 경로
 * @param {string} wpfSerialFile - WPF SerialPort 설정 파일 경로
 * @returns {{ matched: boolean, mismatches: string[] }}
 */
function validateSerialProtocol(mcuProtocolFile, wpfSerialFile) {}

/**
 * Cross-domain 갭 분석 항목 생성
 * @returns {Array<{source: string, target: string, item: string, status: string}>}
 */
function generateCrossDomainGapItems() {}
```

### 3.2 lib/mcu/ — MCU Domain Module (★ 신규)

#### 3.2.1 toolchain.js

```javascript
/**
 * @module lib/mcu/toolchain
 * @description ARM 크로스 컴파일러 자동 탐지 및 설정
 */

/**
 * 설치된 크로스 컴파일러 탐지
 * @returns {{ found: boolean, path: string, version: string, type: 'gcc'|'iar'|'keil' }}
 *
 * 탐색 순서:
 * 1. mcukit.config.json의 mcu.toolchain 값
 * 2. PATH에서 arm-none-eabi-gcc 검색
 * 3. 기본 설치 경로 탐색:
 *    - Windows: C:/ST/STM32CubeIDE/*, C:/NXP/MCUXpressoIDE/*
 *    - Linux: /usr/bin/, /opt/gcc-arm-none-eabi-*
 */
function detectToolchain() {}

/**
 * 빌드 시스템 탐지 (CMake / Makefile / IDE)
 * @returns {{ type: 'cmake'|'makefile'|'keil'|'iar', configFile: string }}
 */
function detectBuildSystem() {}
```

#### 3.2.2 memory-analyzer.js

```javascript
/**
 * @module lib/mcu/memory-analyzer
 * @description 빌드 결과 .map 파일 파싱 및 메모리 사용량 분석
 */

/**
 * .map 파일에서 메모리 사용량 추출
 * @param {string} mapFilePath
 * @returns {{
 *   flash: { used: number, total: number, percent: number },
 *   ram:   { used: number, total: number, percent: number },
 *   symbols: Array<{ name: string, size: number, section: string }>,
 *   topSymbols: Array<{ name: string, size: number }>
 * }}
 */
function parseMapFile(mapFilePath) {}

/**
 * arm-none-eabi-size 출력 파싱
 * @param {string} elfFilePath
 * @returns {{ text: number, data: number, bss: number, total: number }}
 */
function parseElfSize(elfFilePath) {}

/**
 * 이전 빌드와 메모리 사용량 비교
 * @param {Object} current - 현재 빌드 분석 결과
 * @param {Object} previous - 이전 빌드 분석 결과 (.mcukit/state/build-history.json)
 * @returns {{ flashDelta: number, ramDelta: number, newSymbols: string[], removedSymbols: string[] }}
 */
function compareBuildMemory(current, previous) {}

/**
 * 메모리 예산 대비 검증
 * @param {Object} usage - 현재 사용량
 * @param {Object} budget - 메모리 예산 (mcukit.config.json 또는 memory-budget.yaml)
 * @returns {{ passed: boolean, violations: string[] }}
 */
function checkMemoryBudget(usage, budget) {}

/**
 * CLI 대시보드용 메모리 리포트 문자열 생성
 * @param {Object} analysis - 분석 결과
 * @returns {string} ANSI 색상 포함 리포트
 */
function formatMemoryReport(analysis) {}
```

#### 3.2.3 pin-config.js

```javascript
/**
 * @module lib/mcu/pin-config
 * @description 핀 멀티플렉싱 충돌 검출
 */

/**
 * CubeMX .ioc 파일에서 핀 할당 파싱
 * @param {string} iocFilePath
 * @returns {Map<string, {pin: string, function: string, mode: string}>}
 *
 * ★ .ioc 파일 포맷 (검증 완료):
 *   Java Properties 형식 (flat key=value 텍스트), XML/INI 아님
 *   핀 설정 키 패턴:
 *     PA9.Signal=USART1_TX
 *     PA9.Mode=Asynchronous
 *     PA9.GPIO_Label=MY_PIN
 *     PA9.GPIO_PuPd=GPIO_PULLUP
 *     PA9.Locked=true
 *   MCU/핀 목록:
 *     Mcu.Pin0=PA9
 *     Mcu.PinsNb=XX
 *   IP 설정:
 *     Mcu.IP0=USART1
 *     USART1.BaudRate=115200
 */
function parseIocPinConfig(iocFilePath) {}

/**
 * 핀 충돌 검출
 * @param {Map} pinAssignments
 * @returns {Array<{pin: string, conflicts: Array<{function: string, source: string}>}>}
 */
function detectPinConflicts(pinAssignments) {}
```

#### 3.2.4 clock-tree.js

```javascript
/**
 * @module lib/mcu/clock-tree
 * @description 클럭 트리 설정 검증
 */

/**
 * CubeMX .ioc 파일에서 클럭 설정 파싱
 * @param {string} iocFilePath
 * @returns {{ hse: number, pll: Object, sysclk: number, ahb: number, apb1: number, apb2: number }}
 *
 * ★ .ioc 클럭 키 패턴 (검증 완료):
 *   RCC.HSEState=RCC_HSE_ON
 *   RCC.PLLSource=RCC_PLLSOURCE_HSE
 *   RCC.PLLM=8, RCC.PLLN=336, RCC.PLLP=RCC_PLLP_DIV2
 *   RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK
 *   RCC.AHBCLKDivider=RCC_SYSCLK_DIV1
 *   RCC.APB1CLKDivider=RCC_HCLK_DIV4
 *   RCC.APB2CLKDivider=RCC_HCLK_DIV2
 */
function parseClockConfig(iocFilePath) {}

/**
 * 페리페럴의 클럭 요구사항과 실제 설정 비교
 * @param {Object} clockConfig
 * @param {Array<{peripheral: string, requiredClock: number}>} requirements
 * @returns {{ valid: boolean, issues: string[] }}
 */
function validateClockRequirements(clockConfig, requirements) {}
```

### 3.3 lib/mpu/ — MPU Domain Module (★ 신규)

#### 3.3.1 device-tree.js

```javascript
/**
 * @module lib/mpu/device-tree
 * @description Device Tree Source 파싱 및 검증
 */

/**
 * DTS/DTSI 파일 구문 검증 (dtc 호출)
 * @param {string} dtsFilePath
 * @returns {{ valid: boolean, errors: string[], warnings: string[] }}
 *
 * ★ 검증 도구 (검증 완료):
 *   1차: dtc -I dts -O dtb -o /dev/null -W no-unit_address_vs_reg {file}
 *   2차: dt-validate (devicetree schema 기반, 최신 커널 권장)
 *        또는 make dtbs_check (커널 빌드 시스템 내)
 *
 * ★ i.MX DTS 파일명 규칙 (검증 완료):
 *   i.MX6Q:   imx6q.dtsi, imx6qdl.dtsi(공통), imx6q-sabresd.dts
 *   i.MX6DL:  imx6dl.dtsi, imx6dl-sabresd.dts
 *   i.MX6ULL: imx6ull.dtsi, imx6ul.dtsi(UL/ULL공통), imx6ull-14x14-evk.dts
 *   i.MX28:   imx28.dtsi, imx28-evk.dts (mainline 3.7+ DT 지원)
 *
 * ★ 커널 내 경로:
 *   커널 <6.5: arch/arm/boot/dts/imx6*.dts*
 *   커널 6.5+: arch/arm/boot/dts/nxp/imx/imx6*.dts*
 *              arch/arm/boot/dts/nxp/mxs/imx28*.dts* (i.MX28)
 */
function validateDeviceTree(dtsFilePath) {}

/**
 * DTS 파일에서 노드 트리 파싱
 * @param {string} dtsFilePath
 * @returns {Object} 노드 트리 (재귀 구조)
 */
function parseDtsNodes(dtsFilePath) {}

/**
 * 핀멀티플렉싱(pinctrl) 노드 충돌 검사
 * @param {Object} nodeTree
 * @returns {Array<{pad: string, conflicts: string[]}>}
 */
function checkPinctrlConflicts(nodeTree) {}
```

#### 3.3.2 yocto-analyzer.js

```javascript
/**
 * @module lib/mpu/yocto-analyzer
 * @description Yocto 빌드 환경 분석
 */

/**
 * local.conf 파싱
 * @param {string} confPath - build/conf/local.conf (빌드 디렉토리 기준 conf/)
 * @returns {{ machine: string, distro: string, imageFeatures: string[] }}
 *
 * ★ MACHINE 이름 (검증 완료):
 *   i.MX6Q:   imx6qsabresd
 *   i.MX6DL:  imx6dlsabresd
 *   i.MX6ULL: imx6ullevk 또는 imx6ull14x14evk
 *   i.MX28:   최신 Yocto 공식 지원 종료 → Buildroot 권장
 */
function parseLocalConf(confPath) {}

/**
 * bblayers.conf에서 레이어 목록 추출
 * @param {string} confPath - build/conf/bblayers.conf
 * @returns {string[]} 레이어 경로 배열
 *
 * ★ NXP 레이어 구분 (검증 완료):
 *   meta-freescale: 커뮤니티 오픈소스 레이어
 *   meta-imx:       NXP 공식 BSP (프로프라이어터리 GPU/VPU 드라이버 포함)
 *   → 프로젝트에 따라 둘 중 하나 또는 둘 다 사용
 */
function parseBbLayers(confPath) {}

/**
 * 이미지 빌드 결과 크기 분석
 * @param {string} deployDir - tmp/deploy/images/ 경로
 * @returns {{ rootfs: number, kernel: number, dtb: number, uboot: number }}
 *
 * ★ 이미지 이름 (검증 완료):
 *   최신 BSP: imx-image-full, imx-image-multimedia
 *   구 BSP:   fsl-image-gui (레거시, 최신에서 변경됨)
 *   공통:     core-image-minimal, core-image-base
 */
function analyzeImageSize(deployDir) {}
```

#### 3.3.3 cross-compile.js

```javascript
/**
 * @module lib/mpu/cross-compile
 * @description 크로스 컴파일 환경 탐지
 */

/**
 * 크로스 컴파일러 탐지
 * @returns {{ found: boolean, path: string, arch: string, sysroot: string, floatAbi: string }}
 *
 * ★ 플랫폼별 툴체인 분기 (검증 완료):
 *   - i.MX6 (Cortex-A9, ARMv7-A):  arm-linux-gnueabihf-gcc (hard float)
 *   - i.MX6ULL (Cortex-A7, ARMv7-A): arm-linux-gnueabihf-gcc (hard float)
 *   - i.MX28 (ARM926EJ-S, ARMv5TEJ): arm-linux-gnueabi-gcc (soft float)
 *     ⚠️ i.MX28은 VFP/NEON 미탑재 → hard float 바이너리 실행 불가
 *
 * 탐색 순서:
 *   1. Yocto SDK 환경변수 ($CC, $CROSS_COMPILE)
 *   2. PATH에서 arm-linux-gnueabi*-gcc 검색
 *   3. 기본 경로: /opt/poky/*, /opt/fsl-imx-*/*, /opt/imx-*/*
 */
function detectCrossCompiler() {}
```

### 3.4 lib/wpf/ — WPF Domain Module (★ 신규)

#### 3.4.1 xaml-analyzer.js

```javascript
/**
 * @module lib/wpf/xaml-analyzer
 * @description XAML 바인딩 및 리소스 정적 분석
 */

/**
 * XAML 파일에서 바인딩 경로 추출
 * @param {string} xamlFilePath
 * @returns {Array<{path: string, mode: string, type: string, line: number}>}
 *
 * ★ WPF 바인딩 패턴 (검증 완료):
 *   - {Binding Path=PropertyName}           — 표준 바인딩
 *   - {Binding PropertyName}                — Path 생략 (기본 파라미터)
 *   - {Binding Path=..., Mode=TwoWay}       — 모드 지정
 *   - {Binding ElementName=..., Path=...}   — 다른 엘리먼트 참조
 *   - {Binding RelativeSource=...}          — 상대 소스
 *   - {TemplateBinding PropertyName}        — ControlTemplate 내부
 *   - MultiBinding + IMultiValueConverter   — 복합 바인딩
 *
 * ⚠️ {x:Bind}는 UWP/WinUI 전용 → WPF에서 사용 불가, 감지 대상 제외
 *
 * Markup Extension (바인딩과 별도 분류):
 *   - {StaticResource ResourceKey}          — 정적 리소스 참조
 *   - {DynamicResource ResourceKey}         — 동적 리소스 참조
 *
 * ⚠️ 바인딩 에러는 런타임에만 감지 가능 (컴파일 타임 불가)
 *    Output Window 패턴: "System.Windows.Data Error: 40"
 */
function extractBindings(xamlFilePath) {}

/**
 * ViewModel 속성과 바인딩 경로 비교
 * @param {Array} bindings - extractBindings 결과
 * @param {string} viewModelPath - ViewModel .cs 파일 경로
 * @returns {{ matched: string[], unmatched: string[], extra: string[] }}
 *
 * ★ Source Generator 주의 (검증 완료):
 *   CommunityToolkit.Mvvm의 [ObservableProperty]는 private 필드에 적용되어
 *   프로퍼티를 자동 생성하므로, 소스 파일에 프로퍼티가 직접 보이지 않을 수 있음.
 *   → [ObservableProperty] 어트리뷰트가 붙은 필드명을 PascalCase로 변환하여 매칭 필요
 */
function validateBindings(bindings, viewModelPath) {}

/**
 * StaticResource/DynamicResource 참조 검증 (Markup Extension)
 * @param {string} xamlFilePath
 * @param {string[]} resourceDictPaths - ResourceDictionary 파일 경로들 (Resources/, Themes/, Styles/)
 * @returns {{ valid: boolean, missingResources: string[] }}
 */
function validateResources(xamlFilePath, resourceDictPaths) {}
```

#### 3.4.2 mvvm-validator.js

```javascript
/**
 * @module lib/wpf/mvvm-validator
 * @description MVVM 패턴 준수 검증
 */

/**
 * ViewModel이 MVVM 패턴을 따르는지 검증
 * @param {string} viewModelPath
 * @returns {{ score: number, issues: string[] }}
 *
 * 검증 항목:
 * - ObservableObject/INotifyPropertyChanged 상속
 *   (★ [ObservableProperty] Source Generator도 고려 → 필드에 적용됨)
 * - RelayCommand/AsyncRelayCommand/ICommand 사용
 *   (★ [RelayCommand] 어트리뷰트로 메서드에서 자동 생성도 고려)
 * - View 직접 참조 없음:
 *   System.Windows.Controls, System.Windows.Media 등 사용 시 경고
 *   (System.Windows.Input.ICommand은 예외 → ViewModel에서 허용)
 * - 생성자 DI 패턴
 *
 * ★ MVVM 프레임워크 우선순위 (검증 완료):
 *   1. CommunityToolkit.Mvvm (무료, 권장)
 *   2. Prism (⚠️ v9.0+부터 상용 라이선스, 신규 프로젝트 주의)
 *   3. 직접 INotifyPropertyChanged 구현 (소규모 프로젝트)
 */
function validateViewModel(viewModelPath) {}

/**
 * .csproj 의존성 분석
 * @param {string} csprojPath
 * @returns {{ framework: string, isWpf: boolean, packages: Array<{name: string, version: string}>, warnings: string[] }}
 *
 * ★ WPF 감지 방법 (검증 완료):
 *   .NET 8 (SDK-style): <Project Sdk="Microsoft.NET.Sdk"> + <UseWPF>true</UseWPF>
 *     (Microsoft.NET.Sdk.WindowsDesktop는 .NET 5 이하 레거시)
 *     TargetFramework에 -windows 접미사 필수 (net8.0-windows)
 *   .NET Framework: PresentationFramework 어셈블리 참조 또는 ProjectTypeGuids
 *
 * ★ SerialPort 확인 (검증 완료):
 *   .NET 8에서는 System.IO.Ports NuGet 패키지 설치 필요 (기본 미포함)
 *   .NET Framework에서는 BCL에 기본 포함
 */
function analyzeCsproj(csprojPath) {}
```

### 3.5 lib/core/ 이식 변경 상세

변경이 필요한 코어 모듈만 나열합니다 (나머지는 이름 치환만):

#### 3.5.1 platform.js 변경

```javascript
// 변경 사항:
// 1. BKIT_PLATFORM → MCUKIT_PLATFORM
// 2. PLUGIN_ROOT 환경변수명 유지 (Claude Code 플러그인 표준)
// 3. isClaudeCode() 유지

const MCUKIT_PLATFORM = 'claude-code';  // 변경
```

#### 3.5.2 file.js 변경 (TIER_EXTENSIONS)

```javascript
// bkit 원본: 웹 중심 Tier
// mcukit: 임베디드/데스크톱 Tier

const TIER_EXTENSIONS = {
  1: ['.c', '.h', '.cpp', '.hpp', '.cs'],
  2: ['.dts', '.dtsi', '.bb', '.bbappend', '.xaml', '.csproj'],
  3: ['.ld', '.s', '.S', '.icf', '.sln', '.resx'],
  4: ['.sh', '.bash', '.ps1', '.bat', '.cmd', '.cfg'],
};

// 도메인 특화 확장자 (file.js 또는 별도 상수)
const DOMAIN_EXTENSIONS = {
  mcu: ['.ioc', '.ld', '.s', '.S', '.cfg', '.map'],
  mpu: ['.dts', '.dtsi', '.bb', '.bbappend', '.conf', '.its'],
  wpf: ['.xaml', '.csproj', '.sln', '.resx', '.settings'],
};

const DEFAULT_EXCLUDE_PATTERNS = [
  '.git', 'build', 'output', 'bin', 'obj',
  'tmp', 'deploy', 'sysroots', 'node_modules',
  '__pycache__', '.cache', 'Debug', 'Release',
];

const DEFAULT_FEATURE_PATTERNS = [
  'drivers', 'peripherals', 'hal', 'modules',
  'kernel', 'recipes', 'layers',
  'ViewModels', 'Views', 'Services', 'Models',
];
```

#### 3.5.3 constants.js 추가 상수

```javascript
// 기존 bkit 상수 유지 + MCU/MPU/WPF 추가

// 도메인 타입
const DOMAINS = { MCU: 'mcu', MPU: 'mpu', WPF: 'wpf', UNKNOWN: 'unknown' };

// 프로젝트 레벨 (bkit: Starter/Dynamic/Enterprise → mcukit: L1/L2/L3)
const LEVELS = {
  L1_BASIC: 'L1_Basic',
  L2_STANDARD: 'L2_Standard',
  L3_ADVANCED: 'L3_Advanced',
};

// MCU 메모리 기본값
const MCU_DEFAULTS = {
  FLASH_WARNING_PERCENT: 85,
  RAM_WARNING_PERCENT: 75,
  STACK_MARGIN_PERCENT: 20,
};

// 빌드 명령 패턴 (PostToolUse에서 빌드 감지용)
const BUILD_COMMAND_PATTERNS = {
  mcu: ['make', 'cmake --build', 'ninja', 'arm-none-eabi-gcc'],
  mpu: ['bitbake', 'make', 'buildroot'],
  wpf: ['dotnet build', 'msbuild', 'dotnet publish'],
};

// 플래시/위험 명령 패턴
const FLASH_COMMAND_PATTERNS = [
  'st-flash', 'STM32_Programmer', 'JLinkExe', 'openocd',
  'dd if=', 'flashcp', 'nandwrite',
];
```

### 3.6 lib/pdca/level.js 재작성

```javascript
/**
 * @module lib/pdca/level
 * @description 프로젝트 레벨 감지 (bkit의 Starter/Dynamic/Enterprise → mcukit의 L1/L2/L3)
 * @changed 전면 재작성 (bkit 웹 마커 → mcukit 임베디드/데스크톱 마커)
 */

const LEVEL_PHASE_MAP = {
  L1_Basic: {
    required: ['plan', 'do', 'check'],
    optional: ['design'],
    skip: [],
  },
  L2_Standard: {
    required: ['plan', 'design', 'do', 'check', 'report'],
    optional: [],
    skip: [],
  },
  L3_Advanced: {
    required: ['plan', 'design', 'do', 'check', 'act', 'report'],
    optional: [],
    skip: [],
  },
};

/**
 * 프로젝트 레벨 감지
 * @returns {'L1_Basic'|'L2_Standard'|'L3_Advanced'}
 *
 * domain/detector.js의 결과에 기반하여 레벨 결정
 */
function detectLevel() {
  const { domain, level } = require('../domain/detector').getCachedDomainInfo();
  return level || 'L1_Basic';
}
```

---

## 4. Data Model

### 4.1 상태 파일 구조 (.mcukit/)

```
.mcukit/
├── state/
│   ├── pdca-status.json          # PDCA 상태 (bkit 동일 포맷)
│   ├── memory.json               # 메모리 저장소 (bkit 동일)
│   ├── domain-cache.json         # ★ 도메인 감지 캐시
│   ├── build-history.json        # ★ 빌드 메모리 사용량 이력
│   ├── quality-metrics.json      # 품질 메트릭 (bkit 동일)
│   ├── quality-history.json      # 품질 히스토리 (bkit 동일)
│   ├── regression-rules.json     # 회귀 규칙 (bkit 동일)
│   ├── trust-profile.json        # 신뢰 프로필 (bkit 동일)
│   └── workflows/                # 워크플로우 상태 (bkit 동일)
├── runtime/
│   ├── agent-state.json          # 에이전트 상태 (bkit 동일)
│   ├── agent-events.jsonl        # 에이전트 이벤트 로그 (bkit 동일)
│   └── control-state.json        # 제어 상태 (bkit 동일)
├── audit/                        # 감사 로그 (bkit 동일)
├── decisions/                    # 의사결정 추적 (bkit 동일)
├── checkpoints/                  # 체크포인트 (bkit 동일)
└── debug/                        # 디버그 로그
```

### 4.2 domain-cache.json 구조 (★ 신규)

```json
{
  "detectedAt": "2026-03-22T10:00:00Z",
  "domain": "mcu",
  "confidence": 0.95,
  "markers": ["Core/Src/main.c", "STM32F407VGTx.ioc", "STM32F407VGTx_FLASH.ld"],
  "level": "L2_Standard",
  "levelMarkers": ["Middlewares/Third_Party/FreeRTOS/"],
  "platform": {
    "name": "stm32f4",
    "chip": "STM32F407VGT6",
    "sdk": "STM32CubeF4",
    "toolchain": "arm-none-eabi-gcc 13.2.1"
  },
  "secondary": null
}
```

### 4.3 build-history.json 구조 (★ 신규)

```json
{
  "history": [
    {
      "timestamp": "2026-03-22T10:30:00Z",
      "feature": "uart-driver",
      "flash": { "used": 81920, "total": 1048576, "percent": 7.8 },
      "ram": { "used": 24576, "total": 131072, "percent": 18.8 },
      "topSymbols": [
        { "name": "HAL_UART_IRQHandler", "size": 1024 },
        { "name": "main", "size": 512 }
      ]
    }
  ],
  "maxEntries": 100
}
```

---

## 5. Hook Script Design

### 5.1 domain-detect.js (startup/ 신규)

```javascript
/**
 * SessionStart 4단계: 도메인 자동 감지
 *
 * 입력: 없음 (프로젝트 디렉토리 스캔)
 * 출력: domain-cache.json 저장, onboarding에 도메인 정보 전달
 * 실행 시점: context-init.js 이후, onboarding.js 이전
 * 타임아웃: 2초 이내 (파일 존재 검사만, 내용 읽기 없음)
 */
module.exports = {
  run() {
    const { detectDomain, detectDomainLevel, detectPlatform } = require('../../lib/domain/detector');
    const result = detectDomain();
    if (result.domain !== 'unknown') {
      result.level = detectDomainLevel(result.domain);
      result.platform = detectPlatform(result.domain);
    }
    // domain-cache.json 저장
    // 반환: onboarding에서 사용할 도메인 정보
    return result;
  }
};
```

### 5.2 unified-bash-pre.js 확장

```javascript
// 기존 bkit 로직 유지 + 도메인별 위험 명령 추가

function handleDomainDestructiveCheck(input) {
  const { domain } = require('../lib/domain/detector').getCachedDomainInfo();
  const { getDestructivePatterns } = require('../lib/domain/router');
  const patterns = getDestructivePatterns();

  const { command } = parseHookInput(input);
  for (const { pattern, reason } of patterns) {
    if (command.toLowerCase().includes(pattern.toLowerCase())) {
      outputBlock(`[mcukit] ${reason}. 이 명령은 수동 확인이 필요합니다.`);
      return true;
    }
  }
  return false;
}
```

### 5.3 unified-bash-post.js 확장

```javascript
// 기존 bkit 로직 유지 + 빌드 명령 감지 시 도메인별 분석 트리거

function handlePostBashDomainAnalysis(input) {
  const { command } = parseHookInput(input);
  const { domain } = require('../lib/domain/detector').getCachedDomainInfo();
  const { BUILD_COMMAND_PATTERNS } = require('../lib/core/constants');

  const patterns = BUILD_COMMAND_PATTERNS[domain] || [];
  const isBuildCommand = patterns.some(p => command.includes(p));

  if (!isBuildCommand) return null;

  // 도메인별 빌드 후 분석
  switch (domain) {
    case 'mcu': return analyzeMcuBuild(command);   // .map 파일 파싱
    case 'mpu': return analyzeMpuBuild(command);   // 이미지 크기 분석
    case 'wpf': return analyzeWpfBuild(command);   // 경고/에러 분석
    default: return null;
  }
}
```

### 5.4 unified-write-post.js 확장

```javascript
// 기존 bkit 로직 유지 + 도메인별 파일 검증

function handlePostWriteDomainValidation(input) {
  const { file_path } = parseHookInput(input);
  const ext = path.extname(file_path);

  // MCU: .c/.h 파일 작성 시 (향후 MISRA 사전 검사)
  if (['.c', '.h'].includes(ext)) {
    // 향후: cppcheck --addon=misra 연동
    return null;
  }

  // MPU: .dts/.dtsi 파일 작성 시 문법 검증
  if (['.dts', '.dtsi'].includes(ext)) {
    return validateDtsFile(file_path);
  }

  // WPF: .xaml 파일 작성 시 바인딩 검증
  if (ext === '.xaml') {
    return validateXamlBindings(file_path);
  }

  return null;
}
```

---

## 6. Implementation Guide

### 6.1 구현 순서 (Phase 1: MVP-1 코어 이식)

```
Step 1: 플러그인 skeleton 생성
  ├── .claude-plugin/plugin.json
  ├── mcukit.config.json
  └── CLAUDE.md

Step 2: lib/core/ 이식 (12 파일)
  ├── 모든 파일 복사
  ├── BKIT → MCUKIT 일괄 치환 (sed/replace)
  ├── .bkit/ → .mcukit/ 경로 치환
  └── file.js TIER_EXTENSIONS 수정

Step 3: lib/pdca/ 이식 (17 파일)
  ├── 모든 파일 복사
  ├── BKIT → MCUKIT 일괄 치환
  ├── level.js 재작성 (도메인 마커)
  └── tier.js 재작성 (임베디드 Tier)

Step 4: 보조 lib/ 이식 (25 파일)
  ├── lib/audit/ (3)
  ├── lib/control/ (7) + destructive-detector 확장
  ├── lib/quality/ (3)
  ├── lib/intent/ (4)
  ├── lib/task/ (5)
  ├── lib/team/ (9) - 이름 치환만
  └── lib/ui/ (7) - 이름 치환만

Step 5: lib/domain/ 신규 개발 (3 파일)
  ├── detector.js
  ├── router.js
  └── cross.js

Step 6: hooks/ 이식 + 확장
  ├── hooks.json (bkit 이식 + 이름 변경)
  ├── session-start.js (도메인 감지 단계 추가)
  ├── startup/ (5 파일 이식 + domain-detect.js 추가)
  └── scripts/ (bkit 통합 스크립트 이식 + 도메인 분기 추가)

Step 7: 기본 Skills 이식
  ├── skills/pdca/SKILL.md (bkit 이식)
  └── skills/mcukit-rules/SKILL.md (bkit-rules 기반 재작성)

Step 8: 검증
  ├── /pdca status 동작 확인
  ├── /pdca plan test-feature 동작 확인
  └── 도메인 감지 테스트 (STM32 샘플, i.MX 샘플, WPF 샘플)
```

### 6.2 이름 치환 스크립트

```bash
#!/bin/bash
# rename-bkit-to-mcukit.sh
# bkit 코어 모듈을 mcukit으로 이름 치환

SRC_DIR="/tmp/bkit-claude-code"
DST_DIR="./mcukit"

# 1. 파일 복사
cp -r "$SRC_DIR/lib/core" "$DST_DIR/lib/core"
cp -r "$SRC_DIR/lib/pdca" "$DST_DIR/lib/pdca"
# ... (나머지 모듈)

# 2. 이름 치환
find "$DST_DIR/lib" -name "*.js" -exec sed -i \
  -e 's/BKIT_/MCUKIT_/g' \
  -e 's/bkit-/mcukit-/g' \
  -e 's/\.bkit\//\.mcukit\//g' \
  -e "s/'bkit'/'mcukit'/g" \
  -e 's/bkit\.config/mcukit\.config/g' \
  -e 's/bkit-memory/mcukit-memory/g' \
  -e 's/BkitError/McukitError/g' \
  {} \;

# 3. 파일명 변경 (필요시)
# bkit-specific 파일명은 없음 (모두 generic naming)
```

### 6.3 핵심 파일 체크리스트

| # | 파일 | 작업 | 변경 수준 |
|---|------|------|-----------|
| 1 | `.claude-plugin/plugin.json` | 신규 생성 | New |
| 2 | `mcukit.config.json` | bkit 기반 커스터마이즈 | High |
| 3 | `lib/core/platform.js` | 이름 치환 | Low |
| 4 | `lib/core/config.js` | 이름 치환 | Low |
| 5 | `lib/core/paths.js` | 경로 치환 (.bkit→.mcukit) | Low |
| 6 | `lib/core/constants.js` | 이름 치환 + MCU 상수 추가 | Medium |
| 7 | `lib/core/errors.js` | 이름 치환 | Low |
| 8 | `lib/core/file.js` | TIER_EXTENSIONS 재작성 | Medium |
| 9 | `lib/core/state-store.js` | 변경 없음 | None |
| 10 | `lib/pdca/level.js` | **전면 재작성** | **High** |
| 11 | `lib/pdca/tier.js` | **전면 재작성** | **High** |
| 12 | `lib/pdca/state-machine.js` | 변경 없음 | None |
| 13 | `lib/domain/detector.js` | **신규 개발** | **New** |
| 14 | `lib/domain/router.js` | **신규 개발** | **New** |
| 15 | `lib/domain/cross.js` | **신규 개발** | **New** |
| 16 | `lib/control/destructive-detector.js` | MCU/MPU 패턴 추가 | Medium |
| 17 | `hooks/hooks.json` | 이름 치환 | Low |
| 18 | `hooks/session-start.js` | 도메인 감지 단계 추가 | Medium |
| 19 | `hooks/startup/domain-detect.js` | **신규 개발** | **New** |
| 20 | `scripts/unified-bash-pre.js` | 도메인 위험 명령 추가 | Medium |
| 21 | `scripts/unified-bash-post.js` | 빌드 감지 + 도메인 분석 | Medium |
| 22 | `scripts/unified-write-post.js` | 도메인별 파일 검증 | Medium |
| 23 | `skills/pdca/SKILL.md` | 이름 치환 | Low |
| 24 | `skills/mcukit-rules/SKILL.md` | bkit-rules 기반 재작성 | High |

---

## 7. Test Plan

### 7.1 MVP-1 검증 시나리오

| # | 시나리오 | 검증 항목 | 기대 결과 |
|---|---------|-----------|-----------|
| T1 | STM32 프로젝트에서 mcukit 세션 시작 | 도메인 감지 | `domain: mcu, platform: stm32` |
| T2 | i.MX6 Yocto 프로젝트에서 세션 시작 | 도메인 감지 | `domain: mpu, platform: imx6` |
| T3 | WPF 프로젝트에서 세션 시작 | 도메인 감지 | `domain: wpf, platform: wpf-net8` |
| T4 | `/pdca status` 실행 | PDCA 상태 출력 | 정상 표시 |
| T5 | `/pdca plan test-feature` 실행 | Plan 문서 생성 | docs/01-plan/features/test-feature.plan.md |
| T6 | MCU+WPF 혼합 프로젝트 | Cross-domain 감지 | primary: mcu, secondary: wpf |
| T7 | 빈 디렉토리에서 시작 | 도메인 unknown | 도메인 선택 질문 |

### 7.2 샘플 프로젝트 구조

```
test-projects/
├── stm32-blink/              # MCU L1 테스트
│   ├── Core/Src/main.c
│   ├── STM32F407VGTx.ioc
│   └── STM32F407VGTx_FLASH.ld
├── stm32-freertos/           # MCU L2 테스트
│   ├── Core/Src/main.c
│   ├── Middlewares/Third_Party/FreeRTOS/
│   └── STM32F407VGTx.ioc
├── imx6ull-yocto/            # MPU L2 테스트
│   ├── conf/local.conf
│   ├── conf/bblayers.conf
│   └── sources/meta-custom/recipes-bsp/
├── wpf-mvvm/                 # WPF L2 테스트
│   ├── MyApp.sln
│   ├── MyApp/MyApp.csproj
│   ├── MyApp/App.xaml
│   └── MyApp/ViewModels/MainViewModel.cs
└── mcu-wpf-cross/            # Cross-domain 테스트
    ├── firmware/STM32F407.ioc
    └── desktop/MyApp.csproj
```

---

## 8. Security Considerations

| 항목 | 위험 | 대책 |
|------|------|------|
| Flash 소거 명령 | MCU 전체 Flash 유실 | destructive-detector에서 차단, 사용자 확인 필수 |
| dd 명령 | SD/eMMC 덮어쓰기 | `/dev/sd*`, `/dev/mmc*` 타겟 시 차단 |
| Yocto 빌드 | 디스크 공간 대량 소모 (수십 GB) | 디스크 여유 공간 사전 검사 |
| .env / 인증 파일 | 시리얼 통신 키, 서명 키 노출 | git commit 전 .env 파일 경고 |
| MISRA 규칙 데이터 | MISRA C:2012 저작권 | 규칙 번호/설명만 포함, 전문은 외부 참조 |

---

## 9. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-22 | 초기 설계: 5-Layer Architecture, 모듈 인터페이스, Hook 확장, 구현 가이드 | Rootech |
| 0.2 | 2026-03-22 | 3-Domain 기술 검증 반영: detector.js 마커 수정(sdk_config.h→fsl_device_registers.h, MainWindow.xaml 제거), .ioc=Java Properties 포맷 명시, cross-compile.js i.MX28 soft float 분기, xaml-analyzer.js에서 x:Bind 제외+TemplateBinding/MultiBinding 추가, DTS 검증에 dt-validate 추가, Yocto meta-imx/meta-freescale 구분, MVVM Source Generator 고려, Prism 9 상용화 주의, CubeProgrammer CLI 추가 | Rootech |
