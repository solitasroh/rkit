"""bbappend 파일 경로 결정 및 템플릿 생성.

원본 recipe 경로를 기반으로 custom layer 내 올바른 위치에 bbappend를 생성한다.
"""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="bbappend 템플릿 생성")
parser.add_argument("--recipe", required=True,
                    help="원본 recipe 경로 (예: sources/poky/meta/recipes-graphics/wayland/weston_13.0.bb)")
parser.add_argument("--layer", required=True,
                    help="custom layer 경로 (예: sources/meta-mycompany)")
parser.add_argument("--no-wildcard", action="store_true",
                    help="정확한 버전으로 bbappend 생성 (기본: 와일드카드 %% 사용)")
args = parser.parse_args()

recipe_path = Path(args.recipe)
layer_path = Path(args.layer)

if not recipe_path.exists():
    print(f"오류: {recipe_path} 파일이 없습니다.", file=sys.stderr)
    sys.exit(1)

# recipe 경로에서 recipes-xxx/yyy/ 부분 추출
# 예: recipes-graphics/wayland/weston_13.0.bb
parts = recipe_path.parts
recipes_idx = None
for i, p in enumerate(parts):
    if p.startswith("recipes-"):
        recipes_idx = i
        break

if recipes_idx is None:
    print(f"오류: recipe 경로에서 'recipes-*' 디렉토리를 찾을 수 없습니다.", file=sys.stderr)
    print(f"경로: {recipe_path}")
    sys.exit(1)

# recipes-graphics/wayland/ 부분
rel_dir = Path(*parts[recipes_idx:-1])

# 파일명 결정
recipe_name = recipe_path.stem  # weston_13.0
if args.no_wildcard:
    bbappend_name = f"{recipe_name}.bbappend"
else:
    # weston_13.0 → weston_%.bbappend
    if "_" in recipe_name:
        base = recipe_name.split("_")[0]
        bbappend_name = f"{base}_%.bbappend"
    else:
        bbappend_name = f"{recipe_name}.bbappend"

# 최종 경로
bbappend_path = layer_path / rel_dir / bbappend_name
files_dir = layer_path / rel_dir / "files"

# 이미 존재하는지 확인
if bbappend_path.exists():
    print(f"EXISTS: {bbappend_path}")
    print(f"기존 파일에 내용을 추가하세요.")
    sys.exit(0)

# 디렉토리 생성
bbappend_path.parent.mkdir(parents=True, exist_ok=True)
files_dir.mkdir(parents=True, exist_ok=True)

# 기본 템플릿 생성
template = f'''# bbappend for {recipe_path.name}
FILESEXTRAPATHS:prepend := "${{THISDIR}}/files:"

# SRC_URI += "file://your-file-here"

# PACKAGECONFIG:append = " your-config"

# do_install:append() {{
#     install -m 0644 ${{WORKDIR}}/your-file ${{D}}${{sysconfdir}}/
# }}
'''

bbappend_path.write_text(template, encoding="utf-8")

print(f"CREATED: {bbappend_path}")
print(f"CREATED: {files_dir}/")
print(f"")
print(f"원본 recipe: {recipe_path}")
print(f"bbappend:    {bbappend_path}")
print(f"files 디렉토리: {files_dir}")
