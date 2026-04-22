"""rapp-review CLI 러너 — config 로드 → hard_check → XML/MD 산출 → 디렉토리 회전.

진입점:  python .claude/scripts/rapp_review.py --target src/auth --config project-config.json

산출물:
    {paths.review}/{timestamp}/findings.xml   (진실 원본)
    {paths.review}/{timestamp}/summary.md     (결정론적 뷰)
    {paths.review}/latest -> {timestamp}/     (옵션: review.output.keep_latest_symlink)

설계 근거: docs/rapp-review-plan.md §단계 4
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# UTF-8 self-reexec 가드 — 스크립트로 직접 실행될 때만 동작 (__main__ 한정).
# encoding.py의 setup_utf8_io()는 import 후에만 동작하므로 import 전 에러
# (ImportError, argparse 조기 exit 등)의 stderr가 Windows cp949로 깨진다.
# PYTHONUTF8 환경을 확인해 없으면 자기 자신을 UTF-8 모드로 재기동.
# 재기동 후엔 가드 조건 불만족으로 자동 통과 → 무한루프 없음.
# (from __future__ import는 parse-time 지시자로 stdio 영향 0이라 가드보다 앞.)
# subprocess.run 사용 이유: Windows의 os.execvpe는 POSIX exec과 달리 부모가
# 즉시 종료되어 stdout 전달이 끊긴다. run+wait로 POSIX/Windows 모두 안정.
# __main__ 체크 이유: 테스트 등에서 import 시 재기동이 발생하면 부모 프로세스가
# 종료되어 테스트 자체가 중단된다. 스크립트 직접 실행(__main__)일 때만 가드.
# ─────────────────────────────────────────────────────────────
import os as _os
import sys as _sys
if __name__ == "__main__" and _os.environ.get("PYTHONUTF8") != "1":
    import subprocess as _sp
    _env = {**_os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    _sys.exit(_sp.run(
        [_sys.executable, __file__, *_sys.argv[1:]], env=_env,
    ).returncode)

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from encoding import (  # noqa: E402
    load_json_config, read_file, safe_print, subprocess_env, write_file,
)
from models import (  # noqa: E402
    Finding, VERSION, xml_attr, XML_TAG_FINDINGS,
)
from cpp_parser import CPP_EXTENSIONS  # noqa: E402
from hard_check import (  # noqa: E402
    load_config as load_hc_config, run_all as hc_run_all,
    XML_SOURCE_HARD_CHECK,
)
from arch_check import run_all as arch_run_all  # noqa: E402
from patterns import (  # noqa: E402
    run_patterns, SuppressionOpts,
)
from pattern_rules.suppression import parse_patternsignore  # noqa: E402
from review_config import ReviewConfig, load_review_config  # noqa: E402
from render_review import ScanMeta, render_summary_md  # noqa: E402
from cpp_parser import CppParser  # noqa: E402
from project_graph import (  # noqa: E402
    build as build_project_graph,
    render_metrics_summary_xml,
    render_metrics_summary_md,
    ProjectGraph,
)
from structural_brief import render_structural_brief_md  # noqa: E402
from metrics import run_all as metrics_run_all  # noqa: E402

# finding.tool 값 (origin 구분). rapp_review 통합 시점에만 주입.
_TOOL_HARD_CHECK = "hard_check"
_TOOL_PATTERNS = "patterns"
_TOOL_ARCH_CHECK = "arch_check"
_TOOL_METRICS = "metrics"

# <findings source=...> 속성값. 순서 고정(소비자 비교 안정성).
_SOURCE_COMBINED = (
    f"{_TOOL_HARD_CHECK}+{_TOOL_PATTERNS}+{_TOOL_ARCH_CHECK}+{_TOOL_METRICS}"
)

# config 키 — paths 섹션
_CK_PATHS = "paths"
_CK_PATHS_REVIEW = "review"

# 산출물 파일명. SKILL.md의 소비 프로토콜과 계약 — 변경 시 단계 5 동기화.
_OUT_FINDINGS = "findings.xml"
_OUT_SUMMARY = "summary.md"
_OUT_STRUCTURAL_BRIEF = "structural-brief.md"
_LATEST_LINK = "latest"

# --config 미지정 시 자동 탐색할 파일명.
_DEFAULT_CONFIG_FILENAME = "project-config.json"

# cwd 기준 상대 탐색 우선순위. 첫 발견 파일 채택.
# 1) 프로젝트 루트 바로 아래 (개인 취향 / 플랫 레이아웃)
# 2) .rkit/cpp-static-analysis/ 하위 (rkit 플러그인 배포 경로)
# 3) .claude/ 하위 (기존 rapp 배포 호환)
_AUTO_DISCOVERY_SUBDIRS = ("", ".rkit/cpp-static-analysis", ".claude")

# config.paths.review 미정 시 기본값
_DEFAULT_REVIEW_DIR = ".rkit/state/cpp-static-analysis"

# git 명령 실패/타임아웃 시 폴백
_GIT_TIMEOUT_SEC = 5
_EMPTY_GIT = ""


# ─────────────────────────────────────────────────────────────
# config 로드
# ─────────────────────────────────────────────────────────────

def _load_full_config(config_path: Path | None) -> tuple[dict, dict, ReviewConfig, str]:
    """(hard_check_config, raw_config, review_cfg, paths_review) 반환.

    hard_check_config: thresholds + layers (hard_check.run_all 인자용)
    raw_config: 원본 JSON dict (review/paths 등 다른 섹션 추출용)
    review_cfg: review 섹션 정규화 결과
    paths_review: 산출물 디렉토리 베이스 (POSIX 상대경로)
    """
    hc_cfg = load_hc_config(config_path)
    raw = load_json_config(config_path) if config_path and config_path.exists() else {}
    if not isinstance(raw, dict):
        raw = {}
    review_cfg = load_review_config(raw)
    paths = raw.get(_CK_PATHS) if isinstance(raw.get(_CK_PATHS), dict) else {}
    paths_review = paths.get(_CK_PATHS_REVIEW) or _DEFAULT_REVIEW_DIR
    if not isinstance(paths_review, str) or not paths_review.strip():
        safe_print(
            f"경고: paths.review가 비어있거나 문자열 아님 — 기본값 {_DEFAULT_REVIEW_DIR!r} 사용",
            file=sys.stderr,
        )
        paths_review = _DEFAULT_REVIEW_DIR
    return hc_cfg, raw, review_cfg, paths_review


def _resolve_target(arg_target: str | None, review_cfg: ReviewConfig) -> Path:
    target = arg_target or review_cfg.default_target
    return Path(target)


# ─────────────────────────────────────────────────────────────
# 메타데이터 수집
# ─────────────────────────────────────────────────────────────

def _git_short_commit() -> str:
    return _git_run(["git", "rev-parse", "--short", "HEAD"])


def _git_dirty_count() -> int:
    out = _git_run(["git", "status", "--porcelain"])
    if not out:
        return 0
    return sum(1 for line in out.splitlines() if line.strip())


def _git_run(cmd: list[str]) -> str:
    """git 명령 실행. 실패/미설치/타임아웃 시 빈 문자열 반환 (no-throw)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_GIT_TIMEOUT_SEC,
            env=subprocess_env(), check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return _EMPTY_GIT
    if result.returncode != 0:
        return _EMPTY_GIT
    return result.stdout.strip()


