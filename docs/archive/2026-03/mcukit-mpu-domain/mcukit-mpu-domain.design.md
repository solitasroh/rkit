# mcukit-mpu-domain Design Document

> **Summary**: i.MX6/6ULL/28 MPU 도메인 모듈 상세 설계
>
> **Project**: mcukit v0.3.0
> **Date**: 2026-03-22
> **Plan Reference**: `docs/01-plan/features/mcukit-mpu-domain.plan.md`

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | DTS 문법 오류 런타임 발견, Yocto 이미지 크기 수동, i.MX28 soft float 혼동 |
| **Solution** | 5 lib/mpu 모듈 + 4 Skills + 3 Agents + 2 Hooks + 3 Templates + 2 refs |
| **Function/UX Effect** | .dts 저장 → dtc 자동 검증, bitbake → 이미지 리포트, i.MX28 soft float 자동 |
| **Core Value** | Embedded Linux BSP 검증 100% 자동화 |

---

## 1. Module Design

### 1.1 lib/mpu/device-tree.js

```
Exports:
- validateDeviceTree(dtsPath) → { valid, errors[], warnings[] }
  dtc -I dts -O dtb -o /dev/null -W no-unit_address_vs_reg
- parseDtsNodes(dtsPath) → recursive node tree object
  Simple regex-based parser for node { ... } blocks
- checkPinctrlConflicts(nodeTree) → [{ pad, conflicts[] }]
  Find duplicate pads in fsl,pins entries
```

### 1.2 lib/mpu/yocto-analyzer.js

```
Exports:
- parseLocalConf(confPath) → { machine, distro, imageFeatures[] }
  Parse key=value with quotes, handle += append
- parseBbLayers(confPath) → string[] layer paths
  Extract BBLAYERS variable (multiline)
- analyzeImageSize(deployDir) → { rootfs, kernel, dtb, uboot } (bytes)
  Scan tmp/deploy/images/ for *.ext4, zImage, *.dtb, u-boot*
- detectBuildSystem() → 'yocto' | 'buildroot' | 'unknown'
```

### 1.3 lib/mpu/kernel-config.js

```
Exports:
- parseKernelConfig(configPath) → Map<string, string>
  Parse .config (CONFIG_*=y|m|n)
- getEnabledModules(configMap) → string[]
  Filter CONFIG_*=m entries
- getEnabledDrivers(configMap) → string[]
  Filter CONFIG_*=y entries related to drivers
```

### 1.4 lib/mpu/rootfs-analyzer.js

```
Exports:
- analyzeRootfsSize(rootfsPath) → { totalMB, topDirs[] }
  du -sh on rootfs directory or image mount info
- listInstalledPackages(manifestPath) → [{ name, version, size }]
  Parse Yocto manifest or Buildroot .config
```

### 1.5 lib/mpu/cross-compile.js

```
Exports:
- detectCrossCompiler() → { found, path, arch, sysroot, floatAbi }
  Platform-specific:
    i.MX6/6ULL: arm-linux-gnueabihf-gcc (hard float)
    i.MX28:     arm-linux-gnueabi-gcc (soft float, ARMv5TEJ)
  Search: $CC, $CROSS_COMPILE, Yocto SDK env, PATH
- detectSdkEnvironment() → { sdkPath, targetSysroot, envVars }
  Parse /opt/poky/*/environment-setup-* or /opt/fsl-imx-*/*
```

---

## 2. Hook Scripts

### mpu-dts-validate.js (PostToolUse Write, .dts/.dtsi)
```
Trigger: Write/Edit to .dts or .dtsi file
Action: Run dtc syntax check, output errors/warnings
Timeout: 3s
```

### mpu-post-build.js (PostToolUse Bash, bitbake/make)
```
Trigger: bitbake or make in MPU project
Action: Scan deploy dir for image sizes, format report
Timeout: 5s
```

---

## 3. Agents

| Agent | Model | Frontmatter |
|-------|:-----:|-------------|
| linux-bsp-expert | opus | BSP porting, DTS design, kernel config, boot sequence |
| yocto-expert | sonnet | Recipe writing, layer management, build troubleshooting |
| kernel-module-dev | sonnet | Kernel module structure, platform_driver, sysfs/ioctl |

---

## 4. Implementation Order

```
Step 1: lib/mpu/device-tree.js
Step 2: lib/mpu/yocto-analyzer.js
Step 3: lib/mpu/kernel-config.js + rootfs-analyzer.js
Step 4: lib/mpu/cross-compile.js + index.js
Step 5: scripts/mpu-dts-validate.js + mpu-post-build.js
Step 6: agents/ (3 files)
Step 7: skills/ (4 files)
Step 8: templates/ (3) + refs/ (2)
```
