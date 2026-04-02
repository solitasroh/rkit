---
name: yocto-stm32-setup
classification: workflow
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  STM32MP Yocto 빌드 환경 구성 스킬. repo init/sync, custom layer/machine 생성, GitLab push 자동화.
  Triggers: yocto setup, yocto 셋업, stm32 yocto, stm32mp setup, 환경 구성
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---
# Yocto Setup

Yocto 빌드 환경을 구성하고, 변경사항을 내부 GitLab에 자동 push한다.

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

- `repo` 명령이 설치되어 있어야 한다 (repo 모드) 또는 `git` (ti-oe 모드)
- `.env` 파일에 GitLab 접속 정보와 Yocto 환경변수가 설정되어 있어야 한다:
  - `GITLAB_URL`, `GITLAB_TOKEN` — 내부 GitLab 접속
  - `YOCTO_MANIFEST_URL`, `YOCTO_MANIFEST_BRANCH` — repo manifest
  - `YOCTO_PROJECT_NAME` — 프로젝트/회사 식별자
  - `YOCTO_WORK_DIR` — 작업 디렉토리
  - `YOCTO_INTERNAL_GITLAB_GROUP` — 내부 GitLab group path
- `pip install -r overlay/skills/yocto-stm32-setup/scripts/requirements.txt`
- 빌드 환경 초기화 관련: `YOCTO_SETUP_SCRIPT`, `YOCTO_DISTRO`, `YOCTO_BUILD_DIR` (선택)

## 네이밍 규칙

`YOCTO_PROJECT_NAME` 값을 기반으로:

| 항목 | 패턴 | 예시 (PROJECT_NAME=mycompany) |
|------|------|------|
| Custom layer | `meta-{PROJECT_NAME}` | `meta-mycompany` |
| Custom machine | `{BASE_MACHINE}-{PROJECT_NAME}` | `stm32mp21-disco-mycompany` |
| 내부 branch | `{MANIFEST_BRANCH}-{PROJECT_NAME}` | `scarthgap-mycompany` |

## 스크립트 레퍼런스

### gl_ensure_group.py — 내부 GitLab group 확인/생성

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/gl_ensure_group.py --path yocto-stm32mp2
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--path` | O | group path |
| `--name` | × | 표시 이름 (미지정 시 path 사용) |
| `--visibility` | × | `private` (기본) |

출력: `GROUP_ID=42`, `GROUP_EXISTS=true/false`, `GROUP_PATH`, `GROUP_URL`

### gl_ensure_project.py — 내부 GitLab project 확인/생성

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/gl_ensure_project.py --group yocto-stm32mp2 --name meta-mycompany
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--group` | O | group path 또는 ID |
| `--name` | O | 프로젝트 이름 |
| `--visibility` | × | `private` (기본) |
| `--description` | × | 프로젝트 설명 |

출력: `PROJECT_ID`, `PROJECT_EXISTS=true/false`, `PROJECT_HTTP_URL`, `PROJECT_URL`

### manifest_parse.py — manifest 파싱

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_parse.py --manifest .repo/manifests/default.xml
```

출력: JSON (`remotes`, `projects` 배열)

### manifest_local.py — local_manifests XML 관리

```bash
# project 추가
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file .repo/local_manifests/custom.xml \
  --action add-project \
  --remote-name internal \
  --remote-fetch "$GITLAB_URL/$YOCTO_INTERNAL_GITLAB_GROUP" \
  --project meta-mycompany \
  --revision main \
  --path sources/meta-mycompany

# remote 전환
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file .repo/local_manifests/custom.xml \
  --action switch-remote \
  --project meta-st-x-linux-qt \
  --remote-name internal \
  --remote-fetch "$GITLAB_URL/$YOCTO_INTERNAL_GITLAB_GROUP" \
  --revision scarthgap-mycompany

