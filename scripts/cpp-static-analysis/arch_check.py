"""레이어 의존성 검사 (A1) — #include 방향으로 레이어 간 허용되지 않은 의존 탐지.

역할:
- cpp_parser의 preproc_include 쿼리로 #include 수집
- include 경로 → 실제 파일 → 레이어 매핑
- allowed_deps 기반 위반 판정
- Finding 생성

설계 근거: docs/patterns-a1-layer-dep-design.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cpp_parser import (
    CPP_EXTENSIONS, CppParser, _iter_cpp_files, _node_text, _posix, _rel_path,
    _validate_target, PARSE_FILE_ERRORS,
)
from encoding import load_json_config, safe_print, write_file
from models import (
    Finding, FAIL_ON_NONE,
    FMT_XML, FMT_TEXT, FMT_CHOICES,
    SEV_BLOCKER as _SEV_BLOCKER,
    SEV_MAJOR as _SEV_MAJOR,
    XML_TAG_FINDINGS, xml_attr as _xml_attr,
)
from formatters import FormatContext, format_findings, check_fail_on, validate_fail_on
from hard_check import (
    load_config, _detect_layer_cycle,
    _CK_LAYERS, _CK_NAME, _CK_DIRS, _CK_ALLOWED_DEPS,
)

# ── 규칙 상수 ──
RULE_ARCH_01 = "ARCH-01"
_FT_ARCHITECTURE = "architecture"
XML_SOURCE_ARCH_CHECK = "arch_check"

# ── include 쿼리 ──
_Q_INCLUDE = "(preproc_include path: (_) @path)"


# ─────────────────────────────────────────────────────────────
# 파일 인덱스: include 경로 → 실제 파일 매핑
# ─────────────────────────────────────────────────────────────

def build_file_index(target: Path) -> dict[str, str]:
    """target 하위 모든 C++ 헤더/소스의 인덱스. key=상대경로(POSIX), value=동일."""
    index: dict[str, str] = {}
    for fp in target.rglob("*"):
        if fp.is_file() and fp.suffix.lower() in CPP_EXTENSIONS:
            rel = _posix(str(fp.relative_to(target)))
            index[rel] = rel
    return index


def resolve_include(
    inc_path: str, src_rel: str, file_index: dict[str, str],
    include_paths: list[str],
) -> str | None:
    """include 경로를 target 내 상대 경로로 해석. 못 찾으면 None."""
    # 1. 소스 파일과 같은 디렉토리 기준
    src_dir = "/".join(src_rel.split("/")[:-1])
    if src_dir:
        candidate = f"{src_dir}/{inc_path}"
    else:
        candidate = inc_path
    if candidate in file_index:
        return candidate
    # 2. target 루트 기준
    if inc_path in file_index:
        return inc_path
    # 3. include_paths 기준
    for ip in include_paths:
        candidate = f"{ip}/{inc_path}" if ip else inc_path
        if candidate in file_index:
            return candidate
    return None


# ─────────────────────────────────────────────────────────────
# 레이어 매핑
# ─────────────────────────────────────────────────────────────

def resolve_layer(file_path: str, layers: list[dict]) -> str | None:
    """파일 경로를 레이어 이름으로 매핑. longest prefix match."""
    best_name: str | None = None
    best_len = 0
    for layer in layers:
        name = layer.get(_CK_NAME, "")
        if not name:
            continue
        for d in layer.get(_CK_DIRS, []):
            if file_path.startswith(d + "/") and len(d) > best_len:
                best_name = name
                best_len = len(d)
    return best_name


# ─────────────────────────────────────────────────────────────
# include 수집
# ─────────────────────────────────────────────────────────────

def _collect_includes(
    parser: CppParser, fp: Path, rel: str,
) -> list[tuple[str, int]]:
    """파일의 #include 목록을 (경로, 줄번호) 튜플로 수집."""
    try:
        tree, source = parser.parse_file(fp)
    except PARSE_FILE_ERRORS:
        return []
    results = []
    for node in parser.query(tree, _Q_INCLUDE).get("path", []):
        raw = _node_text(node, source).strip().strip('"<>')
        line = node.start_point[0] + 1
        results.append((raw, line))
    return results


# ─────────────────────────────────────────────────────────────
# 의존성 검사
# ─────────────────────────────────────────────────────────────

_SUGGESTION = (
    "의존 방향 추적 → 인터페이스 역전 또는 상위 레이어 경유로 해소, "
    "정당한 예외면 서브레이어로 분리"
)


def _layer_violation_finding(
    rel: str, src_layer: str, dst_layer: str, inc_path: str, line: int,
) -> Finding:
    """레이어 의존 위반 Finding 생성. value=1로 다운스트림 누락 방지."""
    return Finding(
        _FT_ARCHITECTURE, _SEV_MAJOR, rel,
        f"{src_layer} → {dst_layer} 의존: #include \"{inc_path}\":{line} — 레이어 의존 신호",
        rule=RULE_ARCH_01, lines_hint=str(line),
        value=1, limit=0,
        suggestion=_SUGGESTION,
    )


