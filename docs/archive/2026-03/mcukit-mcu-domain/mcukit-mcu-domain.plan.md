# mcukit-mcu-domain Planning Document

> **Summary**: STM32/NXP K MCU 도메인 심화 - 툴체인 탐지, 메모리 분석, 핀/클럭 검증, MCU Skills/Agents 구현
>
> **Project**: mcukit
> **Version**: 0.2.0
> **Author**: Rootech
> **Date**: 2026-03-22
> **Status**: Draft
> **Prerequisite**: mcukit-core MVP-1 완료 (Match Rate 98.6%)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | MVP-1에서 PDCA 코어와 도메인 감지는 완성했으나, MCU 빌드 후 메모리 분석, .ioc 핀 충돌 검출, 클럭 검증, STM32 HAL 가이드 등 MCU 도메인 실질 기능이 없음 |
| **Solution** | lib/mcu/ 4개 모듈(toolchain, memory-analyzer, pin-config, clock-tree) + MCU Skills 6개 + Agent 3개 + Hook 스크립트 2개 + 템플릿 3개 + refs 데이터 |
| **Function/UX Effect** | `make` 실행 후 자동으로 Flash/RAM 사용량 대시보드가 출력되고, `.ioc` 수정 시 핀 충돌이 즉시 경고되며, `/pdca plan`에 MCU HW 스펙 섹션이 자동 포함됨 |
| **Core Value** | "MCU 개발자의 빌드-분석-검증 루프를 AI가 자동화" - 20년차 임베디드 엔지니어의 코드 리뷰 품질을 매 빌드마다 제공 |

---

## 1. Overview

### 1.1 Purpose

MVP-1에서 구축한 mcukit PDCA 코어(141파일) 위에 **MCU 도메인 심화 기능**을 구현합니다. STM32와 NXP Kinetis K 플랫폼을 대상으로, 빌드 결과 자동 분석, 핀 할당 검증, 클럭 트리 검증, HAL/SDK 코딩 가이드를 제공합니다.

### 1.2 Background

MVP-1 완료 상태:

```
mcukit v0.1.0 (MVP-1)
├── PDCA 코어 엔진 (18 모듈)     ✅
├── 도메인 감지/라우팅 (4 모듈)   ✅
├── Hook 시스템 (60 스크립트)     ✅
├── lib/mcu/ (1 파일만)           ⚠️ build-history.js만 존재
├── MCU Skills                    ❌ 없음
├── MCU Agents                    ❌ 없음
├── MCU Hook Scripts              ❌ 없음
└── MCU Templates/Refs            ❌ 없음
```

### 1.3 Related Documents