# 현재 상태 출력
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file .repo/local_manifests/custom.xml \
  --action list
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--file` | O | local manifest XML 경로 |
| `--action` | O | `add-project`, `switch-remote`, `remove-project`, `list` |
| `--remote-name` | action별 | remote 이름 |
| `--remote-fetch` | × | remote fetch URL |
| `--project` | action별 | project name |
| `--revision` | × | branch/tag |
| `--path` | × | checkout path |

### layer_create.py — layer 골격 생성

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/layer_create.py \
  --name meta-mycompany \
  --path sources/meta-mycompany \
  --compat scarthgap \
  --depends core
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--name` | O | layer 이름 (예: meta-mycompany) |
| `--path` | O | layer 생성 경로 |
| `--priority` | × | layer 우선순위 (기본: 10) |
| `--compat` | × | LAYERSERIES_COMPAT (기본: scarthgap). `$YOCTO_MANIFEST_BRANCH` 사용 |
| `--depends` | × | LAYERDEPENDS (기본: core) |
| `--project` | × | 프로젝트 식별자 (skel recipe명에 사용, 미지정 시 layer 이름에서 추출) |

이미 존재하면 SKIP. 생성 항목:
- `conf/layer.conf` — BBFILES 패턴 포함
- `conf/machine/`
- `recipes-core/images/`
- `recipes-core/{project}-skel/{project}-skel.bb` — rootfs skeleton recipe (자동 생성)
- `recipes-core/{project}-skel/files/etc/{project}/config.conf` — 기본 설정 파일
- `recipes-core/{project}-skel/files/usr/bin/` — 실행 스크립트 디렉토리
- `recipes-kernel/linux/`
- `recipes-bsp/u-boot/`

skel recipe는 프로젝트 전용 설정 파일/스크립트를 rootfs에 포함하는 용도이다.
image recipe에서 `IMAGE_INSTALL:append = " {project}-skel"` 로 포함한다.
layer 이름에 유효하지 않은 문자(공백, `/` 등)가 있으면 오류로 종료한다.

### machine_copy.py — machine conf 복사

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/machine_copy.py \
  --source stm32mp257f-ev1 \
  --target stm32mp257f-ev1-mycompany \
  --search-path sources/ \
  --dest sources/meta-mycompany/conf/machine/
```

이미 존재하면 SKIP. 복사 후 include/require 참조 파일 목록도 출력한다.

### bblayers_add.py — bblayers.conf layer 등록 확인

```bash
# 현재 등록된 layer 목록
python3 overlay/skills/yocto-stm32-setup/scripts/bblayers_add.py \
  --bblayers-conf $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/conf/bblayers.conf \
  --list

# 특정 layer 등록 여부 확인
python3 overlay/skills/yocto-stm32-setup/scripts/bblayers_add.py \
  --bblayers-conf $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/conf/bblayers.conf \
  --check /path/to/meta-mycompany /path/to/meta-st-x-linux-qt
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--bblayers-conf` | O | bblayers.conf 파일 경로 |
| `--check` | × | 확인할 layer 경로(들) |
| `--list` | × | 현재 등록된 layer 전체 출력 |

출력: `PRESENT:` / `MISSING:` + 등록 필요 시 `bitbake-layers add-layer` 명령 제시.
실제 등록은 이 스크립트가 아닌, AI가 빌드 환경 source 후 `bitbake-layers add-layer`를 실행한다.

### repo_status.py — 변경된 repo 감지

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/repo_status.py --work-dir ./yocto-build
```

출력: JSON 배열 `[{"path": "sources/xxx", "changes": 3, "status": "modified"}, ...]`

## 절차

실행 시 메뉴를 표시한다:

```
Yocto 환경 설정:

1. 전체 셋업     — repo init/sync + layer/machine 생성 (최초 1회)
2. 동기화/Push   — 변경사항 감지 → commit/push (반복 실행)
3. 패키지 추가   — 외부 repo를 manifest에 추가
```

### 메뉴 1: 전체 셋업

#### Step 1: 환경 확인

`.env`에서 GitLab 접속 정보와 Yocto 환경변수를 확인한다.

**공통 필수:**
- `.env`: `GITLAB_URL`, `GITLAB_TOKEN`
- `.env`: `YOCTO_FETCH_TOOL`, `YOCTO_PROJECT_NAME`, `YOCTO_WORK_DIR`, `YOCTO_BASE_MACHINE`, `YOCTO_INTERNAL_GITLAB_GROUP`

