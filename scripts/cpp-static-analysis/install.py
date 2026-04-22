#!/usr/bin/env python3
"""cpp-static-analysis 부트스트랩: pip install + project-config.json 생성.

rkit 플러그인 내부 경로:
  - 템플릿 원본: ${CLAUDE_PLUGIN_ROOT}/templates/cpp-static-analysis/project-config.example.json
  - 타겟 위치:   ${PROJECT_DIR}/.rkit/cpp-static-analysis/project-config.json

settings.json 병합 단계는 제거 — rkit 플러그인 훅이 `${CLAUDE_PLUGIN_ROOT}` 기반으로 이미 활성.

실행:
  /code-review 또는 /cpp-static-analysis 첫 호출 시 자동 트리거.
  수동: python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# UTF-8 self-reexec 가드 — rapp_review.py 와 동일 패턴.
# encoding.py 의 setup_utf8_io() 는 import 후에만 동작하므로 import 전 에러의
# stderr 가 Windows cp949 로 깨진다. PYTHONUTF8 을 확인해 없으면 재기동.
# ─────────────────────────────────────────────────────────────
import os as _os
import sys as _sys
if __name__ == "__main__" and _os.environ.get("PYTHONUTF8") != "1":
    import subprocess as _sp
    _env = {**_os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    _sys.exit(_sp.run(
        [_sys.executable, __file__, *_sys.argv[1:]], env=_env,
    ).returncode)

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from encoding import (  # noqa: E402
    read_text_utf8, safe_print, write_file,
)

# ─────────────────────────────────────────────────────────────
# pip 의존성 (SoT).
# 신규 런타임 의존성 추가 시 여기에 반영 + 대상 프로젝트에서 재실행 필요.
# ─────────────────────────────────────────────────────────────
PACKAGES = [
    "tree-sitter==0.25.2",
    "tree-sitter-cpp==0.23.4",
    "chardet",
    "pathspec",  # .patternsignore 의 '**' glob. 없으면 fnmatch fallback(경고 발생).
]

VERIFY = "import tree_sitter, tree_sitter_cpp, chardet, pathspec; print('OK')"

# ─────────────────────────────────────────────────────────────
# 경로 계산 — rkit 플러그인 레이아웃 기준.
# ─────────────────────────────────────────────────────────────

def _resolve_plugin_root() -> Path:
    """CLAUDE_PLUGIN_ROOT 환경변수 우선. 없으면 이 파일 기준 상대 계산.

    `scripts/cpp-static-analysis/install.py` → `parent.parent.parent` = 플러그인 루트.
    """
    env_root = _os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parent.parent.parent


PLUGIN_ROOT = _resolve_plugin_root()
TEMPLATE_FILE = PLUGIN_ROOT / "templates" / "cpp-static-analysis" / "project-config.example.json"
PROJECT_ROOT = Path(_os.getcwd())
PROJECT_CONFIG_DIR = PROJECT_ROOT / ".rkit" / "cpp-static-analysis"
PROJECT_CONFIG_FILE = PROJECT_CONFIG_DIR / "project-config.json"


# ─────────────────────────────────────────────────────────────
# Step 1: pip install
# ─────────────────────────────────────────────────────────────

def step_pip() -> int:
    safe_print(f"[1/2] pip install ({len(PACKAGES)}개)...")
    r = subprocess.run([sys.executable, "-m", "pip", "install", *PACKAGES])
    if r.returncode != 0:
        safe_print("pip install 실패.", file=sys.stderr)
        return r.returncode
    r = subprocess.run([sys.executable, "-c", VERIFY])
    if r.returncode != 0:
        safe_print("import 검증 실패.", file=sys.stderr)
    return r.returncode


# ─────────────────────────────────────────────────────────────
# Step 2: project-config.json 부트스트랩
# ─────────────────────────────────────────────────────────────

def step_project_config() -> int:
    safe_print(f"\n[2/2] project-config.json 확인: {PROJECT_CONFIG_FILE}")
    if PROJECT_CONFIG_FILE.exists():
        safe_print("  이미 존재 — 건너뜀.")
        return 0
    if not TEMPLATE_FILE.exists():
        safe_print(f"  템플릿 없음: {TEMPLATE_FILE}", file=sys.stderr)
        safe_print("  플러그인 설치 경로 확인 필요 (CLAUDE_PLUGIN_ROOT).", file=sys.stderr)
        return 1
    # 최상위 `_comment` 는 템플릿 힌트 — 자동 복사 후엔 무의미하므로 제거.
    # 중첩 `_comment`/`_note` 는 설정 문서라 보존.
    data = json.loads(read_text_utf8(TEMPLATE_FILE))
    data.pop("_comment", None)
    PROJECT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    write_file(
        PROJECT_CONFIG_FILE,
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    )
    safe_print(f"  {TEMPLATE_FILE.name} → {PROJECT_CONFIG_FILE.relative_to(PROJECT_ROOT)} 생성.")
    safe_print("  프로젝트에 맞게 paths/thresholds/layers/rules/metrics 수정 요망.")
    return 0


def main() -> int:
    for step in (step_pip, step_project_config):
        rc = step()
        if rc != 0:
            return rc
    safe_print("\n완료. /code-review 호출 시 cpp-static-analysis 자동 실행됨.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
