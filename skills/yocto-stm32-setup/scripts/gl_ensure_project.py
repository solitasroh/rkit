# -*- coding: utf-8 -*-
"""내부 GitLab project 확인/생성. 있으면 URL 반환, 없으면 생성."""
import argparse
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv(Path.cwd() / ".env")

BASE_URL = os.getenv("GITLAB_URL", "").rstrip("/")
TOKEN = os.getenv("GITLAB_TOKEN", "")

if not BASE_URL or not TOKEN:
    print("오류: .env에 GITLAB_URL, GITLAB_TOKEN을 설정해 주세요.")
    sys.exit(1)

parser = argparse.ArgumentParser(description="내부 GitLab project 확인/생성")
parser.add_argument("--group", required=True, help="group path 또는 group ID")
parser.add_argument("--name", required=True, help="프로젝트 이름")
parser.add_argument("--visibility", default="private", help="공개 범위")
parser.add_argument("--description", default="", help="프로젝트 설명")
args = parser.parse_args()

headers = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json"}


def find_group_id(group_ref):
    """group path 또는 ID로 group ID 반환."""
    if group_ref.isdigit():
        return int(group_ref)
    encoded = group_ref.replace("/", "%2F")
    resp = requests.get(
        f"{BASE_URL}/api/v4/groups/{encoded}",
        headers=headers,
        timeout=15,
    )
    if resp.ok:
        return resp.json()["id"]
    return None


group_id = find_group_id(args.group)
if group_id is None:
    print(f"오류: group '{args.group}'을 찾을 수 없습니다.")
    sys.exit(1)

# group 내 기존 프로젝트 검색
resp = requests.get(
    f"{BASE_URL}/api/v4/groups/{group_id}/projects",
    params={"search": args.name, "per_page": 100},
    headers=headers,
    timeout=15,
)

if resp.ok:
    for p in resp.json():
        if p.get("path") == args.name or p.get("name") == args.name:
            print(f"PROJECT_EXISTS=true")
            print(f"PROJECT_ID={p['id']}")
            print(f"PROJECT_PATH={p['path_with_namespace']}")
            print(f"PROJECT_HTTP_URL={p.get('http_url_to_repo', '')}")
            print(f"PROJECT_SSH_URL={p.get('ssh_url_to_repo', '')}")
            print(f"PROJECT_URL={p['web_url']}")
            sys.exit(0)

# 없으면 생성
body = {
    "name": args.name,
    "path": args.name,
    "namespace_id": group_id,
    "visibility": args.visibility,
    "initialize_with_readme": False,
}
if args.description:
    body["description"] = args.description

resp = requests.post(
    f"{BASE_URL}/api/v4/projects",
    headers=headers,
    json=body,
    timeout=15,
)

if not resp.ok:
    print(f"프로젝트 생성 실패: {resp.status_code} {resp.reason}")
    print(resp.text)
    sys.exit(1)

project = resp.json()
print(f"PROJECT_EXISTS=false")
print(f"PROJECT_ID={project['id']}")
print(f"PROJECT_PATH={project['path_with_namespace']}")
print(f"PROJECT_HTTP_URL={project.get('http_url_to_repo', '')}")
print(f"PROJECT_SSH_URL={project.get('ssh_url_to_repo', '')}")
print(f"PROJECT_URL={project['web_url']}")
