---
name: yocto-stm32-bsp
classification: workflow
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  STM32MP BSP 커스터마이징 스킬. Kernel/U-Boot/TF-A/OP-TEE의 defconfig, DTS, patch, 소스 fork.
  Triggers: stm32 bsp, stm32mp kernel, stm32 dts, TF-A 설정, OP-TEE, 부트로더
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---
# Yocto BSP

Kernel, U-Boot, TF-A, OP-TEE 커스터마이징을 자동화한다.

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
- `pip install -r overlay/skills/yocto-stm32-bsp/scripts/requirements.txt`

## 외부 스크립트 참조

- `yocto-setup/scripts/gl_ensure_project.py` — 내부 GitLab repo 생성
- `yocto-setup/scripts/manifest_local.py` — manifest 업데이트
- `yocto-recipe/scripts/bbappend_create.py` — bbappend 생성

## 스크립트 레퍼런스

### kernel_info.py — BSP 컴포넌트 정보 추출

```bash
python overlay/skills/yocto-stm32-bsp/scripts/kernel_info.py \
  --search-path $YOCTO_WORK_DIR/sources/ \
  --type kernel    # kernel | uboot | tfa | optee
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--search-path` | O | sources/ 경로 |
| `--type` | O | `kernel`, `uboot`, `tfa`, `optee` |

## 절차

실행 시 메뉴를 표시한다:

```
Yocto BSP:

1. Kernel 작업     — defconfig, DTS, patch, 소스 fork
2. U-Boot 작업     — defconfig, DTS, patch, 소스 fork
3. TF-A 작업       — 설정, patch, 소스 fork
4. OP-TEE 작업     — 설정, patch, 소스 fork
```

> STM32MP2 부트 체인: TF-A → OP-TEE → U-Boot → Kernel


### a. defconfig/설정 수정

**Step 1: 현재 정보 확인**

```bash
python overlay/skills/yocto-stm32-bsp/scripts/kernel_info.py \
  --search-path $YOCTO_WORK_DIR/sources/ --type {type}
```

**Step 2: cfg fragment 생성 (kernel/uboot)**

`sources/meta-{PROJECT_NAME}/{recipe-dir}/files/{PROJECT_NAME}.cfg`:
```
CONFIG_USB_GADGET=y
CONFIG_USB_ETH=m
# CONFIG_DEBUG_INFO is not set
```

> cfg 규칙: `=y`, `=m`, `is not set` 사용. `=n`은 사용하지 않는다.

**Step 2 (TF-A): bbappend에 변수 설정**

```
TFA_DEVICETREE = "stm32mp257f-{PROJECT_NAME}"
EXTRA_OEMAKE:append = " STM32MP_SDMMC=1"
```

**Step 2 (OP-TEE): bbappend에 변수 설정**

```
OPTEEMACHINE = "stm32mp2"
```

**Step 3: bbappend 생성/수정**

```bash
python overlay/skills/yocto-stm32-recipe/scripts/bbappend_create.py \
  --recipe {recipe 경로} \
  --layer $YOCTO_WORK_DIR/sources/meta-$YOCTO_PROJECT_NAME
```

bbappend에 추가:
```
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://{PROJECT_NAME}.cfg"
```

### b. DTS 수정 (Kernel, U-Boot)

**Step 1: 현재 DTS 파일 확인**

```bash
find $YOCTO_WORK_DIR/sources/ -path "*/arch/arm*/boot/dts/*stm32mp*" -name "*.dts" | head -20
```

**Step 2: 수정 방식 선택**

```
DTS 수정 방식:
a. DTS overlay (dtso) — bbappend + overlay 파일 (권장)
b. DTS 직접 수정 — 소스 fork 필요
```

**Step 3a (overlay):**

`sources/meta-{PROJECT_NAME}/{recipe-dir}/files/{PROJECT_NAME}-overlay.dtso` 생성 후 bbappend에 추가.

**Step 3b (직접 수정):** → 서브메뉴 d (소스 fork)로 진행.

### c. patch 추가

patch 파일을 `meta-{PROJECT_NAME}/{recipe-dir}/files/` 에 배치 → bbappend에 `SRC_URI += "file://0001-xxx.patch"` 추가.

### d. 소스 fork & 수정

**Step 1:** kernel_info.py로 소스 정보 확인

