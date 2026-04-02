"""Yocto custom image recipe 생성.

기존 image를 기반으로 커스텀 image recipe를 생성한다.
"""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Custom image recipe 생성")
parser.add_argument("--name", required=True, help="image 이름 (예: mycompany-image-weston)")
parser.add_argument("--layer", required=True, help="custom layer 경로")
parser.add_argument("--base", default="", help="기반 image (예: st-image-weston, core-image-minimal)")
parser.add_argument("--packages", default="", help="추가 패키지 (공백 구분)")
args = parser.parse_args()

layer_path = Path(args.layer)
image_dir = layer_path / "recipes-core" / "images"
image_file = image_dir / f"{args.name}.bb"

if image_file.exists():
    print(f"EXISTS: {image_file}")
    print(f"기존 파일을 수정하세요.")
    sys.exit(0)

image_dir.mkdir(parents=True, exist_ok=True)

# 패키지 목록 포맷
packages = args.packages.strip()
pkg_lines = ""
if packages:
    pkg_list = packages.split()
    pkg_lines = " \\\n".join(f"    {p}" for p in pkg_list)

if args.base:
    # 기존 image 기반 확장
    template = f'''SUMMARY = "{args.name} image"
DESCRIPTION = "Custom image based on {args.base}"

# 기반 image 포함
# [중요] 아래 경로를 실제 base image recipe 위치에 맞게 수정하세요.
# recipe_find.py --name "{args.base}" 로 정확한 경로를 확인합니다.
#
# 벤더별 예시:
#   ST:  require recipes-st/images/{args.base}.bb
#   NXP: require recipes-fsl/images/{args.base}.bb
#   TI:  require recipes-tisdk/images/{args.base}.bb
#   poky: require recipes-core/images/{args.base}.bb
#
# require: 파일 없으면 에러 / include: 파일 없으면 무시
require __FIXME_PATH__/{args.base}.bb

# 추가 패키지
IMAGE_INSTALL:append = " \\
{pkg_lines}
"

# 추가 설정 (필요 시 주석 해제)
# IMAGE_ROOTFS_EXTRA_SPACE = "1048576"
# IMAGE_FSTYPES = "tar.xz ext4"
'''
else:
    # 처음부터 작성
    template = f'''SUMMARY = "{args.name} image"
DESCRIPTION = "Custom Yocto image"

inherit core-image

IMAGE_INSTALL = " \\
    packagegroup-core-boot \\
    packagegroup-base \\
{pkg_lines}
"

# 추가 설정
# IMAGE_ROOTFS_EXTRA_SPACE = "1048576"
# IMAGE_FSTYPES = "tar.xz ext4"
# IMAGE_LINGUAS = ""
'''

image_file.write_text(template, encoding="utf-8")

print(f"CREATED: {image_file}")
print(f"")
print(f"base image: {args.base or '(없음, core-image 기반)'}")
if packages:
    print(f"추가 패키지: {packages}")
print(f"\nAI가 사용자와 대화하며 추가 수정을 진행합니다.")
