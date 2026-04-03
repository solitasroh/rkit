# mcukit-core Planning Document

> **Summary**: bkit PDCA 엔진을 기반으로 MCU/MPU/Desktop 3개 도메인을 통합 지원하는 AI 네이티브 임베디드 개발 Kit
>
> **Project**: mcukit
> **Version**: 0.1.0
> **Author**: Rootech
> **Date**: 2026-03-22
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 임베디드/데스크톱 개발에서 AI 코딩 도구를 사용할 때, MCU 레지스터, 리눅스 BSP, WPF MVVM 등 도메인 특화 지식이 없어 정확도가 낮고 개발 흐름이 파편화됨 |
| **Solution** | bkit의 PDCA 엔진을 이식하고, MCU(STM32/NXP K), MPU(i.MX6/i.MX6ULL/i.MX28), Desktop(WPF) 3개 도메인을 Skills/Agents로 커버하는 통합 Claude Code 플러그인 |
| **Function/UX Effect** | 하나의 Kit에서 `/pdca plan` → 설계 → 구현 → 검증 사이클을 MCU 펌웨어, 리눅스 BSP, WPF 앱 모두에 동일하게 적용. 빌드 후 메모리 분석, 핀 충돌 검출, XAML 바인딩 검증 등 도메인별 자동 검증 |
| **Core Value** | "One Kit, Three Domains" - 임베디드~데스크톱 전 영역에서 일관된 PDCA 기반 AI 협업 개발 경험 제공 |

---

## 1. Overview

### 1.1 Purpose

bkit-claude-code(v2.0.0)의 PDCA 기반 AI 네이티브 개발 방법론을 **임베디드 + 데스크톱 개발**에 특화하여 이식한 Claude Code 플러그인을 구축합니다. 웹 개발에 최적화된 bkit의 Skills/Agents를 MCU, MPU(Embedded Linux), WPF 도메인으로 전환하되, 도메인 독립적인 PDCA 코어 엔진은 그대로 재활용합니다.

### 1.2 Background

| 구분 | 현황 | 문제점 |
|------|------|--------|
| MCU 개발 | Claude Code가 STM32 HAL/NXP SDK 코드를 생성하지만 정확도 불안정 | 레지스터 맵, 클럭 트리, 핀 멀티플렉싱 등 도메인 컨텍스트 부재 |
| MPU 개발 | i.MX 계열 Yocto/Buildroot 설정이 복잡 | 디바이스 트리, 커널 모듈, 크로스 컴파일 체인 지식 필요 |
| WPF 개발 | MVVM 패턴, XAML 바인딩, Prism/CommunityToolkit 등 프레임워크 다양 | 일관된 아키텍처 가이드 부재, 바인딩 에러 런타임까지 발견 안됨 |
| 공통 | 개발 흐름이 도구/플랫폼마다 파편화 | 통합 PDCA 워크플로우 부재 |

### 1.3 Related Documents

- 마스터 기획서: `docs/01-plan/mcukit-master-plan.md`
- 원본 bkit: https://github.com/popup-studio-ai/bkit-claude-code (Apache 2.0)

---

## 2. Target Platform 정의

### 2.1 3-Domain Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        mcukit                                    │
│                  "One Kit, Three Domains"                        │
├─────────────────┬──────────────────┬────────────────────────────┤
│   Domain A      │   Domain B       │   Domain C                 │
│   MCU           │   MPU            │   Desktop                  │
│  (Bare/RTOS)    │ (Embedded Linux) │   (Windows)                │
├─────────────────┼──────────────────┼────────────────────────────┤
│ STM32 계열      │ i.MX6 (Quad/DL)  │ WPF (.NET 8+)             │
│ NXP Kinetis K   │ i.MX6ULL         │ C# / XAML                 │
│                 │ i.MX28           │ MVVM Pattern              │
├─────────────────┼──────────────────┼────────────────────────────┤
│ ARM Cortex-M    │ ARM Cortex-A     │ x86/x64                   │
│ Flash: KB~MB    │ DDR: 256MB~1GB   │ RAM: GB 단위              │
│ No OS / RTOS    │ Linux (Yocto)    │ Windows 10/11             │
│ C (MISRA)       │ C / Device Tree  │ C# / .NET                 │
├─────────────────┴──────────────────┴────────────────────────────┤
│                    PDCA Core Engine (bkit 이식)                  │
│  State Machine │ Workflow │ Hooks │ Audit │ Control │ Quality   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 플랫폼 상세

#### Domain A: MCU (Microcontroller)

| 플랫폼 | 코어 | SDK | 빌드 | 디버거 | RTOS |
|---------|------|-----|------|--------|------|
| **STM32** | Cortex-M0/M3/M4/M7 | STM32CubeMX + HAL/LL | CMake, arm-gcc | ST-Link, OpenOCD | FreeRTOS, ThreadX |
| **NXP Kinetis K** | Cortex-M4/M7 | MCUXpresso SDK | CMake, arm-gcc | J-Link, MCU-Link | FreeRTOS, Zephyr |

**핵심 특성**: 메모리 제약(KB~MB), 실시간성, 하드웨어 직접 제어, MISRA C 준수

#### Domain B: MPU (Microprocessor / Embedded Linux)

| 플랫폼 | 코어 | 특징 | Linux 배포 | 주요 용도 |
|---------|------|------|-----------|-----------|
| **i.MX6** (Quad/DL) | Cortex-A9 (1~4코어) | GPU(Vivante), 1080p 비디오, PCIe | Yocto (Poky), Buildroot | HMI, 산업용 게이트웨이, 멀티미디어 |
| **i.MX6ULL** | Cortex-A7 (싱글코어) | 저전력, 저비용, LCD | Yocto, Buildroot | IoT 게이트웨이, 제어기, 계측기 |
| **i.MX28** | ARM926EJ-S | 레거시, 저전력 | Linux 4.x, Buildroot | 산업용 제어, 레거시 유지보수 |

**핵심 특성**: Device Tree, 커널 모듈, 루트파일시스템, 크로스 컴파일, Yocto 레시피

#### Domain C: Desktop (WPF)

| 항목 | 내용 |
|------|------|
| **프레임워크** | WPF (.NET 8 / .NET Framework 4.8) |
| **언어** | C# |
| **UI** | XAML |
| **아키텍처 패턴** | MVVM (CommunityToolkit.Mvvm, Prism) |
| **빌드** | MSBuild, dotnet CLI |
| **테스트** | xUnit, NUnit, MSTest |
| **배포** | ClickOnce, MSIX, Installer |

**핵심 특성**: MVVM 바인딩, DI (Dependency Injection), 시리얼 통신(MCU 연동), 데이터 시각화

---

## 3. Scope

### 3.1 In Scope

