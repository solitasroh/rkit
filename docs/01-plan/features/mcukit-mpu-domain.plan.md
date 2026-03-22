# mcukit-mpu-domain Planning Document

> **Summary**: i.MX6/i.MX6ULL/i.MX28 MPU 도메인 - Device Tree 검증, Yocto/Buildroot 분석, 커널 모듈 가이드
>
> **Project**: mcukit
> **Version**: 0.3.0
> **Author**: Rootech
> **Date**: 2026-03-22
> **Status**: Draft
> **Prerequisite**: mcukit-core MVP-1 (98.6%), mcukit-mcu-domain MVP-2 (100%)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | i.MX6/6ULL/28 Embedded Linux 개발에서 Device Tree 문법 오류가 런타임까지 발견 안되고, Yocto 이미지 크기/부팅 시간 관리가 수동이며, 플랫폼별 툴체인 차이(hard float vs soft float)가 혼동됨 |
| **Solution** | lib/mpu/ 5개 모듈(DTS 파서, Yocto 분석기, 커널 설정 분석, 루트파일시스템 분석, 크로스컴파일러 탐지) + 4 Skills + 3 Agents + 2 Hooks + 3 Templates + refs 데이터 |
| **Function/UX Effect** | .dts 파일 저장 시 `dtc` 자동 문법 검증, `bitbake` 완료 후 이미지 크기 리포트, i.MX28 프로젝트에서 자동으로 soft float 툴체인 선택 |
| **Core Value** | "Embedded Linux BSP 개발의 검증 자동화" - DTS 오류 0, 이미지 크기 추적, 플랫폼별 정확한 툴체인 |

---

## 1. Overview

### 1.1 Purpose

MVP-2에서 MCU 도메인을 완성한 데 이어, **MPU(Embedded Linux) 도메인**을 구현합니다. NXP i.MX6(Cortex-A9), i.MX6ULL(Cortex-A7), i.MX28(ARM926EJ-S) 세 플랫폼의 BSP/커널/Yocto 개발을 PDCA 사이클로 지원합니다.

### 1.2 Platform Details (기술 검증 완료)

| 항목 | i.MX6 Quad/DL | i.MX6ULL | i.MX28 |
|------|:-------------:|:--------:|:------:|
| **코어** | Cortex-A9 (1~4코어) | Cortex-A7 (싱글) | ARM926EJ-S |
| **아키텍처** | ARMv7-A | ARMv7-A | **ARMv5TEJ** |
| **GPU** | Vivante GC2000/GC880 | PXP only (no 3D) | 없음 |
| **DDR** | 256MB~2GB DDR3 | 256~512MB DDR3L | 64~256MB DDR2 |
| **빌드 시스템** | Yocto (Scarthgap) | Yocto (Scarthgap) | **Buildroot** (Yocto 공식 지원 종료) |
| **툴체인** | arm-linux-gnueabi**hf** | arm-linux-gnueabi**hf** | arm-linux-gnueabi (soft float) |
| **부트로더** | U-Boot | U-Boot | mxs-bootlets 또는 U-Boot SPL |
| **Device Tree** | 지원 (mainline) | 지원 (mainline) | 지원 (mainline 3.7+) |
| **Yocto MACHINE** | imx6qsabresd | imx6ullevk | N/A (Buildroot defconfig) |
| **meta 레이어** | meta-freescale + meta-imx | meta-freescale + meta-imx | meta-freescale (제한적) |

### 1.3 Key Technical Notes (검증 결과 반영)

- **C2**: i.MX28은 ARMv5TEJ → `arm-linux-gnueabihf-gcc` 사용 불가, **soft float** 필수
- **H3**: `meta-freescale`(커뮤니티 오픈소스) vs `meta-imx`(NXP 공식+프로프라이어터리 GPU/VPU) 구분
- **H4**: i.MX28은 최신 Yocto(Kirkstone+) 공식 지원 종료 → Buildroot 우선
- **M5**: 커널 6.5+에서 DTS 경로가 `arch/arm/boot/dts/nxp/imx/`로 변경
- **M6**: Yocto 이미지명: 최신 BSP = `imx-image-*`, 구 BSP = `fsl-image-*`

---

## 2. Scope

### 2.1 In Scope

- [ ] lib/mpu/ 5개 모듈 (device-tree, yocto-analyzer, kernel-config, rootfs-analyzer, cross-compile)
- [ ] MPU Skills 4개 (imx-bsp, yocto-build, kernel-driver, rootfs-config)
- [ ] MPU Agents 3개 (linux-bsp-expert, yocto-expert, kernel-module-dev)
- [ ] Hook 스크립트 2개 (mpu-dts-validate, mpu-post-build)
- [ ] 문서 템플릿 3개 (mpu-bsp-spec, mpu-dts-spec, mpu-image-spec)
- [ ] 레퍼런스 데이터 (refs/imx/, refs/yocto/)

