# Plan: eval-full-coverage

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 벤치마크 29개 스킬 중 9개만 통과(31%), mcukit 도메인 eval 11개는 placeholder 수준이며 config에 미등록, bkit 공통 웹 스킬이 mcukit과 무관하게 포함되어 있다 |
| **Solution** | config.json을 mcukit 도메인 전용으로 재구성하고, 기존 placeholder eval 업그레이드 + 누락 eval 신규 작성으로 벤치마크 통과율 100% 달성 |
| **Function UX Effect** | `node evals/runner.js --benchmark` 실행 시 mcukit 관련 전체 스킬이 통과하여 도메인 특화 품질 기준선 확보 |
| **Core Value** | mcukit 임베디드 개발 도메인에 집중된 자동화 품질 검증 체계 완성 |

## 1. 배경 및 목표

### 1.1 현황 (벤치마크 결과 2026-04-03)

| 분류 | 통과 | 전체 | 통과율 |
|------|------|------|--------|
| Workflow | 8 | 10 | 80% |
| Capability | 0 | 18 | 0% |
| Hybrid | 1 | 1 | 100% |
| **합계** | **9** | **29** | **31%** |

### 1.2 문제 분류

| 유형 | 스킬 | 원인 |
|------|------|------|
| **Workflow eval 누락** | `zero-script-qa`, `cc-version-analysis` | eval 파일 미작성 |
| **Capability: bkit 공통 (제거 대상)** | `starter`, `dynamic`, `enterprise`, `mobile-app`, `claude-code-learning`, `bkend-quickstart`, `bkend-auth`, `bkend-data`, `bkend-cookbook`, `bkend-storage` | mcukit 도메인과 무관한 웹 개발 스킬 |
| **Capability: mcukit 관련 eval 누락** | `phase-1-schema`, `phase-3-mockup`, `phase-4-api`, `phase-5-design-system`, `phase-6-ui-integration`, `phase-7-seo-security`, `phase-9-deployment`, `desktop-app` | eval 파일 미작성 (mcukit 도메인 적용 필요) |
| **Config 미등록 (placeholder)** | `stm32-hal`, `freertos`, `wpf-mvvm`, `imx-bsp`, `kernel-driver`, `nxp-mcuxpresso`, `serial-bridge`, `cmake-embedded`, `communication`, `xaml-design`, `yocto-build`, `misra-c` | eval 파일 존재하나 단일 라인 placeholder + config 미등록 |

### 1.3 목표

- **벤치마크 통과율 100%** (현재 31% → 100%)
- config.json에서 bkit 공통 웹 스킬 제거, mcukit 도메인 스킬로 재구성
- 기존 placeholder eval 12개 업그레이드 (substantive content)
- 신규 eval 10개 작성 (workflow 2 + capability 8)
- 모든 eval은 mcukit 도메인(MCU/MPU/Desktop) 관점 적용
- 향후 Qt/QML 도메인 추가에 대비한 확장 가능 구조

## 2. mcukit 도메인 정의

### 2.1 현재 지원 도메인

| 도메인 | 플랫폼 | 대표 스킬 |
|--------|--------|----------|
| **MCU** | STM32, NXP Kinetis K | stm32-hal, freertos, nxp-mcuxpresso, communication |
| **MPU** | i.MX6, i.MX6ULL, i.MX28 | imx-bsp, kernel-driver, yocto-build |
| **Desktop** | WPF (.NET 8), WinUI3 | wpf-mvvm, xaml-design, desktop-app |
| **Cross** | MCU↔Desktop 연동 | serial-bridge, cmake-embedded |

### 2.2 향후 확장 예정 도메인

| 도메인 | 플랫폼 | 예상 스킬 | 비고 |
|--------|--------|----------|------|
| **Qt** | Qt 6 / QML | qt-widgets, qml-design, qt-serial | 향후 추가 시 capability에 등록 |

### 2.3 Desktop 도메인 범위 재정의

기존 `desktop-app` 스킬은 Electron/Tauri 웹 기반이었으나, mcukit에서는 **C# 기반 Windows 데스크탑 앱**으로 재정의:

