# -*- coding: utf-8 -*-
"""내부 GitLab group 확인/생성."""
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

parser = argparse.ArgumentParser(description="내부 GitLab group 확인/생성")
parser.add_argument("--path", required=True, help="group path (예: yocto-stm32mp2)")
parser.add_argument("--name", default=None, help="group 표시 이름 (미지정 시 path 사용)")
parser.add_argument("--visibility", default="private", help="공개 범위 (private/internal/public)")
args = parser.parse_args()

headers = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json"}

# 기존 group 검색
resp = requests.get(
    f"{BASE_URL}/api/v4/groups",
    params={"search": args.path, "per_page": 100},
    headers=headers,
    timeout=15,
)

if resp.ok:
    for g in resp.json():
        if g.get("path") == args.path or g.get("full_path") == args.path:
            print(f"GROUP_EXISTS=true")
            print(f"GROUP_ID={g['id']}")
            print(f"GROUP_PATH={g['full_path']}")
            print(f"GROUP_URL={g['web_url']}")
            sys.exit(0)

# 없으면 생성
body = {
    "name": args.name or args.path,
    "path": args.path,
    "visibility": args.visibility,
}

resp = requests.post(
    f"{BASE_URL}/api/v4/groups",
    headers=headers,
    json=body,
    timeout=15,
)

if not resp.ok:
    print(f"group 생성 실패: {resp.status_code} {resp.reason}")
    print(resp.text)
    sys.exit(1)

group = resp.json()
print(f"GROUP_EXISTS=false")
print(f"GROUP_ID={group['id']}")
print(f"GROUP_PATH={group.get('full_path', args.path)}")
print(f"GROUP_URL={group['web_url']}")
