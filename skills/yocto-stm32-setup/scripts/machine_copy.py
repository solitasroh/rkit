# -*- coding: utf-8 -*-
"""기존 Yocto machine conf를 찾아서 custom layer에 복사."""
import argparse
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="machine conf 복사")
parser.add_argument("--source", required=True, help="복사할 원본 machine 이름 (예: stm32mp257f-ev1)")
parser.add_argument("--target", required=True, help="새 machine 이름 (예: stm32mp257f-ev1-mycompany)")
parser.add_argument("--search-path", required=True, help="machine conf를 찾을 디렉토리 (예: sources/)")
parser.add_argument("--dest", required=True, help="복사 대상 디렉토리 (예: sources/meta-mycompany/conf/machine/)")
args = parser.parse_args()

search_root = Path(args.search_path)
dest_dir = Path(args.dest)
target_file = dest_dir / f"{args.target}.conf"

if target_file.exists():
    print(f"SKIP: 이미 존재 — {target_file}")
    sys.exit(0)

# 원본 machine conf 검색
source_file = f"{args.source}.conf"
found = []
for conf in search_root.rglob(source_file):
    # conf/machine/ 하위에 있는 것만
    if "conf" in conf.parts and "machine" in conf.parts:
        found.append(conf)

if not found:
    print(f"오류: '{source_file}'을 {search_root} 하위에서 찾을 수 없습니다.")
    sys.exit(1)

if len(found) > 1:
    print(f"여러 개 발견:")
    for i, f in enumerate(found, 1):
        print(f"  {i}. {f}")
    print(f"\n선택이 필요합니다. --source-index 인자로 번호를 지정하거나,")
    print(f"AI가 사용자에게 확인 후 적절한 것을 선택합니다.")
    print(f"기본값: 1번 사용")

source_path = found[0]
dest_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(source_path, target_file)

print(f"COPIED: {source_path}")
print(f"    → {target_file}")

# include되는 .conf, .inc 파일 목록도 출력 (참고용)
content = source_path.read_text(encoding="utf-8", errors="replace")
includes = []
for line in content.splitlines():
    stripped = line.strip()
    if stripped.startswith("require ") or stripped.startswith("include "):
        includes.append(stripped)

if includes:
    print(f"\n참고 — 원본이 참조하는 파일:")
    for inc in includes:
        print(f"  {inc}")
    print(f"\n이 파일들도 필요할 수 있습니다. AI가 확인 후 안내합니다.")