| 프레임워크 | 대상 | 비고 |
|-----------|------|------|
| **WPF** (.NET 8) | 현재 주력 | MVVM, XAML, CommunityToolkit |
| **WinUI3** (.NET 8) | 차세대 | Windows App SDK, XAML Islands |
| ~~Electron~~ | 제외 | 웹 기반, mcukit 도메인 외 |
| ~~Tauri~~ | 제외 | 웹 기반, mcukit 도메인 외 |
| **Qt** (향후) | 확장 예정 | C++/QML 기반, 크로스 플랫폼 |

## 3. 작업 범위

### 3.1 config.json 재구성

**제거 (bkit 공통 웹 스킬 10개):**
- `starter`, `dynamic`, `enterprise`, `mobile-app`, `claude-code-learning`
- `bkend-quickstart`, `bkend-auth`, `bkend-data`, `bkend-cookbook`, `bkend-storage`

**추가 (mcukit 도메인 스킬 12개):**
- MCU: `stm32-hal`, `freertos`, `nxp-mcuxpresso`
- MPU: `imx-bsp`, `kernel-driver`, `yocto-build`
- Desktop: `wpf-mvvm`, `xaml-design`
- Cross: `cmake-embedded`, `communication`, `serial-bridge`
- Safety: `misra-c` (workflow로 이동)

**변경 후 구성:**

| 분류 | 스킬 수 | 스킬 목록 |
|------|---------|----------|
| **Workflow** | 11 | mcukit-rules, mcukit-templates, pdca, development-pipeline, phase-2-convention, phase-8-review, zero-script-qa, code-review, pm-discovery, cc-version-analysis, misra-c |
| **Capability** | 19 | phase-1-schema, phase-3-mockup, phase-4-api, phase-5-design-system, phase-6-ui-integration, phase-7-seo-security, phase-9-deployment, desktop-app, stm32-hal, freertos, nxp-mcuxpresso, imx-bsp, kernel-driver, yocto-build, wpf-mvvm, xaml-design, cmake-embedded, communication, serial-bridge |
| **Hybrid** | 1 | plan-plus |
| **합계** | **31** | |

### 3.2 기존 eval 업그레이드 (12개)

단일 라인 placeholder → 멀티라인 substantive content:

| 스킬 | 도메인 | 현재 상태 | 목표 |
|------|--------|----------|------|
| `stm32-hal` | MCU | 1줄 placeholder | 5줄+ prompt, 10줄+ expected |
| `freertos` | MCU | 1줄 placeholder | 동일 |
| `nxp-mcuxpresso` | MCU | 1줄 placeholder | 동일 |
| `imx-bsp` | MPU | 1줄 placeholder | 동일 |
| `kernel-driver` | MPU | 1줄 placeholder | 동일 |
| `yocto-build` | MPU | 1줄 placeholder | 동일 |
| `wpf-mvvm` | Desktop | 1줄 placeholder | 동일 |
| `xaml-design` | Desktop | 1줄 placeholder | 동일 |
| `cmake-embedded` | Cross | 1줄 placeholder | 동일 |
| `communication` | Cross | 1줄 placeholder | 동일 |
| `serial-bridge` | Cross | 1줄 placeholder | 동일 |
| `misra-c` | Safety | 1줄 placeholder | 동일 |

### 3.3 Workflow eval 신규 작성 (2개)

| 스킬 | prompt 시나리오 |
|------|----------------|
| `zero-script-qa` | MCU UART 통신 펌웨어의 Docker 로그 기반 QA 테스트 |
| `cc-version-analysis` | CC 버전 업그레이드 시 mcukit 영향 분석 |

### 3.4 Capability eval 신규 작성 (8개, mcukit 도메인 적용)

