"""플랫폼별 .mk 파일과 cmake toolchain 파일을 생성."""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="플랫폼 빌드 설정 생성")
parser.add_argument("--name", required=True, help="플랫폼 이름 (예: stm32mp2)")
parser.add_argument("--sdk-path", required=True, help="SDK 경로")
parser.add_argument("--cross-compile", required=True, help="CROSS_COMPILE 값 (풀 경로 포함)")
parser.add_argument("--arch", required=True, help="ARCH (arm64, arm, x86_64 등)")
parser.add_argument("--sysroot", default="", help="sysroot 경로")
parser.add_argument("--kernel-src", default="", help="커널 소스 경로")
parser.add_argument("--defconfig", default="", help="커널 defconfig 이름")
parser.add_argument("--target-ip", default="", help="타겟 보드 IP")
parser.add_argument("--output-dir", default=".", help="출력 디렉토리")
args = parser.parse_args()

output = Path(args.output_dir)
platform_dir = output / "platform"
cmake_dir = output / "cmake"
platform_dir.mkdir(parents=True, exist_ok=True)
cmake_dir.mkdir(parents=True, exist_ok=True)

name = args.name

# ── platform/{name}.mk 생성 ──
mk_content = f'''# platform/{name}.mk — {name} cross-build 설정
#
# 사용법: make PLATFORM={name} [target]

PLATFORM_NAME    := {name}
SDK_PATH         := {args.sdk_path}
CROSS_COMPILE    := {args.cross_compile}
ARCH             := {args.arch}
'''

if args.sysroot:
    mk_content += f'SYSROOT          := {args.sysroot}\n'

if args.kernel_src:
    mk_content += f'KERNEL_SRC       := {args.kernel_src}\n'
else:
    mk_content += f'KERNEL_SRC       := # TODO: 커널 소스 경로 설정\n'

if args.defconfig:
    mk_content += f'DEFCONFIG        := {args.defconfig}\n'
else:
    mk_content += f'DEFCONFIG        := # TODO: defconfig 이름 설정\n'

mk_content += f'TOOLCHAIN_FILE   := cmake/toolchain-{name}.cmake\n'

if args.target_ip:
    mk_content += f'TARGET_IP        := {args.target_ip}\n'
else:
    mk_content += f'TARGET_IP        := # TODO: 타겟 보드 IP\n'

mk_content += f'''
# 커널 빌드 옵션
KERNEL_MAKE_OPTS := ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE)
'''

if args.sysroot:
    mk_content += f'''
# C/C++ 플래그 (유저스페이스 빌드용)
PLATFORM_CFLAGS  := --sysroot=$(SYSROOT)
PLATFORM_LDFLAGS := --sysroot=$(SYSROOT)
'''

mk_file = platform_dir / f"{name}.mk"
mk_file.write_text(mk_content, encoding="utf-8")
print(f"CREATED: {mk_file}")

# ── cmake/toolchain-{name}.cmake 생성 ──
# CROSS_COMPILE에서 gcc 경로와 prefix 추출
cross = args.cross_compile
if cross.endswith("-"):
    gcc_path = cross + "gcc"
    gxx_path = cross + "g++"
else:
    gcc_path = cross + "gcc"
    gxx_path = cross + "g++"

# CMAKE_SYSTEM_PROCESSOR 결정
proc_map = {
    "arm64": "aarch64",
    "arm": "arm",
    "x86_64": "x86_64",
    "x86": "i686",
    "mips": "mips",
    "riscv": "riscv64",
}
processor = proc_map.get(args.arch, args.arch)

cmake_content = f'''# cmake/toolchain-{name}.cmake — {name} CMake toolchain
#
# 사용법: cmake -B build-{name} -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-{name}.cmake

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR {processor})

set(CMAKE_C_COMPILER   "{gcc_path}")
set(CMAKE_CXX_COMPILER "{gxx_path}")
'''

if args.sysroot:
    cmake_content += f'''set(CMAKE_SYSROOT      "{args.sysroot}")
'''

cmake_content += f'''
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
'''

cmake_file = cmake_dir / f"toolchain-{name}.cmake"
cmake_file.write_text(cmake_content, encoding="utf-8")
print(f"CREATED: {cmake_file}")
