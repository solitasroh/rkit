"""Yocto recipe (bb/bbappend) 파싱 — 주요 변수 추출."""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Yocto recipe 파싱")
parser.add_argument("--recipe", required=True, help="recipe 파일 경로 (.bb 또는 .bbappend)")
args = parser.parse_args()

recipe_path = Path(args.recipe)
if not recipe_path.exists():
    print(f"오류: {recipe_path} 파일이 없습니다.", file=sys.stderr)
    sys.exit(1)

content = recipe_path.read_text(encoding="utf-8", errors="replace")

# 주요 변수 추출
variables = [
    "SRC_URI", "SRCREV", "SRCBRANCH",
    "DEPENDS", "RDEPENDS",
    "PACKAGECONFIG", "PACKAGECONFIG_CONFARGS",
    "KERNEL_DEFCONFIG", "UBOOT_DEFCONFIG",
    "LICENSE", "LIC_FILES_CHKSUM",
    "PV", "PR", "S", "B",
    "COMPATIBLE_MACHINE",
    "MACHINE_FEATURES", "DISTRO_FEATURES",
    "inherit",
]

print(f"=== {recipe_path.name} ===\n")

for var in variables:
    # 다양한 할당 형태: VAR = "", VAR += "", VAR:append = "" 등
    pattern = rf'^{re.escape(var)}(?:\s*(?::[\w-]+)*)?\s*(?:[+?:]?=)\s*(.+?)$'
    matches = re.findall(pattern, content, re.MULTILINE)
    if matches:
        for m in matches:
            val = m.strip().strip('"').strip("'")
            if len(val) > 200:
                val = val[:200] + "..."
            print(f"{var} = {val}")

# SRC_URI 여러 줄 파싱 (\ 연결)
src_uri_block = re.search(
    r'SRC_URI\s*(?:[+?:]?=)\s*"(.*?)"',
    content,
    re.DOTALL,
)
if src_uri_block:
    raw = src_uri_block.group(1)
    entries = [e.strip() for e in raw.replace("\\", "").split() if e.strip()]
    if entries:
        print(f"\nSRC_URI entries ({len(entries)}):")
        for e in entries:
            print(f"  {e}")

# do_ 함수 목록
functions = re.findall(r'^(do_\w+(?::[\w-]+)?)\s*\(\)', content, re.MULTILINE)
if functions:
    print(f"\nFunctions:")
    for f in functions:
        print(f"  {f}()")

# include/require
includes = re.findall(r'^(?:include|require)\s+(.+)$', content, re.MULTILINE)
if includes:
    print(f"\nIncludes:")
    for inc in includes:
        print(f"  {inc.strip()}")
