---
name: yocto-stm32-build
classification: workflow
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  STM32MP Yocto 빌드 실행 스킬. bitbake 빌드, 환경 체크, SDK 생성, 플래싱 패키지, 릴리즈 노트/SBOM.
  Triggers: stm32 build, stm32mp bitbake, 이미지 빌드, SDK 생성, 플래싱 패키지
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---
# Yocto Build

bitbake 빌드 실행 및 환경 체크를 자동화한다.

## 전제 조건

### .env 확인 (공통)

스킬 실행 전 프로젝트 루트의 `.env` 파일을 확인한다:

1. `.env` 파일이 있으면 → 정상 진행 (값을 읽어서 사용)
2. `.env` 파일이 없으면:
   - devkit plugin 디렉토리의 `templates/env.template` 파일을 찾는다
   - `env.template`이 있으면 → 프로젝트 루트에 `.env.example`과 `.env`로 복사
   - 사용자에게 안내: "`.env` 파일이 생성되었습니다. 필요한 값을 채워주세요."
   - `env.template`이 없으면 → "devkit plugin이 설치되지 않은 것 같습니다." 안내
3. `.env`에서 이 스킬에 필요한 변수를 읽는다 (빈 값이면 사용자에게 질문)

- yocto-stm32-setup 스킬로 환경이 구성되어 있어야 한다
- `.env` 파일에 Yocto 환경변수가 설정되어 있어야 한다

## 외부 스크립트 참조

- `yocto-setup/scripts/bblayers_add.py` — layer 등록 확인

## 절차

실행 시 메뉴를 표시한다:

```
Yocto 빌드:

1. 전체 이미지     — bitbake {IMAGE_NAME}
2. 단일 패키지     — bitbake {패키지명}
3. Kernel만        — bitbake virtual/kernel
4. U-Boot만        — bitbake virtual/bootloader
5. TF-A만          — bitbake tf-a-stm32mp
6. OP-TEE만        — bitbake optee-os-stm32mp
7. SDK 생성        — bitbake -c populate_sdk {IMAGE_NAME}
8. 환경 체크       — bblayers, local.conf 확인
9. 리포트 생성     — 빌드 없이 release note + SBOM 생성
```


### 메뉴 1: 전체 이미지

사용자에게 이미지 이름을 확인한다:

```
빌드할 이미지:
  1. {PROJECT_NAME}-image-weston (custom)
  2. st-image-weston (ST 기본)
  3. core-image-minimal
  4. 직접 입력
```

```bash
cd $YOCTO_WORK_DIR
source {YOCTO_SETUP_SCRIPT}
bitbake {이미지명}
```

### 메뉴 2: 단일 패키지

```bash
bitbake {사용자가 입력한 패키지명}
```

### 메뉴 3-6: 개별 컴포넌트

```bash
bitbake virtual/kernel           # Kernel (공통)
bitbake virtual/bootloader       # U-Boot (공통)
```

TF-A / OP-TEE는 벤더별 recipe명이 다르다:

| 컴포넌트 | ST | NXP | TI |
|---------|-----|-----|-----|
| TF-A | `tf-a-stm32mp` | `imx-atf` | `trusted-firmware-a` |
| OP-TEE | `optee-os-stm32mp` | `optee-os-imx` | `optee-os` |

사용자에게 벤더를 확인하고 해당 recipe명으로 실행한다.

### 메뉴 7: SDK 생성

```bash
bitbake -c populate_sdk {이미지명}
```

### 메뉴 8: 환경 체크

Check 1~3을 수동 실행하고 결과를 보여준다:

```
환경 체크 결과:

  MACHINE: stm32mp257f-ev1-mycompany
  DISTRO: openstlinux-weston
  ACCEPT_EULA: 설정됨
  bblayers: meta-mycompany 등록됨
  빌드 환경: bitbake 사용 가능
  DL_DIR: /opt/yocto/downloads
  SSTATE_DIR: (기본값)
```

### 메뉴 9: 리포트 생성

빌드 없이 기존 빌드 산출물에서 release note + SBOM을 생성한다.
빌드 산출물 디렉토리(`tmp-glibc/deploy/`)가 존재해야 한다.

사용자에게 이미지 이름을 확인한 뒤, 아래 "빌드 리포트 생성 (Release Note)" 및 "SBOM" 절차를 바로 실행한다.