**YOCTO_FETCH_TOOL=repo (ST, NXP) 일 때 추가 필수:**
- `YOCTO_MANIFEST_URL`, `YOCTO_MANIFEST_BRANCH`
- NXP는 `YOCTO_MANIFEST_FILE`도 확인 (비어있으면 default.xml 사용)

**YOCTO_FETCH_TOOL=ti-oe (TI) 일 때 추가 필수:**
- `YOCTO_TI_LAYERSETUP_URL`, `YOCTO_TI_CONFIG`

하나라도 없으면 안내 후 종료:

```
.env 파일에 아래 값을 설정해 주세요:

YOCTO_MANIFEST_URL=https://github.com/STMicroelectronics/oe-manifest.git
YOCTO_MANIFEST_BRANCH=scarthgap
YOCTO_PROJECT_NAME=mycompany
YOCTO_WORK_DIR=./yocto-build
YOCTO_BASE_MACHINE=stm32mp21-disco
YOCTO_INTERNAL_GITLAB_GROUP=yocto-stm32mp2
```

#### Step 2: 소스 가져오기

`YOCTO_FETCH_TOOL` 값에 따라 분기한다.

**2-A. repo 모드 (ST, NXP):**

```bash
mkdir -p $YOCTO_WORK_DIR
cd $YOCTO_WORK_DIR
repo init -u $YOCTO_MANIFEST_URL -b $YOCTO_MANIFEST_BRANCH
repo sync
```

NXP에서 `YOCTO_MANIFEST_FILE`이 설정되어 있으면:
```bash
repo init -u $YOCTO_MANIFEST_URL -b $YOCTO_MANIFEST_BRANCH -m $YOCTO_MANIFEST_FILE
repo sync
```

이미 `.repo`가 있으면 `repo sync`만 실행한다.

**재셋업 (빌드 디렉토리 삭제 후 다시 시작):**

`.repo`가 없고 프로젝트 루트의 `conf/local-manifest.xml`이 존재하면,
이전 셋업에서 저장한 manifest를 복원하여 GitLab의 기존 repo를 받아온다:

**GitLab 인증 설정 (internal remote 사용 시):**

local_manifests에 내부 GitLab remote가 포함되어 있으면, repo sync 전에 git credential을 설정한다:

```bash
# .env에서 토큰 로드
source <프로젝트 루트>/.env
echo "http://oauth2:${GITLAB_TOKEN}@<GITLAB_HOST>" >> ~/.git-credentials
git config --global credential.helper store
```

> 이미 설정되어 있으면 건너뛴다. repo sync가 인증 프롬프트에서 멈추는 것을 방지한다.

```bash
mkdir -p $YOCTO_WORK_DIR && cd $YOCTO_WORK_DIR
repo init -u $YOCTO_MANIFEST_URL -b $YOCTO_MANIFEST_BRANCH
mkdir -p .repo/local_manifests
cp <프로젝트 루트>/conf/local-manifest.xml .repo/local_manifests/custom.xml
repo sync
```

복원 후 `repo sync`가 성공하면 **Step 3~9를 건너뛰고 Step 10으로** 진행한다.
(local_manifests에 이미 모든 추가 repo와 custom layer가 등록되어 있으므로)

**2-B. ti-oe 모드 (TI AM6x):**

```bash
git clone $YOCTO_TI_LAYERSETUP_URL $YOCTO_WORK_DIR
cd $YOCTO_WORK_DIR
./oe-layertool-setup.sh -f configs/processor-sdk/$YOCTO_TI_CONFIG
```

이미 `oe-layertool-setup.sh`가 있으면 재실행으로 layer를 업데이트한다.

> TI 모드에서는 `local_manifests` 대신 직접 layer를 clone하고 `bblayers.conf`에 등록한다.
> `manifest_local.py`는 사용하지 않는다.

#### Step 3: 외부 추가 패키지

`YOCTO_EXTRA_REPOS`가 설정되어 있으면 각 repo를 local_manifests에 추가:

