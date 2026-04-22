"""ProjectGraph — C++ 프로젝트 상속·컴포지션·호출 그래프 자료구조 + 빌드.

역할:
- 프로젝트 내 모든 클래스 노드(ClassNode)를 수집한다.
- 상속 엣지(parents)를 추출하여 DIT/NOC/ancestors 질의를 지원한다.
- 컴포지션 엣지(field_types) 및 호출 엣지(method_call_targets) — P4 확장.
- 파일 단위 include 목록(include_files) — P4 확장.
- 결합도(Ca/Ce)와 SCC 순환 탐지 — P5 확장.

설계 근거: docs/metrics-plan.md §2 (P1 기본) + §2.4·§2.5 (P4 확장) + §6 P5
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

# scripts 디렉토리를 path에 추가 (독립 실행 + import 양쪽 지원)
_SCRIPTS = str(Path(__file__).parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from cpp_parser import (  # noqa: E402
    CppParser, _iter_cpp_files, _node_text, _qualifier_prefix, _posix,
    PARSE_FILE_ERRORS,
    F_BODY, F_NAME, F_DECLARATOR, F_TYPE,
    N_FIELD_DECLARATION, N_FUNCTION_DEFINITION, N_FUNCTION_DECLARATOR, N_VIRTUAL,
)
from encoding import safe_print  # noqa: E402
from pattern_rules._shared import (  # noqa: E402
    class_bodies, class_name, has_pure_virtual, is_data_member,
)


# ─────────────────────────────────────────────────────────────
# 데이터클래스
# ─────────────────────────────────────────────────────────────

@dataclass
class MethodNode:
    """클래스 메서드 메타데이터.

    설계 근거: docs/metrics-plan.md §2.1
    """
    qualified_name: str    # 예: "render::Widget::draw"
    is_pure_virtual: bool
    body_size_lines: int
    body_branches: int     # McCabe 근사
    lines_hint: int
    # P4/P5 슬롯 — 1단계에서는 빈 리스트
    calls: list[str] = field(default_factory=list)
    accessed_fields: list[str] = field(default_factory=list)


@dataclass
class FieldNode:
    """클래스 필드 메타데이터.

    설계 근거: docs/metrics-plan.md §2.1
    """
    name: str
    type_name: str    # 정규화된 타입 문자열 (컴포지션 판정용)


@dataclass
class ClassNode:
    """클래스 전체 메타데이터.

    설계 근거: docs/metrics-plan.md §2.1
    """
    qualified_name: str
    file: str           # POSIX 상대 경로
    line: int
    is_abstract: bool   # has_pure_virtual(class_body, source) 결과
    methods: list[MethodNode]
    fields: list[FieldNode]
    parents: list[str]  # 직접 base class qualified names (1단계)
    # P4/P5 슬롯 — 1단계에서는 빈 리스트
    field_types: list[str] = field(default_factory=list)
    method_call_targets: list[str] = field(default_factory=list)
    include_files: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# ProjectGraph
# ─────────────────────────────────────────────────────────────

class ProjectGraph:
    """프로젝트 전역 클래스 상속 그래프.

    설계 근거: docs/metrics-plan.md §2.1
    """

    def __init__(
        self,
        classes: dict[str, ClassNode],
        by_file: dict[str, list[str]],
        unresolved_parents: dict[str, list[str]],
    ) -> None:
        self.classes = classes
        self.by_file = by_file
        self.unresolved_parents = unresolved_parents
        self._dit_cache: dict[str, int] = {}
        # P5 coupling 캐시 — lazy init via _ensure_coupling_index()
        self._efferent_cache: dict[str, set[str]] | None = None
        self._afferent_cache: dict[str, set[str]] | None = None
        self._cycles_cache: list[list[str]] | None = None

    def children_of(self, qn: str) -> list[str]:
        """직접 자식 클래스 목록."""
        return [cqn for cqn, node in self.classes.items() if qn in node.parents]

    def dit(self, qn: str, _visited: frozenset[str] | None = None) -> int:
        """DIT(Depth of Inheritance Tree). memoized DFS, 순환 상속 방어.

        최상위 클래스(parents=[] 또는 unresolved만)의 DIT = 0.
        """
        if qn in self._dit_cache:
            return self._dit_cache[qn]

        visited = _visited or frozenset()
        if qn in visited:
            return 0  # 순환 감지 — 0으로 처리

        node = self.classes.get(qn)
        if node is None:
            self._dit_cache[qn] = 0
            return 0

        new_visited = visited | {qn}
        max_parent_dit = max(
            (self.dit(p, new_visited) for p in node.parents if p in self.classes),
            default=0,
        )
        result = max_parent_dit + (1 if node.parents else 0)
        self._dit_cache[qn] = result
        return result

    def noc(self, qn: str) -> int:
        """NOC(Number Of Children). 직접 자식 수."""
        return len(self.children_of(qn))

    def ancestors(self, qn: str, _visited: frozenset[str] | None = None) -> list[str]:
        """조상 클래스 목록 (순환 방어)."""
        visited = _visited or frozenset()
        node = self.classes.get(qn)
        if node is None:
            return []

        result: list[str] = []
        new_visited = visited | {qn}
        for parent_qn in node.parents:
            if parent_qn in new_visited or parent_qn not in self.classes:
                continue
            result.append(parent_qn)
            result.extend(self.ancestors(parent_qn, new_visited | {parent_qn}))
        return result

    # ── 2단계: 결합도 + 순환 (P5) ──

    def efferent(self, qn: str) -> set[str]:
        """Ce(Efferent Couplings): 이 클래스가 의존하는 다른 클래스 qualified_name 집합.

        소스: parents ∪ field_types ∪ method_call_targets. 프로젝트 내 해소된 것만.
        자기 자신은 제외.
        설계 근거: docs/metrics-plan.md §6 P5
        """
        self._ensure_coupling_index()
        return self._efferent_cache.get(qn, set())

    def afferent(self, qn: str) -> set[str]:
        """Ca(Afferent Couplings): 이 클래스에 의존하는 다른 클래스 qualified_name 집합.

        efferent의 역인덱스. 프로젝트 내 관계만.
        설계 근거: docs/metrics-plan.md §6 P5
        """
        self._ensure_coupling_index()
        return self._afferent_cache.get(qn, set())

    # ── Martin 메트릭 (A-1) ──

    def instability(self, qn: str) -> float:
        """I = Ce / (Ca + Ce). 0 = 안정(아무도 의존 안 해도 됨), 1 = 불안정.

        결합 0(고립 노드)이면 0으로 정의 — 변경 유인 없음.
        설계 근거: Martin, 'Object-Oriented Design Quality Metrics' (1994)
        """
        ca = len(self.afferent(qn))
        ce = len(self.efferent(qn))
        total = ca + ce
        return ce / total if total > 0 else 0.0

    def abstractness(self, qn: str) -> float:
        """A = pure_virtual_methods / total_methods. 0 = 완전 구체, 1 = 완전 추상.

        메서드 0개면 0.0 (데이터 전용 타입 = 구체로 간주).
        ClassNode.is_abstract(at least one pure virtual)와 구별됨 — A는 비율.
        """
        node = self.classes.get(qn)
        if node is None or not node.methods:
            return 0.0
        pure = sum(1 for m in node.methods if m.is_pure_virtual)
        return pure / len(node.methods)

    def distance_from_main_sequence(self, qn: str) -> float:
        """D = |I + A - 1|. Main sequence는 I+A=1 선. 0 = 이상, 1 = 최악."""
        return abs(self.instability(qn) + self.abstractness(qn) - 1.0)

    def zone(self, qn: str) -> str:
        """Martin 좌표 영역 분류: isolated / pain / useless / main_sequence / normal.

        isolated: Ca+Ce=0 (결합도 없음). Martin Pain/Useless 정의는 "with dependents"
          전제라 고립 노드는 별도 분류 — pain 오탐 방지 (dogfooding 버그 수정).
        Pain: I<0.2 AND A<0.2 (Ca+Ce>0 전제, stable concrete with dependents)
        Useless: I>0.8 AND A>0.8 (abstract + unused)
        Main sequence: D<0.2 (A+I=1 선 근방)
        임계 상수는 Martin 저작 관례.
        """
        ca = len(self.afferent(qn))
        ce = len(self.efferent(qn))
        if ca + ce == 0:
            return "isolated"
        i = self.instability(qn)
        a = self.abstractness(qn)
        if i < 0.2 and a < 0.2:
            return "pain"
        if i > 0.8 and a > 0.8:
            return "useless"
        if self.distance_from_main_sequence(qn) < 0.2:
            return "main_sequence"
        return "normal"

    def class_cycles(self) -> list[list[str]]:
        """클래스 단위 순환 의존 그룹 목록 (크기 ≥ 2 SCC만).

        엣지 타입: composition(field_types) + call(method_call_targets) + 상속(parents).
        Tarjan SCC 알고리즘.
        설계 근거: docs/metrics-plan.md §1.3, §6 P5
        """
        self._ensure_coupling_index()
        if self._cycles_cache is None:
            self._cycles_cache = _tarjan_scc(self.classes, self._efferent_cache)
        return self._cycles_cache

    def _ensure_coupling_index(self) -> None:
        """efferent/afferent 캐시 지연 초기화."""
        if getattr(self, "_efferent_cache", None) is not None:
            return
        eff: dict[str, set[str]] = {}
        aff: dict[str, set[str]] = {}
        for qn, node in self.classes.items():
            deps = _resolve_dependencies(qn, node, self.classes)
            eff[qn] = deps
            for target in deps:
                aff.setdefault(target, set()).add(qn)
        self._efferent_cache = eff
        self._afferent_cache = aff
        self._cycles_cache: list[list[str]] | None = None


# ─────────────────────────────────────────────────────────────
# P5: 의존성 해소 + SCC (Tarjan)
# ─────────────────────────────────────────────────────────────

def _resolve_type_to_qn(
    raw: str, owner_qn: str, classes: dict[str, ClassNode],
) -> str | None:
    """raw 타입 이름을 classes 내의 qualified_name으로 해소. 실패 시 None.

    우선순위: exact → 같은 네임스페이스 prefix → suffix 매칭.
    외부 타입(프리미티브 외 미등록)은 None.
    """
    if raw in classes:
        return raw
    if "::" not in raw and "::" in owner_qn:
        candidate = owner_qn.rsplit("::", 1)[0] + "::" + raw
        if candidate in classes:
            return candidate
    matches = [qn for qn in classes if qn == raw or qn.endswith(f"::{raw}")]
    return matches[0] if len(matches) == 1 else None


def _resolve_dependencies(
    qn: str, node: ClassNode, classes: dict[str, ClassNode],
) -> set[str]:
    """단일 클래스의 모든 의존 타겟을 qualified_name set으로 해소. 자기 자신 제외."""
    targets: set[str] = set()
    for p in node.parents:
        if p in classes and p != qn:
            targets.add(p)
    for raw in list(node.field_types) + list(node.method_call_targets):
        resolved = _resolve_type_to_qn(raw, qn, classes)
        if resolved is not None and resolved != qn:
            targets.add(resolved)
    return targets


def _tarjan_scc(
    classes: dict[str, ClassNode],
    efferent: dict[str, set[str]],
) -> list[list[str]]:
    """Tarjan SCC — 크기 ≥ 2 컴포넌트(순환)만 반환. 반복 구현."""
    index_of: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    result: list[list[str]] = []
    counter = [0]

    for start in classes:
        if start in index_of:
            continue
        _scc_visit(start, efferent, index_of, lowlink, on_stack, stack, result, counter)
    return result


def _scc_init_node(
    node: str, counter: list[int],
    index_of: dict[str, int], lowlink: dict[str, int],
    stack: list[str], on_stack: set[str],
) -> None:
    """새로 방문한 노드를 Tarjan 상태에 등록."""
    index_of[node] = counter[0]
    lowlink[node] = counter[0]
    counter[0] += 1
    stack.append(node)
    on_stack.add(node)


def _scc_pop_component(
    root: str, stack: list[str], on_stack: set[str],
    result: list[list[str]],
) -> None:
    """lowlink == index인 root에서 SCC 하나를 stack에서 팝. 크기 ≥ 2만 저장."""
    comp = []
    while True:
        v = stack.pop()
        on_stack.discard(v)
        comp.append(v)
        if v == root:
            break
    if len(comp) >= 2:
        result.append(sorted(comp))


def _scc_visit(
    start: str,
    efferent: dict[str, set[str]],
    index_of: dict[str, int],
    lowlink: dict[str, int],
    on_stack: set[str],
    stack: list[str],
    result: list[list[str]],
    counter: list[int],
) -> None:
    """Tarjan SCC DFS 한 루트에서. 반복(explicit stack) 버전."""
    work: list[tuple[str, list[str]]] = [(start, list(efferent.get(start, ())))]
    _scc_init_node(start, counter, index_of, lowlink, stack, on_stack)

    while work:
        node, succs = work[-1]
        if succs:
            nxt = succs.pop()
            if nxt not in index_of:
                _scc_init_node(nxt, counter, index_of, lowlink, stack, on_stack)
                work.append((nxt, list(efferent.get(nxt, ()))))
            elif nxt in on_stack:
                lowlink[node] = min(lowlink[node], index_of[nxt])
            continue
        work.pop()
        if lowlink[node] == index_of[node]:
            _scc_pop_component(node, stack, on_stack, result)
        if work:
            parent = work[-1][0]
            lowlink[parent] = min(lowlink[parent], lowlink[node])


# ─────────────────────────────────────────────────────────────
# 내부 빌드 헬퍼 — 추출
# ─────────────────────────────────────────────────────────────

_BRANCH_NODE_TYPES = frozenset({
    "if_statement", "for_statement", "for_range_loop",
    "while_statement", "do_statement", "case_statement",
    "catch_clause", "conditional_expression",
})


def _count_branches(node) -> int:
    """노드 하위 트리 내 분기 노드 수."""
    count = 0
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in _BRANCH_NODE_TYPES:
            count += 1
        stack.extend(n.children)
    return count


def _extract_parents(cls_node, source: bytes) -> list[str]:
    """class_specifier 노드에서 base class 이름 목록 추출.

    §2.5 직접 순회 패턴. access_specifier/virtual 토큰은 스킵.
    """
    parents: list[str] = []
    for child in cls_node.children:
        if child.type != "base_class_clause":
            continue
        for sub in child.children:
            if sub.type in ("type_identifier", "qualified_identifier", "template_type"):
                text = _node_text(sub, source).strip()
                if text:
                    parents.append(text)
    return parents


def _method_from_field_decl(member, cls_qn: str, source: bytes) -> MethodNode | None:
    """field_declaration 멤버에서 메서드 MethodNode 추출. 데이터 멤버면 None."""
    has_func_decl = any(c.type == N_FUNCTION_DECLARATOR for c in member.children)
    if not has_func_decl:
        return None  # 데이터 멤버

    has_virt = any(c.type == N_VIRTUAL for c in member.children)
    has_zero = any(
        c.type == "number_literal" and source[c.start_byte:c.end_byte] == b"0"
        for c in member.children
    )
    is_pv = has_virt and has_zero

    for c in member.children:
        if c.type == N_FUNCTION_DECLARATOR:
            name_node = c.child_by_field_name(F_NAME)
            mname = _node_text(name_node, source) if name_node else "<unknown>"
            return MethodNode(
                qualified_name=f"{cls_qn}::{mname}",
                is_pure_virtual=is_pv,
                body_size_lines=0,
                body_branches=0,
                lines_hint=member.start_point[0] + 1,
            )
    return None


_FUNC_NAME_TYPES = frozenset({"identifier", "destructor_name", "operator_name"})


def _func_def_name(decl, source: bytes) -> str:
    """function_declarator 노드에서 메서드 이름 추출."""
    name_node = decl.child_by_field_name(F_NAME)
    if name_node:
        return _node_text(name_node, source)
    for c in decl.children:
        if c.type in _FUNC_NAME_TYPES:
            return _node_text(c, source)
    return "<unknown>"


def _method_from_func_def(member, cls_qn: str, source: bytes) -> MethodNode | None:
    """function_definition 멤버에서 MethodNode 추출."""
    decl = member.child_by_field_name(F_DECLARATOR)
    if decl is None:
        return None

    is_pv = any(c.type == "pure_virtual_clause" for c in member.children)
    mname = _func_def_name(decl, source)

    body = member.child_by_field_name(F_BODY)
    if body:
        blines = source[body.start_byte:body.end_byte].count(b"\n") + 1
        bbranch = _count_branches(body)
    else:
        blines = bbranch = 0

    return MethodNode(
        qualified_name=f"{cls_qn}::{mname}",
        is_pure_virtual=is_pv,
        body_size_lines=blines,
        body_branches=bbranch,
        lines_hint=member.start_point[0] + 1,
    )


def _extract_methods(cls_body, cls_qn: str, source: bytes) -> list[MethodNode]:
    """class body(field_declaration_list)에서 메서드 목록 추출."""
    if cls_body is None:
        return []

    methods: list[MethodNode] = []
    for member in cls_body.children:
        if member.type == N_FIELD_DECLARATION:
            m = _method_from_field_decl(member, cls_qn, source)
            if m is not None:
                methods.append(m)
        elif member.type == N_FUNCTION_DEFINITION:
            m = _method_from_func_def(member, cls_qn, source)
            if m is not None:
                methods.append(m)
    return methods


def _extract_method_bodies(cls_body, cls_qn: str, source: bytes) -> list[tuple[str, object]]:
    """(method_qn, body_node) 쌍 목록. body가 없는 메서드는 제외 (P4 호출 분석용)."""
    if cls_body is None:
        return []
    out: list[tuple[str, object]] = []
    for member in cls_body.children:
        if member.type != N_FUNCTION_DEFINITION:
            continue
        decl = member.child_by_field_name(F_DECLARATOR)
        body = member.child_by_field_name(F_BODY)
        if decl is None or body is None:
            continue
        mname = _func_def_name(decl, source)
        out.append((f"{cls_qn}::{mname}", body))
    return out


def _extract_fields(cls_body, source: bytes) -> list[FieldNode]:
    """class body에서 데이터 멤버 목록 추출."""
    if cls_body is None:
        return []

    fields: list[FieldNode] = []
    for member in cls_body.children:
        if member.type != N_FIELD_DECLARATION or not is_data_member(member):
            continue
        type_node = member.child_by_field_name(F_TYPE)
        type_name = _node_text(type_node, source).strip() if type_node else ""
        fname = ""
        for c in member.children:
            if c.type in ("field_identifier", "identifier"):
                fname = _node_text(c, source)
                break
        fields.append(FieldNode(name=fname, type_name=type_name))
    return fields


# ─────────────────────────────────────────────────────────────
# P4: 타입 정규화 + 컴포지션·호출·include 엣지 추출
# ─────────────────────────────────────────────────────────────

# 타입 문자열에서 제거할 접미사 토큰 (포인터/참조).
_TYPE_SUFFIX_STRIP = ("*", "&", "&&")

# 제거할 수식어 (const/volatile 등).
_TYPE_QUALIFIER_WORDS = frozenset({
    "const", "volatile", "mutable", "static", "inline", "constexpr",
    "struct", "class", "enum", "typename",
})

# 내부 타입으로 승격할 smart pointer 패턴 (prefix 매칭).
_SMART_POINTER_PREFIXES = (
    "std::shared_ptr<", "shared_ptr<",
    "std::unique_ptr<", "unique_ptr<",
    "std::weak_ptr<", "weak_ptr<",
)


def _strip_suffixes(s: str) -> str:
    """포인터/참조 접미사 (`*`, `&`, `&&`) 반복 제거."""
    changed = True
    while changed:
        changed = False
        for suffix in _TYPE_SUFFIX_STRIP:
            if s.endswith(suffix):
                s = s[:-len(suffix)].strip()
                changed = True
    return s


def _strip_qualifiers(s: str) -> str:
    """선두 const/volatile/class/struct 등 수식어 제거."""
    tokens = s.split()
    while tokens and tokens[0] in _TYPE_QUALIFIER_WORDS:
        tokens.pop(0)
    return " ".join(tokens)


def _unwrap_smart_pointer(s: str) -> str | None:
    """smart pointer 패턴이면 내부 타입 추출, 아니면 None."""
    for prefix in _SMART_POINTER_PREFIXES:
        if s.startswith(prefix):
            inner = s[len(prefix):]
            if inner.endswith(">"):
                inner = inner[:-1]
            if "," in inner:  # shared_ptr<T, Deleter>
                inner = inner.split(",", 1)[0]
            return inner
    return None


def _normalize_type_name(raw: str) -> str:
    """타입 문자열에서 베이스 클래스 식별자를 추출 (§2.4)."""
    s = raw.strip()
    if not s:
        return ""
    s = _strip_suffixes(s)
    s = _strip_qualifiers(s)
    inner = _unwrap_smart_pointer(s)
    if inner is not None:
        return _normalize_type_name(inner)
    if "<" in s:  # 템플릿 base만 유지
        s = s.split("<", 1)[0].strip()
    return s


# 프리미티브/표준 타입은 컴포지션 엣지에서 제외 (클래스 그래프 잡음 방지).
_PRIMITIVE_TYPES = frozenset({
    "void", "bool", "char", "wchar_t", "char8_t", "char16_t", "char32_t",
    "short", "int", "long", "float", "double",
    "signed", "unsigned",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "size_t", "ssize_t", "ptrdiff_t", "intptr_t", "uintptr_t",
    "std::string", "string", "std::string_view", "string_view",
    "std::vector", "vector", "std::array", "array",
    "std::map", "map", "std::unordered_map", "unordered_map",
    "std::set", "set", "std::unordered_set", "unordered_set",
    "std::pair", "pair", "std::tuple", "tuple",
    "std::optional", "optional", "std::variant", "variant",
    "std::function", "function", "std::chrono", "chrono",
    "std::mutex", "mutex", "std::atomic", "atomic",
    "std::thread", "thread",
})


def _extract_field_types(fields: list[FieldNode]) -> list[str]:
    """FieldNode 리스트에서 컴포지션 엣지용 타입명 목록 추출.

    프리미티브/STL 컨테이너는 제외하여 사용자 클래스만 반영.
    설계 근거: docs/metrics-plan.md §2.4
    """
    out: list[str] = []
    for f in fields:
        norm = _normalize_type_name(f.type_name)
        if not norm or norm in _PRIMITIVE_TYPES:
            continue
        out.append(norm)
    return out


def _find_field_expression_receiver(call_node, source: bytes) -> str | None:
    """call_expression의 receiver가 field_expression이면 receiver 이름 반환.

    `obj.method(args)` 또는 `ptr->method(args)` 에서 `obj`/`ptr` 이름 추출.
    """
    fn = call_node.child_by_field_name("function")
    if fn is None or fn.type != "field_expression":
        return None
    arg_node = fn.child_by_field_name("argument")
    if arg_node is None:
        return None
    if arg_node.type in ("identifier", "this"):
        return _node_text(arg_node, source)
    return None


def _collect_call_targets_from_body(
    body,
    field_name_to_type: dict[str, str],
    source: bytes,
    targets: set[str],
) -> None:
    """단일 메서드 body에서 호출 대상을 누적 (targets set에 in-place)."""
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type == "call_expression":
            rcv = _find_field_expression_receiver(n, source)
            if rcv is not None:
                t = field_name_to_type.get(rcv)
                if t and t not in _PRIMITIVE_TYPES:
                    targets.add(t)
        stack.extend(n.children)


def _extract_method_call_targets(
    methods_meta: list[tuple[str, object]],
    field_name_to_type: dict[str, str],
    source: bytes,
) -> list[str]:
    """메서드 body들에서 호출 대상 클래스(정규화된 타입) 목록 추출.

    heuristic (P4 1차): field 기반 호출만 — `field.method()`/`field->method()`.
    local 변수/매개변수 기반 호출은 P5 이후 스코프.
    """
    targets: set[str] = set()
    for _mqn, body in methods_meta:
        if body is None:
            continue
        _collect_call_targets_from_body(body, field_name_to_type, source, targets)
    return sorted(targets)


def _extract_includes(tree, source: bytes) -> list[str]:
    """파일의 preproc_include 지시문에서 include path 목록 추출.

    반환: `"foo.h"` 또는 `<foo>` 원문 그대로 (따옴표/꺾쇠 포함).
    """
    result: list[str] = []
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "preproc_include":
            path_node = n.child_by_field_name("path")
            if path_node is not None:
                text = _node_text(path_node, source).strip()
                if text:
                    result.append(text)
        stack.extend(n.children)
    return result


# ─────────────────────────────────────────────────────────────
# 내부 빌드 헬퍼 — resolve
# ─────────────────────────────────────────────────────────────

def _qualifier_prefix_for_qn(qn: str) -> str:
    """qualified name에서 부모 네임스페이스 prefix 추출. 예: 'ns::Foo' → 'ns::'."""
    if "::" not in qn:
        return ""
    return qn.rsplit("::", 1)[0] + "::"


def _resolve_by_suffix(raw: str, classes: dict[str, ClassNode]) -> str | None:
    """raw 이름을 suffix 매칭으로 resolve. 1개 매칭이면 반환, 0 또는 복수면 None."""
    matches = [qn for qn in classes if qn == raw or qn.endswith(f"::{raw}")]
    return matches[0] if len(matches) == 1 else None


def _resolve_one_parent(
    raw: str,
    child_qn: str,
    classes: dict[str, ClassNode],
    unresolved: dict[str, list[str]],
) -> str | None:
    """단일 raw 부모 이름을 resolve. 실패 시 unresolved에 기록하고 None 반환."""
    if raw in classes:
        return raw
    prefix = _qualifier_prefix_for_qn(child_qn)
    candidate = prefix + raw if prefix else raw
    if candidate in classes:
        return candidate
    matched = _resolve_by_suffix(raw, classes)
    if matched:
        return matched
    unresolved.setdefault(child_qn, []).append(raw)
    return None


def _resolve_parents(
    classes: dict[str, ClassNode],
    unresolved: dict[str, list[str]],
) -> None:
    """모든 클래스의 _raw_parents를 resolve하여 node.parents에 설정."""
    for qn, node in classes.items():
        raw_parents: list[str] = getattr(node, "_raw_parents", [])
        resolved = []
        for raw in raw_parents:
            result = _resolve_one_parent(raw, qn, classes, unresolved)
            if result is not None:
                resolved.append(result)
        node.parents = resolved
        if hasattr(node, "_raw_parents"):
            del node._raw_parents  # type: ignore[attr-defined]
        if hasattr(node, "_has_body"):
            del node._has_body     # type: ignore[attr-defined]


# ─────────────────────────────────────────────────────────────
# 내부 빌드 헬퍼 — 파일 처리
# ─────────────────────────────────────────────────────────────

def _p4_edges(
    cls_body, qn: str, fields: list[FieldNode], source: bytes,
) -> tuple[list[str], list[str]]:
    """P4 엣지 추출: (field_types, method_call_targets)."""
    field_types = _extract_field_types(fields)
    field_name_to_type = {
        f.name: _normalize_type_name(f.type_name) for f in fields if f.name
    }
    method_bodies = _extract_method_bodies(cls_body, qn, source)
    call_targets = _extract_method_call_targets(
        method_bodies, field_name_to_type, source,
    )
    return field_types, call_targets


def _make_class_node(
    cls_node, qn: str, rel: str, source: bytes,
) -> ClassNode:
    """단일 class_specifier 노드에서 ClassNode 생성. P4 엣지 포함."""
    cls_body = cls_node.child_by_field_name(F_BODY)
    is_abstract = has_pure_virtual(cls_body, source) if cls_body is not None else False
    raw_parents = _extract_parents(cls_node, source)
    methods = _extract_methods(cls_body, qn, source)
    fields = _extract_fields(cls_body, source)
    field_types, call_targets = _p4_edges(cls_body, qn, fields, source)

    node = ClassNode(
        qualified_name=qn, file=rel, line=cls_node.start_point[0] + 1,
        is_abstract=is_abstract, methods=methods, fields=fields,
        parents=[],  # 단계 8(resolve)에서 채움
        field_types=field_types, method_call_targets=call_targets,
    )
    node._raw_parents = raw_parents           # type: ignore[attr-defined]
    node._has_body = cls_body is not None     # type: ignore[attr-defined]
    return node


def _merge_node(
    qn: str,
    new_node: ClassNode,
    classes: dict[str, ClassNode],
    rel: str,
) -> None:
    """중복 키 처리: body 있는 쪽 우선, 둘 다 body면 경고 + 첫 등장 유지 (§2.2 단계 7)."""
    existing = classes[qn]
    ex_has_body = getattr(existing, "_has_body", False)
    new_has_body = getattr(new_node, "_has_body", False)

    if new_has_body and not ex_has_body:
        classes[qn] = new_node
    elif new_has_body and ex_has_body:
        safe_print(
            f"경고: {qn} 중복 정의 ({rel} / {existing.file}). 첫 등장 유지.",
            file=sys.stderr,
        )


def _register_class(
    cls_node, rel: str, source: bytes, file_includes: list[str],
    classes: dict[str, ClassNode], by_file: dict[str, list[str]],
) -> None:
    """단일 class_specifier를 ClassNode로 변환하여 classes/by_file에 등록."""
    cname = class_name(cls_node, source)
    qn = _qualifier_prefix(cls_node, source) + cname
    new_node = _make_class_node(cls_node, qn, rel, source)
    new_node.include_files = list(file_includes)

    if qn in classes:
        _merge_node(qn, new_node, classes, rel)
    else:
        classes[qn] = new_node

    by_file.setdefault(rel, [])
    if qn not in by_file[rel]:
        by_file[rel].append(qn)


def _process_file(
    fp: Path,
    target: Path,
    parser: CppParser,
    classes: dict[str, ClassNode],
    by_file: dict[str, list[str]],
) -> None:
    """파일 1개 파싱 → 클래스 노드 추출 → classes/by_file에 누적."""
    rel = _posix(str(fp.relative_to(target))) if target.is_dir() else fp.name
    try:
        tree, source = parser.parse_file(fp)
    except PARSE_FILE_ERRORS as e:
        safe_print(f"경고: {rel} 파싱 실패 — {e}", file=sys.stderr)
        return

    file_includes = _extract_includes(tree, source)
    for cls_node in class_bodies(tree):
        _register_class(cls_node, rel, source, file_includes, classes, by_file)


# ─────────────────────────────────────────────────────────────
# P5: graph_hash + metrics_summary 렌더
# ─────────────────────────────────────────────────────────────

def compute_graph_hash(graph: "ProjectGraph") -> str:
    """그래프 엣지 전체의 SHA-256 8자리 해시. metrics_summary 재현성용.

    엣지 정렬 직렬화: parents, field_types, method_call_targets. P1엔 parents만,
    P4~P5에서 자연 확장. 캐시 키 아님 — 재현성 체크 전용.
    설계 근거: docs/metrics-plan.md §1.3, §7.6
    """
    parts: list[str] = []
    for qn in sorted(graph.classes):
        node = graph.classes[qn]
        parts.append(f"|{qn}")
        for p in sorted(node.parents):
            parts.append(f"p<-{p}")
        for t in sorted(node.field_types):
            parts.append(f"o->{t}")
        for t in sorted(node.method_call_targets):
            parts.append(f"c->{t}")
    blob = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:8]


EDGE_INHERIT = "inherit"
EDGE_COMPOSE = "compose"
EDGE_CALL = "call"


def iter_class_edges(graph: "ProjectGraph") -> list[tuple[str, str, str]]:
    """결정론적 엣지 리스트 (from_qn, to_qn, type). type ∈ {inherit, compose, call}.

    프로젝트 내 해소된 엣지만 포함 (graph.classes에 존재하는 타겟). 자기 참조 및
    동일 (from,to,type) 중복은 제외. 정렬 키: (from asc, to asc, type asc).
    """
    edges: set[tuple[str, str, str]] = set()
    for qn, node in graph.classes.items():
        for p in node.parents:
            if p in graph.classes and p != qn:
                edges.add((qn, p, EDGE_INHERIT))
        for raw in node.field_types:
            resolved = _resolve_type_to_qn(raw, qn, graph.classes)
            if resolved is not None and resolved != qn:
                edges.add((qn, resolved, EDGE_COMPOSE))
        for raw in node.method_call_targets:
            resolved = _resolve_type_to_qn(raw, qn, graph.classes)
            if resolved is not None and resolved != qn:
                edges.add((qn, resolved, EDGE_CALL))
    return sorted(edges)


def render_metrics_summary_xml(graph: "ProjectGraph") -> str:
    """<metrics_summary> 블록 문자열 반환. findings.xml 끝에 삽입되는 형식.

    요소 순서: <class> (qn asc) → <edge> (from,to,type asc) → <cycle>.
    실수형 값(I/A/D)은 ×100 정수 매핑. P5엔 I/A/D 계산 미구현 — 향후 추가.
    <cycle> 요소는 composition+inherit+call 통합 SCC 결과.
    설계 근거: docs/metrics-plan.md §1.3
    """
    from models import xml_attr  # 지연 import (순환 방지)

    lines: list[str] = [
        f'  <metrics_summary version="1" graph_hash={xml_attr(compute_graph_hash(graph))}>'
    ]
    for qn in sorted(graph.classes):
        node = graph.classes[qn]
        attrs = _class_summary_attrs(graph, qn, node)
        lines.append(f"    <class {attrs}/>")
    for f, t, typ in iter_class_edges(graph):
        lines.append(
            f'    <edge from={xml_attr(f)} to={xml_attr(t)} type="{typ}"/>'
        )
    for cyc in graph.class_cycles():
        classes_str = ",".join(cyc)
        lines.append(
            f'    <cycle classes={xml_attr(classes_str)}'
            f' size="{len(cyc)}" edge_type="composition"/>'
        )
    lines.append("  </metrics_summary>")
    return "\n".join(lines)


def _class_summary_attrs(
    graph: "ProjectGraph", qn: str, node: ClassNode,
) -> str:
    """<class> 요소의 attribute 문자열 생성.

    I/A/D는 실수 ×100 정수 매핑 (adversarial-review.md §2.5.4-4 계약).
    zone은 문자열 분류: pain/useless/main_sequence/normal.
    """
    from models import xml_attr

    ca = len(graph.afferent(qn))
    ce = len(graph.efferent(qn))
    i_pct = int(round(graph.instability(qn) * 100))
    a_pct = int(round(graph.abstractness(qn) * 100))
    d_pct = int(round(graph.distance_from_main_sequence(qn) * 100))
    return " ".join([
        f"name={xml_attr(qn)}",
        f"file={xml_attr(node.file)}",
        f'line="{node.line}"',
        f'abstract="{"true" if node.is_abstract else "false"}"',
        f'methods="{len(node.methods)}"',
        f'fields="{len(node.fields)}"',
        f'DIT="{graph.dit(qn)}"',
        f'NOC="{graph.noc(qn)}"',
        f'Ca="{ca}"',
        f'Ce="{ce}"',
        f'I="{i_pct}"',
        f'A="{a_pct}"',
        f'D="{d_pct}"',
        f'zone="{graph.zone(qn)}"',
    ])


def render_metrics_summary_md(graph: "ProjectGraph") -> str:
    """summary.md 용 클래스 그래프 섹션. XML <metrics_summary>와 1:1 데이터 미러.

    출력은 "\n## Class graph\n..."으로 시작하여 render_summary_md가 중간에 삽입할
    수 있다. 행 정렬 기준은 qualified_name asc — XML과 동일.
    설계 근거: render_metrics_summary_xml 짝 구조.
    """
    total = len(graph.classes)
    cycles = graph.class_cycles()
    lines: list[str] = [
        "\n## Class graph\n",
        f"- total classes: {total}",
        f"- cycles (composition+inherit+call): {len(cycles)}",
        "",
        "| class | file:line | abstract | methods | fields | DIT | NOC | Ca | Ce | zone |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for qn in sorted(graph.classes):
        node = graph.classes[qn]
        ca = len(graph.afferent(qn))
        ce = len(graph.efferent(qn))
        lines.append(
            f"| `{_md_cell(qn)}` "
            f"| {_md_cell(node.file)}:{node.line} "
            f"| {'true' if node.is_abstract else 'false'} "
            f"| {len(node.methods)} | {len(node.fields)} "
            f"| {graph.dit(qn)} | {graph.noc(qn)} "
            f"| {ca} | {ce} "
            f"| {graph.zone(qn)} |"
        )
    edges = iter_class_edges(graph)
    if edges:
        lines.append("\n### Edges\n")
        lines.append(f"- total edges: {len(edges)}")
        for typ_label, typ_key in (
            ("Inheritance", EDGE_INHERIT),
            ("Composition", EDGE_COMPOSE),
            ("Call",        EDGE_CALL),
        ):
            typ_edges = [(f, t) for f, t, ty in edges if ty == typ_key]
            lines.append(f"\n#### {typ_label} ({len(typ_edges)})\n")
            if not typ_edges:
                lines.append("- (none)")
                continue
            for f, t in typ_edges:
                lines.append(f"- `{_md_cell(f)}` -> `{_md_cell(t)}`")
    if cycles:
        edges_by_from: dict[str, list[tuple[str, str]]] = {}
        for f, t, typ in edges:
            edges_by_from.setdefault(f, []).append((t, typ))
        lines.append("\n### Cycles\n")
        for i, cyc in enumerate(cycles, 1):
            members = ", ".join(f"`{_md_cell(c)}`" for c in cyc)
            lines.append(f"- Cycle {i} ({len(cyc)} classes): {members}")
            cyc_set = set(cyc)
            for f in cyc:
                for t, typ in edges_by_from.get(f, []):
                    if t in cyc_set:
                        lines.append(
                            f"  - `{_md_cell(f)}` -({typ})-> `{_md_cell(t)}`"
                        )
    return "\n".join(lines) + "\n"


def _md_cell(s: str) -> str:
    """마크다운 표 셀 안전화 — '|'·백슬래시 이스케이프, 개행 → 공백, 백틱 → 단일인용."""
    return (
        s.replace("\\", "\\\\").replace("|", "\\|")
         .replace("\n", " ").replace("`", "'")
    )


# ─────────────────────────────────────────────────────────────
# 빌드 함수 (공개 API)
# ─────────────────────────────────────────────────────────────

def build(target: Path, parser: CppParser) -> ProjectGraph:
    """ProjectGraph 빌드. §2.2 빌드 단계 8개를 순서대로 수행.

    설계 근거: docs/metrics-plan.md §2.2, §2.5
    """
    classes: dict[str, ClassNode] = {}
    by_file: dict[str, list[str]] = {}
    unresolved_parents: dict[str, list[str]] = {}

    for fp in _iter_cpp_files(target):
        _process_file(fp, target, parser, classes, by_file)

    _resolve_parents(classes, unresolved_parents)

    return ProjectGraph(
        classes=classes,
        by_file=by_file,
        unresolved_parents=unresolved_parents,
    )
