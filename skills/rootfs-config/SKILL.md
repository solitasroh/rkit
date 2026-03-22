---
name: rootfs-config
classification: capability
deprecation-risk: low
domain: mpu
description: |
  루트파일시스템 구성 가이드. init 시스템, 파일시스템 레이아웃, 부팅 최적화.
  Triggers: rootfs, init, systemd, busybox, 루트파일시스템, ファイルシステム
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---

# Root Filesystem Configuration Guide

## Init Systems
| System | Use Case | Package |
|--------|----------|---------|
| **systemd** | Full-featured, service management | IMAGE_INSTALL += "systemd" |
| **SysVinit** | Traditional, lightweight | Default in many Yocto images |
| **BusyBox init** | Minimal, embedded | Buildroot default |

## Filesystem Layout
```
/ (rootfs)
├── bin/        → /usr/bin (merged on modern distros)
├── etc/        → Configuration files
├── lib/        → Shared libraries
├── usr/
│   ├── bin/    → User binaries
│   ├── lib/    → Libraries
│   └── share/  → Architecture-independent data
├── var/        → Variable data (logs, runtime)
├── tmp/        → Temporary files
├── dev/        → Device nodes (devtmpfs)
├── proc/       → Process info (procfs)
└── sys/        → Kernel/device info (sysfs)
```

## Size Optimization
- Strip binaries: `INHIBIT_PACKAGE_STRIP = "0"` (Yocto)
- Remove docs: `EXTRA_IMAGE_FEATURES:remove = "doc-pkgs"`
- Use musl instead of glibc for small footprint
- Squashfs for read-only rootfs (better compression)