```bash
# 각 repo에 대해
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml \
  --action add-project \
  --remote-name st-github \
  --remote-fetch $YOCTO_EXTRA_REPOS_REMOTE \
  --project {repo} \
  --revision $YOCTO_EXTRA_REPOS_BRANCH \
  --path {layer_path}/{repo}
```

> **layer path 규칙**: ST는 `layers/meta-st/` (벤더 layer) 또는 `layers/` (독립 layer), NXP/TI는 `sources/`.
> default.xml의 기존 project path 패턴을 따른다.

추가 후:
```bash
cd $YOCTO_WORK_DIR && repo sync
```

`YOCTO_EXTRA_REPOS`가 비어있으면 이 단계를 건너뛴다.

> **TI 모드**: `local_manifests` 대신 직접 `git clone`하고 Step 11에서 `bitbake-layers add-layer`로 등록한다:
> ```bash
> cd $YOCTO_WORK_DIR/sources
> git clone {remote URL}/{repo}.git -b {branch}
> ```

#### Step 4: 내부 GitLab group 확인/생성

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/gl_ensure_group.py \
  --path $YOCTO_INTERNAL_GITLAB_GROUP
```

#### Step 5: custom layer 생성

custom layer 디렉토리가 이미 있으면 skip.

> **layer 경로**: ST는 `$YOCTO_WORK_DIR/layers/meta-st/meta-{PROJECT_NAME}`, NXP/TI는 `$YOCTO_WORK_DIR/sources/meta-{PROJECT_NAME}`.

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/layer_create.py \
  --name meta-$YOCTO_PROJECT_NAME \
  --path $YOCTO_WORK_DIR/{layer_path}/meta-$YOCTO_PROJECT_NAME \
  --compat $YOCTO_MANIFEST_BRANCH \
  --project $YOCTO_PROJECT_NAME
```

> skel recipe (`{PROJECT_NAME}-skel`)가 자동 생성된다. image recipe에서 포함하면 rootfs에 설정 파일이 들어간다.

#### Step 6: machine conf 복사

`YOCTO_TARGET_MACHINE`이 설정되어 있으면 그 값을 사용. 없으면 `{YOCTO_BASE_MACHINE}-{YOCTO_PROJECT_NAME}`.

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/machine_copy.py \
  --source $YOCTO_BASE_MACHINE \
  --target $YOCTO_TARGET_MACHINE \
  --search-path $YOCTO_WORK_DIR/{layers_root}/ \
  --dest $YOCTO_WORK_DIR/{layer_path}/meta-$YOCTO_PROJECT_NAME/conf/machine/
```

> ST: `--search-path $YOCTO_WORK_DIR/layers/`, NXP/TI: `--search-path $YOCTO_WORK_DIR/sources/`

#### Step 7: machine conf 수정

복사된 machine conf의 내용을 사용자에게 보여주고, 수정이 필요한 부분을 대화로 진행한다:
- machine 이름 변경 (파일 내 참조)
- include 경로 확인
- 필요한 MACHINE_FEATURES 추가/제거

#### Step 8: 내부 GitLab에 push

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/gl_ensure_project.py \
  --group $YOCTO_INTERNAL_GITLAB_GROUP \
  --name meta-$YOCTO_PROJECT_NAME

cd $YOCTO_WORK_DIR/{layer_path}/meta-$YOCTO_PROJECT_NAME
git init
git add -A
git commit -m "Initial meta-$YOCTO_PROJECT_NAME layer"
git remote add origin {PROJECT_HTTP_URL}
git push -u origin main
```

`PROJECT_HTTP_URL`은 gl_ensure_project.py 출력에서 가져온다.

#### Step 9: local_manifests에 추가

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml \
  --action add-project \
  --remote-name internal \
  --remote-fetch "$GITLAB_URL/$YOCTO_INTERNAL_GITLAB_GROUP" \
  --project meta-$YOCTO_PROJECT_NAME \
  --revision main \
  --path {layer_path}/meta-$YOCTO_PROJECT_NAME