def _config_hash(config_path: Path | None) -> str:
    """project-config.json 내용의 SHA-256 8자리. 미존재 시 빈 문자열."""
    if config_path is None or not config_path.exists():
        return ""
    try:
        content = read_file(config_path).encode("utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return hashlib.sha256(content).hexdigest()[:8]


def _build_scan_meta(
    target: Path, config_path: Path | None, total_files: int, now: datetime,
) -> ScanMeta:
    return ScanMeta(
        timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
        scope=_posix(str(target)),
        git_commit=_git_short_commit(),
        git_dirty_files=_git_dirty_count(),
        config_hash=_config_hash(config_path),
        total_files=total_files,
    )


def _posix(p: str) -> str:
    return p.replace("\\", "/")


# ─────────────────────────────────────────────────────────────
# XML 직렬화 (findings.xml — 진실 원본)
# ─────────────────────────────────────────────────────────────

def _render_findings_xml(
    findings: Iterable[Finding], meta: ScanMeta, now: datetime,
    graph: ProjectGraph | None = None,
) -> str:
    """plan §findings.xml 스키마. 메타데이터 attribute + 평탄 finding 목록.

    source는 rapp-review에서 실행된 모든 도구(hard_check + patterns + arch_check +
    metrics)의 합본 문자열. 각 개별 finding은 `tool` attr로 origin 구분.
    graph가 주어지면 <metrics_summary> 블록을 닫는 태그 직전에 삽입 (P5, 옵션).
    """
    head_attrs = " ".join((
        f"source={xml_attr(_SOURCE_COMBINED)}",
        f'version="{VERSION}"',
        f"generated={xml_attr(now.strftime('%Y-%m-%dT%H:%M:%S'))}",
        f"git_commit={xml_attr(meta.git_commit)}",
        f'git_dirty="{ "true" if meta.git_dirty_files else "false" }"',
        f'git_dirty_files="{meta.git_dirty_files}"',
        f"config_hash={xml_attr(meta.config_hash)}",
        f"scope={xml_attr(meta.scope)}",
        f'total_files="{meta.total_files}"',
    ))
    finding_lines = "\n".join(f.to_xml() for f in findings)
    if finding_lines:
        finding_lines += "\n"
    tail = ""
    if graph is not None:
        tail = render_metrics_summary_xml(graph) + "\n"
    return f"<{XML_TAG_FINDINGS} {head_attrs}>\n{finding_lines}{tail}</{XML_TAG_FINDINGS}>\n"


# ─────────────────────────────────────────────────────────────
# 산출 디렉토리 / 파일 작성
# ─────────────────────────────────────────────────────────────

def _ensure_run_dir(base: Path, subdir_format: str, now: datetime) -> Path:
    """timestamp 기반 run 디렉토리 생성 후 반환."""
    name = now.strftime(subdir_format)
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_artifacts(
    run_dir: Path, xml_str: str, md_str: str, brief_str: str = "",
) -> None:
    write_file(run_dir / _OUT_FINDINGS, xml_str)
    write_file(run_dir / _OUT_SUMMARY, md_str)
    if brief_str:
        write_file(run_dir / _OUT_STRUCTURAL_BRIEF, brief_str)


# ─────────────────────────────────────────────────────────────
# latest 심볼릭 링크
# ─────────────────────────────────────────────────────────────

def _update_latest_symlink(base: Path, run_dir: Path, enabled: bool) -> None:
    """`latest` 심볼릭 링크를 run_dir로 갱신. 권한 부족(Windows) 등은 경고 후 무시."""
    if not enabled:
        return
    link = base / _LATEST_LINK
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(run_dir.name, link, target_is_directory=True)
    except (OSError, NotImplementedError) as e:
        safe_print(
            f"경고: latest 심볼릭 링크 생성 실패 ({e}) — 무시",
            file=sys.stderr,
        )


# ─────────────────────────────────────────────────────────────
# retention (오래된 디렉토리 정리)
# ─────────────────────────────────────────────────────────────

def _retention_candidates(base: Path) -> list[Path]:
    """retention 대상 후보. 정규 디렉토리이며 findings.xml을 포함한 것만.

    `latest` symlink, 점/언더스코어 prefix 디렉토리는 제외 (사용자 임시물 보호).
    """
    if not base.is_dir():
        return []
    out: list[Path] = []
    for entry in base.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.name in (_LATEST_LINK,) or entry.name.startswith((".", "_")):
            continue
        if not (entry / _OUT_FINDINGS).is_file():
            continue
        out.append(entry)
    return out


def _apply_retention(base: Path, max_keep: int) -> None:
    """오래된 run 디렉토리 삭제. base 외부 경로는 절대 건드리지 않음."""
    candidates = _retention_candidates(base)
    if len(candidates) <= max_keep:
        return
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    base_resolved = base.resolve()
    for old in candidates[max_keep:]:
        try:
            target_resolved = old.resolve()
        except OSError:
            continue
        if base_resolved not in target_resolved.parents:
            safe_print(
                f"경고: retention 대상 {old} 가 base 외부로 해석됨 — 건너뜀",
                file=sys.stderr,
            )
            continue
        try:
            shutil.rmtree(old)
        except OSError as e:
            safe_print(f"경고: 디렉토리 삭제 실패 {old} ({e})", file=sys.stderr)


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────

def _count_target_files(target: Path) -> int:
    if not target.is_dir():
        return 0
    return sum(1 for p in target.rglob("*")
               if p.is_file() and p.suffix.lower() in CPP_EXTENSIONS)


def _validate_output_base(base: Path) -> Path:
    """출력 베이스가 디스크 루트면 거부 (retention의 잠재적 광범위 삭제 차단)."""
    resolved = base.resolve()
    if resolved.parent == resolved:
        raise ValueError(
            f"output base {resolved!s}는 디스크 루트 — 안전상 거부 "
            "(retention이 동일 위치의 모든 정규 디렉토리를 후보로 봄)"
        )
    return base


def _render_artifacts(
    findings: list[Finding], meta: ScanMeta, review_cfg: ReviewConfig, now: datetime,
    graph: ProjectGraph | None = None,
) -> tuple[str, str, str]:
    """(xml_str, md_str, brief_str) 반환. 디스크 I/O 없음 — 실패 시 run_dir 미생성 보장.

    graph가 전달되면 config.metrics.dump_all_values=true로 간주되어 <metrics_summary>
    블록이 findings.xml 말미에, summary.md에 Class graph 섹션이, 그리고
    structural-brief.md가 별도 산출물로 생성된다 (B축: 구조 요약기).
    """
    xml_str = _render_findings_xml(findings, meta, now, graph=graph)
    class_graph_md = render_metrics_summary_md(graph) if graph is not None else ""
    md_str = render_summary_md(
        findings, meta,
        group_by=review_cfg.group_by,
        split_by_layer=review_cfg.split_by_layer,
        class_graph_md=class_graph_md,
    )
    brief_str = render_structural_brief_md(graph, findings) if graph is not None else ""
    return xml_str, md_str, brief_str


def _tag_tool(findings: Iterable[Finding], tool: str) -> list[Finding]:
    """각 Finding 에 origin tool 주입. 기존 인스턴스는 보존(replace)."""
    return [replace(f, tool=tool) for f in findings]


def _patternsignore_path(config_path: Path | None, target: Path) -> Path:
    """`.patternsignore` 탐색 경로. config 인접 > target 디렉토리 순."""
    if config_path is not None:
        base = config_path.parent if config_path.is_file() else config_path
        return base / ".patternsignore"
    base = target if target.is_dir() else target.parent
    return base / ".patternsignore"


def _build_patterns_sup(raw_cfg: dict, config_path: Path | None, target: Path) -> SuppressionOpts:
    """rapp-review용 SuppressionOpts. suppression ON, waivers_log 없음."""
    ignore_path = _patternsignore_path(config_path, target)
    ignore_text = ""
    ignore_entries = None
    if ignore_path.is_file():
        try:
            ignore_text = read_file(ignore_path)
        except (OSError, UnicodeDecodeError):
            ignore_text = ""
        ignore_result = parse_patternsignore(ignore_path)
        ignore_entries = ignore_result.entries
    return SuppressionOpts(
        enabled=True, config=raw_cfg or None,
        ignore_entries=ignore_entries, ignore_text=ignore_text,
    )


def _collect_all_findings(
    target: Path, hc_cfg: dict, raw_cfg: dict, config_path: Path | None,
) -> tuple[list[Finding], ProjectGraph]:
    """hard_check + patterns + arch_check + metrics 실행 후 tool 주입 + 정렬.

    반환: (정렬된 findings 리스트, metrics 실행에 사용한 ProjectGraph).
    ProjectGraph는 render 단계에서 선택적으로 <metrics_summary> 생성에 사용.

    patterns/arch_check/metrics는 입력 예외 시(rules 미설정, layers 비어있음,
    metrics.enabled=false 등) 내부적으로 빈 리스트 반환 — rapp_review는 그대로 수용.

    metrics pre-pass (§3.1): ProjectGraph.build → metrics.run_all. 기존 hc/patterns와
    별개로 ProjectGraph를 1회 수집. 파일 파싱은 각 tool이 독립 수행 (P6 이전 허용).
    """
    hc = _tag_tool(hc_run_all(target, hc_cfg), _TOOL_HARD_CHECK)
    sup = _build_patterns_sup(raw_cfg, config_path, target)
    pat_result = run_patterns(target, cli_category="all", sup=sup)
    pat = _tag_tool(pat_result.findings, _TOOL_PATTERNS)
    arch = _tag_tool(arch_run_all(target, hc_cfg), _TOOL_ARCH_CHECK)

    # metrics pre-pass: project graph 수집 → 메트릭 rule 적용
    graph_parser = CppParser()
    graph = build_project_graph(target, graph_parser)
    metrics_findings = _tag_tool(
        metrics_run_all(target, graph, raw_cfg), _TOOL_METRICS,
    )

    combined = hc + pat + arch + metrics_findings
    sorted_findings = sorted(combined, key=lambda f: (f.file, f.lines_hint, f.rule, f.tool))
    return sorted_findings, graph


def _dump_enabled(raw_cfg: dict) -> bool:
    """config.metrics.dump_all_values 플래그 읽기. 기본 False."""
    metrics_cfg = raw_cfg.get("metrics", {}) if isinstance(raw_cfg, dict) else {}
    return bool(metrics_cfg.get("dump_all_values", False))


def run(
    target: Path, config_path: Path | None, base_override: Path | None = None,
    *, preloaded: tuple[dict, dict, ReviewConfig, str] | None = None,
) -> Path:
    """rapp-review 1회 실행. run_dir 경로 반환.

    base_override: paths.review 무시하고 임의 베이스 사용.
    preloaded: main이 이미 _load_full_config를 호출한 경우 결과를 재사용 (이중 로드 방지).

    실행 순서: 산출물 직렬화 모두 마친 후 run_dir 생성 → 작성. hc_run_all/render 실패 시
    빈 디렉토리가 남지 않는다 (적대적 검수 §B 반영).
    """
    now = datetime.now()
    hc_cfg, raw_cfg, review_cfg, paths_review = (
        preloaded if preloaded is not None else _load_full_config(config_path)
    )
    base = _validate_output_base(base_override or Path(paths_review))
    findings, graph = _collect_all_findings(target, hc_cfg, raw_cfg, config_path)
    meta = _build_scan_meta(target, config_path, _count_target_files(target), now)
    # structural-brief.md는 항상 생성 (rkit 통합: /code-review 가 Read 로 소비).
    # _dump_enabled 는 findings.xml 내 <metrics_summary> 블록 삽입 여부만 제어.
    xml_str, md_str, brief_str = _render_artifacts(
        findings, meta, review_cfg, now, graph=graph,
    )
    run_dir = _ensure_run_dir(base, review_cfg.subdir_format, now)
    _write_artifacts(run_dir, xml_str, md_str, brief_str)
    _update_latest_symlink(base, run_dir, review_cfg.keep_latest_symlink)
    _apply_retention(base, review_cfg.retention)
    safe_print(f"cpp-static-analysis: {run_dir} ({len(findings)} findings)")
    return run_dir


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="rapp-review CLI runner")
    p.add_argument("--target", default=None, help="대상 디렉토리 (생략 시 config.review.default_target)")
    p.add_argument("--config", default=None,
                   help=f"project-config.json 경로 (생략 시 cwd의 {_DEFAULT_CONFIG_FILENAME} 자동 탐색)")
    p.add_argument("--output-base", default=None, help="paths.review 무시하고 출력 베이스 override")
    return p