- [x] bkit PDCA 코어 엔진 이식 (state-machine, workflow, hooks, audit, control, quality)
- [ ] MCU 도메인 Skills & Agents (STM32, NXP K)
- [ ] MPU 도메인 Skills & Agents (i.MX6, i.MX6ULL, i.MX28)
- [ ] WPF 도메인 Skills & Agents (C#/XAML/MVVM)
- [ ] 도메인별 Quality Gates (메모리 분석, Device Tree 검증, XAML 바인딩 검증)
- [ ] 도메인별 문서 템플릿 (Plan, Design, Analysis, Report)
- [ ] mcukit.config.json 설정 체계
- [ ] 도메인 자동 감지 (프로젝트 파일 기반)

### 3.2 Out of Scope

- RTOS 자체 개발 (기존 FreeRTOS/Zephyr 활용)
- Yocto/Buildroot 배포판 자체 제작
- WPF 외 다른 .NET UI 프레임워크 (MAUI, Avalonia 등)
- 실제 HW 에뮬레이터 개발 (QEMU 등 기존 도구 활용)
- bkit의 웹 개발 스킬 (bkend, starter, dynamic, enterprise 등)

---

## 4. Architecture

### 4.1 Project Level 재정의 (3-Level × 3-Domain)

| Level | Domain A (MCU) | Domain B (MPU) | Domain C (WPF) |
|-------|---------------|----------------|-----------------|
| **L1: Basic** | Bare-metal, 폴링 기반, 단일 페리페럴 | Buildroot 기본, 단일 앱 | 단일 윈도우, 기본 MVVM |
| **L2: Standard** | RTOS, 멀티태스크, 복수 페리페럴 | Yocto 커스텀 레이어, 복수 데몬 | 멀티윈도우, DI, 시리얼 통신 |
| **L3: Advanced** | 멀티코어, 기능안전, 부트로더 | GPU 가속, 멀티미디어, OTA | Plugin 아키텍처, 실시간 데이터 |

### 4.2 도메인 자동 감지

```javascript
// lib/mcu/domain-detector.js
const DOMAIN_MARKERS = {
  mcu: {
    files: ['STM32*.ioc', 'CMakeLists.txt', '*.ld', 'startup_*.s',
            'fsl_device_registers.h', 'board.h', 'fsl_*.h', 'FreeRTOSConfig.h'],
    extensions: ['.ioc', '.ld', '.s', '.S'],
    content: ['HAL_Init', 'NVIC_', 'FreeRTOS', 'MCUXpresso',
              'arm-none-eabi', 'Cortex-M']
  },
  mpu: {
    files: ['*.dts', '*.dtsi', 'Makefile', 'local.conf',
            'bblayers.conf', 'machine.conf', '*.bb', '*.bbappend'],
    extensions: ['.dts', '.dtsi', '.bb', '.bbappend'],
    content: ['imx6', 'imx6ull', 'imx28', 'ARCH=arm',
              'device-tree', 'yocto', 'buildroot', 'rootfs']
  },
  wpf: {
    files: ['*.csproj', '*.sln', 'App.xaml', '*.xaml'],
    // ★ MainWindow.xaml 제거: 기본 템플릿명일 뿐, 감지 기준 부적합
    // ★ .csproj 내부 <UseWPF>true</UseWPF> 파싱 필요 (파일 존재만으로 WPF 판별 불가)
    extensions: ['.xaml', '.csproj', '.cs'],
    content: ['<Window', '<UserControl', 'xmlns:wpf',
              'System.Windows', 'PresentationFramework',
              'CommunityToolkit.Mvvm', 'Prism']
  }
};
```

### 4.3 디렉토리 구조 (전체)

```
mcukit/
├── .claude-plugin/
│   └── plugin.json              # Claude Code 플러그인 매니페스트
│
├── agents/                       # AI 에이전트 (20개)
│   ├── # ── 공통 (bkit 이식) ──
│   ├── cto-lead.md               # 팀 오케스트레이션
│   ├── gap-detector.md           # 설계-구현 갭 분석
│   ├── code-analyzer.md          # 코드 품질 분석 (MISRA/C#/DT 확장)
│   ├── report-generator.md       # PDCA 보고서 생성
│   ├── pdca-iterator.md          # 자동 반복 개선
│   │
│   ├── # ── Domain A: MCU ──
│   ├── fw-architect.md           # 펌웨어 아키텍처 설계
│   ├── hw-interface-expert.md    # HW 인터페이스 (GPIO/SPI/I2C/CAN)
│   ├── driver-developer.md       # 디바이스 드라이버 개발
│   ├── rtos-expert.md            # RTOS 태스크/동기화 설계
│   ├── safety-auditor.md         # MISRA C / 기능안전 검증
│   ├── memory-optimizer.md       # Flash/RAM 최적화
│   │
│   ├── # ── Domain B: MPU (Embedded Linux) ──
│   ├── linux-bsp-expert.md       # BSP/Device Tree/커널 설정
│   ├── yocto-expert.md           # Yocto 레시피/레이어 관리
│   ├── kernel-module-dev.md      # 커널 모듈/드라이버 개발
│   │
│   ├── # ── Domain C: WPF ──
│   ├── wpf-architect.md          # WPF MVVM 아키텍처 설계
│   ├── xaml-expert.md            # XAML UI/바인딩/스타일
│   └── dotnet-expert.md          # .NET/C# 패턴/DI/테스트
│
├── skills/                       # 도메인 지식 스킬 (30개)
│   ├── # ── 공통 (bkit 이식) ──
│   ├── pdca/                     # PDCA 사이클 관리
│   ├── mcukit-rules/             # 핵심 규칙
│   ├── mcukit-templates/         # 문서 템플릿
│   ├── code-review/              # 코드 리뷰 (도메인 확장)
│   │
│   ├── # ── Phase Skills (도메인 공통 9단계) ──
│   ├── phase-1-spec/             # 사양 정의 (HW스펙/DT스펙/UI스펙)
│   ├── phase-2-convention/       # 코딩 컨벤션 (MISRA/Kernel/C#)
│   ├── phase-3-architecture/     # 아키텍처 설계
│   ├── phase-4-foundation/       # 기반 구현 (BSP/커널설정/프로젝트셋업)
│   ├── phase-5-core-impl/        # 핵심 구현 (드라이버/모듈/ViewModel)
│   ├── phase-6-integration/      # 통합 (페리페럴/앱/UI연결)
│   ├── phase-7-test/             # 테스트/검증
│   ├── phase-8-optimization/     # 최적화 (메모리/성능/UX)
│   ├── phase-9-production/       # 양산/배포
│   │
│   ├── # ── Domain A: MCU Skills ──
│   ├── stm32-hal/                # STM32 HAL/LL API
│   ├── stm32-cubemx/             # CubeMX 코드 생성
│   ├── nxp-mcuxpresso/           # NXP MCUXpresso SDK
│   ├── freertos/                 # FreeRTOS 태스크/동기화
│   ├── communication/            # UART/SPI/I2C/CAN/USB
│   ├── misra-c/                  # MISRA C:2012
│   ├── interrupt-design/         # 인터럽트/DMA 설계
│   ├── linker-memory/            # 링커 스크립트/메모리 맵
│   ├── bootloader/               # 부트로더/OTA
│   ├── cmake-embedded/           # 임베디드 CMake
│   │
│   ├── # ── Domain B: MPU Skills ──
│   ├── imx-bsp/                  # i.MX BSP/Device Tree
│   ├── yocto-build/              # Yocto/Buildroot 빌드
│   ├── kernel-driver/            # 리눅스 커널 모듈
│   ├── rootfs-config/            # 루트파일시스템 구성
│   │
│   ├── # ── Domain C: WPF Skills ──
│   ├── wpf-mvvm/                 # WPF MVVM 패턴
│   ├── xaml-design/              # XAML UI 디자인/스타일
│   ├── dotnet-patterns/          # .NET DI/패턴/테스트
│   └── serial-bridge/            # MCU↔WPF 시리얼 통신
│
├── lib/                          # 코어 라이브러리
│   ├── core/                     # bkit에서 이식 (93 exports)
│   │   ├── index.js
│   │   ├── platform.js           # 플랫폼 감지 (mcukit 적응)
│   │   ├── config.js             # mcukit.config.json 로더
│   │   ├── paths.js              # .mcukit/ 상태 파일 레지스트리
│   │   ├── constants.js          # MCUKIT_* 상수
│   │   ├── errors.js             # MCUKIT_* 에러 코드
│   │   ├── state-store.js        # 원자적 파일 I/O + 잠금
│   │   ├── cache.js              # TTL 기반 캐시
│   │   ├── io.js                 # Hook 입출력
│   │   ├── debug.js              # 디버그 로깅
│   │   ├── file.js               # 소스 파일 판별 (MCU/MPU/WPF 확장)
│   │   └── hook-io.js            # Hook I/O 유틸
│   │
│   ├── pdca/                     # bkit에서 이식 (130+ exports)
│   │   ├── index.js
│   │   ├── state-machine.js      # 선언적 상태 전이 (20 transitions)
│   │   ├── workflow-engine.js    # 워크플로우 실행 엔진
│   │   ├── workflow-parser.js    # YAML DSL 파서
│   │   ├── phase.js              # PDCA 단계 관리
│   │   ├── level.js              # 프로젝트 레벨 감지 (MCU/MPU/WPF 마커)
│   │   ├── tier.js               # 언어 Tier (C/DTS/C# 추가)
│   │   ├── status.js             # PDCA 상태 저장/조회
│   │   ├── automation.js         # 자동화 레벨 (L0~L4)
│   │   ├── feature-manager.js    # 다중 Feature 관리
│   │   ├── batch-orchestrator.js # 배치 오케스트레이션
│   │   ├── executive-summary.js  # 실행 요약 생성
│   │   ├── template-validator.js # 문서 템플릿 검증
│   │   ├── lifecycle.js          # 라이프사이클 관리
│   │   └── resume.js             # 세션 재개
│   │
│   ├── domain/                   # ★ 도메인 감지/라우팅 (신규)
│   │   ├── index.js              # 도메인 모듈 진입점
│   │   ├── detector.js           # 도메인 자동 감지 (MCU/MPU/WPF)
│   │   ├── router.js             # 도메인별 스킬/에이전트 라우팅
│   │   └── cross-domain.js       # 도메인 간 연동 (MCU↔WPF 시리얼 등)
│   │
│   ├── mcu/                      # ★ MCU 도메인 모듈 (신규)
│   │   ├── index.js
│   │   ├── toolchain.js          # arm-none-eabi-gcc, IAR, Keil 탐지
│   │   ├── flash.js              # ST-Link, J-Link, OpenOCD 플래싱
│   │   ├── memory-analyzer.js    # .map 파일 파서, Flash/RAM 리포트
│   │   ├── linker-analyzer.js    # 링커 스크립트 분석
│   │   ├── pin-config.js         # 핀 멀티플렉싱 충돌 검출
│   │   ├── clock-tree.js         # 클럭 트리 설정 검증
│   │   └── register-map.js       # 레지스터 맵 파서
│   │
│   ├── mpu/                      # ★ MPU 도메인 모듈 (신규)
│   │   ├── index.js
│   │   ├── device-tree.js        # DTS/DTSI 파서/검증
│   │   ├── yocto-analyzer.js     # Yocto 레시피/레이어 분석
│   │   ├── kernel-config.js      # 커널 설정(.config) 분석
│   │   ├── rootfs-analyzer.js    # 루트파일시스템 크기/의존성 분석
│   │   └── cross-compile.js      # 크로스 컴파일 환경 탐지
│   │
│   ├── wpf/                      # ★ WPF 도메인 모듈 (신규)
│   │   ├── index.js
│   │   ├── xaml-analyzer.js      # XAML 바인딩/리소스 검증
│   │   ├── mvvm-validator.js     # MVVM 패턴 준수 검증
│   │   ├── csproj-analyzer.js    # .csproj 의존성/설정 분석
│   │   └── nuget-manager.js      # NuGet 패키지 관리
│   │
│   ├── audit/                    # bkit에서 이식
│   │   ├── audit-logger.js
│   │   ├── decision-tracer.js
│   │   └── explanation-generator.js
│   │
│   ├── control/                  # bkit에서 이식
│   │   ├── automation-controller.js
│   │   ├── checkpoint-manager.js
│   │   ├── destructive-detector.js  # MCU: flash erase, MPU: rm rootfs 추가
│   │   ├── loop-breaker.js
│   │   ├── blast-radius.js
│   │   ├── scope-limiter.js
│   │   └── trust-engine.js
│   │
│   ├── quality/                  # bkit에서 이식 + 도메인 확장
│   │   ├── gate-manager.js       # 도메인별 Quality Gate 추가
│   │   ├── metrics-collector.js  # MCU: 메모리, MPU: 이미지크기, WPF: 바인딩에러
│   │   └── regression-guard.js
│   │
│   ├── intent/                   # bkit에서 이식
│   ├── task/                     # bkit에서 이식
│   ├── team/                     # bkit에서 이식
│   └── ui/                       # bkit에서 이식
│
├── hooks/                        # 이벤트 훅
│   ├── hooks.json                # 18 이벤트 (bkit 이식 + 도메인 확장)
│   ├── session-start.js          # 초기화 (도메인 감지 포함)
│   ├── startup/
│   │   ├── migration.js
│   │   ├── restore.js
│   │   ├── context-init.js
│   │   ├── onboarding.js
│   │   └── domain-detect.js      # ★ 세션 시작 시 도메인 자동 감지
│   └── scripts/
│       ├── # ── 공통 (bkit 이식) ──
│       ├── unified-bash-pre.js
│       ├── unified-bash-post.js
│       ├── unified-write-post.js
│       ├── unified-stop.js
│       ├── skill-post.js
│       ├── user-prompt-handler.js
│       │
│       ├── # ── Domain A: MCU ──
│       ├── mcu-post-build.js     # .map 파일 파싱, 메모리 리포트
│       ├── mcu-pre-flash.js      # 플래싱 전 안전 검사
│       │
│       ├── # ── Domain B: MPU ──
│       ├── mpu-post-build.js     # Yocto/Buildroot 빌드 결과 분석
│       ├── mpu-dts-validate.js   # Device Tree 수정 후 검증
│       │
│       └── # ── Domain C: WPF ──
│           ├── wpf-post-build.js  # 빌드 경고/에러 분석
│           └── wpf-xaml-check.js  # XAML 바인딩 검증
│
├── templates/                    # 문서 템플릿
│   ├── # ── 공통 ──
│   ├── plan.template.md          # Plan (도메인 섹션 추가)
│   ├── design.template.md        # Design (도메인 섹션 추가)
│   ├── analysis.template.md      # Gap Analysis
│   ├── report.template.md        # 완료 보고서
│   ├── CLAUDE.template.md        # CLAUDE.md 생성 템플릿
│   │
│   ├── # ── Domain A: MCU ──
│   ├── mcu-hw-spec.template.md   # HW 사양서
│   ├── mcu-memory-budget.template.md  # 메모리 예산
│   ├── mcu-driver-spec.template.md    # 드라이버 사양
│   │
│   ├── # ── Domain B: MPU ──
│   ├── mpu-bsp-spec.template.md  # BSP 사양서
│   ├── mpu-dts-spec.template.md  # Device Tree 설계
│   ├── mpu-image-spec.template.md # 이미지 구성 사양
│   │
│   └── # ── Domain C: WPF ──
│       ├── wpf-ui-spec.template.md    # UI 사양서
│       └── wpf-mvvm-spec.template.md  # MVVM 구조 설계
│
├── refs/                         # 레퍼런스 데이터
│   ├── stm32/                    # STM32 칩 데이터
│   ├── nxp-k/                    # NXP Kinetis K 칩 데이터
│   ├── imx/                      # i.MX6/i.MX6ULL/i.MX28 데이터
│   ├── misra-c/                  # MISRA C:2012 규칙
│   ├── freertos/                 # FreeRTOS API
│   ├── yocto/                    # Yocto 레이어/변수 레퍼런스
│   └── wpf/                      # WPF/MVVM 패턴 레퍼런스
│
├── servers/                      # MCP 서버
│   ├── mcukit-pdca-server/       # PDCA 관리 (bkit 이식)
│   └── mcukit-analysis-server/   # 도메인별 분석 도구
│
├── evals/                        # 스킬 평가 (bkit 이식)
│   ├── config.json
│   ├── runner.js
│   └── reporter.js
│
├── mcukit.config.json            # 통합 설정
├── mcukit.config.schema.json     # 설정 스키마
└── CLAUDE.md                     # Claude Code 연동
```

### 4.4 도메인별 PDCA Phase 매핑

| Phase | MCU (Domain A) | MPU (Domain B) | WPF (Domain C) |
|-------|---------------|----------------|-----------------|
| **Phase 1: Spec** | HW 사양, 핀맵, 클럭, 메모리 예산 | SoC 선정, DT 설계, 이미지 구성 | UI 와이어프레임, 화면 목록 |
| **Phase 2: Convention** | MISRA C, 네이밍, 파일 구조 | 커널 코딩 스타일, DTS 컨벤션 | C# 코딩 컨벤션, XAML 규칙 |
| **Phase 3: Architecture** | 레이어 구조, 인터럽트 맵 | BSP 레이어, 디바이스 트리 구조 | MVVM 구조, DI 컨테이너 |
| **Phase 4: Foundation** | BSP 초기화, 스타트업 코드 | 커널 설정, 루트파일시스템 | 프로젝트 셋업, NuGet, DI |
| **Phase 5: Core** | 디바이스 드라이버, HAL 래퍼 | 커널 모듈, 사용자공간 데몬 | ViewModel, Model, Service |
| **Phase 6: Integration** | 페리페럴 통합, RTOS 태스크 | 앱↔커널 연동, D-Bus/IPC | View↔ViewModel 바인딩 |
| **Phase 7: Test** | Unit(Host), HIL, QEMU | 커널 테스트, 통합 테스트 | xUnit, UI 자동화 테스트 |
| **Phase 8: Optimize** | 메모리, 전력, 인터럽트 응답 | 부팅 시간, 이미지 크기 | 렌더링 성능, 메모리 |
| **Phase 9: Production** | 플래싱, OTA, 양산 테스트 | 이미지 빌드, OTA, 공장 초기화 | 설치 패키지, 자동 업데이트 |

### 4.5 도메인별 Quality Gates

```javascript
// mcukit.config.json - quality.domainThresholds
{
  "mcu": {
    "flashUsagePercent": 85,
    "ramUsagePercent": 75,
    "stackMarginPercent": 20,
    "misraRequired": 0,          // 필수 규칙 위반 0
    "misraAdvisoryMax": 10
  },
  "mpu": {
    "imageMaxSizeMB": 256,       // 루트파일시스템 크기 상한
    "kernelSizeKB": 8192,        // 커널 이미지 크기 상한
    "bootTimeSeconds": 10,       // 부팅 시간 상한
    "dtbValid": true             // Device Tree 컴파일 성공 필수
  },
  "wpf": {
    "buildWarnings": 0,          // 빌드 경고 0
    "bindingErrors": 0,          // XAML 바인딩 에러 0
    "nullabilityViolations": 0,  // Nullable 위반 0
    "codeAnalysis": "recommended" // .NET 코드 분석 수준
  },
  "common": {
    "matchRate": 90,
    "codeQualityScore": 70,
    "conventionCompliance": 90
  }
}
```

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Domain | Priority |
|----|-------------|--------|----------|
| FR-01 | PDCA 코어 엔진 이식 (state-machine, workflow, hooks, audit, control, quality) | 공통 | High |
| FR-02 | 프로젝트 도메인 자동 감지 (MCU/MPU/WPF) | 공통 | High |
| FR-03 | 도메인별 Skills 라우팅 | 공통 | High |
| FR-04 | mcukit.config.json 설정 체계 | 공통 | High |
| FR-05 | STM32 HAL/LL Skills + CubeMX 연동 가이드 | MCU | High |
| FR-06 | NXP MCUXpresso SDK Skills | MCU | High |
| FR-07 | 빌드 후 .map 파일 자동 분석 (Flash/RAM 리포트) | MCU | High |
| FR-08 | 핀 멀티플렉싱 충돌 검출 | MCU | Medium |
| FR-09 | MISRA C 코딩 표준 검사 연동 | MCU | Medium |
| FR-10 | i.MX Device Tree 파싱/검증 | MPU | High |
| FR-11 | Yocto 레시피/레이어 관리 가이드 | MPU | High |
| FR-12 | 커널 모듈 개발 가이드 | MPU | Medium |
| FR-13 | 크로스 컴파일 환경 자동 탐지 | MPU | Medium |
| FR-14 | WPF MVVM 아키텍처 가이드 | WPF | High |
| FR-15 | XAML 바인딩 정적 검증 | WPF | High |
| FR-16 | .NET DI/패턴 가이드 | WPF | Medium |
| FR-17 | MCU↔WPF 시리얼 통신 브릿지 가이드 | Cross | Medium |
| FR-18 | 도메인별 문서 템플릿 (Plan/Design/Analysis/Report) | 공통 | High |
| FR-19 | 도메인별 Quality Gates | 공통 | Medium |
| FR-20 | fw-architect, linux-bsp-expert, wpf-architect 에이전트 | 공통 | High |

### 5.2 Non-Functional Requirements

| Category | Criteria | Measurement |
|----------|----------|-------------|
| 호환성 | Claude Code v2.1.78+ 에서 동작 | 플러그인 로드 테스트 |
| 성능 | SessionStart 5초 이내 완료 | Hook timeout |
| 확장성 | 새 MCU/MPU 플랫폼 추가 시 Skill 1개 + refs/ 데이터만 추가 | 구조 검증 |
| 정확도 | MCU 코드 생성 시 레지스터/핀 오류 0 (refs 데이터 기반) | 샘플 프로젝트 테스트 |

---

## 6. Implementation Phases (로드맵)

### Phase 1: PDCA 코어 이식 + 도메인 감지 (MVP-1)

**목표**: bkit 코어를 mcukit으로 이식하고, 3개 도메인 자동 감지 동작

| Task | Source | Action | 예상 파일 수 |
|------|--------|--------|-------------|
| lib/core/ 전체 | bkit lib/core/ | 복사 + BKIT→MCUKIT 이름 변경 | 12 |
| lib/pdca/ 전체 | bkit lib/pdca/ | 복사 + 이름 변경 + Level 마커 수정 | 17 |
| lib/audit/ | bkit | 복사 | 3 |
| lib/control/ | bkit | 복사 + destructive-detector MCU 규칙 추가 | 7 |
| lib/quality/ | bkit | 복사 + 도메인별 threshold 구조 추가 | 3 |
| lib/intent/, task/, team/, ui/ | bkit | 복사 | 25 |
| lib/domain/detector.js | 신규 | 도메인 자동 감지 | 3 |
| hooks/ 기본 구조 | bkit | 복사 + 적응 | 8 |
| skills/pdca/ | bkit | 복사 | 1 |
| mcukit.config.json | bkit 기반 | 커스터마이즈 | 2 |
| plugin.json | 신규 | 플러그인 매니페스트 | 1 |
| **합계** | | | **~82** |

**완료 기준**: `/pdca plan`, `/pdca status`, 도메인 감지가 동작

### Phase 2: MCU 도메인 (MVP-2)

**목표**: STM32 Bare-metal 프로젝트에서 PDCA 사이클 완전 동작

| Task | 유형 | 예상 파일 수 |
|------|------|-------------|
| lib/mcu/ (toolchain, flash, memory-analyzer 등) | 신규 | 8 |
| skills/stm32-hal/ | 신규 | 1 |
| skills/nxp-mcuxpresso/ | 신규 | 1 |
| skills/cmake-embedded/ | 신규 | 1 |
| skills/communication/ | 신규 | 1 |
| skills/freertos/ | 신규 | 1 |
| skills/misra-c/ | 신규 | 1 |
| agents/fw-architect.md | 신규 | 1 |
| agents/hw-interface-expert.md | 신규 | 1 |
| agents/safety-auditor.md | 신규 | 1 |
| hooks/scripts/mcu-post-build.js | 신규 | 2 |
| templates/mcu-*.template.md | 신규 | 3 |
| refs/stm32/, refs/nxp-k/ | 신규 | 2+ |
| **합계** | | **~24** |

### Phase 3: MPU 도메인

**목표**: i.MX6 Yocto 프로젝트에서 PDCA 사이클 동작

| Task | 유형 | 예상 파일 수 |
|------|------|-------------|
| lib/mpu/ (device-tree, yocto-analyzer 등) | 신규 | 5 |
| skills/imx-bsp/ | 신규 | 1 |
| skills/yocto-build/ | 신규 | 1 |
| skills/kernel-driver/ | 신규 | 1 |
| agents/linux-bsp-expert.md | 신규 | 1 |
| agents/yocto-expert.md | 신규 | 1 |
| agents/kernel-module-dev.md | 신규 | 1 |
| hooks/scripts/mpu-*.js | 신규 | 2 |
| templates/mpu-*.template.md | 신규 | 3 |
| refs/imx/, refs/yocto/ | 신규 | 2+ |
| **합계** | | **~18** |

### Phase 4: WPF 도메인

**목표**: WPF MVVM 프로젝트에서 PDCA 사이클 동작

| Task | 유형 | 예상 파일 수 |
|------|------|-------------|
| lib/wpf/ (xaml-analyzer, mvvm-validator 등) | 신규 | 4 |
| skills/wpf-mvvm/ | 신규 | 1 |
| skills/xaml-design/ | 신규 | 1 |
| skills/dotnet-patterns/ | 신규 | 1 |
| skills/serial-bridge/ | 신규 | 1 |
| agents/wpf-architect.md | 신규 | 1 |
| agents/xaml-expert.md | 신규 | 1 |
| agents/dotnet-expert.md | 신규 | 1 |
| hooks/scripts/wpf-*.js | 신규 | 2 |
| templates/wpf-*.template.md | 신규 | 2 |
| refs/wpf/ | 신규 | 1 |
| **합계** | | **~16** |

### Phase 5: Cross-Domain + 고급 기능

| Task | 유형 |
|------|------|
| lib/domain/cross-domain.js (MCU↔WPF 연동) | 신규 |
| 나머지 MCU skills (interrupt, bootloader, low-power) | 신규 |
| 나머지 agents (rtos-expert, memory-optimizer 등) | 신규 |
| MCP 서버 (mcukit-pdca, mcukit-analysis) | 신규 |
| 스킬 평가 (evals/) | bkit 이식 |

---

## 7. Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 코어 엔진 | 자체 개발 / bkit 이식 | **bkit 이식** | 검증된 PDCA 엔진(~465 함수), Apache 2.0 라이선스 |
| 도메인 구분 | 별도 플러그인 3개 / 통합 1개 | **통합 1개** | MCU↔WPF 시리얼 연동 등 Cross-domain 시나리오 지원 |
| 도메인 감지 | 수동 설정 / 자동 감지 | **자동 감지 + 수동 오버라이드** | .ioc/.dts/.csproj 등 마커 파일로 자동 판별, config에서 오버라이드 가능 |
| MCU 빌드 | IDE 의존 / CMake 표준 | **CMake 기본 + IDE 선택적** | 크로스 플랫폼, CI 친화적 |
| MPU 빌드 | Yocto / Buildroot / 둘 다 | **둘 다 (Yocto 우선)** | i.MX6는 Yocto 주류, i.MX28은 Buildroot가 더 적합 |
| WPF 타겟 | .NET 8 / .NET Framework / 둘 다 | **둘 다** | 레거시 유지보수(.NET FW) + 신규 개발(.NET 8) 모두 지원 |
| 이름 컨벤션 | BKIT→MCUKIT 전체 변경 | **MCUKIT으로 통일** | .mcukit/, MCUKIT_*, mcukit.config.json |
| 상태 디렉토리 | .mcukit/ 단일 | **.mcukit/{state,runtime,audit,...}** | bkit v1.5.8 구조 그대로 이식 |

---

## 8. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| bkit 코어 이식 시 웹 전용 로직이 섞여있을 수 있음 | High | Medium | 이식 전 lib/core 의존성 그래프 검증, 웹 참조 제거 |
| Claude가 i.MX Device Tree를 정확히 생성하지 못할 수 있음 | High | High | refs/imx/ 에 SoC별 DTS 템플릿과 핀멀티플렉싱 데이터 사전 적재 |
| Claude가 MISRA C 규칙을 정확히 알지 못할 수 있음 | Medium | Medium | skills/misra-c/ 에 규칙 테이블 + 위반 예시/수정 예시 포함 |
| 3개 도메인 동시 지원으로 Skills 수가 과도해질 수 있음 | Medium | Low | 도메인별 lazy loading, 감지된 도메인 스킬만 활성화 |
| WPF XAML 바인딩 정적 분석이 완벽하지 않을 수 있음 | Low | Medium | 빌드 시 바인딩 에러 로그 파싱으로 보완 |
| bkit 업스트림 업데이트 시 코어 동기화 비용 | Medium | High | lib/core, lib/pdca를 git subtree로 관리 |

---

## 9. Success Criteria

### 9.1 Definition of Done

- [ ] 3개 도메인(MCU/MPU/WPF) 모두에서 `/pdca plan` → `/pdca report` 전 사이클 동작
- [ ] 도메인 자동 감지가 샘플 프로젝트에서 100% 정확
- [ ] MCU 빌드 후 메모리 리포트 자동 출력
- [ ] MPU Device Tree 수정 후 자동 검증
- [ ] WPF XAML 바인딩 에러 자동 검출
- [ ] gap-detector가 3개 도메인 모두에서 동작

### 9.2 MVP Definition

**MVP-1** (코어만): PDCA 엔진 + 도메인 감지 → `/pdca status` 동작
**MVP-2** (MCU): STM32 프로젝트에서 Plan→Design→Do→Check 동작
**MVP-3** (전체): 3개 도메인 모두 PDCA 전 사이클 동작

---

## 10. bkit 이식 상세 매핑 (리서치 결과)

> 이 섹션은 bkit-claude-code v2.0.0 심층 리서치 결과를 기반으로 mcukit에서의 이식/변경 범위를 정밀하게 정의합니다.

### 10.1 Plugin Manifest (plugin.json) 매핑

```json
// bkit 원본
{
  "name": "bkit",
  "version": "2.0.0",
  "displayName": "bkit — AI Native Development OS",
  "engines": {"claude-code": ">=2.1.78"},
  "outputStyles": "./output-styles/"
}

// mcukit 변환
{
  "name": "mcukit",
  "version": "0.1.0",
  "displayName": "mcukit — AI Native Embedded Development Kit",
  "description": "PDCA-driven MCU/MPU/WPF development with domain-specific AI agents",
  "engines": {"claude-code": ">=2.1.78"},
  "outputStyles": "./output-styles/"
}
```

### 10.2 Skill SKILL.md Frontmatter 포맷 (mcukit 적응)

bkit의 Skill frontmatter 필드를 그대로 사용하되, 도메인 관련 필드를 추가합니다:

```yaml
---
name: stm32-hal                           # 스킬 고유 이름
classification: capability                 # workflow / capability / hybrid
classification-reason: "STM32 HAL 패턴 가이드, 모델 진화 시 내재화 가능"
deprecation-risk: low                      # none / low / medium / high
domain: mcu                                # ★ 신규: mcu / mpu / wpf / common
platforms: [stm32]                         # ★ 신규: 적용 플랫폼
description: |
  STM32 HAL/LL API 사용 가이드 및 베스트 프랙티스.
  Triggers: STM32, HAL, LL, CubeMX, Cortex-M,
  STM32 개발, STM32開発, STM32开发
argument-hint: "[peripheral]"
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
imports:
  - ${PLUGIN_ROOT}/refs/stm32/hal-patterns.md
  - ${PLUGIN_ROOT}/templates/mcu-driver-spec.template.md
next-skill: communication
pdca-phase: do
task-template: "[MCU] {feature} - STM32 HAL"
---
```

**추가 필드**:
- `domain`: mcu / mpu / wpf / common - 도메인 라우팅에 사용
- `platforms`: 해당 스킬이 적용되는 세부 플랫폼 배열

### 10.3 Agent Frontmatter 포맷 (mcukit 적응)

```yaml
---
name: fw-architect
description: |
  펌웨어 아키텍처 설계 전문가.
  레이어 구조, 인터럽트 맵, 메모리 레이아웃, RTOS 태스크 설계.
  Triggers: firmware architecture, 펌웨어 아키텍처, ファームウェア設計
model: opus                                # opus / sonnet / haiku
effort: high                               # low / medium / high
maxTurns: 30
permissionMode: acceptEdits
memory: project                            # project / session / off
context: fork                              # CC native fork
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task(Explore)
  - Task(code-analyzer)
skills: [pdca, mcukit-rules]
imports:
  - ${PLUGIN_ROOT}/refs/stm32/hal-patterns.md
  - ${PLUGIN_ROOT}/templates/design.template.md
disallowedTools:
  - "Bash(rm -rf*)"
  - "Bash(st-flash erase*)"               # ★ MCU: 플래시 전체 소거 금지
  - "Bash(JLinkExe -CommandFile erase*)"   # ★ MCU: J-Link 전체 소거 금지
---
```

**MCU/MPU/WPF별 Agent 모델 배분 계획**:

| Agent | 모델 | 근거 |
|-------|------|------|
| fw-architect | opus | 아키텍처 설계는 높은 추론 필요 |
| hw-interface-expert | sonnet | 페리페럴 설정은 패턴 기반 |
| driver-developer | sonnet | 드라이버 구현은 반복적 패턴 |
| rtos-expert | opus | 동시성 설계는 높은 추론 필요 |
| safety-auditor | opus | MISRA 분석은 정밀도 중요 |
| memory-optimizer | sonnet | 최적화는 데이터 분석 기반 |
| linux-bsp-expert | opus | DTS/커널 설정은 복잡한 상호작용 |
| yocto-expert | sonnet | 레시피 작성은 패턴 기반 |
| kernel-module-dev | sonnet | 커널 API는 문서화 잘 되어있음 |
| wpf-architect | opus | MVVM 아키텍처 설계 |
| xaml-expert | sonnet | XAML은 선언적 패턴 |
| dotnet-expert | sonnet | .NET 패턴은 잘 문서화됨 |
| gap-detector | opus | 설계-구현 갭 분석 (bkit 이식) |
| code-analyzer | opus | 코드 품질 분석 (bkit 이식) |
| report-generator | sonnet | 보고서 생성 (bkit 이식) |
| cto-lead | opus | 팀 오케스트레이션 (bkit 이식) |
| pdca-iterator | sonnet | 자동 수정 (bkit 이식) |

### 10.4 Hook 시스템 매핑 (18 이벤트)

bkit의 18개 Hook 이벤트를 **그대로 이식**하되, 스크립트 내용을 MCU/MPU/WPF 도메인으로 확장합니다:

| # | Hook Event | bkit Script | mcukit 변경 사항 |
|---|-----------|-------------|-----------------|
| 1 | **SessionStart** | session-start.js (5s) | 도메인 감지 단계 추가 (startup/domain-detect.js) |
| 2 | **PreToolUse** (Write/Edit) | pre-write.js (5s) | MISRA 사전검사, DTS 문법 검사, XAML 검증 분기 추가 |
| 3 | **PreToolUse** (Bash) | unified-bash-pre.js (5s) | `st-flash erase`, `dd if=`, `nand erase` 등 위험 명령 추가 |
| 4 | **PostToolUse** (Write) | unified-write-post.js (5s) | .c/.h 파일 MISRA 검사, .dts 문법 검사, .xaml 바인딩 검사 |
| 5 | **PostToolUse** (Bash) | unified-bash-post.js (5s) | 빌드 명령 감지 시 .map 분석 트리거 |
| 6 | **PostToolUse** (Skill) | skill-post.js (5s) | 그대로 이식 |
| 7 | **Stop** | unified-stop.js (10s) | 그대로 이식 (state-machine, checkpoint, audit 통합) |
| 8 | **StopFailure** | stop-failure-handler.js (5s) | 그대로 이식 |
| 9 | **UserPromptSubmit** | user-prompt-handler.js (3s) | 도메인별 implicit trigger 추가 |
| 10 | **PreCompact** | context-compaction.js (5s) | 그대로 이식 |
| 11 | **PostCompact** | post-compaction.js (5s) | 그대로 이식 |
| 12 | **TaskCompleted** | pdca-task-completed.js (5s) | 그대로 이식 |
| 13 | **SubagentStart** | subagent-start-handler.js (5s) | 그대로 이식 |
| 14 | **SubagentStop** | subagent-stop-handler.js (5s) | 그대로 이식 |
| 15 | **TeammateIdle** | team-idle-handler.js (5s) | 그대로 이식 |
| 16 | **SessionEnd** | session-end-handler.js (1.5s) | 그대로 이식 |
| 17 | **PostToolUseFailure** | tool-failure-handler.js (5s) | 빌드 실패 분석 로직 추가 |
| 18 | **ConfigChange** | config-change-handler.js (3s) | 그대로 이식 |

**MCU 도메인 확장 스크립트** (신규):

| Script | 트리거 | 기능 |
|--------|--------|------|
| mcu-post-build.js | PostToolUse(Bash) - `make`/`cmake --build` 감지 | .map 파일 파싱 → Flash/RAM 리포트 |
| mcu-pre-flash.js | PreToolUse(Bash) - `st-flash`/`JLinkExe` 감지 | 바이너리 크기 검증, 올바른 타겟 확인 |
| mpu-dts-validate.js | PostToolUse(Write) - .dts/.dtsi 파일 감지 | `dtc` 컴파일 검증 |
| mpu-post-build.js | PostToolUse(Bash) - `bitbake`/`make` 감지 | 이미지 크기 리포트 |
| wpf-xaml-check.js | PostToolUse(Write) - .xaml 파일 감지 | 바인딩 경로 검증, 리소스 참조 확인 |
| wpf-post-build.js | PostToolUse(Bash) - `dotnet build`/`msbuild` 감지 | 경고/에러 분석 |

### 10.5 Startup Flow 상세 (session-start.js)

bkit의 9단계 초기화 흐름을 이식하되, **4번째에 도메인 감지**를 삽입합니다:

```
mcukit SessionStart Flow:
  1. migration.js       - 레거시 경로 마이그레이션
  2. restore.js         - PLUGIN_DATA 백업 복원
  3. context-init.js    - Context Hierarchy 초기화, .mcukit/ 디렉토리 생성
  4. domain-detect.js   - ★ 프로젝트 도메인 자동 감지 (MCU/MPU/WPF)
  5. onboarding.js      - 온보딩 메시지, 환경변수, 트리거 테이블
  6. session-context.js  - additionalContext 문자열 빌드
  7. progress-bar       - PDCA 진행률 표시줄
  8. workflow-map       - PDCA 단계 시각화
  9. control-panel      - 자동화 레벨 표시
  10. stale-detect      - 오래된 Feature 경고
```

### 10.6 MCP 서버 매핑

#### mcukit-pdca-server (bkit-pdca-server 이식 + 확장)

| 도구 | bkit 원본 | mcukit 변경 |
|------|-----------|-------------|
| mcukit_pdca_status | bkit_pdca_status | 이름만 변경 |
| mcukit_pdca_history | bkit_pdca_history | 이름만 변경 |
| mcukit_feature_list | bkit_feature_list | 이름만 변경 |
| mcukit_feature_detail | bkit_feature_detail | 도메인 필드 추가 |
| mcukit_plan_read | bkit_plan_read | 이름만 변경 |
| mcukit_design_read | bkit_design_read | 이름만 변경 |
| mcukit_analysis_read | bkit_analysis_read | 이름만 변경 |
| mcukit_report_read | bkit_report_read | 이름만 변경 |
| mcukit_metrics_get | bkit_metrics_get | 도메인별 메트릭 추가 |
| mcukit_metrics_history | bkit_metrics_history | 이름만 변경 |

#### mcukit-analysis-server (bkit-analysis-server 이식 + 확장)

| 도구 | bkit 원본 | mcukit 변경 |
|------|-----------|-------------|
| mcukit_code_quality | bkit_code_quality | MISRA/DTS/C# 분석 추가 |
| mcukit_gap_analysis | bkit_gap_analysis | 도메인별 갭 항목 |
| mcukit_regression_rules | bkit_regression_rules | 이름만 변경 |
| mcukit_checkpoint_list | bkit_checkpoint_list | 이름만 변경 |
| mcukit_checkpoint_detail | bkit_checkpoint_detail | 이름만 변경 |
| mcukit_audit_search | bkit_audit_search | 이름만 변경 |
| **mcukit_memory_report** | ★ 신규 | Flash/RAM 사용량 시계열 |
| **mcukit_domain_info** | ★ 신규 | 감지된 도메인/플랫폼 정보 |

### 10.7 템플릿 매핑 (bkit → mcukit)

#### 공통 PDCA 템플릿 (이식 + 도메인 섹션 추가)

| 템플릿 | 변경 | 추가 섹션 |
|--------|------|-----------|
| plan.template.md | Architecture 섹션 MCU/MPU/WPF 선택지로 변경 | HW 사양 요약, 메모리 예산 |
| design.template.md | Clean Architecture → 도메인별 레이어 구조 | MCU: 인터럽트 맵, 핀 할당. MPU: DTS 설계. WPF: MVVM 다이어그램 |
| analysis.template.md | 코드 품질 → 도메인별 검증 항목 | MCU: 메모리 사용률, MISRA. MPU: 이미지 크기. WPF: 바인딩 에러 |
| report.template.md | Quality Metrics → 도메인별 메트릭 | 빌드 메트릭 (Flash/RAM/이미지/바인딩) |
| do.template.md | 구현 순서 → 도메인별 구현 가이드 | MCU: BSP→Driver→App. MPU: 커널→RFS→App. WPF: Model→VM→View |

#### Phase 파이프라인 템플릿 (완전 재작성)

bkit의 9-Phase 웹 파이프라인을 MCU/MPU/WPF 파이프라인으로 재설계:

| Phase | bkit (Web) | mcukit (Embedded/Desktop) |
|-------|-----------|--------------------------|
| 1 | 용어/스키마 | **사양 정의** - HW 사양, DTS 구조, UI 화면 목록 |
| 2 | 코딩 규칙 | **컨벤션** - MISRA C, 커널 코딩 스타일, C# 규칙 |
| 3 | 목업 | **아키텍처** - FW 레이어, BSP 구조, MVVM 구조 |
| 4 | API 설계 | **기반 구현** - BSP 초기화, 커널 설정, 프로젝트 셋업 |
| 5 | 디자인 시스템 | **핵심 구현** - 드라이버, 커널 모듈, ViewModel |
| 6 | UI 통합 | **통합** - 페리페럴 통합, 앱↔커널, View↔VM |
| 7 | SEO/보안 | **테스트** - Unit, HIL, 커널 테스트, xUnit |
| 8 | 코드 리뷰 | **최적화** - 메모리, 부팅시간, 렌더링 |
| 9 | 배포 | **양산/배포** - 플래싱, 이미지, 설치 패키지 |

### 10.8 이름 변경 체크리스트 (bkit → mcukit)

| 범위 | bkit | mcukit |
|------|------|--------|
| 환경변수 | `BKIT_*` | `MCUKIT_*` |
| 상태 디렉토리 | `.bkit/` | `.mcukit/` |
| 설정 파일 | `bkit.config.json` | `mcukit.config.json` |
| 메모리 파일 | `.bkit/state/memory.json` | `.mcukit/state/memory.json` |
| 상태 파일 | `.bkit/state/pdca-status.json` | `.mcukit/state/pdca-status.json` |
| 캐시 키 | `bkit-config` | `mcukit-config` |
| 에러 코드 | `BKIT_PDCA_*`, `BKIT_STATE_*` | `MCUKIT_PDCA_*`, `MCUKIT_STATE_*` |
| 플러그인 이름 | `bkit` | `mcukit` |
| MCP 도구 접두사 | `bkit_*` | `mcukit_*` |
| Output Style 접두사 | `bkit-*` | `mcukit-*` |
| 디버그 로그 | `.bkit/debug/` | `.mcukit/debug/` |

### 10.9 lib/core/ 이식 상세 (93 exports)

| 모듈 | 파일 | exports | 변경 필요 |
|------|------|---------|-----------|
| Platform | platform.js | 9 | `BKIT_PLATFORM` → `MCUKIT_PLATFORM`, 경로 변수 |
| Config | config.js | 5 | `getBkitConfig` → `getMcukitConfig`, 파일명 |
| Paths | paths.js | 10+ | `.bkit/` → `.mcukit/`, STATE_PATHS 전체 |
| Constants | constants.js | 30+ | 접두사 변경 + MCU 상수 추가 |
| Errors | errors.js | 20+ | `BKIT_*` → `MCUKIT_*` |
| StateStore | state-store.js | 8 | 변경 없음 (도메인 독립) |
| Cache | cache.js | 10 | 변경 없음 |
| IO | io.js | 9 | 변경 없음 |
| Debug | debug.js | 3 | 로그 경로만 변경 |
| File | file.js | 8 | `TIER_EXTENSIONS` MCU/MPU/WPF 확장 (★) |
| HookIO | hook-io.js | - | 변경 없음 |

**file.js TIER_EXTENSIONS 확장**:
```javascript
// bkit 원본: 웹 중심
TIER_EXTENSIONS: {
  1: ['.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.java', '.kt'],
  3: ['.c', '.cpp', '.h', '.hpp', '.cs', '.m', '.mm'],
}

// mcukit 확장: 임베디드/데스크톱 중심
TIER_EXTENSIONS: {
  1: ['.c', '.h', '.cpp', '.hpp', '.cs'],           // MCU C, WPF C#
  2: ['.dts', '.dtsi', '.bb', '.bbappend', '.xaml'], // MPU DTS, Yocto, WPF XAML
  3: ['.ld', '.s', '.S', '.icf'],                    // 링커/스타트업
  4: ['.sh', '.bash', '.ps1', '.bat', '.cmd'],       // 스크립트
  mcu: ['.ioc', '.ld', '.s', '.S', '.cfg'],          // ★ MCU 전용
  mpu: ['.dts', '.dtsi', '.bb', '.bbappend', '.conf'], // ★ MPU 전용
  wpf: ['.xaml', '.csproj', '.sln', '.resx'],        // ★ WPF 전용
}
```

### 10.10 lib/pdca/ 이식 상세 (130+ exports)

| 모듈 | 변경 수준 | 상세 |
|------|-----------|------|
| state-machine.js | 없음 | 20 transitions 그대로 유지 |
| workflow-engine.js | 없음 | YAML DSL 엔진 그대로 |
| workflow-parser.js | 없음 | 파서 그대로 |
| **level.js** | **높음** | MCU/MPU/WPF 마커로 전면 재작성 (★) |
| **tier.js** | **높음** | 임베디드/데스크톱 언어 Tier 재정의 (★) |
| phase.js | 낮음 | PDCA_PHASES 아이콘/이름 유지 |
| status.js | 낮음 | 파일명 변경만 |
| automation.js | 없음 | L0~L4 그대로 |
| feature-manager.js | 없음 | 도메인 독립 |
| batch-orchestrator.js | 없음 | 도메인 독립 |
| executive-summary.js | 낮음 | 도메인별 메트릭 테이블 확장 |
| template-validator.js | 중간 | MCU/MPU/WPF 필수 섹션 추가 |
| lifecycle.js | 없음 | stale 감지 그대로 |
| resume.js | 없음 | 세션 재개 그대로 |

**level.js 재작성 핵심**:
```javascript
// bkit: 웹 프로젝트 마커
// Enterprise: kubernetes, k8s, terraform, docker-compose.yml
// Dynamic: package.json, requirements.txt, go.mod
// Starter: 기본값

// mcukit: 도메인 + 레벨 감지
const DOMAIN_MARKERS = {
  mcu: ['*.ioc', '*.ld', 'startup_*.s', 'board.h', 'fsl_*.h', 'stm32*.h'],
  mpu: ['*.dts', '*.dtsi', 'local.conf', 'bblayers.conf', '*.bb'],
  wpf: ['*.csproj+<UseWPF>true', 'App.xaml', '*.sln']  // MainWindow.xaml 제거 (감지 부적합)
};

const LEVEL_MARKERS = {
  mcu: {
    L1_Basic: ['main.c'],          // 단순 bare-metal
    L2_Standard: ['FreeRTOS*', 'cmsis_os*', 'tasks.c'], // RTOS 사용
    L3_Advanced: ['*_core0*', '*_core1*', 'safety*']     // 멀티코어/안전
  },
  mpu: {
    L1_Basic: ['buildroot*', 'defconfig'],
    L2_Standard: ['local.conf', 'bblayers.conf'],  // Yocto 커스텀
    L3_Advanced: ['*gpu*', '*multimedia*', '*ota*']  // GPU/멀티미디어/OTA
  },
  wpf: {
    L1_Basic: ['App.xaml'],                 // 단일 윈도우 (최소 구조)
    L2_Standard: ['*ViewModel*', '*Service*', 'App.xaml.cs'],  // MVVM + DI
    L3_Advanced: ['*Plugin*', '*Module*', 'Shell*']            // Plugin/Prism
  }
};
```

### 10.11 Evals (스킬 품질 평가) 체계

bkit의 Eval 프레임워크를 이식하여 mcukit 스킬 품질을 측정합니다:

```
evals/
├── config.json                    # 평가 설정 (threshold, 분류)
├── runner.js                      # 평가 실행 엔진 (bkit 이식)
├── reporter.js                    # 결과 보고서 (bkit 이식)
├── ab-tester.js                   # A/B + Parity 테스트 (bkit 이식)
│
├── workflow/                      # Workflow 스킬 평가
│   ├── pdca/eval.yaml
│   └── mcukit-rules/eval.yaml
│
├── capability/                    # Capability 스킬 평가
│   ├── stm32-hal/
│   │   ├── eval.yaml
│   │   ├── prompt-1.md            # "UART DMA 드라이버 작성"
│   │   └── expected-1.md          # HAL_UART_Transmit_DMA 패턴
│   ├── imx-bsp/
│   │   ├── eval.yaml
│   │   ├── prompt-1.md            # "i.MX6ULL GPIO Device Tree 추가"
│   │   └── expected-1.md          # pinctrl + gpio-leds 노드
│   ├── wpf-mvvm/
│   │   ├── eval.yaml
│   │   ├── prompt-1.md            # "RelayCommand으로 ViewModel 작성"
│   │   └── expected-1.md          # ObservableObject + RelayCommand
│   └── ...
```

**Parity Test 의미**:
- Capability 스킬은 모델 진화에 따라 불필요해질 수 있음
- Parity Test: 스킬 있을 때 vs 없을 때 출력 품질 비교
- 점수 차이 < 0.85(85%) → 스킬 deprecation 후보

### 10.12 Output Styles (응답 포맷)

```
output-styles/
├── mcukit-learning.md             # 입문자용 (설명 상세)
├── mcukit-pdca-guide.md           # PDCA 워크플로우 가이드 (표준)
├── mcukit-embedded.md             # 임베디드 전문가용 (간결, 레지스터 수준)
└── mcukit-pdca-embedded.md        # PDCA + 임베디드 전문가 (고급)
```

### 10.13 Context Hierarchy (4-Level 설정 우선순위)

bkit의 4-level 설정 계층을 그대로 이식:

```
Priority 1 (최저): Plugin Level  - mcukit.config.json (플러그인 기본값)
Priority 2:       User Level    - ~/.claude/mcukit/user-config.json
Priority 3:       Project Level - PROJECT_DIR/mcukit.config.json
Priority 4 (최고): Session Level - 메모리 기반 (런타임 오버라이드)
```

### 10.14 Destructive Operation Detection (MCU/MPU 확장)

bkit의 destructive-detector.js에 MCU/MPU 위험 명령을 추가:

```javascript
const MCU_DANGEROUS_PATTERNS = [
  { pattern: 'st-flash erase',                reason: 'STM32 전체 Flash 소거 (st-link)' },
  { pattern: 'st-flash --reset',              reason: 'STM32 리셋 동반 플래시' },
  { pattern: 'STM32_Programmer_CLI.*-e all',   reason: 'CubeProgrammer 전체 소거' },
  { pattern: 'JLinkExe.*erase',               reason: 'J-Link 전체 Flash 소거 (Linux/macOS)' },
  { pattern: 'JLink.exe.*erase',              reason: 'J-Link 전체 Flash 소거 (Windows)' },
  { pattern: 'openocd.*flash erase',          reason: 'OpenOCD Flash 소거' },
  { pattern: 'openocd.*mass_erase',           reason: 'OpenOCD 대량 소거' },
  { pattern: 'nand erase',                    reason: 'NAND 전체 소거' },
];

const MPU_DANGEROUS_PATTERNS = [
  { pattern: 'dd if=.*of=/dev/sd',   reason: 'SD 카드 직접 쓰기' },
  { pattern: 'dd if=.*of=/dev/mmc',  reason: 'eMMC 직접 쓰기' },
  { pattern: 'mkfs\\.',              reason: '파일시스템 포맷' },
  { pattern: 'rm -rf /rootfs',       reason: '루트파일시스템 삭제' },
  { pattern: 'flashcp.*mtd',         reason: 'MTD 파티션 덮어쓰기' },
];

const WPF_DANGEROUS_PATTERNS = [
  { pattern: 'dotnet publish.*--self-contained', reason: '자체 포함 배포 (크기 주의)' },
];
```

---

## 11. mcukit.config.json 설계

```json
{
  "$schema": "./mcukit.config.schema.json",
  "version": "0.1.0",

  "domain": {
    "autoDetect": true,
    "override": null,
    "lazyLoadSkills": true
  },

  "pdca": {
    "docPaths": {
      "plan": ["docs/01-plan/features/{feature}.plan.md"],
      "design": ["docs/02-design/features/{feature}.design.md"],
      "analysis": ["docs/03-analysis/{feature}.analysis.md"],
      "report": ["docs/04-report/features/{feature}.report.md"],
      "archive": "docs/archive/{date}/{feature}"
    },
    "matchRateThreshold": 90,
    "autoIterate": true,
    "maxIterations": 5,
    "requireDesignDoc": true,
    "automationLevel": "semi-auto"
  },

  "mcu": {
    "platforms": ["stm32", "nxp-k"],
    "toolchain": "arm-none-eabi-gcc",
    "flashTool": "auto",
    "memoryBudget": {
      "flashWarningPercent": 85,
      "ramWarningPercent": 75,
      "stackMarginPercent": 20
    },
    "misra": {
      "enabled": true,
      "tool": "cppcheck",
      "requiredViolations": 0,
      "advisoryMax": 10
    }
  },

  "mpu": {
    "platforms": ["imx6", "imx6ull", "imx28"],
    "buildSystem": "yocto",
    "crossCompiler": "auto",
    "imageLimits": {
      "rootfsMaxMB": 256,
      "kernelMaxKB": 8192,
      "bootTimeMaxSeconds": 10
    }
  },

  "wpf": {
    "framework": "net8.0",
    "mvvmToolkit": "CommunityToolkit.Mvvm",
    "buildTool": "dotnet",
    "qualityChecks": {
      "bindingErrors": 0,
      "buildWarnings": 0,
      "nullability": true,
      "codeAnalysis": "recommended"
    }
  },

  "featurePatterns": [
    "drivers", "peripherals", "hal", "modules",
    "kernel", "recipes", "layers",
    "ViewModels", "Views", "Services", "Models"
  ],

  "fileDetection": {
    "sourceExtensions": [".c", ".h", ".cpp", ".hpp", ".cs", ".xaml", ".dts", ".dtsi"],
    "excludePatterns": [
      ".git", "build", "output", "bin", "obj",
      "tmp", "deploy", "sysroots"
    ]
  },

  "permissions": {
    "Write": "allow",
    "Edit": "allow",
    "Read": "allow",
    "Bash": "allow",
    "Bash(rm -rf*)": "deny",
    "Bash(st-flash erase*)": "ask",
    "Bash(dd if=*)": "ask",
    "Bash(mkfs*)": "ask",
    "Bash(git push --force*)": "deny"
  },

  "automation": {
    "defaultLevel": 2,
    "trustScoreEnabled": true,
    "maxConcurrentFeatures": 3,
    "emergencyStopEnabled": true
  },

  "guardrails": {
    "destructiveDetection": true,
    "loopBreaker": {
      "maxPdcaIterations": 5,
      "maxSameFileEdits": 10,
      "cooldownMs": 60000
    },
    "checkpointOnPhaseTransition": true
  },

  "quality": {
    "gateEnabled": true,
    "metricsCollection": true,
    "regressionGuard": true,
    "thresholds": {
      "matchRate": 90,
      "codeQualityScore": 70,
      "conventionCompliance": 90
    }
  },

  "team": {
    "enabled": true,
    "maxTeammates": 5,
    "ctoAgent": "cto-lead",
    "orchestrationPatterns": {
      "L2_Standard": {
        "plan": "leader", "design": "leader",
        "do": "swarm", "check": "council", "act": "leader"
      },
      "L3_Advanced": {
        "plan": "leader", "design": "council",
        "do": "swarm", "check": "council", "act": "watchdog"
      }
    }
  }
}
```

---

## 12. Next Steps

1. [ ] `/pdca design mcukit-core` - Phase 1 코어 이식 상세 설계서 작성
2. [ ] plugin.json 매니페스트 생성
3. [ ] bkit lib/core/ 복사 + BKIT→MCUKIT 이름 변경 스크립트 작성
4. [ ] lib/domain/detector.js 도메인 감지 모듈 구현
5. [ ] mcukit.config.json 설정 파일 생성
6. [ ] 첫 번째 MCU Skill (stm32-hal) SKILL.md 작성

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-22 | 초기 기획 (MCU only) | Rootech |
| 0.2 | 2026-03-22 | WPF, i.MX6/i.MX6ULL/i.MX28 추가, 3-Domain 아키텍처 재설계 | Rootech |
| 0.3 | 2026-03-22 | bkit 심층 리서치 결과 반영: Skill/Agent frontmatter, Hook 18이벤트 매핑, MCP서버 16도구, 템플릿 매핑, Evals 체계, 이름변경 체크리스트, config.json 설계, destructive detection 확장 | Rootech |
| 0.4 | 2026-03-22 | 3-Domain 기술 검증 반영: sdk_config.h→fsl_device_registers.h(C1), i.MX28 soft float(C2), x:Bind UWP전용(C3), .ioc=Java Properties(H1), STM32_Programmer_CLI(H2), meta-imx/meta-freescale 구분(H3), MainWindow.xaml 감지 제거(H6), Prism 9 상용화(H8), SerialPort NuGet(H9) | Rootech |
