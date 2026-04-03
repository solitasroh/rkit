# mcukit-wpf-domain Planning Document

> **Summary**: WPF(C#/XAML/MVVM) 도메인 - 바인딩 검증, MVVM 패턴 가이드, MCU↔WPF 시리얼 브릿지
>
> **Project**: mcukit v0.4.0
> **Date**: 2026-03-22
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | WPF XAML 바인딩 에러가 런타임에만 발견되고, MVVM 패턴 준수가 수동 검증이며, MCU↔WPF 시리얼 통신 파라미터 불일치가 디버깅 어려움 |
| **Solution** | lib/wpf/ 4모듈(XAML 분석, MVVM 검증, csproj 분석, NuGet 관리) + 3 Skills + 3 Agents + 2 Hooks + 2 Templates + refs |
| **Function/UX Effect** | .xaml 저장 → 바인딩 경로 vs ViewModel 속성 자동 비교, .csproj 분석 → WPF/.NET 버전 감지, MCU UART 설정과 WPF SerialPort 설정 자동 교차 검증 |
| **Core Value** | "WPF 바인딩 에러 Zero + MVVM 패턴 자동 검증 + Cross-Domain 시리얼 일관성" |

---

## Key Technical Notes (검증 완료)

| 항목 | 정확한 정보 |
|------|-----------|
| WPF 감지 | `.csproj` 내부 `<UseWPF>true</UseWPF>` 파싱 필수 (파일 존재만으로 판별 불가) |
| .NET 8 SDK | `Microsoft.NET.Sdk` + `<UseWPF>true</UseWPF>` (WindowsDesktop SDK는 레거시) |
| TFM | `net8.0-windows` (-windows 접미사 필수) |
| 바인딩 문법 | `{Binding}`, `{TemplateBinding}`, `{MultiBinding}` (x:Bind는 UWP전용, WPF 불가) |
| 바인딩 에러 | **런타임에만 감지** (컴파일 타임 불가). Output 패턴: "System.Windows.Data Error: 40" |
| MVVM 툴킷 | CommunityToolkit.Mvvm 권장 (Prism 9.0+ 상용화) |
| Source Generator | `[ObservableProperty]`는 private 필드에 적용 → PascalCase 프로퍼티 자동 생성 |
| SerialPort | .NET 8에서 `System.IO.Ports` NuGet 패키지 별도 설치 필요 |
| Markup Extension | `{StaticResource}`, `{DynamicResource}`는 Binding이 아닌 별도 분류 |

---

## Scope

### In Scope
- [ ] lib/wpf/ 4개 모듈 (xaml-analyzer, mvvm-validator, csproj-analyzer, nuget-manager)
- [ ] WPF Skills 3개 (wpf-mvvm, xaml-design, dotnet-patterns)
- [ ] WPF Agents 3개 (wpf-architect, xaml-expert, dotnet-expert)
- [ ] Hook 스크립트 2개 (wpf-xaml-check, wpf-post-build)
- [ ] 문서 템플릿 2개 (wpf-ui-spec, wpf-mvvm-spec)
- [ ] 레퍼런스 데이터 (refs/wpf/)
- [ ] serial-bridge 스킬 (MCU↔WPF cross-domain)

### Out of Scope
- WPF 외 .NET UI (MAUI, Avalonia, WinUI)
- WPF 디자이너 도구 연동
- UI 자동화 테스트 프레임워크 (FlaUI 등)

---

## Requirements (17개)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | XAML 바인딩 경로 추출 ({Binding}, {TemplateBinding}, MultiBinding) | High |
| FR-02 | ViewModel 속성과 바인딩 경로 비교 (Source Generator [ObservableProperty] 포함) | High |
| FR-03 | StaticResource/DynamicResource 참조 검증 | Medium |
| FR-04 | MVVM 패턴 준수 검증 (ObservableObject, RelayCommand, View 참조 금지) | High |
| FR-05 | .csproj 파싱 (UseWPF, TargetFramework, NuGet 패키지) | High |
| FR-06 | .NET Framework vs .NET 8 자동 구분 | High |
| FR-07 | NuGet 패키지 관리 (CommunityToolkit.Mvvm, System.IO.Ports 등) | Medium |
| FR-08 | .xaml 저장 시 바인딩 검증 Hook (PostToolUse Write) | High |
| FR-09 | dotnet build 후 경고/에러 분석 Hook (PostToolUse Bash) | High |
| FR-10 | WPF MVVM 아키텍처 가이드 스킬 | High |
| FR-11 | XAML UI 디자인/스타일 가이드 스킬 | Medium |
| FR-12 | .NET DI/패턴/테스트 가이드 스킬 | Medium |
| FR-13 | MCU↔WPF 시리얼 통신 브릿지 스킬 | Medium |
| FR-14 | wpf-architect 에이전트 (MVVM 아키텍처) | High |
| FR-15 | xaml-expert 에이전트 (XAML UI/바인딩) | Medium |
| FR-16 | dotnet-expert 에이전트 (.NET 패턴/DI) | Medium |
| FR-17 | WPF 문서 템플릿 (UI 사양, MVVM 구조) | Medium |
