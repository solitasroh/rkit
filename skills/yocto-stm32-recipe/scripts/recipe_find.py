"""Yocto recipe 검색 — 패키지명/키워드로 bb/bbappend 파일 찾기."""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="Yocto recipe 검색")
parser.add_argument("--search-path", required=True, help="검색 루트 (예: sources/)")
parser.add_argument("--name", required=True, help="검색 키워드 (패키지명)")
parser.add_argument("--type", default="all", choices=["bb", "bbappend", "inc", "all"],
                    help="파일 타입 필터 (기본: all)")
args = parser.parse_args()

search_root = Path(args.search_path)
if not search_root.exists():
    print(f"오류: {search_root} 경로가 없습니다.", file=sys.stderr)
    sys.exit(1)

patterns = {
    "bb": f"*{args.name}*.bb",
    "bbappend": f"*{args.name}*.bbappend",
    "inc": f"*{args.name}*.inc",
}

if args.type == "all":
    search_patterns = patterns.values()
else:
    search_patterns = [patterns[args.type]]

results = []
for pattern in search_patterns:
    for f in search_root.rglob(pattern):
        if ".git" in f.parts:
            continue
        rel = f.relative_to(search_root)
        ext = f.suffix
        results.append({"path": str(rel), "abs_path": str(f), "type": ext})

# 정렬: bb → bbappend → inc, 그 안에서 경로순
type_order = {".bb": 0, ".bbappend": 1, ".inc": 2}
results.sort(key=lambda r: (type_order.get(r["type"], 9), r["path"]))

if not results:
    print(f"'{args.name}' 관련 recipe를 찾을 수 없습니다.")
    sys.exit(0)

print(f"검색 결과 ({len(results)}건):\n")
for i, r in enumerate(results, 1):
    print(f"  {i}. [{r['type']}] {r['path']}")