- MVP-1 완료 보고서: `docs/04-report/features/mcukit-core.report.md`
- 원본 설계서 (MCU 모듈): `docs/02-design/features/mcukit-core.design.md` Section 3.2
- 도메인 기술 검증: `docs/03-analysis/mcukit-core-domain-verification.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] lib/mcu/ 4개 모듈 (toolchain, memory-analyzer, pin-config, clock-tree)
- [ ] MCU Skills 6개 (stm32-hal, nxp-mcuxpresso, cmake-embedded, communication, freertos, misra-c)
- [ ] MCU Agents 3개 (fw-architect, hw-interface-expert, safety-auditor)
- [ ] Hook 스크립트 2개 (mcu-post-build, mcu-pre-flash)
- [ ] 문서 템플릿 3개 (mcu-hw-spec, mcu-memory-budget, mcu-driver-spec)
- [ ] 레퍼런스 데이터 (refs/stm32/, refs/nxp-k/)

### 2.2 Out of Scope

- MPU 도메인 (lib/mpu/, i.MX Skills) → MVP-3
- WPF 도메인 (lib/wpf/, WPF Skills) → MVP-4
- MCU 에뮬레이션 (QEMU 연동)
- MCU 부트로더/OTA 스킬 (추후)
- 인터럽트 설계/저전력 스킬 (추후)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | ARM 크로스 컴파일러 자동 탐지 (arm-none-eabi-gcc, PATH/기본 경로 탐색) | High |
| FR-02 | 빌드 시스템 자동 탐지 (CMake, Makefile, Keil, IAR) | High |
| FR-03 | GCC ARM .map 파일 파싱 → Flash/RAM 사용량 추출 | High |
| FR-04 | arm-none-eabi-size 출력 파싱 (text/data/bss) | High |
| FR-05 | 빌드 간 메모리 사용량 비교 (delta 표시) | Medium |
| FR-06 | 메모리 예산 대비 검증 (config 임계값 기반) | Medium |
| FR-07 | CLI 대시보드용 메모리 리포트 (ANSI 색상 프로그레스바) | High |
| FR-08 | CubeMX .ioc 파일 핀 할당 파싱 (Java Properties 형식) | High |
| FR-09 | 핀 멀티플렉싱 충돌 자동 검출 | High |
| FR-10 | .ioc 파일 클럭 트리 설정 파싱 (RCC.* 키) | Medium |
| FR-11 | 페리페럴 클럭 요구사항 vs 실제 설정 검증 | Medium |
| FR-12 | STM32 HAL/LL API 코딩 가이드 스킬 | High |
| FR-13 | NXP MCUXpresso SDK 코딩 가이드 스킬 | High |
| FR-14 | 임베디드 CMake 빌드 시스템 스킬 | High |
| FR-15 | UART/SPI/I2C/CAN 통신 드라이버 패턴 스킬 | Medium |
| FR-16 | FreeRTOS 태스크/동기화 설계 스킬 | Medium |
| FR-17 | MISRA C:2012 코딩 표준 가이드 스킬 | Medium |
| FR-18 | 빌드 후 .map 자동 분석 Hook (PostToolUse Bash) | High |
| FR-19 | 플래싱 전 안전 검사 Hook (PreToolUse Bash) | Medium |
| FR-20 | fw-architect 에이전트 (FW 아키텍처 설계) | High |
| FR-21 | hw-interface-expert 에이전트 (페리페럴 설정) | Medium |
| FR-22 | safety-auditor 에이전트 (MISRA 검증) | Medium |
| FR-23 | MCU HW 스펙 문서 템플릿 | High |
| FR-24 | 메모리 예산 문서 템플릿 | Medium |
| FR-25 | 드라이버 스펙 문서 템플릿 | Medium |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 성능 | .map 파일 파싱 < 1초 (10MB 맵 파일 기준) |
| 정확도 | .ioc 핀 파싱 정확도 100% (CubeMX 6.x 생성 파일 기준) |
| 정확도 | Flash/RAM 계산 오차 < 1% (arm-none-eabi-size 대비) |
| 호환성 | GCC ARM 10.x ~ 13.x .map 포맷 지원 |

---

## 4. Key Technical Details (검증 완료)

> 이 섹션의 정보는 MVP-1 기술 검증에서 확인됨 (docs/03-analysis/mcukit-core-domain-verification.md)

### 4.1 .ioc 파일 포맷 (Java Properties)

```
# CubeMX .ioc 파일 구조 (flat key=value)
Mcu.UserName=STM32F407VGTx
Mcu.Pin0=PA9
Mcu.Pin1=PA10
Mcu.PinsNb=2
PA9.Signal=USART1_TX
PA9.Mode=Asynchronous
PA9.GPIO_Label=DEBUG_TX
PA10.Signal=USART1_RX
PA10.Mode=Asynchronous
RCC.HSEState=RCC_HSE_ON
RCC.PLLSource=RCC_PLLSOURCE_HSE
RCC.PLLM=8
RCC.PLLN=336
RCC.PLLP=RCC_PLLP_DIV2
RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK
RCC.AHBCLKDivider=RCC_SYSCLK_DIV1
RCC.APB1CLKDivider=RCC_HCLK_DIV4
RCC.APB2CLKDivider=RCC_HCLK_DIV2
```

### 4.2 GCC ARM .map 파일 구조

```
주요 섹션:
- "Memory Configuration" → FLASH, RAM 영역 정의 (origin, length)
- "Linker script and memory map" → .text, .data, .bss, .rodata 배치

Flash 사용량 = .text + .rodata + .data (초기값)
RAM 사용량 = .data + .bss (+ heap/stack)
```

### 4.3 arm-none-eabi-size 출력

```
   text    data     bss     dec     hex filename
  12345     678     234   13257    33C9 firmware.elf

Flash = text + data
RAM   = data + bss
```

### 4.4 NXP MCUXpresso SDK 구조

```
/board/    - board.c/h, pin_mux.c/h, clock_config.c/h
/source/   - main.c, 애플리케이션 코드
/drivers/  - fsl_*.c/h (SDK 드라이버)
/CMSIS/    - CMSIS Core 헤더
/device/   - 디바이스별 시스템 파일, 스타트업 코드

