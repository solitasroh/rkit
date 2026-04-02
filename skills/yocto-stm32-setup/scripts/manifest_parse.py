# -*- coding: utf-8 -*-
"""repo manifest (default.xml) 파싱 → project 목록 JSON 출력."""
import argparse
import json
import sys
import xml.etree.ElementTree as ET

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="repo manifest 파싱")
parser.add_argument("--manifest", required=True, help="manifest XML 경로")
args = parser.parse_args()

try:
    tree = ET.parse(args.manifest)
except (ET.ParseError, FileNotFoundError) as e:
    print(f"오류: manifest 파싱 실패 — {e}", file=sys.stderr)
    sys.exit(1)

root = tree.getroot()

# remote 정보 수집
remotes = {}
for r in root.findall("remote"):
    remotes[r.get("name")] = {
        "name": r.get("name"),
        "fetch": r.get("fetch", ""),
    }

# default remote/revision
default = root.find("default")
default_remote = default.get("remote", "") if default is not None else ""
default_revision = default.get("revision", "") if default is not None else ""

# project 목록
projects = []
for p in root.findall("project"):
    name = p.get("name", "")
    remote_name = p.get("remote", default_remote)
    revision = p.get("revision", default_revision)
    path = p.get("path", name)
    remote_info = remotes.get(remote_name, {})
    projects.append({
        "name": name,
        "path": path,
        "remote": remote_name,
        "remote_fetch": remote_info.get("fetch", ""),
        "revision": revision,
    })

output = {
    "remotes": remotes,
    "default_remote": default_remote,
    "default_revision": default_revision,
    "projects": projects,
}

print(json.dumps(output, indent=2, ensure_ascii=False))
