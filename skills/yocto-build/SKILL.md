---
name: yocto-build
classification: capability
deprecation-risk: low
domain: mpu
platforms: [imx6, imx6ull]
description: |
  Yocto 빌드 시스템 가이드. 레시피 작성, 레이어 관리, 이미지 커스터마이징.
  Triggers: Yocto, bitbake, recipe, layer, meta-imx, meta-freescale
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
imports:
  - ${PLUGIN_ROOT}/refs/yocto/recipe-patterns.md
pdca-phase: do
---

# Yocto Build Guide

## Setup
```bash
source oe-init-build-env build
# Edit build/conf/local.conf:
#   MACHINE ??= "imx6qsabresd"
#   DISTRO ?= "poky"
# Edit build/conf/bblayers.conf:
#   Add meta-freescale and/or meta-imx layers
```

## Recipe Structure (.bb)
```
SUMMARY = "My application"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=..."
SRC_URI = "file://myapp.c"
S = "${WORKDIR}"
do_compile() { ${CC} ${CFLAGS} ${LDFLAGS} -o myapp myapp.c }
do_install() { install -d ${D}${bindir}; install -m 0755 myapp ${D}${bindir}/ }
```

## NXP Layers
- **meta-freescale**: Community open-source (kernel, u-boot, base BSP)
- **meta-imx**: NXP official (proprietary GPU/VPU drivers, multimedia)
- Use meta-imx when GPU/video acceleration needed

## Image Names
| BSP Version | Image Name |
|-------------|-----------|
| Latest (Scarthgap) | imx-image-full, imx-image-multimedia |
| Legacy | fsl-image-gui (deprecated) |
| Minimal | core-image-minimal |

## i.MX28 Note
Yocto official support ended (Kirkstone+). Use **Buildroot** instead:
```bash
make freescale_imx28evk_defconfig
make -j$(nproc)
```