주의: sdk_config.h는 Nordic nRF → NXP는 fsl_device_registers.h 사용
```

### 4.5 디버거/플래시 도구

| 도구 | 명령 예시 | 플랫폼 |
|------|----------|--------|
| st-flash | `st-flash write firmware.bin 0x08000000` | Linux/macOS |
| STM32_Programmer_CLI | `STM32_Programmer_CLI -c port=SWD -w firmware.bin 0x08000000` | 전체 |
| JLinkExe / JLink.exe | `JLinkExe -CommandFile flash.jlink` | Linux / Windows |
| OpenOCD | `openocd -f interface/stlink.cfg -f target/stm32f4x.cfg` | 전체 |

---

## 5. Implementation Phases

### Phase A: lib/mcu/ 핵심 모듈 (4 파일)

| 파일 | 기능 | 의존성 |
|------|------|--------|
| toolchain.js | ARM 툴체인/빌드 시스템 탐지 | lib/core/config |
| memory-analyzer.js | .map 파싱, size 출력 파싱, 메모리 리포트 | lib/core/io, lib/mcu/build-history |
| pin-config.js | .ioc 핀 파싱, 충돌 검출 | lib/core/debug |
| clock-tree.js | .ioc 클럭 파싱, 요구사항 검증 | lib/core/debug |

### Phase B: MCU Skills (6 파일)

| Skill | 분류 | 핵심 내용 |
|-------|------|-----------|
| stm32-hal/ | capability | HAL_Init, HAL_UART, HAL_SPI 등 패턴, CubeMX 코드 생성 후 수정 가이드 |
| nxp-mcuxpresso/ | capability | fsl_* 드라이버 패턴, board.h/pin_mux.h 구조 |
| cmake-embedded/ | capability | arm-none-eabi 툴체인 파일, 링커 스크립트 연동, 빌드 타겟 |
| communication/ | capability | UART DMA, SPI 풀듀플렉스, I2C 마스터/슬레이브, CAN 필터 패턴 |
| freertos/ | capability | xTaskCreate, xQueueSend, xSemaphoreTake, vTaskDelay, 스택 사이징 |
| misra-c/ | workflow | 필수(Required)/권고(Advisory)/문서화(Documented) 규칙 분류, cppcheck 연동 |

### Phase C: MCU Agents (3 파일)

| Agent | 모델 | 역할 |
|-------|------|------|
| fw-architect.md | opus | FW 레이어 구조, 인터럽트 맵, 메모리 레이아웃, RTOS 태스크 설계 |
| hw-interface-expert.md | sonnet | GPIO/SPI/I2C/UART/CAN/ADC/DMA 페리페럴 설정 |
| safety-auditor.md | opus | MISRA C:2012 준수 검증, 스택 오버플로 위험 분석 |

### Phase D: Hooks + Templates + Refs (8+ 파일)

| 파일 | 유형 | 기능 |
|------|------|------|
| scripts/mcu-post-build.js | Hook | `make`/`cmake --build` 감지 → .map 파싱 → 메모리 리포트 |
| scripts/mcu-pre-flash.js | Hook | `st-flash`/`JLinkExe` 감지 → 바이너리 크기/타겟 검증 |
| templates/mcu-hw-spec.template.md | Template | MCU 선정, 핀맵, 클럭 트리, 페리페럴 할당 |
| templates/mcu-memory-budget.template.md | Template | Flash/RAM 예산 할당 (부트로더/앱/예비) |
| templates/mcu-driver-spec.template.md | Template | 드라이버 인터페이스, 초기화 순서, 에러 처리 |
| refs/stm32/hal-patterns.md | Reference | STM32 HAL 코드 패턴/베스트 프랙티스 |
| refs/stm32/peripheral-map.md | Reference | 주요 칩별 페리페럴 매핑 |
| refs/nxp-k/sdk-patterns.md | Reference | MCUXpresso SDK 코드 패턴 |

---

## 6. Success Criteria

### 6.1 Definition of Done

- [ ] STM32 프로젝트에서 `make` 실행 후 자동 메모리 리포트 출력
- [ ] .ioc 파일 핀 충돌 검출 동작 확인
- [ ] `/pdca plan` 실행 시 MCU HW 스펙 섹션 자동 포함
- [ ] fw-architect 에이전트가 FW 아키텍처 설계 수행 가능
- [ ] misra-c 스킬이 MISRA C 규칙 가이드 제공
- [ ] Gap Analysis 90% 이상

### 6.2 Test Scenario

```
test-projects/stm32-blink/
├── Core/
│   ├── Src/main.c
│   ├── Startup/startup_stm32f407xx.s
│   └── Inc/main.h
├── STM32F407VGTx.ioc
├── STM32F407VGTx_FLASH.ld
├── CMakeLists.txt
├── build/
│   ├── firmware.elf
│   └── firmware.map
└── Makefile
```

---

## 7. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| .map 파일 포맷이 GCC 버전마다 다를 수 있음 | Medium | GCC 10.x~13.x 샘플로 파서 검증, 정규식 유연하게 |
| .ioc 파일이 CubeMX 버전에 따라 키 이름 변동 | Medium | CubeMX 6.x 기준, 버전별 차이는 fallback 처리 |
| refs/ 데이터가 너무 크면 플러그인 로드 지연 | Low | lazy loading + 필요한 칩 데이터만 참조 |

---

## 8. Next Steps

1. [ ] `/pdca design mcukit-mcu-domain` - 상세 설계서
2. [ ] lib/mcu/ 4개 모듈 구현
3. [ ] MCU Skills 6개 SKILL.md 작성
4. [ ] MCU Agents 3개 작성
5. [ ] Hook 스크립트 + 템플릿 + refs 데이터

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-22 | 초기 기획 | Rootech |
