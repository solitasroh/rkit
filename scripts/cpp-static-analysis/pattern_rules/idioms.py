"""IDIOM-* 패턴 규칙 (관용구 리팩토링 후보 탐지).

설계 근거: docs/patterns-mvp-impl-design.md §4.4
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from tree_sitter import Node, Tree

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from cpp_parser import CppParser, N_CALL_EXPRESSION
from pattern_rules._shared import (
    PatternRule, line_hint, node_text, SEV_MAJOR, CONF_MEDIUM, CAT_IDIOM,
    F_BODY, F_CONDITION,
)

if TYPE_CHECKING:
    from models import Finding

_CATEGORY = CAT_IDIOM
_FOR_TYPES = ("for_statement", "for_range_loop")

# E2 option 키 상수
_OPT_MIN_BRANCHES = "min_branches"
_OPT_MIN_CHAIN_DEPTH = "min_chain_depth"

# ─────────────────────────────────────────────────────────────
# IDIOM-07: Type dispatch (switch N+ case)
# ─────────────────────────────────────────────────────────────

# 다형성 리팩토링 검토 임계값 (patterns-mvp.md §MVP-5).
# 엔터프라이즈에서 project-config.json으로 이동 가능.
MIN_CASE_COUNT = 5

_Q_SWITCH = "(switch_statement) @s"


def detect_type_dispatch_switch(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    min_cases = rule.default_options.get(_OPT_MIN_BRANCHES, MIN_CASE_COUNT)
    out: list[Finding] = []
    for sw in parser.query(tree, _Q_SWITCH).get("s", []):
        body = sw.child_by_field_name(F_BODY)
        if body is None:
            continue
        case_count = sum(1 for c in body.children if c.type == "case_statement")
        if case_count >= min_cases:
            out.append(rule.make_finding(
                rel, f"switch {case_count}개 case — 분기 구조 검토",
                suggestion=(
                    "분기 목적 추적 → 타입 분기면 variant/virtual dispatch, "
                    "값 매핑이면 lookup table, "
                    "의도된 상태 머신이면 NOPATTERN + 사유"
                ),
                value=case_count,
                lines_hint=line_hint(sw),
            ))
    return out


# ─────────────────────────────────────────────────────────────
# IDIOM-01: Nested-for-grid (2중 for 중첩)
# ─────────────────────────────────────────────────────────────

def _has_nested_for(node: Node) -> bool:
    """node의 자손에 for_statement/for_range_loop이 있는지 (자기 자신 제외). 스택 기반."""
    stack = list(node.children)
    while stack:
        c = stack.pop()
        if c.type in _FOR_TYPES:
            return True
        stack.extend(c.children)
    return False


def detect_nested_for_grid(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    stack = list(reversed(tree.root_node.children))
    while stack:
        n = stack.pop()
        if n.type in _FOR_TYPES and _has_nested_for(n):
            out.append(rule.make_finding(
                rel, "2중 for 루프 — 중첩 구조 검토",
                suggestion=(
                    "중첩 목적 추적 → 동일 컬렉션 쌍 탐색이면 해시/정렬로 개선, "
                    "행렬 순회·고정 크기 선형 순회면 NOPATTERN + 사유"
                ),
                lines_hint=line_hint(n),
            ))
            continue  # 내부 중첩은 중복 보고 방지 — children 미탐색
        stack.extend(reversed(n.children))
    return out


# ─────────────────────────────────────────────────────────────
# IDIOM-02/03: Queue/stack manual iteration
# ─────────────────────────────────────────────────────────────

def _body_has_pop(body, source: bytes) -> bool:
    """compound_statement 안에 .pop() 호출이 있는지."""
    for c in body.children:
        text = node_text(c, source)
        if ".pop()" in text:
            return True
    return False


def detect_queue_stack_drain(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for wh in parser.query(tree, "(while_statement) @w").get("w", []):
        cond = wh.child_by_field_name(F_CONDITION)
        if cond is None:
            continue
        cond_text = node_text(cond, source)
        if ".empty()" not in cond_text:
            continue
        body = wh.child_by_field_name(F_BODY)
        if body is None:
            continue
        if _body_has_pop(body, source):
            out.append(rule.make_finding(
                rel, "queue/stack 수동 drain 루프",
                suggestion=(
                    "drain 필요 이유 추적 → 자료구조 선택이 부적절하면 재설계, "
                    "적절하되 반복 패턴이면 유틸 추출, 의도된 패턴이면 NOPATTERN + 사유"
                ),
                lines_hint=line_hint(wh),
            ))
    return out


# ─────────────────────────────────────────────────────────────
# IDIOM-04: Builder method chain (3+)
# ─────────────────────────────────────────────────────────────

MIN_CHAIN_DEPTH = 3


def _chain_depth(node: Node) -> int:
    """call_expression의 메서드 체이닝 깊이. obj.a().b().c() → 3. 반복 기반."""
    if node.type != N_CALL_EXPRESSION:
        return 0
    depth = 0
    current = node
    while current.type == N_CALL_EXPRESSION:
        depth += 1
        # call_expression 안에서 field_expression → 내부 call_expression 추적
        found_next = False
        for c in current.children:
            if c.type == "field_expression":
                for gc in c.children:
                    if gc.type == N_CALL_EXPRESSION:
                        current = gc
                        found_next = True
                        break
                break
        if not found_next:
            break
    return depth


def detect_builder_chain(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    min_depth = rule.default_options.get(_OPT_MIN_CHAIN_DEPTH, MIN_CHAIN_DEPTH)
    out: list[Finding] = []
    seen_lines: set[int] = set()
    stack = list(reversed(tree.root_node.children))
    while stack:
        n = stack.pop()
        if n.type == N_CALL_EXPRESSION:
            depth = _chain_depth(n)
            line = n.start_point[0]
            if depth >= min_depth and line not in seen_lines:
                seen_lines.add(line)
                out.append(rule.make_finding(
                    rel, f"메서드 체이닝 {depth}단계 — 결합도 검토",
                    suggestion=(
                        "체이닝 목적 추적 → 객체 탐색이면 결합도 설계 재검토, "
                        "빌더/fluent API면 NOPATTERN + 사유"
                    ),
                    value=depth,
                    lines_hint=line_hint(n),
                ))
                continue  # 내부 체인 중복 방지 — children 미탐색
        stack.extend(reversed(n.children))
    return out


# ─────────────────────────────────────────────────────────────
# IDIOM-05: Filter-collect (for + if + push_back)
# ─────────────────────────────────────────────────────────────

def _has_push_back(root: Node, source: bytes) -> bool:
    """노드 자손에 push_back 호출이 있는지. 스택 기반."""
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == N_CALL_EXPRESSION:
            if "push_back" in node_text(node, source):
                return True
        stack.extend(node.children)
    return False


def detect_filter_collect(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    stack = list(reversed(tree.root_node.children))
    while stack:
        n = stack.pop()
        if n.type in _FOR_TYPES:
            # for 루프 본문에서 if + push_back 패턴 찾기
            body = n.child_by_field_name(F_BODY)
            if body is None:
                body = n  # for_range_loop은 body 필드가 다를 수 있음
            found = False
            for c in body.children:
                if c.type == "if_statement" and _has_push_back(c, source):
                    out.append(rule.make_finding(
                        rel, "for + if + push_back — std::copy_if 리팩토링 후보",
                        suggestion=(
                            "수동 필터링 이유 추적 → 단순 필터면 std::copy_if/ranges::views::filter, "
                            "변환 동반이면 filter|transform, 부수효과가 있으면 NOPATTERN + 사유"
                        ),
                        lines_hint=line_hint(n),
                    ))
                    found = True
                    break  # 같은 for문에서 중복 방지
            if not found:
                stack.extend(reversed(n.children))
        else:
            stack.extend(reversed(n.children))
    return out


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

IDIOM_RULES: list[PatternRule] = [
    PatternRule("IDIOM-07", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_type_dispatch_switch,
                default_options={_OPT_MIN_BRANCHES: MIN_CASE_COUNT},
                known_options=frozenset({_OPT_MIN_BRANCHES})),
    PatternRule("IDIOM-01", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_nested_for_grid),
    PatternRule("IDIOM-02", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_queue_stack_drain),
    PatternRule("IDIOM-04", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_builder_chain,
                default_options={_OPT_MIN_CHAIN_DEPTH: MIN_CHAIN_DEPTH},
                known_options=frozenset({_OPT_MIN_CHAIN_DEPTH})),
    PatternRule("IDIOM-05", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_filter_collect),
]
