"""Kernel, U-Boot, TF-A, OP-TEE recipe 정보 추출.

SRC_URI, SRCREV, defconfig, 기존 bbappend/patch/cfg 목록을 출력한다.
"""
import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="BSP recipe 정보 추출")
parser.add_argument("--search-path", required=True, help="sources/ 경로")
parser.add_argument("--type", required=True,
                    choices=["kernel", "uboot", "tfa", "optee"],
                    help="대상 컴포넌트")
args = parser.parse_args()

search_root = Path(args.search_path)

# 컴포넌트별 설정
# 벤더별 우선순위: ST → NXP → TI → 범용 (구체적 패턴 먼저)
TYPE_CONFIG = {
    "kernel": {
        "patterns": [
            "linux-stm32mp*.bb",    # ST
            "linux-imx*.bb",        # NXP
            "linux-ti*.bb",         # TI
            "linux-*.bb",           # 범용 fallback
        ],
        "recipe_dir": "recipes-kernel",
        "defconfig_var": "KERNEL_DEFCONFIG",
        "label": "KERNEL",
    },
    "uboot": {
        "patterns": [
            "u-boot-stm32mp*.bb",   # ST
            "u-boot-imx*.bb",       # NXP
            "u-boot-ti*.bb",        # TI
            "u-boot-*.bb",          # 범용 fallback
        ],
        "recipe_dir": "recipes-bsp",
        "defconfig_var": "UBOOT_DEFCONFIG",
        "label": "U-BOOT",
    },
    "tfa": {
        "patterns": [
            "tf-a-stm32mp*.bb",         # ST
            "imx-atf*.bb",              # NXP
            "trusted-firmware-a*.bb",    # TI / 범용
            "tf-a-*.bb",                # 범용 fallback
        ],
        "recipe_dir": "recipes-bsp",
        "defconfig_var": "TFA_DEVICETREE",
        "label": "TF-A",
    },
    "optee": {
        "patterns": [
            "optee-os-stm32mp*.bb",  # ST
            "optee-os-imx*.bb",      # NXP
            "optee-os*.bb",          # TI / 범용
        ],
        "recipe_dir": "recipes-security",
        "defconfig_var": "OPTEEMACHINE",
        "label": "OP-TEE",
    },
}

cfg = TYPE_CONFIG[args.type]
patterns = cfg["patterns"]
recipe_dir_pattern = cfg["recipe_dir"]
defconfig_var = cfg["defconfig_var"]

# recipe 검색
recipes = []
for pattern in patterns:
    for f in search_root.rglob(pattern):
        if ".git" in f.parts:
            continue
        if recipe_dir_pattern in str(f):
            recipes.append(f)

# bbappend 검색
appends = []
for pattern in patterns:
    append_pattern = pattern.replace(".bb", "*.bbappend")
    for f in search_root.rglob(append_pattern):
        if ".git" in f.parts:
            continue
        appends.append(f)

if not recipes:
    print(f"오류: {cfg['label']} recipe를 찾을 수 없습니다.", file=sys.stderr)
    sys.exit(1)

print(f"=== {cfg['label']} 정보 ===\n")

# 각 recipe 분석
for recipe in sorted(recipes):
    print(f"Recipe: {recipe.relative_to(search_root)}")
    content = recipe.read_text(encoding="utf-8", errors="replace")

    # SRC_URI
    src_match = re.search(r'SRC_URI\s*(?:[+?:]?=)\s*"(.*?)"', content, re.DOTALL)
    if src_match:
        raw = src_match.group(1).replace("\\", "").strip()
        entries = [e.strip() for e in raw.split() if e.strip()]
        git_entries = [e for e in entries if e.startswith("git://") or e.startswith("https://")]
        if git_entries:
            print(f"  SRC_URI (git): {git_entries[0]}")

    # SRCREV
    srcrev_match = re.search(r'SRCREV\s*=\s*"([^"]+)"', content)
    if srcrev_match:
        print(f"  SRCREV: {srcrev_match.group(1)}")

    # SRCBRANCH
    branch_match = re.search(r'SRCBRANCH\s*(?:[?:]?=)\s*"([^"]+)"', content)
    if branch_match:
        print(f"  SRCBRANCH: {branch_match.group(1)}")

    # DEFCONFIG / type-specific variable
    defconfig_match = re.search(rf'{defconfig_var}\s*(?:[?:]?=)\s*"([^"]+)"', content)
    if defconfig_match:
        print(f"  {defconfig_var}: {defconfig_match.group(1)}")

    # COMPATIBLE_MACHINE
    compat_match = re.search(r'COMPATIBLE_MACHINE\s*=\s*"([^"]+)"', content)
    if compat_match:
        print(f"  COMPATIBLE_MACHINE: {compat_match.group(1)}")

    # TF-A specific: TFA_PLATFORM
    if args.type == "tfa":
        plat_match = re.search(r'TFA_PLATFORM\s*(?:[?:]?=)\s*"([^"]+)"', content)
        if plat_match:
            print(f"  TFA_PLATFORM: {plat_match.group(1)}")

    # OP-TEE specific: OPTEEMACHINE, OPTEE_CONF
    if args.type == "optee":
        for var in ["OPTEEMACHINE", "OPTEE_CONF"]:
            m = re.search(rf'{var}\s*(?:[?:]?=)\s*"([^"]+)"', content)
            if m:
                print(f"  {var}: {m.group(1)}")

    print()

# bbappend 목록
if appends:
    print("bbappend 파일:")
    for a in sorted(appends):
        print(f"  {a.relative_to(search_root)}")

    # bbappend 내 cfg/patch/dts 파일 추출
    print()
    for a in sorted(appends):
        a_content = a.read_text(encoding="utf-8", errors="replace")
        files = re.findall(r'file://([^\s;"]+)', a_content)
        if files:
            print(f"  {a.relative_to(search_root)} 참조 파일:")
            for f in files:
                if f.endswith(".cfg"):
                    ftype = "cfg"
                elif f.endswith(".patch"):
                    ftype = "patch"
                elif f.endswith(".dts") or f.endswith(".dtsi") or f.endswith(".dtso"):
                    ftype = "dts"
                else:
                    ftype = "file"
                print(f"    [{ftype}] {f}")
else:
    print("bbappend: 없음")
