# mcukit-wpf-domain MVP-4 Completion Report

> **Feature**: mcukit-wpf-domain (C#/XAML/MVVM Desktop)
> **Date**: 2026-03-22
> **PDCA**: Plan → Do → Check → Report
> **Status**: COMPLETED

---

## Executive Summary

| Item | Value |
|------|-------|
| **Match Rate** | **100%** (16/16) |
| **Iteration** | 0 |
| **New Files** | 16 (JS 5, MD 11) |

### Value Delivered

| Perspective | Content |
|-------------|---------|
| **Problem** | WPF 바인딩 에러 런타임 발견, MVVM 패턴 수동 검증, MCU↔WPF 시리얼 불일치 |
| **Solution** | lib/wpf/ 3모듈(5함수) + 4 Skills + 3 Agents + 2 Hooks + 2 Templates + 1 ref |
| **Function/UX Effect** | .xaml 저장 → 바인딩 경로 자동 추출, ViewModel 속성 매칭, [ObservableProperty] Source Generator 인식 |
| **Core Value** | WPF 바인딩 Zero Error + MVVM 자동 검증 + MCU↔WPF Cross-Domain 시리얼 일관성 |

---

## Deliverables

| Category | Files |
|----------|:-----:|
| lib/wpf/ (xaml-analyzer, mvvm-validator, index) | 3 |
| Agents (wpf-architect:opus, xaml-expert:sonnet, dotnet-expert:sonnet) | 3 |
| Skills (wpf-mvvm, xaml-design, dotnet-patterns, serial-bridge) | 4 |
| Hooks (wpf-xaml-check, wpf-post-build) | 2 |
| Templates (wpf-ui-spec, wpf-mvvm-spec) | 2 |
| Refs (wpf/mvvm-patterns) | 1 |
| Plan doc | 1 |

## Key Technical Decisions

- `{x:Bind}` 완전 제외 (UWP/WinUI 전용, WPF 불가)
- `[ObservableProperty]` Source Generator 인식: private 필드 → PascalCase 프로퍼티 매핑
- `[RelayCommand]` 인식: 메서드 → {Name}Command 프로퍼티 매핑
- Prism 9.0+ 상용화 경고 포함, CommunityToolkit.Mvvm 권장
- SerialPort: .NET 8에서 `System.IO.Ports` NuGet 별도 설치 필요 명시
- `.csproj` 감지: `<UseWPF>true</UseWPF>` 파싱 필수 (파일 존재만으로 판별 불가)

---

## Final Project Status: mcukit v0.4.0

```
┌─────────────────────────────────────────────────────────────────────┐
│                    mcukit v0.4.0 — "One Kit, Three Domains"          │
├─────────────────────────────────────────────────────────────────────┤
│  Domain A: MCU (STM32, NXP K)                                       │
│    lib/mcu/: 6 modules (24 functions)                                │
│    Skills: stm32-hal, nxp-mcuxpresso, cmake-embedded,               │
│            communication, freertos, misra-c                          │
│    Agents: fw-architect, hw-interface-expert, safety-auditor         │
│                                                                      │
│  Domain B: MPU (i.MX6, i.MX6ULL, i.MX28)                           │
│    lib/mpu/: 6 modules (16 functions)                                │
│    Skills: imx-bsp, yocto-build, kernel-driver, rootfs-config        │
│    Agents: linux-bsp-expert, yocto-expert, kernel-module-dev         │
│                                                                      │
│  Domain C: WPF (C#/XAML/MVVM)                                       │
│    lib/wpf/: 3 modules (5 functions)                                 │
│    Skills: wpf-mvvm, xaml-design, dotnet-patterns, serial-bridge     │
│    Agents: wpf-architect, xaml-expert, dotnet-expert                 │
│                                                                      │
│  Core: PDCA Engine (18) + Core Infra (58) + Domain Routing (4)      │
│  Total: 16 Skills, 9 Agents, 62 Hook Scripts                        │
└─────────────────────────────────────────────────────────────────────┘
```

| MVP | Feature | Match Rate | Files | Commit |
|:---:|---------|:----------:|:-----:|--------|
| 1 | PDCA 코어 + 도메인 감지 | 98.6% | 145 | e1c380a |
| 2 | MCU 도메인 (STM32/NXP K) | 100% | +21 | e1c380a |
| 3 | MPU 도메인 (i.MX6/6ULL/28) | 100% | +24 | 34ceac6 |
| **4** | **WPF 도메인 (C#/XAML/MVVM)** | **100%** | **+16** | **pending** |
| **Total** | | | **~206** | |