**Step 2:** 내부 GitLab에 repo 생성

```bash
python overlay/skills/yocto-stm32-setup/scripts/gl_ensure_project.py \
  --group $YOCTO_INTERNAL_GITLAB_GROUP --name {repo명}
```

**Step 3:** 내부에 push

```bash
cd $YOCTO_WORK_DIR/sources/{소스 디렉토리}
git remote add internal {PROJECT_HTTP_URL} 2>/dev/null || true
git push internal HEAD:$YOCTO_MANIFEST_BRANCH-$YOCTO_PROJECT_NAME
```

**Step 4:** 사용자와 AI 대화하며 소스 수정

**Step 5:** commit & push

**Step 6:** bbappend로 SRC_URI/SRCREV override

```
SRC_URI:remove = "git://{외부URL}..."
SRC_URI:prepend = "git://{내부URL}/{repo}.git;branch={BRANCH}-{PROJECT_NAME};protocol=http "
SRCREV = "{새 commit hash}"
```

**Step 7:** local_manifests 업데이트

```bash
python overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml \
  --action switch-remote \
  --project {repo명} --remote-name internal \
  --remote-fetch "$GITLAB_URL/$YOCTO_INTERNAL_GITLAB_GROUP" \
  --revision $YOCTO_MANIFEST_BRANCH-$YOCTO_PROJECT_NAME
```

### e. 현재 설정 확인

```bash
python overlay/skills/yocto-stm32-bsp/scripts/kernel_info.py \
  --search-path $YOCTO_WORK_DIR/sources/ --type {type}
```

### f. DTS 비교 (dts-diff)

레퍼런스 DTS와 커스텀 DTS를 정규화하여 비교한다.
`dtc` (device-tree-compiler)가 필요하다.

**Step 1: DTS 파일 찾기**

```bash
find $YOCTO_WORK_DIR/sources/ -name "stm32mp215f-dk.dts" -type f
find $YOCTO_WORK_DIR/sources/ -name "stm32mp215f-{PROJECT_NAME}.dts" -type f
```

**Step 2: 정규화 후 비교**

DTS를 DTB로 컴파일 후 다시 DTS로 디컴파일하면 include 해소 + 정렬되어 정확한 비교가 가능:

```bash
# 레퍼런스 DTS 정규화
cpp -nostdinc -I {include_dirs} -undef -x assembler-with-cpp reference.dts | \
  dtc -I dts -O dtb -p 0x1000 - | \
  dtc -I dtb -O dts -s - > ref_normalized.dts

# 커스텀 DTS 정규화
cpp -nostdinc -I {include_dirs} -undef -x assembler-with-cpp custom.dts | \
  dtc -I dts -O dtb -p 0x1000 - | \
  dtc -I dtb -O dts -s - > custom_normalized.dts

# 비교
diff -u ref_normalized.dts custom_normalized.dts
```

> include 경로는 커널 소스의 `arch/arm64/boot/dts/` 및 `include/dt-bindings/`를 포함해야 한다.

**Step 3: 차이점 문서화**

변경된 노드를 정리하여 `docs/hardware/pinmap/{board-name}-dts-diff.md`에 저장:

```markdown
| Node | Change | Reference | Custom | Impact |
|------|--------|-----------|--------|--------|
| &sdmmc1 | bus-width | <4> | <8> | eMMC 8-bit |
| &eth1 | phy-handle | <&phy0> | <&phy1> | PHY 변경 |
```

**간단한 비교 (dtc 없이)**

DTS 소스를 직접 비교할 수도 있다. 단, include가 해소되지 않으므로 dtsi 차이는 보이지 않음:

```bash
diff -u reference.dts custom.dts
```

## 주의사항

- SRCREV는 정확한 commit hash로 지정해야 재현성이 보장된다.
- `SRC_URI:remove`는 정확한 문자열 매치가 필요하다. 원본 recipe를 확인 후 작성.
- cfg fragment는 `=y`, `=m`, `is not set` 형태. `=n`은 사용하지 않는다.
- DTS overlay(`.dtso`)는 kernel 5.x+. 이전 버전은 소스 fork로 직접 수정.
- DTS 비교 시 `dtc`가 필요하다. `sudo apt install device-tree-compiler`로 설치.