| 스킬 | mcukit 도메인 적용 | prompt 시나리오 |
|------|-------------------|----------------|
| `phase-1-schema` | 임베디드 데이터 구조 | MCU 레지스터 맵 + UART 프레임 프로토콜 스키마 정의 |
| `phase-3-mockup` | Desktop 모니터링 UI | MCU 센서 데이터 실시간 모니터링 WPF/WinUI3 대시보드 목업 |
| `phase-4-api` | 시리얼 통신 API | MCU↔PC 시리얼 통신 명령 프로토콜 API 설계 |
| `phase-5-design-system` | Desktop 컴포넌트 | MCU 제어용 WPF/WinUI3 컴포넌트 디자인 시스템 (게이지, 차트, LED) |
| `phase-6-ui-integration` | Desktop-MCU 연동 | WPF ViewModel과 시리얼 포트 데이터 바인딩 통합 |
| `phase-7-seo-security` | 임베디드 보안 | MCU 펌웨어 OTA 업데이트 보안 (서명 검증, 암호화, 롤백) |
| `phase-9-deployment` | 펌웨어 배포 | STM32 플래시 프로그래밍 + i.MX SD카드 이미지 배포 |
| `desktop-app` | C# 데스크탑 앱 | MCU 시리얼 모니터링 WPF/WinUI3 데스크탑 앱 프로젝트 구조 |

## 4. 파일 구조

각 eval은 3개 파일로 구성:

```
evals/{classification}/{skill-name}/
├── eval.yaml        # eval 정의 (name, criteria, timeout)
├── prompt-1.md      # 테스트 시나리오 (≥50자, 멀티라인)
└── expected-1.md    # 기대 출력 (≥100자, ≥5라인, 구조화된 스텝)
```

### 4.1 통과 기준 (evaluateAgainstCriteria)

- prompt: >1줄 AND ≥50자 (placeholder 탈락 방지)
- expected: >1줄 AND ≥50자 (placeholder 탈락 방지)
- expected: ≥100자 AND ≥5줄 (generic criteria 통과)
- criteria 키워드 매칭: trigger/keyword, process/step, output/produce, pattern/follow
- score ≥ 0.8 && failedCriteria.length === 0

### 4.2 향후 Qt 도메인 확장 시 구조

```
evals/capability/qt-widgets/
├── eval.yaml
├── prompt-1.md      # Qt Widget 기반 시리얼 모니터 UI 설계
└── expected-1.md

evals/capability/qml-design/
├── eval.yaml
├── prompt-1.md      # QML 기반 임베디드 HMI 디자인
└── expected-1.md
```

config.json에 추가만 하면 벤치마크에 자동 포함되는 구조.

## 5. 구현 순서

| 단계 | 작업 | 파일 수 |
|------|------|---------|
| **Step 1** | config.json 재구성 (bkit 제거 + 도메인 추가) | 1 |
| **Step 2** | runner.js criteria 확장 (도메인 키워드 추가) | 1 |
| **Step 3** | 기존 placeholder eval 12개 업그레이드 | 36 |
| **Step 4** | Workflow eval 2개 신규 작성 | 6 |
| **Step 5** | Capability eval 8개 신규 작성 | 24 |
| **Step 6** | 벤치마크 실행 및 검증 | 0 |
| **합계** | | **68 파일** (2 수정 + 36 업그레이드 + 30 신규) |

## 6. 성공 기준

| 항목 | 기준 |
|------|------|
| 벤치마크 통과율 | 31/31 = 100% |
| Workflow 통과 | 11/11 (기존 8 + misra-c 업그레이드 + 신규 2) |
| Capability 통과 | 19/19 (기존 0→11 업그레이드 + 8 신규) |
| Hybrid 통과 | 1/1 (변경 없음) |
| eval 품질 | 모든 prompt ≥50자 멀티라인, expected ≥100자·≥5줄 |
| 도메인 적용 | 모든 eval이 MCU/MPU/Desktop 시나리오 반영 |
| 확장성 | Qt 도메인 추가 시 config.json + eval 3파일만 추가하면 완료 |

## 7. 제약사항

- eval은 정적 파일 기반 (CI 실행 가능, 외부 의존성 없음)
- mcukit 도메인(MCU/MPU/Desktop) 스킬만 포함, bkit 공통 웹 스킬 제외
- Desktop 도메인은 C# 기반(WPF/WinUI3)만 포함, 웹 기반(Electron/Tauri) 제외
- 향후 Qt 도메인 추가를 고려한 config 구조 유지
- MCU/MPU/Desktop 3개 도메인 균등 반영
