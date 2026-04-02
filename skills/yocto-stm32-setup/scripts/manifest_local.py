# -*- coding: utf-8 -*-
"""local_manifests XML 생성/수정.

Actions:
  add-project    — remote + project 추가 (이미 있으면 skip)
  switch-remote  — 기존 project의 remote/revision 변경
  remove-project — project 제거
  list           — 현재 local manifest 내용 출력
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="local_manifests XML 관리")
parser.add_argument("--file", required=True, help="local manifest XML 경로")
parser.add_argument("--action", required=True,
                    choices=["add-project", "switch-remote", "remove-project", "list"])
parser.add_argument("--remote-name", help="remote 이름")
parser.add_argument("--remote-fetch", help="remote fetch URL")
parser.add_argument("--project", help="project name")
parser.add_argument("--revision", help="branch/tag/commit")
parser.add_argument("--path", help="project checkout path")
args = parser.parse_args()

manifest_path = Path(args.file)


def ensure_manifest():
    """manifest 파일이 없으면 빈 manifest 생성."""
    if manifest_path.exists():
        return ET.parse(str(manifest_path))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("manifest")
    tree = ET.ElementTree(root)
    return tree


def write_manifest(tree):
    """pretty-print으로 XML 저장."""
    rough = ET.tostring(tree.getroot(), encoding="unicode")
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
    # minidom adds extra xml declaration; keep it clean
    lines = [l for l in pretty.splitlines() if l.strip()]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_remote(root, name, fetch):
    """remote이 없으면 추가, 있으면 fetch URL 확인 (다르면 경고)."""
    for r in root.findall("remote"):
        if r.get("name") == name:
            existing_fetch = r.get("fetch", "")
            if fetch and existing_fetch and existing_fetch != fetch:
                print(f"WARNING: remote '{name}' fetch URL 변경: {existing_fetch} → {fetch}")
                r.set("fetch", fetch)
            elif fetch and not existing_fetch:
                r.set("fetch", fetch)
            return
    remote_elem = ET.SubElement(root, "remote")
    remote_elem.set("name", name)
    if fetch:
        remote_elem.set("fetch", fetch)


def find_project(root, name):
    """project name으로 element 찾기."""
    for p in root.findall("project"):
        if p.get("name") == name:
            return p
    return None


# ── list ──
if args.action == "list":
    if not manifest_path.exists():
        print(f"파일 없음: {manifest_path}")
        sys.exit(0)
    tree = ET.parse(str(manifest_path))
    root = tree.getroot()
    print(f"=== {manifest_path} ===\n")
    for r in root.findall("remote"):
        print(f"  remote: {r.get('name')} → {r.get('fetch', '')}")
    print()
    for p in root.findall("project"):
        print(f"  project: {p.get('name')}  remote={p.get('remote', '')}  "
              f"revision={p.get('revision', '')}  path={p.get('path', '')}")
    sys.exit(0)

# ── add-project ──
if args.action == "add-project":
    if not args.remote_name or not args.project:
        print("오류: --remote-name, --project 필수")
        sys.exit(1)
    tree = ensure_manifest()
    root = tree.getroot()
    ensure_remote(root, args.remote_name, args.remote_fetch)

    existing = find_project(root, args.project)
    if existing is not None:
        print(f"SKIP: project '{args.project}' 이미 존재")
        sys.exit(0)

    proj = ET.SubElement(root, "project")
    proj.set("name", args.project)
    proj.set("remote", args.remote_name)
    if args.revision:
        proj.set("revision", args.revision)
    if args.path:
        proj.set("path", args.path)

    write_manifest(tree)
    print(f"ADD: project '{args.project}' remote={args.remote_name} "
          f"revision={args.revision or ''} path={args.path or ''}")

# ── switch-remote ──
elif args.action == "switch-remote":
    if not args.project or not args.remote_name:
        print("오류: --project, --remote-name 필수")
        sys.exit(1)
    if not manifest_path.exists():
        print(f"오류: 파일 없음 — {manifest_path}")
        sys.exit(1)
    tree = ET.parse(str(manifest_path))
    root = tree.getroot()
    ensure_remote(root, args.remote_name, args.remote_fetch)

    proj = find_project(root, args.project)
    if proj is None:
        print(f"오류: project '{args.project}'을 찾을 수 없습니다.")
        sys.exit(1)

    old_remote = proj.get("remote", "")
    old_revision = proj.get("revision", "")
    proj.set("remote", args.remote_name)
    if args.revision:
        proj.set("revision", args.revision)

    write_manifest(tree)
    print(f"SWITCH: project '{args.project}' "
          f"remote: {old_remote}→{args.remote_name} "
          f"revision: {old_revision}→{args.revision or old_revision}")

# ── remove-project ──
elif args.action == "remove-project":
    if not args.project:
        print("오류: --project 필수")
        sys.exit(1)
    if not manifest_path.exists():
        print(f"오류: 파일 없음 — {manifest_path}")
        sys.exit(1)
    tree = ET.parse(str(manifest_path))
    root = tree.getroot()

    proj = find_project(root, args.project)
    if proj is None:
        print(f"SKIP: project '{args.project}' 없음")
        sys.exit(0)

    root.remove(proj)
    write_manifest(tree)
    print(f"REMOVE: project '{args.project}'")
