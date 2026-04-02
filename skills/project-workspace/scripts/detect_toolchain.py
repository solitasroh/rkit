"""SDK/toolchain 경로를 스캔하여 cross-compiler 설정을 자동 감지."""
import argparse
import glob
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="SDK/toolchain 자동 감지")
parser.add_argument("--sdk-path", required=True, help="SDK 설치 경로 (예: /opt/yocto-sdk/stm32mp2)")
args = parser.parse_args()

sdk = Path(args.sdk_path)
if not sdk.exists():
    print(f"오류: {sdk} 경로가 없습니다.", file=sys.stderr)
    sys.exit(1)

# ── cross-compiler 검색 ──
# Yocto SDK 구조: sysroots/x86_64-pokysdk-linux/usr/bin/{tuple}/{tuple}-gcc
# 일반 toolchain: bin/{tuple}-gcc
candidates = []

# Yocto SDK 패턴
for gcc in sdk.rglob("*-gcc"):
    if gcc.is_file() and "x86_64" not in gcc.name:
        name = gcc.name
        if name.endswith("-gcc"):
            prefix = name[:-3]  # xxx-gcc → xxx-
            candidates.append({
                "gcc": str(gcc),
                "prefix": prefix,
                "bin_dir": str(gcc.parent),
            })

# 중복 제거 (가장 짧은 경로 우선)
seen = set()
unique = []
for c in sorted(candidates, key=lambda x: len(x["gcc"])):
    if c["prefix"] not in seen:
        seen.add(c["prefix"])
        unique.append(c)

if not unique:
    print("오류: cross-compiler를 찾을 수 없습니다.", file=sys.stderr)
    print(f"검색 경로: {sdk}", file=sys.stderr)
    sys.exit(1)

# ── ARCH 감지 ──
ARCH_MAP = {
    "aarch64": "arm64",
    "arm": "arm",
    "x86_64": "x86_64",
    "i686": "x86",
    "mips": "mips",
    "riscv64": "riscv",
}

for c in unique:
    prefix = c["prefix"]
    arch = "unknown"
    for key, val in ARCH_MAP.items():
        if prefix.startswith(key):
            arch = val
            break
    c["arch"] = arch

# ── Sysroot 검색 ──
# Yocto SDK: sysroots/{target-tuple}
sysroots = []
sysroots_dir = sdk / "sysroots"
if sysroots_dir.exists():
    for d in sysroots_dir.iterdir():
        if d.is_dir() and "x86_64" not in d.name and "sdk" not in d.name.lower():
            sysroots.append(str(d))

# 일반 toolchain: 직접 sysroot 디렉토리
for candidate_path in [sdk / "sysroot", sdk / "target"]:
    if candidate_path.exists():
        sysroots.append(str(candidate_path))

# ── environment-setup 스크립트 검색 ──
env_scripts = list(sdk.glob("environment-setup-*"))

# ── cmake toolchain file 검색 ──
cmake_files = list(sdk.rglob("OEToolchainConfig.cmake"))

# ── 결과 출력 ──
print(f"SDK_PATH={sdk}")
print(f"TOOLCHAINS_FOUND={len(unique)}")
print()

for i, c in enumerate(unique):
    print(f"[{i}]")
    print(f"  CROSS_COMPILE={c['prefix']}")
    print(f"  CROSS_COMPILE_PATH={c['bin_dir']}/{c['prefix']}")
    print(f"  GCC={c['gcc']}")
    print(f"  ARCH={c['arch']}")
    print(f"  BIN_DIR={c['bin_dir']}")

if sysroots:
    print(f"\nSYSROOT={sysroots[0]}")
    if len(sysroots) > 1:
        for s in sysroots[1:]:
            print(f"SYSROOT_ALT={s}")

if env_scripts:
    print(f"\nENV_SCRIPT={env_scripts[0]}")

if cmake_files:
    print(f"\nCMAKE_TOOLCHAIN={cmake_files[0]}")
