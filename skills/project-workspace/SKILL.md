---
name: project-workspace
classification: workflow
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  프로젝트 워크스페이스 구성 스킬. git submodule + Kconfig + Makefile 빌드 시스템 생성.
  Triggers: 워크스페이스 구성, 빌드 환경, workspace setup, platform add
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---
# Project Workspace

프로젝트의 소스 구조(git submodule)와 빌드 시스템(Kconfig + Makefile)을 한번에 구성한다.

## !! 시작 전 필수 준비 !!

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  이 스킬을 실행하기 전에 아래 항목을 반드시 정해두세요:            ║
║                                                                  ║
║  1. 각 컴포넌트의 Git Repository URL                             ║
║     - kernel:      http://gitlab/group/linux-stm32mp.git         ║
║     - uboot:       http://gitlab/group/u-boot-stm32mp.git       ║
║     - application: http://gitlab/group/my-app.git                ║
║     - (필요한 만큼 추가)                                          ║
║                                                                  ║
║  2. 각 컴포넌트의 Branch (또는 Tag)                               ║
║     - kernel:      scarthgap-mycompany                           ║
║     - uboot:       scarthgap-mycompany                           ║
║     - application: main                                          ║
║                                                                  ║
║  3. SDK/Toolchain 설치 경로                                      ║
║     - /opt/yocto-sdk/stm32mp2                                    ║
║                                                                  ║
║  4. 타겟 보드 IP (배포용)                                         ║
║     - 192.168.1.100                                              ║
║                                                                  ║
║  repo URL과 branch가 정해지지 않으면 구성할 수 없습니다.          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

## 전제 조건

- Git 설치
- Python 3.6+ 및 `kconfiglib`: `pip install kconfiglib`
- SDK 또는 cross-compiler toolchain 설치 (플랫폼 등록 시)
- 각 컴포넌트의 **Git repo URL과 branch가 확정**되어 있어야 한다

## 최종 프로젝트 구조

```
project.git/                         ← 메인 repo
  make/                              ← 빌드 시스템
    Makefile                         ← 통합 빌드 오케스트레이터
    Kconfig                          ← 프로젝트 설정 (menuconfig)
    .config                          ← 현재 활성 설정
    include.mk                       ← .config 변환 (자동 생성)
    platform/
      native.mk                     ← x86 native
      stm32mp2.mk                   ← cross 플랫폼
    cmake/
      toolchain-stm32mp2.cmake
    configs/                         ← 저장된 defconfig
      stm32mp2_full_defconfig
    build/                           ← cmake 빌드 디렉토리 (자동 생성)
    output/                          ← 산출물 수집 (make collect)
  kernel/                            ← git submodule
  uboot/                             ← git submodule
  application/                       ← git submodule
  firmware/                          ← git submodule (선택)
  .gitmodules                        ← submodule 정의
  .gitignore
```

## 스크립트 레퍼런스

### detect_toolchain.py — SDK 자동 감지

```bash
python overlay/skills/project-workspace/scripts/detect_toolchain.py \
  --sdk-path /opt/yocto-sdk/stm32mp2
```

### generate_platform.py — 플랫폼 설정 생성

```bash
python overlay/skills/project-workspace/scripts/generate_platform.py \
  --name stm32mp2 \
  --sdk-path /opt/yocto-sdk/stm32mp2 \
  --cross-compile /opt/.../aarch64-poky-linux- \
  --arch arm64 \
  --sysroot /opt/.../cortexa35-poky-linux \
  --output-dir make/
```

### generate_kconfig.py — Kconfig 생성

```bash
python overlay/skills/project-workspace/scripts/generate_kconfig.py \
  --output make/ \
  --components kernel uboot application \
  --platforms stm32mp2
```

### generate_makefile.py — Makefile 생성

```bash
python overlay/skills/project-workspace/scripts/generate_makefile.py --output make/
```

## 절차

실행 시 메뉴를 표시한다:

```
Project Workspace:

1. 전체 구성     — submodule + make/ 빌드 시스템 생성 (최초 1회)
2. 플랫폼 추가   — SDK 경로로 새 플랫폼 등록
3. 컴포넌트 추가 — git submodule 추가
4. 빌드 안내     — 사용법 안내
```


### 메뉴 2: 플랫폼 추가

1. SDK 경로 입력 → `detect_toolchain.py`
2. `generate_platform.py`로 설정 생성
3. Kconfig에 플랫폼 항목 추가
4. defconfig 저장


### 메뉴 4: 빌드 안내

```bash
cd project/make

# 설정
make menuconfig                    # 대화형 프로젝트 설정
make xxx_defconfig                 # 저장된 설정 로드
make savedefconfig NAME=xxx        # 현재 설정 저장

# 커널
make kernel                        # 커널 빌드
make kernel-menuconfig             # 커널 menuconfig
make kernel-modules-dir M=path     # 특정 모듈만 (수 초)

# U-Boot
make uboot
make uboot-menuconfig

# 앱
make application                   # cmake/make 자동 감지

# 전체
make all                           # 활성화된 컴포넌트 전체

# 산출물 수집
make collect                       # output/{platform}/에 결과 모음

# 배포
make deploy                        # 타겟에 전체 배포
make deploy-module M=path          # 모듈 하나 배포 + insmod

# 플랫폼 전환 (같은 터미널)
make PLATFORM=stm32mp2 kernel
make PLATFORM=imx kernel
make PLATFORM=native application
```

## 다른 개발자가 참여할 때

```bash
# 1. clone (submodule 포함)
git clone --recurse-submodules {project URL}

# 2. SDK 설치 (별도)

# 3. 플랫폼 등록
#    AI: "플랫폼 추가 해줘" → project-workspace 메뉴 2

# 4. defconfig 로드 + 빌드
cd make
make stm32mp2_default_defconfig
make all
```

## submodule 작업 흐름

```bash
# 컴포넌트 안에서 개발
cd kernel
git checkout -b dev/my-driver
# ... 수정, 커밋, push ...

# 메인 repo에서 submodule 커밋 업데이트
cd ..
git add kernel
git commit -m "kernel: update to dev/my-driver HEAD"

# 다른 개발자가 최신 받기
git pull && git submodule update --init --recursive
```

## ccache

Kconfig에서 활성화 (기본 ON). 재빌드 시간 대폭 단축.

```bash
sudo apt install ccache
make info                  # ccache ON/OFF 확인
```

## 산출물 수집

```bash
make collect
```

```
make/output/{platform}/
  boot/Image, *.dtb, u-boot.bin
  modules/lib/modules/...
  app/...
  version.txt              # 플랫폼, 날짜, git describe
```

## project-bootstrap과의 관계

| 스킬 | 역할 | 호출 |
|------|------|------|
| `project-bootstrap` | AI 에이전트 규칙/프로세스 | "프로젝트 부트스트랩 해줘" |
| `project-workspace` | 소스 구조 + 빌드 시스템 | "워크스페이스 구성 해줘" |

프로젝트 시작 시 순서:
1. `project-bootstrap` → AI rules, docs 구조
2. `project-workspace` → submodule + make/ + SDK

## 주의사항

- **repo URL과 branch를 먼저 정하세요.** 정해지지 않으면 submodule을 추가할 수 없습니다.
- `source environment-setup-*.sh`는 사용하지 않는다.
- 모든 빌드 명령은 `make/` 디렉토리에서 실행한다.
- submodule 안에서 작업 후 메인 repo에서 `git add {submodule}` 커밋 필요.
- `kconfiglib` 필요: `pip install kconfiglib`
- `make/.config`, `make/include.mk`, `make/build/`, `make/output/`은 `.gitignore` 대상.
