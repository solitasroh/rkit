---
template: mr-description
version: 1.0
description: GitLab MR description template with domain-specific impact sections
variables:
  - feature: Feature name
  - op_number: OpenProject task number (optional)
  - domain: Detected domain (MCU/MPU/WPF)
  - match_rate: PDCA gap-detector match rate (optional)
  - iteration_count: PDCA iteration count (optional)
---

## Summary

<!-- 무엇을 변경했고, 왜 필요한지. 동기(motivation)를 명확히 기술. -->

{summary}

## Type of Change

- [ ] Feature (신규 기능)
- [ ] Bugfix (버그 수정)
- [ ] Refactoring (기능 변경 없음)
- [ ] Configuration (Kconfig, DTS, linker script, .csproj)
- [ ] Documentation

## Related

- OpenProject: {op_link}
- PDCA Plan: {plan_link}
- Fixes: #{issue_number}

## PDCA Report

| Metric | Value |
|--------|-------|
| AI Check (gap-detector) | {match_rate}% |
| Iterations | {iteration_count} |

## Changes

{file_change_list}

<!-- 도메인별 Impact: AI가 감지된 도메인 섹션만 남기고 나머지를 제거 -->

## MCU Impact

| Region | Before | After | Delta | Budget |
|--------|--------|-------|-------|--------|
| Flash  |        |       |       | < 85%  |
| RAM    |        |       |       | < 75%  |

- **Peripheral changes:**
- **Interrupt changes:**
- **MISRA compliance:** Required 위반 0건

## MPU Impact

- **Kernel ABI:** 변경 없음 / 변경 있음 (상세)
- **Device Tree:** 변경 없음 / 변경 있음 (상세)
- **Driver interface:** 변경 없음 / 변경 있음 (ioctl/sysfs)

## WPF Impact

- **NuGet packages:** 변경 없음 / 추가·변경 (상세)
- **XAML binding:** 변경 없음 / 변경 있음 (상세)
- **.NET target:** net8.0-windows 호환 확인

## Test Evidence

- [ ] On-target test / Unit test 통과
- [ ] Regression test 범위:

**Test Configuration:**
- Hardware:
- Toolchain:
- SDK:

## Checklist

- [ ] Self-review 완료
- [ ] 코딩 컨벤션 준수
- [ ] 에러 경로 리소스 정리 확인
- [ ] 링커 스크립트 / DTS / .csproj 변경 없음 (또는 리뷰 완료)
- [ ] Breaking change 없음 (또는 아래 기술)

## Breaking Changes

<!-- 없으면 "None". 있으면 영향 범위와 마이그레이션 방법 기술. -->

None
