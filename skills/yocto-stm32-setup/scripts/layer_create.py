# -*- coding: utf-8 -*-
"""Yocto custom layer 골격 생성 + skel recipe 자동 포함."""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Yocto layer 골격 생성")
parser.add_argument("--name", required=True, help="layer 이름 (예: meta-mycompany)")
parser.add_argument("--path", required=True, help="layer 생성 경로")
parser.add_argument("--priority", default="10", help="layer 우선순위 (기본: 10)")
parser.add_argument("--compat", default="scarthgap", help="LAYERSERIES_COMPAT (예: scarthgap, kirkstone)")
parser.add_argument("--depends", default="core", help="LAYERDEPENDS (기본: core)")
parser.add_argument("--project", default="", help="프로젝트 식별자 (skel recipe명에 사용)")
args = parser.parse_args()

# layer 이름 유효성 검증
layer_short = args.name.replace("meta-", "")
if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', layer_short):
    print(f"오류: layer 이름에 사용할 수 없는 문자가 포함되어 있습니다: '{layer_short}'")
    print(f"영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.")
    sys.exit(1)

project = args.project or layer_short
layer_path = Path(args.path)

if layer_path.exists() and (layer_path / "conf" / "layer.conf").exists():
    print(f"SKIP: layer 이미 존재 — {layer_path}")
    sys.exit(0)

# 디렉토리 구조 생성
dirs = [
    "conf/machine",
    "recipes-core/images",
    "recipes-kernel/linux",
    "recipes-bsp/u-boot",
    f"recipes-core/{project}-skel/files/etc/{project}",
    f"recipes-core/{project}-skel/files/usr/bin",
]
for d in dirs:
    (layer_path / d).mkdir(parents=True, exist_ok=True)

# conf/layer.conf
layer_conf = f'''# Layer configuration for {args.name}
# POKY_BBLAYERS_CONF_VERSION is increased each time build/conf/bblayers.conf
# changes incompatibly
BBPATH .= ":\\${{LAYERDIR}}"
BBFILES += "\\${{LAYERDIR}}/recipes-*/*/*.bb \\${{LAYERDIR}}/recipes-*/*/*.bbappend"

BBFILE_COLLECTIONS += "{layer_short}"
BBFILE_PATTERN_{layer_short} = "^\\${{LAYERDIR}}/"
BBFILE_PRIORITY_{layer_short} = "{args.priority}"

LAYERDEPENDS_{layer_short} = "{args.depends}"
LAYERSERIES_COMPAT_{layer_short} = "{args.compat}"
'''

(layer_path / "conf" / "layer.conf").write_text(layer_conf, encoding="utf-8")

# skel recipe
skel_bb = f'''SUMMARY = "{project} skeleton files"
DESCRIPTION = "Rootfs skeleton files for {project} project"
LICENSE = "CLOSED"

SRC_URI = " \\
    file://etc \\
    file://usr \\
"

S = "${{WORKDIR}}"

do_install() {{
    # /etc/{project}/
    install -d ${{D}}${{sysconfdir}}/{project}
    if ls ${{WORKDIR}}/etc/{project}/* 1>/dev/null 2>&1; then
        install -m 0644 ${{WORKDIR}}/etc/{project}/* ${{D}}${{sysconfdir}}/{project}/
    fi

    # /usr/bin/
    if ls ${{WORKDIR}}/usr/bin/* 1>/dev/null 2>&1; then
        install -d ${{D}}${{bindir}}
        install -m 0755 ${{WORKDIR}}/usr/bin/* ${{D}}${{bindir}}/
    fi
}}

FILES:${{PN}} = " \\
    ${{sysconfdir}} \\
    ${{bindir}} \\
"
'''

skel_dir = layer_path / f"recipes-core/{project}-skel"
(skel_dir / f"{project}-skel.bb").write_text(skel_bb, encoding="utf-8")

# skel 기본 파일: 빈 config 예시
config_example = f"""### {project} configuration
### 이 파일을 프로젝트에 맞게 수정하세요.
"""
(skel_dir / f"files/etc/{project}/config.conf").write_text(config_example, encoding="utf-8")

# README
readme = f"""# {args.name}

Custom Yocto layer for {project} project.

## 구조

```
{args.name}/
  conf/
    layer.conf
    machine/          <- custom machine conf
  recipes-core/
    images/           <- custom image recipe
    {project}-skel/   <- rootfs skeleton files (설정, 스크립트 등)
  recipes-kernel/
    linux/            <- kernel bbappend, cfg, patch
  recipes-bsp/
    u-boot/           <- u-boot bbappend
```

## Skel 파일

`recipes-core/{project}-skel/files/` 하위에 rootfs에 포함할 파일을 배치합니다:

- `etc/{project}/` — 설정 파일
- `usr/bin/` — 실행 스크립트

image recipe에서 `IMAGE_INSTALL:append = " {project}-skel"` 로 포함합니다.

## Dependencies

- openembedded-core (meta)

## Usage

```
BBLAYERS += "/path/to/{args.name}"
```
"""

(layer_path / "README.md").write_text(readme, encoding="utf-8")

print(f"CREATED: {layer_path}")
print(f"  conf/layer.conf")
print(f"  conf/machine/")
print(f"  recipes-core/images/")
print(f"  recipes-core/{project}-skel/{project}-skel.bb")
print(f"  recipes-core/{project}-skel/files/etc/{project}/config.conf")
print(f"  recipes-core/{project}-skel/files/usr/bin/")
print(f"  recipes-kernel/linux/")
print(f"  recipes-bsp/u-boot/")
print(f"")
print(f"skel 파일을 files/ 하위에 추가한 뒤,")
print(f"image recipe에 IMAGE_INSTALL:append = \" {project}-skel\" 로 포함하세요.")
