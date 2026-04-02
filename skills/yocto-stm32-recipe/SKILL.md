---
name: yocto-stm32-recipe
classification: workflow
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  STM32MP Yocto recipe/image/distro 작업 스킬. bbappend 생성, custom image, distro conf, 패키지 추가.
  Triggers: stm32 recipe, stm32mp bbappend, 이미지 생성, distro 생성, 패키지 추가
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---
# Yocto Recipe

bbappend 생성/편집, 새 recipe 작성, custom image/distro 생성을 자동화한다.

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
- `pip install -r overlay/skills/yocto-stm32-recipe/scripts/requirements.txt`

## 스크립트 레퍼런스

### recipe_find.py — recipe 검색

```bash
python overlay/skills/yocto-stm32-recipe/scripts/recipe_find.py \
  --search-path $YOCTO_WORK_DIR/sources/ --name qtbase
```

### recipe_parse.py — recipe 파싱

```bash
python overlay/skills/yocto-stm32-recipe/scripts/recipe_parse.py \
  --recipe {recipe 경로}
```

### bbappend_create.py — bbappend 템플릿 생성

```bash
python overlay/skills/yocto-stm32-recipe/scripts/bbappend_create.py \
  --recipe {원본 recipe} --layer sources/meta-$YOCTO_PROJECT_NAME
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--recipe` | O | 원본 recipe 경로 |
| `--layer` | O | custom layer 경로 |
| `--no-wildcard` | × | 정확한 버전으로 생성 (기본: `%` 와일드카드 사용) |

기본: `weston_%.bbappend` (모든 버전 적용). `--no-wildcard`: `weston_13.0.bbappend` (특정 버전만).

### image_create.py — custom image recipe 생성

```bash
python overlay/skills/yocto-stm32-recipe/scripts/image_create.py \
  --name ${YOCTO_PROJECT_NAME}-image-weston \
  --layer sources/meta-$YOCTO_PROJECT_NAME \
  --base st-image-weston \
  --packages "openssh strace my-app"
```

### distro_create.py — custom distro conf 생성

```bash
python overlay/skills/yocto-stm32-recipe/scripts/distro_create.py \
  --name $YOCTO_PROJECT_NAME \
  --layer sources/meta-$YOCTO_PROJECT_NAME \
  --base openstlinux-weston
```

## 절차

실행 시 메뉴를 표시한다:

```
Yocto Recipe:

1. bbappend 생성  — 기존 recipe override
2. 새 recipe 생성 — 자체 패키지 추가
3. Image 작업     — custom image 생성/수정
4. Distro 작업    — custom distro conf 생성/수정
5. 패키지 추가    — local.conf 또는 image에 패키지 추가
6. recipe 검색    — 패키지 recipe 위치/내용 확인
```


### 메뉴 2: 새 recipe 생성

사용자 입력:
- 패키지명, 버전, 소스 URL, 라이선스, 카테고리
- inherit(cmake, autotools, meson 등)

`sources/meta-{PROJECT_NAME}/{카테고리}/{패키지명}/{패키지명}_{버전}.bb` 생성.


### 메뉴 4: Distro 작업

```
Distro 작업:
a. custom distro 생성
b. 기존 distro 확인
```

#### 4-a. custom distro 생성

```bash
python overlay/skills/yocto-stm32-recipe/scripts/distro_create.py \
  --name $YOCTO_PROJECT_NAME \
  --layer $YOCTO_WORK_DIR/sources/meta-$YOCTO_PROJECT_NAME \
  --base openstlinux-weston
```

> **bblayers.conf.sample 순서**: custom layer(meta-{PROJECT_NAME})는 FRAMEWORKLAYERS에서 반드시 마지막에 위치해야 한다.
> bitbake는 BBLAYERS 순서대로 layer.conf를 파싱하며, 같은 변수를 여러 layer에서 설정하면 마지막이 우선한다.
> custom layer가 다른 layer의 설정을 override해야 하므로 맨 뒤에 와야 한다.

> **include 경로 규칙**: custom distro conf에서 다른 layer의 inc 파일을 참조할 때는
> `require conf/distro/include/xxx.inc` (BBPATH 기준 전체 경로)를 사용한다.
> `require include/xxx.inc` (상대 경로)는 같은 layer 안에서만 동작한다.

AI와 대화하며 수정:
- DISTRO_FEATURES 조정
- INIT_MANAGER (systemd/sysvinit)
- PACKAGE_CLASSES (rpm/deb/ipk)

생성 후 local.conf의 `DISTRO`와 `.env`의 `YOCTO_DISTRO`를 업데이트.


### 메뉴 6: recipe 검색

recipe_find.py → recipe_parse.py 순서로 실행.

## 주의사항

- bbappend 디렉토리 구조는 원본 recipe와 동일해야 bitbake가 인식한다.
- `%` 와일드카드 bbappend는 모든 버전에 적용된다. Yocto 업그레이드 시 주의.
- custom distro 생성 후 local.conf과 .env 모두 업데이트 필요.
- EULA 미설정 시 빌드 실패 가능: ST(`ACCEPT_EULA`), NXP(`ACCEPT_FSL_EULA`), TI(`LICENSE_FLAGS_ACCEPTED`).
