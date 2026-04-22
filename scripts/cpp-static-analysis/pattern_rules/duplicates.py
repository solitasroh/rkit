"""D1 중복 탐지 — 함수 단위 Type-2 클론 검출.

역할:
- Pass 1: 함수별 AST 정규화 → fingerprint (per-file, CacheEntry에 저장)
- Pass 2: fingerprint 해시 인덱스 → 중복 Finding 생성 (cross-file + same-file)

원칙:
- Type-2 클론만 (식별자/리터럴 정규화, 구조 매칭)
- 2+ 함수 그룹이면 탐지 (같은 파일 내 복붙도 포함 — 단일 파일 훅에서도 작동해야 함)
- min_stmts는 순수 Pass 2 필터 (fingerprint 계산에 영향 없음, getter/setter 오탐 억제)

설계 근거: docs/patterns-d1-duplicate-design.md
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter import Node, Tree

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from cache import FunctionFingerprint  # noqa: E402
from cpp_parser import _node_text, F_BODY, F_DECLARATOR  # noqa: E402
from models import (  # noqa: E402
    CAT_DUPLICATE, Finding,
    SEV_MAJOR, CONF_HIGH,
)

if TYPE_CHECKING:
    from cpp_parser import CppParser
    from pattern_rules.suppression import IgnoreRule, SuppressionMap

# ── 상수 ──

DUP_RULE_ID = "DUP-01"

# 정규화 알고리즘 버전. 정규화 로직 변경 시 승격 → context_hash 변경 → 캐시 전역 무효화.
DUP_NORM_V = "1"

# 최소 문장 수 기본값. Pass 2 필터.
MIN_STMT_COUNT = 3


# ─────────────────────────────────────────────────────────────
# AST 정규화 (§2)
# ─────────────────────────────────────────────────────────────

# leaf 노드 → 플레이스홀더 매핑 (Type-2 정규화)
_NORMALIZE_MAP: dict[str, str] = {
    "identifier": "$I",
    "field_identifier": "$FI",
    "type_identifier": "$TI",
    "namespace_identifier": "$NI",
    "number_literal": "$N",
    "string_literal": "$S",
    "char_literal": "$C",
    "true": "$B",
    "false": "$B",
    "null": "$NP",
    "nullptr": "$NP",
}

# 순회 시 완전 생략하는 노드 타입
_SKIP_TYPES = frozenset({"comment"})


def _normalize_node(node: Node, source: bytes) -> str:
    """단일 노드를 정규화된 S-expression 토큰으로 변환. 재귀.

    설계: docs/patterns-d1-duplicate-design.md §2.5
    """
    ntype = node.type

    if ntype in _SKIP_TYPES:
        return ""

    placeholder = _NORMALIZE_MAP.get(ntype)
    if placeholder is not None:
        return placeholder

    # unnamed leaf (키워드/연산자): 원본 텍스트 보존
    if not node.is_named and node.child_count == 0:
        return _node_text(node, source)

    # 내부 노드: 자식 재귀
    parts: list[str] = []
    for child in node.children:
        part = _normalize_node(child, source)
        if part:
            parts.append(part)
    inner = " ".join(parts)
    return f"({ntype} {inner})" if inner else f"({ntype})"


def _normalize_body(body: Node, source: bytes) -> str:
    """compound_statement를 Type-2 정규화 S-expression으로 변환."""
    return _normalize_node(body, source)


def _fingerprint_hash(normalized: str) -> str:
    """정규화 문자열 → SHA-256 hex digest."""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────
# Pass 1: per-file fingerprint 수집 (§3.2)
# ─────────────────────────────────────────────────────────────

_SKIP_STMT_PREFIXES = ("comment", "preproc_")


def _stmt_count(body: Node) -> int:
    """compound_statement의 직계 문장 수. 주석/전처리기 지시문 제외."""
    return sum(1 for c in body.children
               if c.is_named and not c.type.startswith(_SKIP_STMT_PREFIXES))


_NAME_NODE_TYPES = frozenset({
    "destructor_name", "operator_name",
    "identifier", "field_identifier", "qualified_identifier",
})


def _func_name(func_def: Node, source: bytes) -> str:
    """function_definition에서 함수명 추출."""
    decl = func_def.child_by_field_name(F_DECLARATOR)
    if decl is None:
        return "<unknown>"
    for child in decl.children:
        if child.type in _NAME_NODE_TYPES:
            return _node_text(child, source)
    return "<unknown>"


def _fingerprint_func(
    func_def: Node, source: bytes, smap: "SuppressionMap | None",
) -> FunctionFingerprint | None:
    """단일 function_definition → FunctionFingerprint. 본문 없으면 None."""
    body = func_def.child_by_field_name(F_BODY)
    if body is None or body.type != "compound_statement":
        return None
    line = func_def.start_point[0] + 1
    suppressed = smap.is_suppressed(line, DUP_RULE_ID) if smap else False
    return FunctionFingerprint(
        func_name=_func_name(func_def, source),
        line=line,
        fp_hash=_fingerprint_hash(_normalize_body(body, source)),
        stmt_count=_stmt_count(body),
        inline_suppressed=suppressed,
    )


def compute_fingerprints(
    tree: Tree,
    source: bytes,
    rel: str,
    smap: "SuppressionMap | None",
) -> list[FunctionFingerprint]:
    """파일 내 모든 function_definition에서 fingerprint 수집.

    모든 함수에 대해 계산 (min_stmts 필터 없음, Pass 2에서 적용).
    smap: inline suppression 확인용. None이면 억제 검사 안 함.
    """
    result: list[FunctionFingerprint] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":
            fp = _fingerprint_func(node, source, smap)
            if fp is not None:
                result.append(fp)
        stack.extend(reversed(node.children))
    return result


# ─────────────────────────────────────────────────────────────
# Pass 2: cross-file 중복 매칭 (§3.3)
# ─────────────────────────────────────────────────────────────

@dataclass
class FuncLocation:
    """Pass 2 인덱스 항목."""
    file: str
    func_name: str
    line: int
    stmt_count: int


def _index_file(
    rel: str, fps: list[FunctionFingerprint],
    min_stmts: int, index: dict[str, list[FuncLocation]],
) -> None:
    """단일 파일의 fingerprints를 글로벌 인덱스에 추가."""
    for fp in fps:
        if fp.inline_suppressed or fp.stmt_count < min_stmts:
            continue
        loc = FuncLocation(rel, fp.func_name, fp.line, fp.stmt_count)
        index.setdefault(fp.fp_hash, []).append(loc)


def build_fingerprint_index(
    all_fingerprints: dict[str, list[FunctionFingerprint]],
    ignore_entries: "list[IgnoreRule] | None",
    min_stmts: int = MIN_STMT_COUNT,
) -> dict[str, list[FuncLocation]]:
    """파일별 fingerprints → 글로벌 해시 인덱스 구축.

    필터: inline_suppressed, stmt_count < min_stmts, .patternsignore.
    반환: {fp_hash: [FuncLocation, ...]} — 2+ 함수 그룹. same-file 복붙도 포함.
    """
    from pattern_rules.suppression import is_file_ignored

    index: dict[str, list[FuncLocation]] = {}
    for rel, fps in all_fingerprints.items():
        if ignore_entries and is_file_ignored(rel, DUP_RULE_ID, ignore_entries):
            continue
        _index_file(rel, fps, min_stmts, index)
    return {h: locs for h, locs in index.items() if len(locs) >= 2}


def _dup_message(first: FuncLocation, others: list[FuncLocation]) -> str:
    """DUP-01 Finding message 포맷."""
    suffix = f"(Type-2 클론, {first.stmt_count}문장)"
    if len(others) == 1:
        o = others[0]
        return (f"{first.func_name}() — "
                f"{o.file}:{o.line} {o.func_name}()와 구조 동일 {suffix}")
    parts = ", ".join(f"{o.file}:{o.line} {o.func_name}()" for o in others)
    return (f"{first.func_name}() — "
            f"{len(others)}건 구조 동일: {parts} {suffix}")


def _make_dup_finding(group: list[FuncLocation], severity: str) -> Finding:
    """중복 그룹에서 DUP-01 Finding 생성. severity는 E2 오버라이드 반영."""
    first = group[0]
    return Finding(
        type=CAT_DUPLICATE,
        severity=severity,
        file=first.file,
        message=_dup_message(first, group[1:]),
        rule=DUP_RULE_ID,
        confidence=CONF_HIGH,
        suggestion="공통 함수 추출 또는 템플릿화 검토",
        lines_hint=str(first.line),
        symbol=first.func_name,
    )


def detect_duplicates(
    index: dict[str, list[FuncLocation]],
    severity: str = SEV_MAJOR,
) -> list[Finding]:
    """인덱스에서 중복 Finding 생성 (cross-file + same-file 복붙).

    그룹당 1건. (file, line) 동일 위치만 dedup (중복 수집 방지).
    (file, line) 오름차순 정렬의 첫 함수가 Finding 위치.
    """
    findings: list[Finding] = []
    for _fp_hash, locations in sorted(index.items()):
        seen_locs: set[tuple[str, int]] = set()
        deduped: list[FuncLocation] = []
        for loc in sorted(locations, key=lambda l: (l.file, l.line)):
            key = (loc.file, loc.line)
            if key in seen_locs:
                continue
            seen_locs.add(key)
            deduped.append(loc)
        if len(deduped) < 2:
            continue
        findings.append(_make_dup_finding(deduped, severity))
    return findings


# ─────────────────────────────────────────────────────────────
# Sentinel PatternRule (E2 연동용, §9.4)
# ─────────────────────────────────────────────────────────────

# _shared.py에서 import하면 순환 import 위험 → 지연 import 또는 직접 구성.
# DUP_RULE은 __init__.py에서 조립.