```

> ST: `--path layers/meta-st/meta-{PROJECT_NAME}`, NXP/TI: `--path sources/meta-{PROJECT_NAME}`

**GitLab 인증 설정 (internal remote 사용 시):**

local_manifests에 내부 GitLab remote가 포함되어 있으면, 이후 repo sync 전에 git credential을 설정한다:

```bash
# .env에서 토큰 로드
source <프로젝트 루트>/.env
echo "http://oauth2:${GITLAB_TOKEN}@<GITLAB_HOST>" >> ~/.git-credentials
git config --global credential.helper store
```

> 이미 설정되어 있으면 건너뛴다. repo sync가 인증 프롬프트에서 멈추는 것을 방지한다.

#### Step 9-1: local-manifest.xml 백업

셋업 완료 후, 재셋업 시 복원할 수 있도록 manifest를 프로젝트 루트에 백업한다:

```bash
cp $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml <프로젝트 루트>/conf/local-manifest.xml
```

이 파일을 git에 커밋해 두면, 빌드 디렉토리를 삭제해도 Step 2 재셋업 경로로 복원 가능하다.

#### Step 10: 빌드 환경 초기화

**10-1. 초기화 스크립트 결정:**

`YOCTO_SETUP_SCRIPT`가 설정되어 있으면 그대로 사용.
비어있으면 사용자에게 선택을 물어본다:

```
빌드 환경 초기화 방식을 선택해 주세요:

1. poky 기본:  source sources/poky/oe-init-build-env build/
2. ST 전용:    DISTRO={DISTRO} MACHINE={MACHINE} source layers/meta-st/scripts/envsetup.sh
3. NXP 전용:   DISTRO={DISTRO} MACHINE={MACHINE} source imx-setup-release.sh -b build
4. TI 전용:    . conf/setenv
5. 직접 입력:  사용자가 명령을 입력
```

**10-2. 빌드 환경 source:**

`YOCTO_SETUP_SCRIPT`가 설정되어 있으면 그대로 실행.
비어있으면 사용자가 위 메뉴에서 선택한 방식으로 실행:

```bash
cd $YOCTO_WORK_DIR
source {YOCTO_SETUP_SCRIPT}
```

벤더별 예시:
```bash
# ST
DISTRO=openstlinux-weston MACHINE=$YOCTO_TARGET_MACHINE source layers/meta-st/scripts/envsetup.sh

# NXP
DISTRO=fsl-imx-xwayland MACHINE=$YOCTO_TARGET_MACHINE source imx-setup-release.sh -b $YOCTO_BUILD_DIR

# TI
cd $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR && . conf/setenv