def _auto_discovery_candidates(cwd: Path) -> list[Path]:
    """cwd 기준 config 자동 탐색 후보 경로 목록. 우선순위 순서."""
    return [
        cwd / sub / _DEFAULT_CONFIG_FILENAME if sub else cwd / _DEFAULT_CONFIG_FILENAME
        for sub in _AUTO_DISCOVERY_SUBDIRS
    ]


def _resolve_config_path(arg_config: str | None) -> Path | None:
    """--config 인자 해소. 명시값 > cwd 자동 탐색 > None(경고 동반).

    명시 경로는 존재 여부 무관히 그대로 반환 (부재 시 뒤단 _config_hash/load가 graceful 처리).
    자동 탐색은 cwd 및 cwd/.claude 하위 순으로 훑어 첫 발견 파일 채택.
    못 찾으면 stderr 경고 후 None 반환하여 hard_check 기본 임계 적용을 명시적으로 알림.
    """
    if arg_config:
        return Path(arg_config)
    cwd = Path.cwd()
    for candidate in _auto_discovery_candidates(cwd):
        if candidate.is_file():
            return candidate
    searched = ", ".join(
        f"{sub}/" if sub else "./" for sub in _AUTO_DISCOVERY_SUBDIRS
    )
    safe_print(
        f"경고: --config 미지정 + {_DEFAULT_CONFIG_FILENAME} 자동 탐색 실패 "
        f"(확인 경로: {searched}) — hard_check 기본 임계로 실행 "
        "(project-config.json을 만들어 프로젝트별 thresholds/layers/patterns를 적용하세요)",
        file=sys.stderr,
    )
    return None


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    config_path = _resolve_config_path(args.config)
    preloaded = _load_full_config(config_path)
    target = _resolve_target(args.target, preloaded[2])
    base_override = Path(args.output_base) if args.output_base else None
    run(target, config_path, base_override=base_override, preloaded=preloaded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
