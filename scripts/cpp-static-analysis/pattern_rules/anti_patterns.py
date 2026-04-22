"""AP-* 패턴 규칙 (안티패턴 탐지).

설계 근거: docs/patterns-mvp-impl-design.md §4.3
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from tree_sitter import Node, Tree

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from cpp_parser import CppParser
from pattern_rules._shared import (
    PatternRule, line_hint, SEV_MAJOR, CONF_LOW, CAT_ANTI_PATTERN,
    F_BODY, F_TYPE, N_FIELD_DECLARATION,
    node_text, class_bodies, class_name, field_identifier_text, is_data_member,
)

if TYPE_CHECKING:
    from models import Finding

_CATEGORY = CAT_ANTI_PATTERN

# C++ Core Guidelines 참조 (ID + 원문 제목 — Claude 가 제목으로 즉시 매칭).
_CG_I27 = (
    "참조: C++ Core Guidelines I.27 "
    "'For stable library ABI, consider using a Pimpl idiom'"
)

# AP-08 suggestion 공용 상수 — 함수 본문 길이 제한(30) 회피 + 문구 단일 진실.
_SUG_AP08 = (
    "파일명 분리(*Linux.cpp / *Win.cpp 등) 또는 PIMPL Detail 위임으로 "
    "공용 TU에서 #ifdef 제거. 의도된 얇은 wrapper라면 .patternsignore 로 억제 "
    f"({_CG_I27})"
)


# ─────────────────────────────────────────────────────────────
# AP-07: std::array + counter 멤버 공존
# ─────────────────────────────────────────────────────────────

_COUNTER_KEYWORDS = ("count", "size", "num", "len", "idx", "index")
_INT_TYPE_TOKENS = ("size_t", "int", "unsigned", "uint", "int8", "int16", "int32", "int64")


def _is_std_array_field(fd: Node, source: bytes) -> bool:
    """field_declaration의 type이 std::array<...>인지."""
    if not is_data_member(fd):
        return False
    type_node = fd.child_by_field_name(F_TYPE)
    if type_node is None:
        return False
    txt = node_text(type_node, source)
    return "array" in txt and ("std::" in txt or "array<" in txt)


def _is_integer_counter_field(fd: Node, source: bytes) -> bool:
    """field_declaration이 정수 타입 + 카운터 키워드 식별자인 데이터 멤버인지."""
    if not is_data_member(fd):
        return False
    type_node = fd.child_by_field_name(F_TYPE)
    if type_node is None:
        return False
    type_txt = node_text(type_node, source).lower()
    if not any(tok in type_txt for tok in _INT_TYPE_TOKENS):
        return False
    name = field_identifier_text(fd, source).lower()
    return bool(name) and any(kw in name for kw in _COUNTER_KEYWORDS)


def detect_array_with_counter(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for cls in class_bodies(tree):
        body = cls.child_by_field_name(F_BODY)
        if body is None:
            continue
        has_array = False
        counter_nodes = []
        for member in body.children:
            if member.type != N_FIELD_DECLARATION:
                continue
            if _is_std_array_field(member, source):
                has_array = True
            elif _is_integer_counter_field(member, source):
                counter_nodes.append(member)
        if has_array and counter_nodes:
            name = class_name(cls, source)
            out.append(rule.make_finding(
                rel, f"{name}: std::array + 카운터 멤버 공존 (수동 StaticVector 패턴)",
                symbol=name,
                suggestion=(
                    "수동 카운터 필요 이유 추적 → 고정 크기 제약 유무와 무관하게 "
                    "StaticVector<T,N> 캡슐화가 우선, 고정 크기 자체가 불필요하면 std::vector 전환"
                ),
                lines_hint=line_hint(counter_nodes[0]),
            ))
    return out


# ─────────────────────────────────────────────────────────────
# AP-08: 공용 TU 내 플랫폼 #ifdef
# ─────────────────────────────────────────────────────────────

# 플랫폼·컴파일러 구분 매크로. "공용 파일 안에서 분기하고 있다"는 신호의 근거.
# 헤더 가드·일반 feature 매크로는 이 집합에 없어 자연스럽게 제외됨.
_PLATFORM_MACROS = frozenset({
    "_WIN32", "_WIN64", "WIN32", "WIN64",
    "__linux__", "__unix__", "__unix",
    "__APPLE__", "__MACH__", "TARGET_OS_MAC",
    "__ANDROID__", "__gnu_linux__",
    "_MSC_VER", "__MINGW32__", "__MINGW64__", "__CYGWIN__",
    "__GNUC__", "__clang__",
})

# 플랫폼 바운더리 파일 — 그 자체가 "이 파일은 이 플랫폼 전용" 임이 파일명으로 선언됨.
# suffix 일치 비교 (대소문자 구분 — C++ 명명 관례 존중).
_PLATFORM_FILE_SUFFIXES = (
    "Win.cpp", "Win.h", "Win.hpp",
    "Windows.cpp", "Windows.h",
    "Linux.cpp", "Linux.h",
    "Posix.cpp", "Posix.h",
    "Mac.cpp", "Mac.h", "Darwin.cpp", "Darwin.h",
    "Android.cpp", "Android.h",
    "Unix.cpp", "Unix.h",
)

# preproc 조건 노드 타입 — #ifdef/#ifndef 는 preproc_ifdef 로 통합되고, #if 는 preproc_if.
_PREPROC_COND_TYPES = frozenset({"preproc_ifdef", "preproc_if"})


def _is_platform_boundary_file(rel: str) -> bool:
    """파일명이 플랫폼 전용 바운더리 패턴인지. 그런 파일에서는 #ifdef가 정당."""
    return rel.endswith(_PLATFORM_FILE_SUFFIXES)


