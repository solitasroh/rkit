"""프로젝트 Kconfig 파일 생성.

kconfiglib 기반 menuconfig를 지원하는 프로젝트 레벨 Kconfig.
"""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="프로젝트 Kconfig 생성")
parser.add_argument("--output", default=".", help="make/ 디렉토리 경로")
parser.add_argument("--components", nargs="+", default=[],
                    help="빌드 컴포넌트 디렉토리명 (예: kernel uboot application)")
parser.add_argument("--platforms", nargs="+", default=[],
                    help="플랫폼 이름 (예: stm32mp2 imx ti)")
args = parser.parse_args()

output = Path(args.output)
kconfig_file = output / "Kconfig"
configs_dir = output / "configs"
configs_dir.mkdir(parents=True, exist_ok=True)

if kconfig_file.exists():
    print(f"EXISTS: {kconfig_file}")
    print(f"기존 Kconfig를 수정하세요. 또는 삭제 후 재실행.")
    sys.exit(0)

# 플랫폼 choice 생성
platform_choices = ""
platform_defaults = ""
first = True
for p in args.platforms:
    pname = p.upper().replace("-", "_")
    default_line = "default y" if first else ""
    platform_choices += f'''
config PLATFORM_{pname}
    bool "{p}"
'''
    platform_defaults += f'    default "{p}" if PLATFORM_{pname}\n'
    first = False

# native 항상 포함
platform_choices += '''
config PLATFORM_NATIVE
    bool "x86 Native"
'''
platform_defaults += '    default "native" if PLATFORM_NATIVE\n'

# 컴포넌트 메뉴 생성
component_menu = ""
for comp in args.components:
    cname = comp.upper().replace("-", "_")
    comp_type = "Kernel" if comp == "kernel" else \
                "U-Boot" if comp == "uboot" else \
                "Application" if comp == "application" else comp.title()

    component_menu += f'''
config BUILD_{cname}
    bool "Build {comp_type}"
    default y

config {cname}_DIR
    string "{comp_type} source directory"
    default "../{comp}"
    depends on BUILD_{cname}

'''
    # 커널/uboot은 defconfig 설정 추가
    if comp in ("kernel", "uboot"):
        component_menu += f'''config {cname}_DEFCONFIG
    string "{comp_type} defconfig name"
    default ""
    depends on BUILD_{cname}
    help
      커널/U-Boot의 defconfig 이름.
      빈 값이면 기존 .config를 그대로 사용.

'''

kconfig = f'''# Kconfig — 프로젝트 빌드 설정
#
# make menuconfig  — 대화형 설정
# make xxx_defconfig — configs/에서 설정 로드
# make savedefconfig NAME=xxx — 현재 설정 저장

mainmenu "Project Build Configuration"

# ══════════════════════════════════
# 플랫폼 선택
# ══════════════════════════════════

choice
    prompt "Target Platform"
{platform_choices}
endchoice

config PLATFORM
    string
{platform_defaults}

# ══════════════════════════════════
# 빌드 컴포넌트
# ══════════════════════════════════

menu "Build Components"
{component_menu}
endmenu

# ══════════════════════════════════
# 배포 설정
# ══════════════════════════════════

menu "Deploy"

config TARGET_IP
    string "Target board IP"
    default "192.168.1.100"

config DEPLOY_PATH
    string "Deploy base path on target"
    default "/opt/deploy"

config DEPLOY_BOOT_PATH
    string "Boot files path on target"
    default "/boot"

endmenu

# ══════════════════════════════════
# 고급 설정
# ══════════════════════════════════

menu "Advanced"

config USE_CCACHE
    bool "Use ccache (빌드 캐시)"
    default y
    help
      ccache를 사용하여 재빌드 속도를 향상시킵니다.
      ccache가 설치되어 있어야 합니다: sudo apt install ccache

config PARALLEL_JOBS
    int "Parallel build jobs (-j)"
    default 0
    help
      0이면 nproc 값을 자동 사용.

config VERBOSE
    bool "Verbose build output"
    default n

endmenu

menu "Output"

config COLLECT_OUTPUT
    bool "Enable build output collection"
    default y
    help
      빌드 산출물을 output/ 디렉토리에 수집합니다.
      make collect 로 실행.

config OUTPUT_DIR
    string "Output directory"
    default "output"
    depends on COLLECT_OUTPUT

endmenu
'''

kconfig_file.write_text(kconfig, encoding="utf-8")
print(f"CREATED: {kconfig_file}")
print(f"CREATED: {configs_dir}/")
print(f"")
print(f"컴포넌트: {', '.join(args.components) if args.components else '(없음 — Kconfig에 수동 추가)'}")
print(f"플랫폼: {', '.join(args.platforms) if args.platforms else '(없음 — 추가 필요)'}")
print(f"")
print(f"kconfiglib 설치 필요: pip install kconfiglib")
