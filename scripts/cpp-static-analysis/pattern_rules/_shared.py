"""patterns 규칙 간 공용 AST 헬퍼 + PatternRule 데이터클래스.

패키지 내부 모듈 간 공유 API. _ prefix 없이 노출.

설계 근거: docs/patterns-mvp-impl-design.md §2.2, §3.1
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from tree_sitter import Node, Tree

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from cpp_parser import (  # noqa: E402 — 재사용 (P2-2: 중복 제거)
    _node_text, ANON_NAME,
    F_BODY, F_TYPE, F_NAME, F_DECLARATOR, F_CONDITION,
    N_FIELD_DECLARATION, N_FUNCTION_DEFINITION, N_FUNCTION_DECLARATOR,
    N_CLASS_SPECIFIER, N_STRUCT_SPECIFIER, N_VIRTUAL,
)
from models import (  # noqa: E402 — leaf 모듈, 순환 없음
    Finding,
    SEV_BLOCKER, SEV_MAJOR, SEV_MINOR,
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    CAT_SMELL, CAT_IDIOM, CAT_ANTI_PATTERN,
)

if TYPE_CHECKING:
    from cpp_parser import CppParser

# Detector 시그니처: (rule, tree, source, rel, parser) -> list[Finding]
# rule을 받아 rule.make_finding()으로 Finding 생성 → severity/confidence/type 하드코딩 방지.
Detector = Callable[["PatternRule", "Tree", bytes, str, "CppParser"], list["Finding"]]


@dataclass(frozen=True)
class PatternRule:
    """개별 탐지 규칙 메타데이터 + 실행 함수."""
    rule_id: str        # 예: "SMELL-03"
    category: str       # CAT_SMELL | CAT_IDIOM | CAT_ANTI_PATTERN
    severity: str       # SEV_BLOCKER | SEV_MAJOR | SEV_MINOR
    confidence: str     # CONF_HIGH | CONF_MEDIUM | CONF_LOW
    detect: Detector
    default_options: dict = field(default_factory=dict)          # E2: 기본 옵션 값
    known_options: frozenset = field(default_factory=frozenset)  # E2: 유효 키 목록

    def make_finding(self, file: str, message: str, **kwargs) -> Finding:
        """rule 메타데이터가 자동 주입된 Finding 생성.

        detect 함수는 이 메서드만 호출. type/severity/confidence/rule은
        PatternRule에서 가져오므로 하드코딩 불필요.
        """
        return Finding(
            type=self.category,
            severity=self.severity,
            file=file,
            message=message,
            rule=self.rule_id,
            confidence=self.confidence,
            **kwargs,
        )


# cpp_parser._node_text를 패키지 공용으로 재노출
node_text = _node_text


def line_hint(node: Node) -> str:
    """tree-sitter 노드의 1-based 행번호 문자열. Finding.lines_hint용."""
    return str(node.start_point[0] + 1)


# ─────────────────────────────────────────────────────────────
# 공용 AST 헬퍼
# ─────────────────────────────────────────────────────────────

def class_bodies(tree: Tree) -> list[Node]:
    """트리 내 모든 class_specifier / struct_specifier 노드를 스택 기반 수집."""
    out: list[Node] = []
    stack = list(tree.root_node.children)
    while stack:
        n = stack.pop()
        if n.type in (N_CLASS_SPECIFIER, N_STRUCT_SPECIFIER):
            out.append(n)
        stack.extend(n.children)
    return out


def class_name(cls_node: Node, source: bytes) -> str:
    """class/struct 노드에서 이름 추출."""
    name_node = cls_node.child_by_field_name(F_NAME)
    return node_text(name_node, source) if name_node else ANON_NAME


def field_identifier_text(field_decl: Node, source: bytes) -> str:
    """field_declaration에서 field_identifier 텍스트 추출. 없으면 빈 문자열."""
    for c in field_decl.children:
        if c.type == "field_identifier":
            return node_text(c, source)
    return ""


def is_data_member(fd: Node) -> bool:
    """field_declaration이 데이터 멤버인지 (메서드 선언이 아닌지).

    tree-sitter-cpp는 메서드 선언도 field_declaration으로 파싱하므로,
    function_declarator 자식이 있으면 메서드 → False.
    """
    return not any(c.type == N_FUNCTION_DECLARATOR for c in fd.children)


# ── placement new 판정 ──

def is_placement_new(new_expr: Node) -> bool:
    """new_expression이 placement new인지. 첫 named child가 argument_list이면 placement."""
    named = [c for c in new_expr.children if c.is_named]
    return bool(named) and named[0].type == "argument_list"


# ── SMELL-09 관련 ──

def is_dtor_def(func_def: Node) -> bool:
    """function_definition이 소멸자 정의인지."""
    decl = func_def.child_by_field_name(F_DECLARATOR)
    if decl is None:
        return False
    return any(c.type == "destructor_name" for c in decl.children)


def find_explicit_dtor(class_body: Node) -> Node | None:
    """field_declaration_list 안에서 명시적 소멸자 function_definition을 찾는다."""
    for member in class_body.children:
        if member.type == N_FUNCTION_DEFINITION and is_dtor_def(member):
            return member
    return None


def dtor_is_virtual(func_def: Node) -> bool:
    """소멸자 function_definition이 virtual인지.

    두 가지 판정:
    1. 'virtual' 토큰이 function_declarator보다 앞에 있으면 → 직접 virtual
    2. function_declarator 내부에 virtual_specifier(override/final)이 있으면 → 상속 virtual
    """
    for c in func_def.children:
        if c.type == N_FUNCTION_DECLARATOR:
            return any(gc.type == "virtual_specifier" for gc in c.children)
        if c.type == N_VIRTUAL:
            return True
    return False


def has_pure_virtual(class_body: Node, source: bytes) -> bool:
    """field_declaration_list 안에 순수가상 멤버가 있는지."""
    for member in class_body.children:
        if member.type == N_FIELD_DECLARATION:
            has_virt = any(c.type == N_VIRTUAL for c in member.children)
            has_zero = any(
                c.type == "number_literal"
                and source[c.start_byte:c.end_byte] == b"0"
                for c in member.children
            )
            if has_virt and has_zero:
                return True
        elif member.type == N_FUNCTION_DEFINITION:
            if any(c.type == "pure_virtual_clause" for c in member.children):
                return True
    return False
