"""rapp-review MD 렌더러 — Finding 리스트를 결정론적 텍스트로 덤프.

Claude 호출 없이 입력→출력이 1:1 결정. 누락 0, 요약·판단 생성 금지.

leaf 모듈: encoding + models 만 import. hard_check / review_config 의존 없음.

설계 근거: docs/rapp-review-plan.md §단계 3
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from encoding import safe_print
from models import (
    Finding, SEV_BLOCKER, SEV_MAJOR, SEV_MINOR, ALL_SEVERITIES,
)

# 정렬 우선순위는 ALL_SEVERITIES의 인덱스 (desc 순서로 정의됨).
# 별도 _SEV_ORDER dict를 두지 않고 단일 진실 사용.

# group_by 허용값 (단계 3 범위)
GROUP_BY_SEVERITY = "severity"
GROUP_BY_FILE = "file"
GROUP_BY_LAYER = "layer"  # 단계 4에서 본격 구현. 단계 3은 fallback
_SUPPORTED_GROUP_BY = (GROUP_BY_SEVERITY, GROUP_BY_FILE)

# 0건 케이스 고정 텍스트. plan §0건 케이스의 정확한 표현을 보존한다.
# 변경 시 SKILL.md / docs / 테스트 단언과 동기화 필요.
ZERO_FINDINGS_NOTE = (
    "**Note**: 이 스캔은 기계적 임계값 기반입니다.\n"
    "findings 0건이 \"검토 완료\"를 의미하지 않습니다.\n"
    "설계 적합성·책임 분리·명명 등 심층 주제는 대화로 논의 가능합니다."
)


@dataclass(frozen=True)
class ScanMeta:
    """렌더링에 필요한 스캔 메타데이터.

    오케스트레이터(단계 4)가 채워서 전달. timestamp는 ISO 비슷한 사람-친화 표기
    ("2026-04-17 14:30:22") 권장. config_hash/git_commit은 짧은 ID 또는 "" 가능.
    """
    timestamp: str
    scope: str
    git_commit: str = ""
    git_dirty_files: int = 0
    config_hash: str = ""
    total_files: int = 0


def render_summary_md(
    findings: list[Finding], meta: ScanMeta,
    group_by: str = GROUP_BY_SEVERITY, split_by_layer: bool = False,
    class_graph_md: str = "",
) -> str:
    """findings + meta를 markdown 요약으로 변환. 결정론적, side effect 없음.

    split_by_layer / group_by="layer"는 단계 4에서 layer 매핑이 인프라로
    들어온 후 본격 지원. 단계 3에서는 stderr 경고 후 severity로 폴백.

    class_graph_md가 비어있지 않으면 per-file counts 뒤·findings 앞에 삽입.
    0건 케이스에서도 Note 뒤에 삽입. 오케스트레이터가 project_graph의
    render_metrics_summary_md 결과를 전달하는 계약 (config.metrics.dump_all_values).
    """
    if split_by_layer:
        safe_print("경고: split_by_layer는 단계 4에서 지원 예정 — 무시", file=sys.stderr)
    grouping = _resolve_group_by(group_by)
    if not findings:
        return _zero_findings_md(meta) + class_graph_md
    sections = (
        _header_md(meta, findings),
        _per_file_counts_md(findings),
        class_graph_md,
        _findings_md(findings, grouping),
    )
    return "\n".join(s for s in sections if s) + "\n"


def _resolve_group_by(value: str) -> str:
    if value in _SUPPORTED_GROUP_BY:
        return value
    if value == GROUP_BY_LAYER:
        safe_print(
            f"경고: group_by='{value}'는 단계 4에서 지원 예정 — "
            f"'{GROUP_BY_SEVERITY}' 사용", file=sys.stderr,
        )
    else:
        safe_print(
            f"경고: group_by='{value}' 알 수 없음 — '{GROUP_BY_SEVERITY}' 사용",
            file=sys.stderr,
        )
    return GROUP_BY_SEVERITY


def _zero_findings_md(meta: ScanMeta) -> str:
    return (
        "# Review Summary\n\n"
        "- total: 0 findings\n"
        f"- scope: {meta.scope} "
        f"(config {meta.config_hash}, commit {meta.git_commit})\n\n"
        f"{ZERO_FINDINGS_NOTE}\n"
    )


def _header_md(meta: ScanMeta, findings: list[Finding]) -> str:
    counts = _count_by_severity(findings)
    dirty = (
        f" (+uncommitted: {meta.git_dirty_files} files)"
        if meta.git_dirty_files else ""
    )
    total = len(findings)
    return (
        "# Review Summary\n\n"
        f"- timestamp: {meta.timestamp}\n"
        f"- scope: {meta.scope}\n"
        f"- git_commit: {meta.git_commit}{dirty}\n"
        f"- config_hash: {meta.config_hash}\n"
        f"- total: {total} "
        f"(blocker {counts[SEV_BLOCKER]} / "
        f"major {counts[SEV_MAJOR]} / "
        f"minor {counts[SEV_MINOR]})\n"
    )


def _empty_sev_counts() -> dict[str, int]:
    return {s: 0 for s in ALL_SEVERITIES}


def _count_by_severity(findings: Iterable[Finding]) -> dict[str, int]:
    out = _empty_sev_counts()
    for f in findings:
        if f.severity in out:
            out[f.severity] += 1
    return out


def _md_table_escape(s: str) -> str:
    """마크다운 표 셀 안전화 — '|' 와 백슬래시 이스케이프, 줄바꿈 → 공백."""
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _md_inline_code_safe(s: str) -> str:
    """인라인 코드 백틱 충돌 방지 — 백틱은 동등한 단일 인용부호로 치환."""
    return s.replace("`", "'") if "`" in s else s


def _per_file_counts_md(findings: list[Finding]) -> str:
    """파일별 severity 카운트 표 (file asc 정렬)."""
    by_file: dict[str, dict[str, int]] = defaultdict(_empty_sev_counts)
    for f in findings:
        if f.severity in by_file[f.file]:
            by_file[f.file][f.severity] += 1
    lines = [
        "\n## Per-file counts\n",
        "| file | blocker | major | minor |",
        "| --- | --- | --- | --- |",
    ]
    for fname in sorted(by_file):
        c = by_file[fname]
        lines.append(
            f"| {_md_table_escape(fname)} | "
            f"{c[SEV_BLOCKER]} | {c[SEV_MAJOR]} | {c[SEV_MINOR]} |"
        )
    return "\n".join(lines)


def _line_int(s: str) -> int:
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def _sev_index(severity: str) -> int:
    """ALL_SEVERITIES desc 순서의 index. 미상이면 후순위(=99)."""
    try:
        return ALL_SEVERITIES.index(severity)
    except ValueError:
        return 99


def _sort_key(f: Finding) -> tuple[int, str, int]:
    return (_sev_index(f.severity), f.file, _line_int(f.lines_hint))


def _findings_md(findings: list[Finding], group_by: str) -> str:
    if group_by == GROUP_BY_FILE:
        return _findings_grouped_by_file(findings)
    return _findings_grouped_by_severity(findings)


def _findings_grouped_by_severity(findings: list[Finding]) -> str:
    sorted_fs = sorted(findings, key=_sort_key)
    lines = ["\n## Findings (severity desc → file → line)"]
    for f in sorted_fs:
        lines.extend(_finding_block(f))
    return "\n".join(lines)


def _findings_grouped_by_file(findings: list[Finding]) -> str:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_file[f.file].append(f)
    lines = ["\n## Findings (per file)"]
    for fname in sorted(by_file):
        lines.append(f"\n### {fname}")
        for f in sorted(by_file[fname], key=_sort_key):
            lines.extend(_finding_block(f))
    return "\n".join(lines)


def _finding_block(f: Finding) -> list[str]:
    has_line = bool(f.lines_hint) and f.lines_hint != "0"
    location = f"{f.file}:{f.lines_hint}" if has_line else f.file
    rule = f.rule or f.type or "unknown"
    sym = f" in `{_md_inline_code_safe(f.symbol)}`" if f.symbol else ""
    return [
        f"- {location} **[{f.severity}]** `{_md_inline_code_safe(rule)}`{sym}",
        f"  > {f.message}",
    ]
