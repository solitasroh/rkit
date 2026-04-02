# -*- coding: utf-8 -*-
"""bblayers.conf에 layer가 등록되어 있는지 확인하고 목록 출력.

bitbake-layers add-layer는 빌드 환경 source 후 직접 실행해야 하므로,
이 스크립트는 현재 등록 상태 확인 + 등록해야 할 layer 경로 출력만 담당한다.
실제 추가는 AI가 bitbake-layers add-layer 명령을 실행한다.
"""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="bblayers.conf layer 등록 확인")
parser.add_argument("--bblayers-conf", required=True,
                    help="bblayers.conf 경로 (예: build/conf/bblayers.conf)")
parser.add_argument("--check", nargs="+",
                    help="확인할 layer 경로(들) — 절대경로 또는 상대경로")
parser.add_argument("--list", action="store_true",
                    help="현재 등록된 layer 목록 출력")
args = parser.parse_args()

conf_path = Path(args.bblayers_conf)

if not conf_path.exists():
    print(f"오류: {conf_path} 파일이 없습니다.", file=sys.stderr)
    print(f"빌드 환경을 먼저 초기화하세요 (source envsetup / oe-init-build-env).")
    sys.exit(1)

content = conf_path.read_text(encoding="utf-8", errors="replace")

# BBLAYERS에서 경로 추출
# 여러 줄에 걸친 BBLAYERS = " ... " 파싱
bblayers_match = re.search(
    r'BBLAYERS\s*[\?:]?=\s*"(.*?)"',
    content,
    re.DOTALL,
)

registered = []
if bblayers_match:
    raw = bblayers_match.group(1)
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            # 변수 치환은 무시하고 경로 부분만 추출
            registered.append(stripped)

# BBLAYERS:append, BBLAYERS += 등도 확인
for m in re.finditer(r'BBLAYERS\s*(?::append\s*=|[+]=)\s*"(.*?)"', content, re.DOTALL):
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            registered.append(stripped)

if args.list:
    print(f"=== {conf_path} ===")
    print(f"등록된 layer ({len(registered)}개):\n")
    for i, layer in enumerate(registered, 1):
        print(f"  {i}. {layer}")
    sys.exit(0)

if args.check:
    missing = []
    present = []
    for check_path in args.check:
        # 경로의 마지막 부분(layer 이름)으로 정확 매칭
        layer_name = Path(check_path).name
        found = any(Path(r).name == layer_name or r.rstrip("/").endswith("/" + layer_name)
                     for r in registered)
        if found:
            present.append(check_path)
        else:
            missing.append(check_path)

    if present:
        print("PRESENT:")
        for p in present:
            print(f"  {p}")
    if missing:
        print("MISSING:")
        for m in missing:
            print(f"  {m}")
        print(f"\n등록 명령:")
        for m in missing:
            print(f"  bitbake-layers add-layer {m}")
    if not missing:
        print("\n모든 layer가 등록되어 있습니다.")
    sys.exit(0)