### 2.2 Out of Scope

- WPF 도메인 → MVP-4
- GPU/멀티미디어 가속 (Vivante/PXP 드라이버)
- OTA 업데이트 시스템 (SWUpdate, Mender)
- 실시간 리눅스 (PREEMPT_RT)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | DTS/DTSI 파일 문법 검증 (dtc 호출) | High |
| FR-02 | DTS pinctrl 노드 충돌 검사 (fsl,pins) | High |
| FR-03 | DTS 노드 트리 파싱 (계층 구조 추출) | Medium |
| FR-04 | Yocto local.conf 파싱 (MACHINE, DISTRO, IMAGE_FEATURES) | High |
| FR-05 | bblayers.conf 레이어 목록 추출 | High |
| FR-06 | Yocto/Buildroot 이미지 크기 분석 (rootfs, kernel, dtb, u-boot) | High |
| FR-07 | 커널 .config 파싱 (활성화된 모듈/드라이버 목록) | Medium |
| FR-08 | 루트파일시스템 패키지 목록/크기 분석 | Medium |
| FR-09 | 크로스 컴파일러 자동 탐지 (i.MX28 soft float 분기) | High |
| FR-10 | Yocto SDK 환경변수 감지 ($CC, $CROSS_COMPILE, $SDKTARGETSYSROOT) | Medium |
| FR-11 | i.MX BSP/Device Tree 개발 가이드 스킬 | High |
| FR-12 | Yocto 빌드/레시피 작성 가이드 스킬 | High |
| FR-13 | 리눅스 커널 모듈 개발 가이드 스킬 | Medium |
| FR-14 | 루트파일시스템 구성 가이드 스킬 | Medium |
| FR-15 | .dts 파일 저장 시 자동 dtc 검증 Hook (PostToolUse Write) | High |
| FR-16 | bitbake/make 완료 후 이미지 크기 리포트 Hook (PostToolUse Bash) | High |
| FR-17 | linux-bsp-expert 에이전트 (BSP/DT/커널 설정) | High |
| FR-18 | yocto-expert 에이전트 (레시피/레이어 관리) | Medium |
| FR-19 | kernel-module-dev 에이전트 (커널 모듈 개발) | Medium |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 정확도 | dtc 검증 결과와 100% 일치 |
| 성능 | DTS 검증 < 2초 |
| 호환성 | Yocto Kirkstone(4.0) ~ Scarthgap(5.0) 지원 |
| 호환성 | Buildroot 2024.x i.MX28 defconfig 지원 |

---

## 4. Key Technical Details

### 4.1 Device Tree Specifics

**DTS 파일 명명 규칙**:
```
i.MX6Q:   imx6q.dtsi, imx6qdl.dtsi(공통), imx6q-sabresd.dts
i.MX6DL:  imx6dl.dtsi, imx6dl-sabresd.dts
i.MX6ULL: imx6ull.dtsi, imx6ul.dtsi(UL/ULL공통), imx6ull-14x14-evk.dts
i.MX28:   imx28.dtsi, imx28-evk.dts
```

**커널 내 DTS 경로**:
```
커널 <6.5: arch/arm/boot/dts/imx6*.dts*
커널 6.5+: arch/arm/boot/dts/nxp/imx/imx6*.dts*
           arch/arm/boot/dts/nxp/mxs/imx28*.dts*
```

**pinctrl 노드 형식** (i.MX6):
```dts
&iomuxc {
    pinctrl_uart1: uart1grp {
        fsl,pins = <
            MX6QDL_PAD_CSI0_DAT10__UART1_TX_DATA  0x1b0b1
            MX6QDL_PAD_CSI0_DAT11__UART1_RX_DATA  0x1b0b1
        >;
    };
};
```

**dtc 검증 명령**:
```bash
dtc -I dts -O dtb -o /dev/null -W no-unit_address_vs_reg file.dts
# 고급: dt-validate (schema 기반), make dtbs_check (커널 빌드 내)
```

### 4.2 Yocto/Buildroot 구조

**Yocto conf 파일** (build/conf/):
```
local.conf:    MACHINE, DISTRO, IMAGE_FEATURES, EXTRA_IMAGE_FEATURES
bblayers.conf: BBLAYERS 변수 (레이어 경로 목록)
```

**NXP 레이어**:
- `meta-freescale`: 커뮤니티 오픈소스
- `meta-imx`: NXP 공식 (GPU/VPU 프로프라이어터리 드라이버 포함)

