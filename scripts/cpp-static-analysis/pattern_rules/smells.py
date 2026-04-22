"""SMELL-* 패턴 규칙 (코드 냄새 탐지).

설계 근거: docs/patterns-mvp-impl-design.md §4.1, §4.2, §4.5
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from tree_sitter import Tree

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from pathlib import PurePosixPath

from cpp_parser import CppParser
from pattern_rules._shared import (
    PatternRule, line_hint, node_text,
    SEV_MAJOR, CONF_HIGH, CONF_MEDIUM, CAT_SMELL,
    F_BODY,
    class_bodies, class_name, has_pure_virtual,
    find_explicit_dtor, dtor_is_virtual, is_placement_new,
)

if TYPE_CHECKING:
    from models import Finding

_CATEGORY = CAT_SMELL

# C++ Core Guidelines 참조 (Claude 가 제목으로 즉시 매칭하도록 ID + 원문 제목).
_CG_ES48_49 = (
    "참조: C++ Core Guidelines ES.48 'Avoid casts' / ES.49 'If you must use a cast, use a named cast'"
)
_CG_R11 = "참조: C++ Core Guidelines R.11 'Avoid calling new and delete explicitly'"
_CG_C35 = (
    "참조: C++ Core Guidelines C.35 "
    "'A base class destructor should be either public and virtual, or protected and non-virtual'"
)
_CG_SF7 = (
    "참조: C++ Core Guidelines SF.7 "
    "'Don't write using namespace at global scope in a header file'"
)


# ─────────────────────────────────────────────────────────────
# SMELL-03: C-style cast
# ─────────────────────────────────────────────────────────────

_Q_CAST = "(cast_expression) @c"


def _is_void_cast(node: Node, source: bytes) -> bool:
    """(void)expr 패턴인지 판별. 반환값 무시 관용구는 C-style cast가 아님."""
    type_node = node.child_by_field_name("type")
    if type_node is None:
        return False
    return node_text(type_node, source).strip() == "void"


def detect_c_style_cast(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for n in parser.query(tree, _Q_CAST).get("c", []):
        if _is_void_cast(n, source):
            continue
        out.append(rule.make_finding(
            rel, "C-style cast 사용",
            suggestion=(
                "캐스트 필요 이유 추적 → 타입 불일치가 설계 문제면 타입 재설계, "
                f"불가피한 변환이면 named cast 전환 ({_CG_ES48_49})"
            ),
            lines_hint=line_hint(n),
        ))
    return out


# ─────────────────────────────────────────────────────────────
# SMELL-01: Raw new/delete (placement 제외)
# ─────────────────────────────────────────────────────────────

_Q_NEW = "(new_expression) @n"
_Q_DELETE = "(delete_expression) @d"


def detect_raw_new_delete(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for n in parser.query(tree, _Q_NEW).get("n", []):
        if is_placement_new(n):
            continue
        out.append(rule.make_finding(
            rel, "raw new 사용",
            suggestion=(
                "소유권 흐름 추적 → 단일 소유면 unique_ptr, 공유면 shared_ptr, "
                f"소유권 구조 자체가 불명확하면 설계 재검토 ({_CG_R11})"
            ),
            lines_hint=line_hint(n),
        ))
    for n in parser.query(tree, _Q_DELETE).get("d", []):
        out.append(rule.make_finding(
            rel, "raw delete 사용",
            suggestion=(
                "소유권 경계 추적 → 해제 책임이 명확하면 RAII 전환, "
                f"소유권 구조 자체가 불명확하면 설계 재검토 ({_CG_R11})"
            ),
            lines_hint=line_hint(n),
        ))
    return out


# ─────────────────────────────────────────────────────────────
# SMELL-09: non-virtual dtor in pure virtual class
# ─────────────────────────────────────────────────────────────

def detect_non_virtual_dtor(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for cls in class_bodies(tree):
        body = cls.child_by_field_name(F_BODY)
        if body is None:
            continue
        if not has_pure_virtual(body, source):
            continue
        dtor = find_explicit_dtor(body)
        if dtor is None:
            continue  # 명시 안 된 경우 FN 허용
        if dtor_is_virtual(dtor):
            continue
        name = class_name(cls, source)
        out.append(rule.make_finding(
            rel, f"{name}: 순수가상 클래스의 non-virtual 소멸자",
            symbol=name,
            suggestion=f"virtual ~{name}() = default; ({_CG_C35})",
            lines_hint=line_hint(dtor),
        ))
    return out


# ─────────────────────────────────────────────────────────────
# SMELL-02: Using namespace in header
# ─────────────────────────────────────────────────────────────

_Q_USING = "(using_declaration) @u"

_HEADER_EXTS = {".h", ".hpp", ".hxx"}


def detect_using_namespace_in_header(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    # 헤더 파일만 대상
    if PurePosixPath(rel).suffix.lower() not in _HEADER_EXTS:
        return []
    out: list[Finding] = []
    for n in parser.query(tree, _Q_USING).get("u", []):
        # using namespace X; → 'namespace' unnamed 토큰이 있음
        # using std::vector; → 'namespace' 토큰 없음
        has_namespace = any(c.type == "namespace" for c in n.children)
        if has_namespace:
            out.append(rule.make_finding(
                rel, "헤더에 using namespace 사용",
                suggestion=(
                    "네임스페이스 한정자(std::vector) 사용, using은 함수/클래스 스코프 내로 "
                    f"제한 ({_CG_SF7})"
                ),
                lines_hint=line_hint(n),
            ))
    return out


# ─────────────────────────────────────────────────────────────
# SMELL-07: Empty catch block
# ─────────────────────────────────────────────────────────────

_Q_CATCH = "(catch_clause) @c"


def detect_empty_catch(rule: PatternRule, tree: Tree, source: bytes, rel: str, parser: CppParser) -> list[Finding]:
    out: list[Finding] = []
    for n in parser.query(tree, _Q_CATCH).get("c", []):
        body = n.child_by_field_name(F_BODY)
        if body is None:
            continue
        # compound_statement의 named child가 없으면 빈 catch (주석만 있는 경우도 빈 것으로 판정)
        has_statements = any(c.is_named and c.type != "comment" for c in body.children)
        if not has_statements:
            out.append(rule.make_finding(
                rel, "빈 catch 블록 — 예외를 삼킴",
                suggestion=(
                    "예외 삼킴 이유 추적 → 에러 처리 전략 부재면 전략 수립, "
                    "의도적 무시면 NOPATTERN + 사유, 최소한 로깅 추가"
                ),
                lines_hint=line_hint(n),
            ))
    return out


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

SMELL_RULES: list[PatternRule] = [
    PatternRule("SMELL-03", _CATEGORY, SEV_MAJOR, CONF_HIGH,   detect_c_style_cast),
    PatternRule("SMELL-01", _CATEGORY, SEV_MAJOR, CONF_HIGH,   detect_raw_new_delete),
    PatternRule("SMELL-09", _CATEGORY, SEV_MAJOR, CONF_MEDIUM, detect_non_virtual_dtor),
    PatternRule("SMELL-02", _CATEGORY, SEV_MAJOR, CONF_HIGH,   detect_using_namespace_in_header),
    PatternRule("SMELL-07", _CATEGORY, SEV_MAJOR, CONF_HIGH,   detect_empty_catch),
]
