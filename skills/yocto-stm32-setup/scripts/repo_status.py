# -*- coding: utf-8 -*-
"""Yocto 작업 디렉토리에서 변경된 project 감지 → JSON 출력.

repo 모드 (.repo 존재): repo status + git status 병행
ti-oe 모드 (.repo 없음): sources/ 하위 git repo 직접 순회
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="변경된 repo project 감지")
parser.add_argument("--work-dir", required=True, help="Yocto 작업 디렉토리")
args = parser.parse_args()

work_dir = Path(args.work_dir)
projects = []

use_repo = (work_dir / ".repo").exists()

# ── repo 모드: repo status 파싱 ──
if use_repo:
    try:
        result = subprocess.run(
            ["repo", "status"],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        print("오류: 'repo' 명령을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    output = result.stdout + result.stderr
    current_project = None
    change_count = 0

    for line in output.splitlines():
        line = line.rstrip()
        if line.startswith("project "):
            if current_project and change_count > 0:
                projects.append({
                    "path": current_project,
                    "changes": change_count,
                    "status": "modified",
                })
            current_project = line.replace("project ", "").rstrip("/").strip()
            change_count = 0
        elif current_project and line.strip():
            stripped = line.strip()
            if stripped and len(stripped) >= 2 and stripped[0] in "-_":
                change_count += 1

    if current_project and change_count > 0:
        projects.append({
            "path": current_project,
            "changes": change_count,
            "status": "modified",
        })

# ── sources/ 하위 git repo 직접 순회 (repo 모드 보완 + ti-oe 모드) ──
sources_dir = work_dir / "sources"
if not sources_dir.exists():
    # TI의 경우 sources/ 대신 다른 구조일 수 있음
    # work_dir 자체에 layer들이 있을 수 있음
    for candidate in [work_dir / "sources", work_dir]:
        if candidate.exists():
            sources_dir = candidate
            break

if sources_dir.exists():
    for d in sources_dir.iterdir():
        if not d.is_dir():
            continue
        git_dir = d / ".git"
        if not git_dir.exists():
            continue

        # 이미 repo status에서 감지된 것은 skip
        rel_path = str(d.relative_to(work_dir))
        already_listed = any(
            p["path"].endswith(d.name) or p["path"] == rel_path
            for p in projects
        )
        if already_listed:
            continue

        # git status + unpushed commits
        try:
            st = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(d),
                capture_output=True,
                text=True,
                timeout=30,
            )
            changes = [l for l in st.stdout.splitlines() if l.strip()]

            log = subprocess.run(
                ["git", "log", "--oneline", "@{u}..HEAD"],
                cwd=str(d),
                capture_output=True,
                text=True,
                timeout=30,
            )
            unpushed = [l for l in log.stdout.splitlines() if l.strip()]
        except Exception:
            changes = []
            unpushed = []

        if changes or unpushed:
            projects.append({
                "path": rel_path,
                "changes": len(changes),
                "unpushed_commits": len(unpushed),
                "status": "modified",
            })

print(json.dumps(projects, indent=2, ensure_ascii=False))