def _collect_condition_identifiers(node: Node, source: bytes) -> set[str]:
    """preproc 조건 노드에서 참조된 매크로 identifier 이름 집합.

    preproc_ifdef: children = [#ifdef|#ifndef 토큰, identifier(매크로명), body..., #endif]
    preproc_if:    children = [#if 토큰, <expression>, body..., #endif]

    조건부(두 번째 자식) 서브트리만 훑어 body 내부 식별자 오염을 막음.
    """
    if len(node.children) < 2:
        return set()
    cond_node = node.children[1]
    out: set[str] = set()
    stack = [cond_node]
    while stack:
        n = stack.pop()
        if n.type == "identifier":
            out.add(node_text(n, source))
        stack.extend(n.children)
    return out


def detect_platform_ifdef_in_common_tu(
    rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser,
) -> list[Finding]:
    """공용 translation unit 내부에서 플랫폼 매크로를 조건으로 쓰는 preproc 지시자 탐지.

    바운더리 파일(*Linux.cpp / *Win.cpp 등)은 제외 — 그 자체가 플랫폼 선언.
    nested 지시자는 각각 보고 (중첩 플랫폼 분기도 책임 분리 여지의 독립 신호).
    """
    if _is_platform_boundary_file(rel):
        return []
    out: list[Finding] = []
    stack: list[Node] = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in _PREPROC_COND_TYPES:
            macros = _collect_condition_identifiers(node, source) & _PLATFORM_MACROS
            if macros:
                out.append(rule.make_finding(
                    rel,
                    f"공용 TU 내 플랫폼 #ifdef ({', '.join(sorted(macros))}) "
                    f"— 분리 추상화 위임 검토",
                    lines_hint=line_hint(node),
                    suggestion=_SUG_AP08,
                ))
        stack.extend(node.children)
    return out


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

ANTI_PATTERN_RULES: list[PatternRule] = [
    PatternRule("AP-07", _CATEGORY, SEV_MAJOR, CONF_LOW, detect_array_with_counter),
    PatternRule("AP-08", _CATEGORY, SEV_MAJOR, CONF_LOW, detect_platform_ifdef_in_common_tu),
]