# poky
source sources/poky/oe-init-build-env $YOCTO_BUILD_DIR
```

> **주의**: `source` 명령은 현재 shell 환경을 변경한다.
> Bash 도구에서 실행 시 매번 source를 먼저 실행해야 bitbake 명령이 동작한다.

**10-2b. 빌드 환경 검증:**

source 후 bitbake가 사용 가능한지 확인한다:

```bash
cd $YOCTO_WORK_DIR
source {SETUP_SCRIPT} && which bitbake
```

`which bitbake`가 실패하면 source 스크립트 경로를 확인하고 사용자에게 안내한다.

**10-3. local.conf 설정 확인:**

```bash
# MACHINE 확인/설정
grep -q "^MACHINE" $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/conf/local.conf
```

MACHINE이 설정 안 되어 있으면 추가:
```
MACHINE = "{YOCTO_TARGET_MACHINE}"
```

DISTRO가 `.env`에 있으면 확인/추가:
```
DISTRO = "{YOCTO_DISTRO}"
```

**10-4. EULA / 라이선스 설정 (벤더별):**

`.env`의 EULA 변수를 확인하고 해당하는 것만 local.conf에 추가:

ST (`YOCTO_ACCEPT_EULA=1`):
```
ACCEPT_EULA_{YOCTO_TARGET_MACHINE} = "1"
```

NXP (`YOCTO_ACCEPT_FSL_EULA=1`):
```
ACCEPT_FSL_EULA = "1"
```

TI (`YOCTO_TI_LICENSE_FLAGS` 설정 시):
```
LICENSE_FLAGS_ACCEPTED += "{YOCTO_TI_LICENSE_FLAGS}"
```

> 해당 EULA 변수가 비어있으면 이 설정을 건너뛴다.

**10-5. Secure Boot 설정 (선택):**

`.env`에 `YOCTO_SECURE_BOOT_CONF`가 설정되어 있으면 local.conf에 다음을 추가:
```
# Secure Boot
SECURE_BOOT_KEYS_DIR = "<키 디렉토리 절대경로>"
STM32_SIGNING_TOOL = "<자동 탐색된 경로>"
include <YOCTO_SECURE_BOOT_CONF의 절대경로>
```

- `SECURE_BOOT_KEYS_DIR`은 `YOCTO_SECURE_BOOT_CONF` 파일이 있는 디렉토리의 절대경로로 설정한다.
- `STM32_SIGNING_TOOL`은 다음 순서로 자동 탐색한다:
  1. `which STM32_SigningTool_CLI`
  2. 기본 설치 경로 탐색: `/opt/st/STM32CubeProgrammer/bin/`, `$HOME/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin/` 등
  3. 못 찾으면 placeholder를 넣고 사용자에게 안내
- `yocto-secure-boot.conf` 내부에서 `${SECURE_BOOT_KEYS_DIR}/...`, `${STM32_SIGNING_TOOL}`로 참조하므로 conf 파일 자체에는 절대경로가 없다.

> `YOCTO_SECURE_BOOT_CONF`가 비어있으면 이 설정을 건너뛴다.
> 상대경로로 설정된 경우 프로젝트 루트 기준으로 절대경로를 계산한다.
> `generate_keys.sh`로 생성한 `yocto-secure-boot.conf` 파일을 지정한다.

**10-6. 빌드 성능 설정 (선택):**

`.env`에 `YOCTO_DL_DIR`, `YOCTO_SSTATE_DIR`이 있으면 local.conf에 추가:

> **상대경로 처리**: 값이 상대경로(`../` 등)이면 **프로젝트 루트(stm32_workspace) 기준으로 절대경로를 계산**하여 local.conf에 기록한다.
> bitbake는 local.conf의 상대경로를 `${TOPDIR}`(빌드 디렉토리) 기준으로 해석하므로, 의도와 다른 위치를 참조하게 된다.

```
DL_DIR = "{절대경로로 변환된 YOCTO_DL_DIR}"
SSTATE_DIR = "{절대경로로 변환된 YOCTO_SSTATE_DIR}"
```

추가 권장 설정 (사용자에게 확인):
```
# 빌드 병렬 수 (CPU 코어 수에 맞게)
BB_NUMBER_THREADS = "8"
PARALLEL_MAKE = "-j 8"
```

#### Step 11: bblayers.conf에 layer 등록

**11-1. 현재 등록 상태 확인:**

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/bblayers_add.py \
  --bblayers-conf $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/conf/bblayers.conf \
  --check $YOCTO_WORK_DIR/sources/meta-$YOCTO_PROJECT_NAME
```

EXTRA_REPOS가 있으면 해당 layer들도 함께 확인한다.

**11-2. 누락된 layer 등록:**

빌드 환경 source 후 bitbake-layers로 등록:

```bash
cd $YOCTO_WORK_DIR
source {SETUP_SCRIPT}  # 10-2에서 결정한 스크립트
bitbake-layers add-layer $YOCTO_WORK_DIR/sources/meta-$YOCTO_PROJECT_NAME
```

EXTRA_REPOS의 layer도 마찬가지:
```bash
bitbake-layers add-layer $YOCTO_WORK_DIR/sources/{extra_repo}
```

**11-3. 등록 결과 확인:**

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/bblayers_add.py \
  --bblayers-conf $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/conf/bblayers.conf \
  --list