**이미지명**:
- 최신 BSP: `imx-image-full`, `imx-image-multimedia`
- 구 BSP: `fsl-image-gui` (레거시)
- 공통: `core-image-minimal`, `core-image-base`

**Buildroot (i.MX28)**:
- defconfig: `freescale_imx28evk_defconfig`
- 출력: `output/images/` (rootfs.ext2, zImage, imx28-evk.dtb)

### 4.3 크로스 컴파일러

| 플랫폼 | 툴체인 | Float ABI | 근거 |
|---------|--------|:---------:|------|
| i.MX6 (Cortex-A9) | arm-linux-gnueabi**hf**-gcc | hard | VFPv3/NEON 탑재 |
| i.MX6ULL (Cortex-A7) | arm-linux-gnueabi**hf**-gcc | hard | VFPv4 탑재 |
| i.MX28 (ARM926EJ-S) | arm-linux-gnueabi-gcc | **soft** | VFP/NEON 미탑재 (ARMv5) |

**Yocto SDK 환경변수**:
```bash
source /opt/poky/<version>/environment-setup-cortexa9t2hf-neon-poky-linux-gnueabi
# 설정되는 변수: CC, CXX, LD, SDKTARGETSYSROOT, CROSS_COMPILE, CFLAGS, LDFLAGS
```

---

## 5. Implementation Phases

### Phase A: lib/mpu/ 핵심 모듈 (5 파일)

| 파일 | 기능 |
|------|------|
| device-tree.js | DTS 문법 검증(dtc), 노드 파싱, pinctrl 충돌 검사 |
| yocto-analyzer.js | local.conf/bblayers.conf 파싱, 이미지 크기 분석 |
| kernel-config.js | .config 파싱, 모듈/드라이버 목록 |
| rootfs-analyzer.js | 루트파일시스템 크기/패키지 분석 |
| cross-compile.js | 크로스 컴파일러 탐지 (i.MX28 soft float 분기) |

### Phase B: MPU Skills (4 파일)

| Skill | 핵심 내용 |
|-------|----------|
| imx-bsp/ | i.MX DTS 구조, pinctrl/클럭/GPIO 노드, 보드 포팅 가이드 |
| yocto-build/ | 레시피(.bb) 작성, 레이어 관리, IMAGE_INSTALL, meta-imx vs meta-freescale |
| kernel-driver/ | 커널 모듈 구조, platform_driver, probe/remove, sysfs/ioctl |
| rootfs-config/ | Busybox/systemd, init 스크립트, 파일시스템 레이아웃 |

### Phase C: MPU Agents (3 파일)

| Agent | 모델 | 역할 |
|-------|:----:|------|
| linux-bsp-expert | opus | BSP 포팅, DTS 설계, 커널 설정, 부팅 시퀀스 |
| yocto-expert | sonnet | 레시피 작성, 레이어 관리, 빌드 문제 해결 |
| kernel-module-dev | sonnet | 커널 모듈/드라이버 개발 |

### Phase D: Hooks + Templates + Refs (7+ 파일)

| 파일 | 기능 |
|------|------|
| scripts/mpu-dts-validate.js | PostToolUse(Write) .dts → dtc 검증 |
| scripts/mpu-post-build.js | PostToolUse(Bash) bitbake → 이미지 크기 리포트 |
| templates/mpu-bsp-spec.template.md | BSP 사양서 |
| templates/mpu-dts-spec.template.md | DTS 설계서 |
| templates/mpu-image-spec.template.md | 이미지 구성 사양 |
| refs/imx/dts-patterns.md | i.MX DTS 패턴 레퍼런스 |
| refs/yocto/recipe-patterns.md | Yocto 레시피 패턴 레퍼런스 |

---

## 6. Success Criteria

- [ ] .dts 파일 저장 시 dtc 자동 검증 동작
- [ ] `bitbake` 완료 후 이미지 크기 리포트 자동 출력
- [ ] i.MX28 프로젝트에서 soft float 툴체인 자동 선택
- [ ] local.conf MACHINE 파싱 정확
- [ ] Gap Analysis 90% 이상

---

## 7. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| dtc가 시스템에 미설치 | High | 미설치 시 경고 + 설치 가이드 출력 |
| Yocto 빌드 디렉토리가 프로젝트 외부 | Medium | 환경변수/config에서 빌드 경로 지정 |
| i.MX28 Buildroot가 매우 오래된 버전 | Low | 지원 범위를 명시 (defconfig 존재 여부로 판단) |

---

## 8. Next Steps

1. [ ] `/pdca design mcukit-mpu-domain`
2. [ ] lib/mpu/ 5개 모듈 구현
3. [ ] MPU Skills/Agents/Hooks/Templates 작성

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-22 | 초기 기획 (기술 검증 결과 반영) | Rootech |