def check_layer_deps(
    parser: CppParser, fp: Path, rel: str,
    layers: list[dict], file_index: dict[str, str],
    include_paths: list[str],
) -> list[Finding]:
    """단일 파일의 #include를 검사하여 레이어 의존성 위반 탐지."""
    src_layer = resolve_layer(rel, layers)
    if src_layer is None:
        return []
    allowed = _get_allowed_deps(src_layer, layers)
    if allowed is None:
        return []
    findings: list[Finding] = []
    for inc_path, line in _collect_includes(parser, fp, rel):
        resolved = resolve_include(inc_path, rel, file_index, include_paths)
        if resolved is None:
            continue
        dst_layer = resolve_layer(resolved, layers)
        if dst_layer is None or dst_layer == src_layer:
            continue
        if dst_layer not in allowed:
            findings.append(_layer_violation_finding(rel, src_layer, dst_layer, inc_path, line))
    return findings


def _get_allowed_deps(layer_name: str, layers: list[dict]) -> list[str] | None:
    """레이어의 allowed_deps 조회. 미지정이면 None."""
    for layer in layers:
        if layer.get(_CK_NAME) == layer_name:
            return layer.get(_CK_ALLOWED_DEPS)
    return None


# ─────────────────────────────────────────────────────────────
# 통합 실행
# ─────────────────────────────────────────────────────────────

def run_all(
    target: Path, config: dict, include_paths: list[str] | None = None,
) -> list[Finding]:
    """target 하위 전체 파일에 레이어 의존성 검사."""
    layers = config[_CK_LAYERS]
    if not layers:
        return []
    # config 순환 검사
    findings = _detect_layer_cycle(layers)
    # 의존성에 allowed_deps가 하나도 없으면 검사 불필요
    if not any(_CK_ALLOWED_DEPS in l for l in layers):
        return findings
    parser = CppParser()
    file_index = build_file_index(target)
    inc_paths = include_paths or []
    for fp in _iter_cpp_files(target):
        rel = _rel_path(fp, target)
        findings.extend(check_layer_deps(parser, fp, rel, layers, file_index, inc_paths))
    return findings


# ─────────────────────────────────────────────────────────────
# 렌더링
# ─────────────────────────────────────────────────────────────

def render_findings(findings: list[Finding], fmt: str) -> str:
    """findings 포맷 렌더링."""
    rendered = format_findings(findings, fmt, FormatContext(tool=XML_SOURCE_ARCH_CHECK))
    if rendered is not None:
        return rendered
    if fmt == FMT_XML:
        inner = "\n".join(f.to_xml() for f in findings)
        return (
            f'<{XML_TAG_FINDINGS} source={_xml_attr(XML_SOURCE_ARCH_CHECK)}'
            f' count="{len(findings)}">\n{inner}\n</{XML_TAG_FINDINGS}>\n'
        )
    if fmt != FMT_TEXT:
        raise ValueError(f"unknown format: {fmt!r}")
    if not findings:
        return "레이어 의존성 위반 없음\n"
    lines = [f.to_text_line() for f in findings]
    return "\n".join(lines) + f"\n\n총 {len(findings)}건\n"


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def _parse_args():
    ap = argparse.ArgumentParser(description="C++ 레이어 의존성 검사 (arch_check)")
    ap.add_argument("--target", required=True, help="대상 디렉토리")
    ap.add_argument("--config", help="project-config.json 경로")
    ap.add_argument("--format", choices=FMT_CHOICES, default=FMT_TEXT)
    ap.add_argument("--output", help="출력 파일")
    ap.add_argument("--fail-on", default=FAIL_ON_NONE)
    ap.add_argument("--include-path", action="append", default=[],
                    help="추가 include 탐색 경로 (반복 가능)")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        fail_on = validate_fail_on(args.fail_on)
    except ValueError as e:
        safe_print(f"에러: {e}", file=sys.stderr)
        return 1
    target = Path(args.target)
    err = _validate_target(target)
    if err:
        safe_print(f"에러: {err}", file=sys.stderr)
        return 1
    config = load_config(Path(args.config) if args.config else None)
    include_paths = args.include_path
    # config의 build.include_paths도 합산
    if args.config:
        raw = load_json_config(Path(args.config)) or {}
        config_inc = raw.get("build", {}).get("include_paths", [])
        if isinstance(config_inc, list):
            include_paths = list(set(include_paths + config_inc))
    findings = run_all(target, config, include_paths)
    rendered = render_findings(findings, args.format)
    if args.output:
        write_file(args.output, rendered)
        safe_print(f"생성: {args.output} ({len(findings)}건)", file=sys.stderr)
    else:
        safe_print(rendered, end="")
    return check_fail_on(findings, fail_on)


if __name__ == "__main__":
    sys.exit(main())