```

#### Step 12: 결과 출력

```
전체 셋업 완료:

  작업 디렉토리: ./yocto-build
  Manifest: {URL} ({BRANCH})
  Custom Layer: meta-{PROJECT_NAME}
  Machine: {TARGET_MACHINE}
  DISTRO: {DISTRO}
  내부 GitLab: {GITLAB_URL}/{GROUP}/{PROJECT}
  추가 패키지: {EXTRA_REPOS 목록 또는 "없음"}
  빌드 디렉토리: $YOCTO_WORK_DIR/$YOCTO_BUILD_DIR/

  bblayers.conf 등록된 layer:
  (bblayers_add.py --list 결과)

  local_manifests/custom.xml 내용:
  (manifest_local.py --action list 결과)

빌드하려면:
  cd $YOCTO_WORK_DIR
  source {SETUP_SCRIPT}
  bitbake {이미지명}
```

### 메뉴 2: 동기화/Push (반복 실행)

#### Step 1: 변경사항 스캔

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/repo_status.py \
  --work-dir $YOCTO_WORK_DIR
```

변경사항이 없으면:
```
변경된 프로젝트가 없습니다.
```
→ 종료.

#### Step 2: 변경 목록 표시

```
수정된 프로젝트:

 1. sources/meta-mycompany         (+3 files)
 2. sources/meta-st-x-linux-qt     (+1 file)

Push할 항목을 선택하세요 (예: 1,2 / all):
```

#### Step 3: 선택된 각 repo 처리

**3-a. 내부 GitLab repo 확인/생성:**

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/gl_ensure_project.py \
  --group $YOCTO_INTERNAL_GITLAB_GROUP \
  --name {repo명}
```

**3-b. remote 확인/추가:**

```bash
cd $YOCTO_WORK_DIR/sources/{repo명}
git remote get-url internal 2>/dev/null || \
  git remote add internal {PROJECT_HTTP_URL}
```

**3-c. commit:**

변경사항이 있으면 사용자에게 커밋 메시지를 입력받는다:

```bash
git add -A
git commit -m "{사용자 입력 메시지}"
```

**3-d. push:**

custom layer (`meta-{PROJECT_NAME}`)는 `main` branch로 push:
```bash
git push internal main
```

수정된 외부 repo는 `{MANIFEST_BRANCH}-{PROJECT_NAME}` branch로 push:
```bash
git push internal HEAD:$YOCTO_MANIFEST_BRANCH-$YOCTO_PROJECT_NAME
```

**3-e. local_manifests 업데이트 (repo 모드만):**

> TI 모드에서는 이 단계를 건너뛴다. TI는 local_manifests가 없으므로 push만 수행한다.

해당 project의 remote가 아직 `internal`이 아니면 전환:

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml \
  --action switch-remote \
  --project {repo명} \
  --remote-name internal \
  --remote-fetch "$GITLAB_URL/$YOCTO_INTERNAL_GITLAB_GROUP" \
  --revision $YOCTO_MANIFEST_BRANCH-$YOCTO_PROJECT_NAME
```

#### Step 4: 결과 출력

```
Push 완료:

  meta-mycompany → internal/main
  meta-st-x-linux-qt → internal/scarthgap-mycompany

local_manifests/custom.xml 업데이트됨.
```

### 메뉴 3: 패키지 추가

#### Step 1: 사용자 입력

```
추가할 외부 repo 정보를 입력해 주세요:

  repo 이름 (예: meta-st-x-linux-qt):
  remote URL (예: https://github.com/STMicroelectronics):
  branch (예: scarthgap):
```

또는 `YOCTO_EXTRA_REPOS` 목록에서 아직 추가 안 된 것을 표시할 수 있다.

#### Step 2: local_manifests에 추가

```bash
python3 overlay/skills/yocto-stm32-setup/scripts/manifest_local.py \
  --file $YOCTO_WORK_DIR/.repo/local_manifests/custom.xml \
  --action add-project \
  --remote-name {remote명} \
  --remote-fetch {remote URL} \
  --project {repo명} \
  --revision {branch} \
  --path sources/{repo명}
```

#### Step 3: repo sync

```bash
cd $YOCTO_WORK_DIR && repo sync sources/{repo명}
```

#### Step 4: 결과 출력

