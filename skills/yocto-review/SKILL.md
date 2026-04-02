---
name: yocto-review
classification: capability
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  Yocto/Embedded Linux 코드 리뷰 기준. Recipe, 스크립트, DTS, defconfig 리뷰 체크리스트.
  Triggers: yocto review, recipe review, bbappend review, Yocto 리뷰
user-invocable: false
allowed-tools: [Read, Glob, Grep]
pdca-phase: check
---

# Yocto Code Review Checklist

## Principles

- Prioritize actual build failures and runtime errors.
- Minimize style/formatting nitpicks.
- **No over-critique**: If no real issues found, respond "LGTM". Do not invent problems.

## Must-Check Items

### Recipe (.bb / .bbappend)

| Issue | Description |
|-------|-------------|
| SRC_URI errors | Wrong URL, checksum mismatch, missing file references |
| License missing | `LICENSE`, `LIC_FILES_CHKSUM` not specified |
| Dependency errors | Missing or circular `DEPENDS`/`RDEPENDS` |
| Override misuse | `=` vs `:append` vs `:prepend` used incorrectly |
| FILESEXTRAPATHS missing | bbappend adds files but omits path setup |
| do_install path errors | Misuse of `${D}`, `${bindir}`, etc. |

### Scripts (.sh)

| Issue | Description |
|-------|-------------|
| No error handling | Missing `set -e`, continues on failure |
| Hardcoded paths | Environment-dependent absolute paths |
| Unquoted variables | Breaks on paths with spaces |

### Makefile / CMakeLists.txt

| Issue | Description |
|-------|-------------|
| No cross-compile support | Calls host tools directly |
| Ignores DESTDIR/prefix | Hardcoded install paths |

### DTS / defconfig

| Issue | Description |
|-------|-------------|
| Pin conflicts | Same pin assigned to multiple functions |
| Clock/interrupt mismatch | Reference node vs actual hardware mismatch |

## Recommendations (non-blocking)

- Unnecessary `do_compile`/`do_install` overrides
- Excessive patches when bbappend could solve it
