# mcukit-core Domain Technical Verification Report

> **Date**: 2026-03-22
> **Purpose**: Plan/Design 문서의 도메인 기술 정보 정확성 검증
> **Method**: 3개 도메인 전문 에이전트 병렬 검증

---

## 1. 발견된 오류 및 수정 사항

### Critical (설계 오류 → 즉시 수정 필수)

| # | 도메인 | 오류 내용 | 수정 사항 | 영향 범위 |
|---|--------|----------|-----------|-----------|
| C1 | MCU | `sdk_config.h`를 NXP 마커로 사용 | **Nordic nRF SDK 파일**. NXP는 `fsl_device_registers.h` 사용 | detector.js 마커 |
| C2 | MPU | i.MX28에 `arm-linux-gnueabihf-gcc` 적용 | ARM926EJ-S는 **ARMv5TEJ**. `arm-linux-gnueabi-gcc` (soft float) 필요 | cross-compile.js |
| C3 | WPF | `{x:Bind}` 를 XAML 바인딩 감지에 포함 | **UWP/WinUI 전용**. WPF에서 사용 불가 | xaml-analyzer.js |

### High (기능 영향 → 수정 권장)

| # | 도메인 | 오류 내용 | 수정 사항 |
|---|--------|----------|-----------|
| H1 | MCU | .ioc 파일 포맷을 "XML/INI/custom"으로 모호하게 기술 | **Java Properties 형식** (flat key=value 텍스트) |
| H2 | MCU | STM32_Programmer_CLI 누락 | `st-flash` 외에 **`STM32_Programmer_CLI`** (CubeProgrammer)도 지원해야 함 |
| H3 | MPU | NXP meta 레이어를 단일로 취급 | **`meta-freescale`** (커뮤니티 오픈소스) vs **`meta-imx`** (NXP 공식+프로프라이어터리) 구분 필요 |
| H4 | MPU | i.MX28 Yocto 지원 상태 미기재 | 최신 Yocto(Kirkstone+)에서 **공식 지원 종료**. Buildroot만 실질적 |
| H5 | MPU | i.MX28 부트로더를 U-Boot만 기술 | **mxs-bootlets** (레거시) 또는 U-Boot SPL 지원 |
| H6 | WPF | `MainWindow.xaml`을 감지 마커로 사용 | 기본 템플릿 이름일 뿐, **감지 기준 부적합** |
| H7 | WPF | `Microsoft.NET.Sdk.WindowsDesktop` 사용 | .NET 6+에서는 **`Microsoft.NET.Sdk`** + `<UseWPF>true</UseWPF>`가 권장 |
| H8 | WPF | Prism 패키지를 `Prism.Wpf`로 기술 | **Prism 9.0+부터 상용 라이선스**. CommunityToolkit.Mvvm 우선 권장 |
| H9 | WPF | .NET 8에서 SerialPort 기본 포함으로 기술 | **NuGet 패키지 `System.IO.Ports` 설치 필요** |

### Medium (정확도 보완)

| # | 도메인 | 보완 사항 |
|---|--------|-----------|
| M1 | MCU | NXP Kinetis K의 `fsl_uart.h` 외에 `fsl_lpuart.h`도 있음 (최신 디바이스) |
| M2 | MCU | CMSIS-RTOS v2 (`cmsis_os2.h`)가 최신 CubeMX 기본값. v1은 레거시 |
| M3 | MCU | cppcheck MISRA addon은 규칙의 약 60-70%만 커버 |
| M4 | MPU | i.MX6 GPU: Quad/Dual=GC2000, DualLite/Solo=GC880으로 성능 차이 큼 |
| M5 | MPU | DTS 파일 경로: 커널 6.5+에서 `arch/arm/boot/dts/nxp/imx/`로 이동 |
| M6 | MPU | Yocto 이미지: `fsl-image-*`는 구 BSP, 최신은 `imx-image-*` |
| M7 | WPF | `StaticResource`/`DynamicResource`는 Binding이 아닌 **Markup Extension** |
| M8 | WPF | 누락된 바인딩 패턴: `TemplateBinding`, `ElementName`, `MultiBinding` |
| M9 | WPF | WPF 바인딩 에러는 **런타임에만** 감지 가능 (컴파일 타임 불가) |
| M10 | WPF | `App.xaml`은 99% 존재하지만 **필수 아님** (강력한 힌트로 취급) |

---

## 2. 수정 반영 대상 문서

### Plan 문서 (`mcukit-core.plan.md`)
- Section 2.2: i.MX28 크로스 컴파일러 수정
- Section 4.2: 도메인 감지 마커 수정 (sdk_config.h 제거, MainWindow.xaml 제거)
- Section 10.8: 이름 변경 체크리스트에 반영

### Design 문서 (`mcukit-core.design.md`)
- Section 3.1.1: detector.js 마커 테이블 수정
- Section 3.2: .ioc 파일 포맷 명시 (Java Properties)
- Section 3.3.3: cross-compile.js i.MX28 툴체인 분기
- Section 3.4.1: xaml-analyzer.js 바인딩 패턴 수정
- Section 5.4: unified-write-post.js XAML 검증 범위 보완