```
패키지 추가 완료:

  {repo명} → sources/{repo명} (remote: {remote명}, branch: {branch})

수정 후 "동기화/Push" (메뉴 2)를 실행하면 내부 GitLab에 push됩니다.
```

## 주의사항

- `repo sync`은 시간이 오래 걸릴 수 있다. 사용자에게 진행 상황을 안내한다.
- `git push --force`는 절대 사용하지 않는다. 충돌 시 사용자에게 안내한다.
- `.env` 파일의 토큰 등 민감 정보가 commit되지 않도록 주의한다.
- machine conf 수정 시 원본 파일의 include/require 의존성을 확인한다.
- `local_manifests/custom.xml`에서 `remove-project`로 default.xml의 project를 override할 수 있다 (같은 path의 project를 제거 후 재추가).

## 실전 트러블슈팅 (셋업 과정에서 확인된 사항)

### ST machine 네이밍
- ST MP2 시리즈는 SoC 패밀리명으로 machine을 지정한다.
  - `stm32mp215f-dk` (X) → `stm32mp21-disco` (O)
  - `stm32mp257f-ev1` (X) → `stm32mp25-eval` (O)
- `find layers/ -path "*/conf/machine/*.conf"` 로 실제 machine 이름을 확인한다.

### ST 소스 디렉토리 구조
- ST manifest는 소스를 `sources/`가 아닌 `layers/` 하위에 배치한다.
- local_manifests의 path도 `layers/meta-st/...` 형식으로 지정해야 한다.

### ST envsetup.sh 빌드 디렉토리
- ST `envsetup.sh`는 빌드 디렉토리를 `build-{DISTRO}-{MACHINE}` 형식으로 자동 생성한다.
  - 예: `build-openstlinuxapollo-stm32mp21-disco-apollo`
  - DISTRO 이름에서 하이픈이 제거된다 (`openstlinux-apollo` → `openstlinuxapollo`)
- `.env`의 `YOCTO_BUILD_DIR`에 실제 생성된 디렉토리명을 기록해야 한다.

### ST envsetup.sh template 요구사항
- envsetup.sh는 `_META_LAYER_ROOT` (layers/meta-st) 하위에서 `{DISTRO}.conf`를 찾고,
  해당 layer의 `conf/templates/default/` 디렉토리에서 template 파일을 요구한다.
- custom distro를 만들 때 반드시 `conf/templates/default/` 에 아래 파일을 생성해야 한다:
  - `bblayers.conf.sample` — layer 등록 (meta-apollo, meta-st-x-linux-qt 등 포함)
  - `local.conf.sample` — MACHINE, DISTRO 기본값
  - `conf-notes.txt` — 사용 가능한 image 목록

### ST DISTRO 제한
- scarthgap 릴리즈 기준 `openstlinux-weston`만 기본 제공된다.
- `openstlinux-eglfs`는 이 릴리즈에 포함되지 않는다.
- Qt EGLFS/LinuxFB 전용 distro가 필요하면 custom layer에 생성한다.

### Git push/fetch 인증
- 내부 GitLab에 push 시 interactive 인증이 동작하지 않을 수 있다.
- 토큰을 URL에 포함하여 push한 뒤, 즉시 remote URL에서 토큰을 제거한다:
  ```bash
  git remote set-url origin http://oauth2:{TOKEN}@{HOST}/{GROUP}/{PROJECT}.git
  git push -u origin main
  git remote set-url origin http://{HOST}/{GROUP}/{PROJECT}.git  # 토큰 제거
  ```
- **repo sync에서도 동일한 문제가 발생한다.** local_manifests에 내부 GitLab remote가 포함되어 있으면, repo sync가 fetch 시 인증 프롬프트(askpass)에서 멈출 수 있다. `~/.git-credentials`에 토큰을 등록하고 `git config --global credential.helper store`를 설정하면 해결된다.

### Python 스크립트 실행
- 모든 스크립트는 `python3`로 실행해야 한다 (`python` 아님).
- Ubuntu 20.04에서 `python`이 Python 2를 가리킬 수 있으며, 한글 docstring이 encoding 에러를 발생시킨다.
