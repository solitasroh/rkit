"""PostToolUse hook — C++ 파일 Edit/Write 후 경량 정적 분석.

rkit 정책: **non-blocking**. `decision: block` 출력하지 않음.
모든 finding 은 stderr 경고로만 전달 — Claude Code 가 메시지로 수신.

심층 분석은 `/code-review` 에서 rapp_review.py 러너가 target 전체 대상으로 수행.
본 훅은 저장 직후 경량 검사만 담당 (p95 < 3s 목표).

비-C++ 확장자는 즉시 early-return (성능 가드).
"""
import json
import os
import sys
from pathlib import Path

# 플러그인 레이아웃 기준 절대 경로로 scripts 디렉토리 해석.
# 환경변수 우선, 없으면 hook 파일 위치 기반 상대 경로.
_PLUGIN_ROOT = Path(
    os.environ.get("CLAUDE_PLUGIN_ROOT")
    or Path(__file__).resolve().parent.parent
)
_SCRIPTS_DIR = _PLUGIN_ROOT / "scripts" / "cpp-static-analysis"

sys.path.insert(0, str(_SCRIPTS_DIR))
from encoding import safe_print  # noqa: E402
from hard_check import load_config, run_all as hc_run_all  # noqa: E402
from patterns import run_patterns  # noqa: E402
from models import SEV_BLOCKER, SEV_MAJOR, CONF_HIGH  # noqa: E402
from cpp_parser import CPP_EXTENSIONS  # noqa: E402

_CONFIG = None

# UB 위험이라 confidence 무관하게 block으로 올리는 rule.
# SMELL-09(non-virtual dtor): conf=MEDIUM이지만 슬라이싱·릭 직결.
HOOK_BLOCK_ALWAYS: frozenset[str] = frozenset({"SMELL-09"})


def _load_config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_config(None)
    return _CONFIG


def _extract_file_path(data: dict) -> str:
    return (data.get("tool_input", {}).get("file_path")
            or data.get("tool_response", {}).get("filePath", ""))


def _collect_findings(file_path: Path) -> list | None:
    try:
        config = _load_config()
        hc = hc_run_all(file_path, config)
        pat = run_patterns(file_path, "all")
        return hc + pat.findings
    except Exception:
        return None


def _findings_to_text(findings: list) -> str:
    """finding 1건당 2줄: 본문 + suggestion(있을 때)."""
    lines: list[str] = []
    for f in findings:
        lines.append(f.to_text_line())
        if getattr(f, "suggestion", ""):
            lines.append(f"  suggestion: {f.suggestion}")
    return "\n".join(lines)


def _is_block_finding(f) -> bool:
    """block 게이팅 — A2 + 화이트리스트.

    - blocker: 무조건
    - HOOK_BLOCK_ALWAYS rule: conf 무관하게 block (UB 위험)
    - major & confidence 비어있음: hard_check 임계 위반 (기계적 확정)
    - major & confidence=HIGH: 확실한 patterns 악취
    - 그 외: safe_print
    """
    if f.severity == SEV_BLOCKER:
        return True
    if f.rule in HOOK_BLOCK_ALWAYS:
        return True
    if f.severity != SEV_MAJOR:
        return False
    return (not f.confidence) or f.confidence == CONF_HIGH


def _block_reason(blockers: list) -> str:
    return (
        f"{len(blockers)}건 block. 너는 방금 작성한 코드의 검수자다 — 변호인이 아니라 검사.\n"
        f"이 findings는 코드가 답해야 할 **의혹**이다. NOPATTERN은 의도성 증명이 있을 때만.\n\n"
        f"금지 어휘 (이런 어휘로 dismiss 시도 금지):\n"
        f"  변호어   : '얇은 wrapper', '의도된 패턴', '표준 관행', '흔한 관용',\n"
        f"             '이미 분리돼 있으니', '이미 동작하니'\n"
        f"  비용회피 : '실용적', '과도', '규모가 크다', '오버엔지니어링',\n"
        f"             '현상 유지가 낫다', '억제가 낫다'\n"
        f"  메트릭회피: '판단 애매', '정보 불충분'\n"
        f"  과거근거 : '원래 그랬으니'는 타당성 근거 아님.\n\n"
        f"선택지:\n"
        f"  (a) 수정 — 국소/설계 층위 맞춰. 헬퍼 추출로 줄 수만 맞추는 피상적 분리 금지.\n"
        f"      설계 수정 규모 크다고 (b)/(c)로 도피 금지.\n"
        f"  (b) NOPATTERN — 의도된 패턴 **증명** 있을 때만. '귀찮아서'는 사유 아님.\n"
        f"  (c) `// REVIEW(rule): <사유>` — 확신 없으면 기본값. 사용자 리뷰 대기.\n\n"
        f"확신 없는 (a) 대신 (c). 안이한 (b) 대신 (a) 또는 (c).\n"
        f"suggestion 적합성부터 검증 (rule은 generic 휴리스틱).\n\n"
        f"{_findings_to_text(blockers)}"
    )


def _warn_summary(warns: list, file_name: str) -> str:
    """safe_print 대상 요약 — 흐름 유지하되 존재는 알림."""
    return (
        f"hook: {file_name} — {len(warns)}건 경고 (흐름 유지).\n"
        f"{_findings_to_text(warns)}"
    )


def main():
    """C++ 파일 저장 시 호출. rkit 정책에 따라 항상 non-blocking.

    - 비-C++ 확장자: 조용히 종료 (Node 브릿지에서 이미 필터링하지만 이중 안전장치)
    - 분석 실패: stderr 경고만, 리턴 코드 0
    - finding 있음: stderr 경고로 요약 출력
    - finding 없음: 조용히 종료 (Claude 프롬프트 오염 방지)
    """
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # stdin 없거나 파싱 실패 — 조용히 종료

    fp = _extract_file_path(data)
    if not fp:
        return

    fp_path = Path(fp)
    if fp_path.suffix.lower() not in CPP_EXTENSIONS:
        return  # 비-C++ early-return

    findings = _collect_findings(fp_path)
    if findings is None:
        # 분석 실패 — stderr 경고만, block 금지
        safe_print(
            f"hook(cpp-static-analysis): {fp_path.name} 분석 실패 — skip",
            file=sys.stderr,
        )
        return
    if not findings:
        return  # 정상 — 조용히 종료

    blockers = [f for f in findings if _is_block_finding(f)]
    warns = [f for f in findings if not _is_block_finding(f)]

    # rkit 정책: decision:block 사용 금지. 모두 stderr 경고.
    if blockers:
        safe_print(_block_reason(blockers), file=sys.stderr)
    if warns:
        safe_print(_warn_summary(warns, fp_path.name), file=sys.stderr)


if __name__ == "__main__":
    main()
