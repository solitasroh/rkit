"""Yocto custom distro conf 생성."""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Custom distro conf 생성")
parser.add_argument("--name", required=True, help="distro 이름 (예: mycompany)")
parser.add_argument("--layer", required=True, help="custom layer 경로")
parser.add_argument("--base", default="", help="기반 distro conf (예: openstlinux-weston)")
parser.add_argument("--display-name", default="", help="표시 이름")
args = parser.parse_args()

layer_path = Path(args.layer)
distro_dir = layer_path / "conf" / "distro"
distro_file = distro_dir / f"{args.name}.conf"

if distro_file.exists():
    print(f"EXISTS: {distro_file}")
    print(f"기존 파일을 수정하세요.")
    sys.exit(0)

distro_dir.mkdir(parents=True, exist_ok=True)

display_name = args.display_name or args.name.replace("-", " ").title()

if args.base:
    template = f'''# Custom distro based on {args.base}
require conf/distro/{args.base}.conf

DISTRO = "{args.name}"
DISTRO_NAME = "{display_name}"
DISTRO_VERSION = "1.0"

# Init manager
# INIT_MANAGER = "systemd"

# DISTRO_FEATURES 수정
# DISTRO_FEATURES:append = " systemd"
# DISTRO_FEATURES:remove = "x11"

# 추가 설정
# DISTRO_FEATURES_BACKFILL_CONSIDERED = ""
'''
else:
    template = f'''# Custom distro configuration
DISTRO = "{args.name}"
DISTRO_NAME = "{display_name}"
DISTRO_VERSION = "1.0"

# Init manager
INIT_MANAGER = "systemd"

# 기본 features
DISTRO_FEATURES = "acl argp ext2 ipv4 ipv6 largefile usbgadget usbhost wifi systemd"

# 추가 설정
# TCLIBC = "glibc"
# DISTRO_FEATURES_BACKFILL_CONSIDERED = ""
'''

distro_file.write_text(template, encoding="utf-8")

print(f"CREATED: {distro_file}")
print(f"")
print(f"distro 이름: {args.name}")
print(f"표시 이름: {display_name}")
print(f"base: {args.base or '(없음, 처음부터 작성)'}")
print(f"\nlocal.conf에서 DISTRO = \"{args.name}\" 으로 설정하세요.")
print(f"AI가 사용자와 대화하며 features를 조정합니다.")
