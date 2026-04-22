"""기계적 거부(hard rejection) — 임계값 초과/규칙 위반 탐지.

역할:
- cpp_parser로 얻은 AST + 간단 비교로 위반 판정
- project-config.json의 thresholds/layers 기반
- Claude에게 주입할 <findings> XML 생성

판단 원칙:
- 기계적으로 결정 가능한 것만 (크기, 폴더, XML 형식)
- 설계 적합성/논리 오류 등은 Claude가 판단 (이 모듈 범위 밖)

설계 근거: docs/v3-redesign.md §4.4
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tree_sitter import Node
from cpp_parser import (
    CppParser, _iter_cpp_files, _node_text, _posix, _rel_path, _validate_target,
    source_line_count, qualified_name, PARSE_FILE_ERRORS, ANON_NAME,
    F_DECLARATOR, F_NAME, F_PARAMETERS,
    N_COMPOUND_STATEMENT, N_FUNCTION_DECLARATOR, N_PARAMETER_DECLARATION,
)
from encoding import load_json_config, read_file, safe_print, write_file
from models import (
    Finding, FAIL_ON_NONE, VERSION, xml_attr as _xml_attr,
    FMT_XML, FMT_TEXT, FMT_CHOICES,
    SEV_BLOCKER as _SEV_BLOCKER,
    SEV_MAJOR as _SEV_MAJOR,
    SEV_MINOR as _SEV_MINOR,
    XML_TAG_FINDINGS,
)
from formatters import FormatContext, format_findings, check_fail_on, validate_fail_on
from cache import (
    AnalysisCache, CacheEntry, CacheOpts,
    context_hash, file_content_hash, grammar_version,
)
from pattern_rules.suppression import parse_inline_suppressions, SuppressionMap

# ── threshold / config 키 상수 ──
# project-config.json 스키마와 계약. DEFAULT_THRESHOLDS, thresholds[] 접근,
# Finding(rule=...) 세 곳이 동일 문자열을 공유. 오타 시 KeyError 또는 불일치 방지.
TH_FILE_LINES = "file_lines"
TH_CLASS_LINES = "class_lines"
TH_FUNCTION_LINES = "function_lines"
TH_FUNCTION_BRANCHES = "function_branches"
TH_NESTING_DEPTH = "nesting_depth"
TH_FUNCTION_PARAMS = "function_params"

# config dict 섹션 키
_CK_THRESHOLDS = "thresholds"
_CK_LAYERS = "layers"
_CK_DIRS = "dirs"

# Finding type 상수
_FT_SIZE = "size"
_FT_COMPLEXITY = "complexity"
_FT_NESTING = "nesting"
_FT_PARAMS = "params"
_FT_FOLDER = "folder"
_FT_READ_ERROR = "read-error"
_FT_XML_WELLFORMED = "xml-wellformed"
_RULE_LAYER_MEMBERSHIP = "layer_membership"

# function 복잡도 통합 룰 — 분기 = 주 신호, 라인 = 보조 컨텍스트.
# 별개의 function_lines/function_branches로 emit 하던 것을 단일 finding으로 통합.
# function_lines / function_branches는 NOPATTERN 알리아스로만 보존(_is_suppressed 참조).
RULE_FUNCTION_COMPLEXITY = "function_complexity"

# ── 분기 노드 타입 (McCabe cyclomatic complexity 근사) ──
# 각 제어 흐름 분기 = 1. &&/||는 업계 관행대로 제외 (해석 복잡 대비 효용 낮음).
_BRANCH_NODE_TYPES = frozenset({
    "if_statement",
    "for_statement",
    "for_range_loop",
    "while_statement",
    "do_statement",
    "case_statement",
    "catch_clause",
    "conditional_expression",
})

# 함수 시그니처 표시 최대 길이 (truncation)
_MAX_FUNC_SIG_LEN = 80

# ── suggestion 문구 ──
# 처방이 아니라 원인 추적을 유도한다. AI가 코드를 읽고 판단해야 할 부분.
_SUG_FILE_LINES = "초과 원인 분석: 응집도 높은 단일 모듈인지, 무관한 책임이 한 파일에 섞인 건지 판별"
_SUG_CLASS_LINES = "초과 원인 분석: 클래스가 단일 책임을 넘어선 건지, 내부 구조가 비대한 건지 판별"
_CG_F3 = "참조: C++ Core Guidelines F.3 'Keep functions short and simple'"
_CG_I23 = "참조: C++ Core Guidelines I.23 'Keep the number of function arguments low'"

_SUG_FUNCTION_COMPLEXITY_FLAT = (
    "초과 원인 분석: 분기가 적은 긴 함수는 widget 배치/조립 등 의도된 평면 코드일 수 있음. "
    f"책임 단일성 확인 ({_CG_F3})"
)
_SUG_FUNCTION_COMPLEXITY_BRANCHES = (
    "초과 원인 분석: 분기가 실제 도메인 복잡도인지, 상태 조건을 다형/전략으로 분리 가능한지 "
    f"판별 ({_CG_F3})"
)
_SUG_FUNCTION_COMPLEXITY_BOTH = (
    "초과 원인 분석: 분기·라인 동반 초과는 강한 복잡도 신호. 책임 분리 또는 다형 적용 "
    f"검토 ({_CG_F3})"
)
_SUG_NESTING_DEPTH = "초과 원인 분석: early return/continue로 평탄화 가능한지, 분기 구조 자체가 설계 문제인지 판별"
_SUG_FUNCTION_PARAMS = (
    "초과 원인 분석: 함수 책임이 과다한 건지, 관련 데이터를 묶는 구조체가 빠진 건지 "
    f"판별 ({_CG_I23})"
)
_SUG_LAYER_MEMBERSHIP = "레이어 소속 확인: project-config.json의 layers 정의와 파일 위치 대조"
_SUG_LAYER_CYCLE = "순환 의존 원인 분석: 어떤 레이어 간 의존이 역방향인지 추적"

# ── XML 출력 스키마 상수 ──
XML_SOURCE_HARD_CHECK = "hard_check"

# ── cache 설정 키 (project-config.json `cache` 섹션) ──
_CK_CACHE = "cache"
_CK_CACHE_ENABLED = "enabled"
_CK_CACHE_HARD_CHECK_FILE = "hard_check_file"

# 기본 캐시 파일명(§1.5). hard_check은 patterns와 별도 캐시.
_DEFAULT_CACHE_FILENAME = ".hard-check-cache.json"

# ─────────────────────────────────────────────────────────────
# 설정 (project-config.json의 thresholds/layers)
# ─────────────────────────────────────────────────────────────

DEFAULT_THRESHOLDS: dict[str, int] = {
    TH_FILE_LINES: 300,
    TH_CLASS_LINES: 300,
    TH_FUNCTION_LINES: 30,
    TH_FUNCTION_BRANCHES: 10,
    TH_NESTING_DEPTH: 3,
    TH_FUNCTION_PARAMS: 3,
}


def _validate_thresholds(thresholds: dict) -> dict[str, int]:
    """threshold 값을 int로 변환하고 양수 검증. 실패 시 기본값 사용 + stderr 경고."""
    validated = {}
    for key, default in DEFAULT_THRESHOLDS.items():
        raw = thresholds.get(key, default)
        try:
            val = int(raw)
        except (TypeError, ValueError):
            safe_print(f"경고: threshold '{key}' 값 {raw!r}은 정수가 아님, 기본값 {default} 사용",
                       file=sys.stderr)
            val = default
        if val <= 0:
            safe_print(f"경고: threshold '{key}' 값 {val}은 양수가 아님, 기본값 {default} 사용",
                       file=sys.stderr)
            val = default
        validated[key] = val
    return validated


def _default_config() -> dict:
    return {_CK_THRESHOLDS: DEFAULT_THRESHOLDS.copy(), _CK_LAYERS: []}


_CK_NAME = "name"
_CK_ALLOWED_DEPS = "allowed_deps"
_CK_EXTRA_DEPS = "extra_deps"


def _validate_layers(raw_layers: list) -> list[dict]:
    """layers 항목 검증: dict 타입, dirs 정규화, deps 필드 검증."""
    validated = []
    seen_names: set[str] = set()
    for i, layer in enumerate(raw_layers):
        if not isinstance(layer, dict):
            safe_print(f"경고: layers[{i}] 타입 {type(layer).__name__}, dict 아님 — 무시",
                       file=sys.stderr)
            continue
        if _CK_DIRS in layer:
            # 빈 문자열 + 선행/후행 슬래시 정규화
            layer[_CK_DIRS] = [d.strip("/") for d in layer[_CK_DIRS] if d and d.strip("/")]
        # name 중복 검사
        name = layer.get(_CK_NAME, "")
        if name and name in seen_names:
            safe_print(f"경고: layers[{i}] name '{name}' 중복 — 무시",
                       file=sys.stderr)
            continue
        if name:
            seen_names.add(name)
        # allowed_deps + extra_deps 동시 지정 금지
        if _CK_ALLOWED_DEPS in layer and _CK_EXTRA_DEPS in layer:
            safe_print(f"경고: layers[{i}] '{name}': allowed_deps와 extra_deps 동시 지정 불가 — extra_deps 무시",
                       file=sys.stderr)
            del layer[_CK_EXTRA_DEPS]
        validated.append(layer)
    return validated


def _resolve_layer_deps(layers: list[dict]) -> list[dict]:
    """서브레이어 extra_deps를 부모 allowed_deps와 합산하여 resolved_deps 생성."""
    name_map = {l[_CK_NAME]: l for l in layers if _CK_NAME in l}
    for layer in layers:
        name = layer.get(_CK_NAME, "")
        if _CK_EXTRA_DEPS in layer:
            parent_name = _find_parent_layer(name, layer.get(_CK_DIRS, []), layers)
            parent_deps = name_map[parent_name].get(_CK_ALLOWED_DEPS, []) if parent_name else []
            layer[_CK_ALLOWED_DEPS] = list(set(parent_deps + layer[_CK_EXTRA_DEPS]))
            del layer[_CK_EXTRA_DEPS]
    return layers


def _find_parent_layer(sub_name: str, sub_dirs: list[str], layers: list[dict]) -> str | None:
    """서브레이어의 부모 레이어를 찾는다. dirs longest prefix match (자기 자신 제외)."""
    best_name = None
    best_len = 0
    for layer in layers:
        l_name = layer.get(_CK_NAME, "")
        if l_name == sub_name:
            continue
        for parent_dir in layer.get(_CK_DIRS, []):
            for sub_dir in sub_dirs:
                if sub_dir.startswith(parent_dir + "/") and len(parent_dir) > best_len:
                    best_name = l_name
                    best_len = len(parent_dir)
    return best_name


def _validate_layer_dep_names(layers: list[dict]) -> None:
    """allowed_deps의 레이어 이름이 실제 정의된 레이어인지 검증."""
    known = {l.get(_CK_NAME, "") for l in layers} - {""}
    for layer in layers:
        name = layer.get(_CK_NAME, "")
        for dep in layer.get(_CK_ALLOWED_DEPS, []):
            if dep not in known:
                safe_print(f"경고: layers '{name}': allowed_deps의 '{dep}'는 정의되지 않은 레이어",
                           file=sys.stderr)


def _build_layer_graph(layers: list[dict]) -> dict[str, list[str]]:
    """layers config에서 의존성 인접 리스트 구축."""
    graph: dict[str, list[str]] = {}
    for layer in layers:
        name = layer.get(_CK_NAME, "")
        if name and _CK_ALLOWED_DEPS in layer:
            graph[name] = layer[_CK_ALLOWED_DEPS]
    return graph


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """방향 그래프에서 순환 탐지. DFS 기반. 순환 경로 리스트 반환."""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[list[str]] = []

    def _dfs(node: str, path: list[str]) -> None:
        if node in in_stack:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited or node not in graph:
            return
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        for dep in graph[node]:
            _dfs(dep, path)
        path.pop()
        in_stack.discard(node)

    for name in graph:
        if name not in visited:
            _dfs(name, [])
    return cycles


def _detect_layer_cycle(layers: list[dict]) -> list[Finding]:
    """config 수준 순환 의존 탐지 (ARCH-02)."""
    cycles = _find_cycles(_build_layer_graph(layers))
    return [Finding(
        _FT_FOLDER, _SEV_BLOCKER, "(config)",
        f"레이어 순환 의존: {' → '.join(c)}",
        rule="ARCH-02",
        suggestion=_SUG_LAYER_CYCLE,
    ) for c in cycles]


def load_config(config_path: Path | None) -> dict:
    """project-config.json 로드. 미지정/미존재 시 기본값 반환."""
    if config_path is None or not config_path.exists():
        return _default_config()
    data = load_json_config(config_path)
    if data is None:
        return _default_config()
    raw_thresholds = {**DEFAULT_THRESHOLDS, **data.get(_CK_THRESHOLDS, {})}
    thresholds = _validate_thresholds(raw_thresholds)
    raw_layers = data.get(_CK_LAYERS, [])
    if not isinstance(raw_layers, list):
        safe_print(f"경고: layers가 list가 아님 ({type(raw_layers).__name__}) — 무시",
                   file=sys.stderr)
        raw_layers = []
    layers = _validate_layers(raw_layers)
    layers = _resolve_layer_deps(layers)
    _validate_layer_dep_names(layers)
    return {_CK_THRESHOLDS: thresholds, _CK_LAYERS: layers}





# ─────────────────────────────────────────────────────────────
# Size 검사 (file/class/function/nesting/params)
# ─────────────────────────────────────────────────────────────

def _func_name(node: Node, source: bytes) -> str:
    """function_definition 노드에서 qualified 식별자 추출.

    부모 namespace/class를 prefix로 붙여 영구 앵커성 강화 (Foo::Bar::baz(...)).
    declarator가 이미 '::'를 포함(외부 정의)하면 그대로 사용.
    """
    decl = node.child_by_field_name(F_DECLARATOR)
    if decl is None:
        return ANON_NAME
    sig = " ".join(_node_text(decl, source).split())
    if not sig:
        return ANON_NAME
    full = qualified_name(node, source, sig)
    return full[:_MAX_FUNC_SIG_LEN]


def _count_params(func_node: Node, source: bytes) -> int:
    """함수의 파라미터 수 (function_declarator의 parameter_list)."""
    decl = func_node.child_by_field_name(F_DECLARATOR)
    while decl is not None and decl.type != N_FUNCTION_DECLARATOR:
        decl = decl.child_by_field_name(F_DECLARATOR)
    if decl is None:
        return 0
    params = decl.child_by_field_name(F_PARAMETERS)
    if params is None:
        return 0
    return sum(1 for c in params.children if c.type == N_PARAMETER_DECLARATION)


def _max_nesting(root: Node) -> int:
    """compound_statement 최대 중첩 깊이. 스택 기반 반복."""
    best = 0
    stack: list[tuple] = [(root, 0)]  # (node, depth)
    while stack:
        node, depth = stack.pop()
        current = depth + 1 if node.type == N_COMPOUND_STATEMENT else depth
        if current > best:
            best = current
        for child in node.children:
            stack.append((child, current))
    return best


def _count_branches(root: Node) -> int:
    """함수 본체 내 분기 노드 수 (McCabe cyclomatic complexity 근사)."""
    count = 0
    stack: list[Node] = [root]
    while stack:
        node = stack.pop()
        if node.type in _BRANCH_NODE_TYPES:
            count += 1
        stack.extend(node.children)
    return count


def _lines_of(node) -> int:
    """AST 노드의 라인 수 (start_point → end_point)."""
    return node.end_point[0] - node.start_point[0] + 1


def _suppressed_by_alias(line: int, severity: str, smap: SuppressionMap) -> bool:
    """function_complexity finding의 backward-compat 알리아스 매칭.

    - NOPATTERN(function_branches): 분기 초과(MAJOR)일 때만 매칭
    - NOPATTERN(function_lines): 라인-only(MINOR)일 때만 매칭
    의도: 한쪽 축만 의도적 허용 시 다른 축이 추후 임계 초과해도 다시 보고됨.
    """
    if severity == _SEV_MAJOR and smap.is_suppressed(line, TH_FUNCTION_BRANCHES):
        return True
    if severity == _SEV_MINOR and smap.is_suppressed(line, TH_FUNCTION_LINES):
        return True
    return False


def _is_suppressed(f: Finding, smap: SuppressionMap) -> bool:
    """Finding이 inline NOPATTERN으로 억제되는지 확인."""
    if not f.lines_hint:
        return False
    try:
        line = int(f.lines_hint)
    except ValueError:
        return False
    if line <= 0:
        return False
    if smap.is_suppressed(line, f.rule):
        return True
    if f.rule == RULE_FUNCTION_COMPLEXITY:
        return _suppressed_by_alias(line, f.severity, smap)
    return False


def _check_file_lines(source: bytes, rel: str, thresholds: dict) -> list[Finding]:
    """파일 전체 라인 수 검사. file 단위 룰이라 symbol/lines_hint 없음."""
    total_lines = source_line_count(source)
    limit = thresholds[TH_FILE_LINES]
    if total_lines <= limit:
        return []
    return [Finding(
        _FT_SIZE, _SEV_MAJOR, rel,
        f"파일 {total_lines}줄 (임계 {limit}) — 파일 크기 신호",
        rule=TH_FILE_LINES, value=total_lines, limit=limit,
        suggestion=_SUG_FILE_LINES,
    )]


def check_size(parser: CppParser, fp: Path, rel: str, thresholds: dict) -> list[Finding]:
    """파일 1개에 대한 크기/중첩/파라미터 검사. inline NOPATTERN 적용."""
    try:
        tree, source = parser.parse_file(fp)
    except PARSE_FILE_ERRORS as e:
        return [Finding(_FT_READ_ERROR, _SEV_BLOCKER, rel, str(e))]
    smap = parse_inline_suppressions(tree, source, parser)
    findings: list[Finding] = _check_file_lines(source, rel, thresholds)
    for fn in parser.query(tree, "(function_definition) @f").get("f", []):
        findings.extend(_check_function(fn, source, rel, thresholds))
    for q in (CppParser.Q_CLASS, CppParser.Q_STRUCT):
        for node in parser.query(tree, q).get("node", []):
            findings.extend(_check_class(node, source, rel, thresholds))
    return [f for f in findings if not _is_suppressed(f, smap)]


def _complexity_case(
    sym: str, lines: int, line_limit: int, branches: int, branch_limit: int,
) -> tuple[str, str, str] | None:
    """(severity, message, suggestion) 결정. 둘 다 OK면 None."""
    over_lines = lines > line_limit
    over_branches = branches > branch_limit
    if over_branches and over_lines:
        return _SEV_MAJOR, (
            f"{sym}: 분기 {branches} (임계 {branch_limit}) + 라인 {lines} (임계 {line_limit}) 동반 — 복잡도 신호"
        ), _SUG_FUNCTION_COMPLEXITY_BOTH
    if over_branches:
        return _SEV_MAJOR, (
            f"{sym}: 분기 {branches} (임계 {branch_limit}), 라인 {lines} ≤ {line_limit} — 복잡도 신호"
        ), _SUG_FUNCTION_COMPLEXITY_BRANCHES
    if over_lines:
        return _SEV_MINOR, (
            f"{sym}: 라인 {lines} (임계 {line_limit}), 분기 {branches} ≤ {branch_limit} — 긴-평면 가능성, 검토 필요"
        ), _SUG_FUNCTION_COMPLEXITY_FLAT
    return None


def _check_function_complexity(fn_node: Node, rel: str, sym: str, thresholds: dict) -> list[Finding]:
    """함수 복잡도 통합 판정 — 분기 = 주 신호, 라인 = 보조 컨텍스트.

    `value`/`limit` 은 분기 기준 (XML 후속 도구의 일관 소트/필터).
    NOPATTERN 알리아스는 _is_suppressed 참조.
    """
    lines = _lines_of(fn_node)
    branches = _count_branches(fn_node)
    branch_limit = thresholds[TH_FUNCTION_BRANCHES]
    case = _complexity_case(sym, lines, thresholds[TH_FUNCTION_LINES], branches, branch_limit)
    if case is None:
        return []
    sev, msg, sug = case
    return [Finding(
        _FT_COMPLEXITY, sev, rel, msg,
        rule=RULE_FUNCTION_COMPLEXITY, symbol=sym,
        value=branches, limit=branch_limit,
        lines_hint=str(fn_node.start_point[0] + 1), suggestion=sug,
    )]


def _check_function_nesting(fn_node: Node, rel: str, sym: str, thresholds: dict) -> list[Finding]:
    """compound_statement 최대 중첩 깊이."""
    depth = _max_nesting(fn_node) - 1  # 함수 본체 자체는 depth 1, 내부 블록부터 카운트
    limit = thresholds[TH_NESTING_DEPTH]
    if depth <= limit:
        return []
    return [Finding(
        _FT_NESTING, _SEV_MAJOR, rel,
        f"{sym}: 중첩 {depth} (임계 {limit}) — 중첩 깊이 신호",
        rule=TH_NESTING_DEPTH, symbol=sym, value=depth, limit=limit,
        lines_hint=str(fn_node.start_point[0] + 1), suggestion=_SUG_NESTING_DEPTH,
    )]


def _check_function_params(fn_node: Node, source: bytes, rel: str, sym: str, thresholds: dict) -> list[Finding]:
    """파라미터 개수."""
    count = _count_params(fn_node, source)
    limit = thresholds[TH_FUNCTION_PARAMS]
    if count <= limit:
        return []
    return [Finding(
        _FT_PARAMS, _SEV_MINOR, rel,
        f"{sym}: 파라미터 {count} (임계 {limit}) — 파라미터 수 신호",
        rule=TH_FUNCTION_PARAMS, symbol=sym, value=count, limit=limit,
        lines_hint=str(fn_node.start_point[0] + 1), suggestion=_SUG_FUNCTION_PARAMS,
    )]


def _check_function(fn_node: Node, source: bytes, rel: str, thresholds: dict) -> list[Finding]:
    """단일 함수 검사 — 복잡도(라인+분기 통합)·중첩·파라미터 축별 검사 합산."""
    sym = _func_name(fn_node, source)
    return (_check_function_complexity(fn_node, rel, sym, thresholds)
            + _check_function_nesting(fn_node, rel, sym, thresholds)
            + _check_function_params(fn_node, source, rel, sym, thresholds))


def _check_class(cls_node: Node, source: bytes, rel: str, thresholds: dict) -> list[Finding]:
    """클래스/구조체 줄 수 검사."""
    name_node = cls_node.child_by_field_name(F_NAME)
    sym = _node_text(name_node, source) if name_node else ANON_NAME
    lines = _lines_of(cls_node)
    limit = thresholds[TH_CLASS_LINES]
    if lines > limit:
        return [Finding(
            _FT_SIZE, _SEV_MAJOR, rel,
            f"{sym}: 클래스 {lines}줄 (임계 {limit}) — 클래스 크기 신호",
            rule=TH_CLASS_LINES, symbol=sym, value=lines, limit=limit,
            lines_hint=str(cls_node.start_point[0] + 1), suggestion=_SUG_CLASS_LINES,
        )]
    return []


# ─────────────────────────────────────────────────────────────
# Folder 검사 (layer 규칙)
# ─────────────────────────────────────────────────────────────

def check_folder(fp: Path, rel: str, layers: list[dict]) -> list[Finding]:
    """파일이 정의된 layer 디렉토리 중 하나에 속하는지 검사.

    layers가 비어있으면 검사 생략. project-config.json의 layers 참조.
    """
    if not layers:
        return []
    path_str = _posix(str(fp))
    for layer in layers:
        for d in layer.get(_CK_DIRS, []):
            # 디렉토리 경계 매칭: "src" in "resource" 오탐 방지
            if f"/{d}/" in f"/{path_str}":
                return []  # 어느 layer에 속함 = OK
    return [Finding(
        _FT_FOLDER, _SEV_MINOR, rel,
        f"어떤 레이어에도 속하지 않음 (layers 정의 확인)",
        rule=_RULE_LAYER_MEMBERSHIP,
        suggestion=_SUG_LAYER_MEMBERSHIP,
    )]


# ─────────────────────────────────────────────────────────────
# XML well-formed 검사
# ─────────────────────────────────────────────────────────────

def check_xml_wellformed(fp: Path) -> list[Finding]:
    """XML 파일이 well-formed인지 파싱 시도."""
    rel = fp.name
    try:
        ET.fromstring(read_file(fp))
        return []
    except (ET.ParseError, UnicodeDecodeError, OSError) as e:
        return [Finding(_FT_XML_WELLFORMED, _SEV_BLOCKER, rel, str(e))]


# ─────────────────────────────────────────────────────────────
# 통합 실행
# ─────────────────────────────────────────────────────────────

def _hc_context_hash(config: dict) -> str:
    """hard_check context_hash(§3.4). thresholds + layers + 도구/grammar 버전."""
    return context_hash(
        tool_version=VERSION,
        grammar_version=grammar_version(),
        thresholds=config[_CK_THRESHOLDS],
        layers=config[_CK_LAYERS],
    )


def _init_cache(cache_opts: CacheOpts, config: dict) -> AnalysisCache | None:
    """cache_opts.enabled일 때만 AnalysisCache 생성."""
    if not cache_opts.enabled or cache_opts.path is None:
        return None
    return AnalysisCache(cache_opts.path, _hc_context_hash(config))


def _check_file(parser: CppParser, fp: Path, rel: str, config: dict) -> list[Finding]:
    """size + folder 검사를 합친 단일 파일 분석."""
    out = check_size(parser, fp, rel, config[_CK_THRESHOLDS])
    out.extend(check_folder(fp, rel, config[_CK_LAYERS]))
    return out


def _cache_put_hc(cache: AnalysisCache | None, rel: str, fp: Path,
                  findings: list[Finding]) -> None:
    """hard_check 캐시 저장. stat/hash 실패 시 조용히 건너뜀."""
    if cache is None:
        return
    try:
        size = fp.stat().st_size
        h = file_content_hash(fp)
    except OSError:
        return
    cache.update(rel, CacheEntry(
        content_hash=h, size=size, findings=findings, suppressed=[]))


def run_all(
    target: Path, config: dict, cache_opts: CacheOpts | None = None,
) -> list[Finding]:
    """target 하위 C++ 파일 전체에 size + folder 검사. cache_opts로 캐시 제어."""
    cache_opts = cache_opts or CacheOpts.disabled()
    cache = _init_cache(cache_opts, config)
    parser = CppParser()
    findings: list[Finding] = []
    for fp in _iter_cpp_files(target):
        rel = _rel_path(fp, target)
        if cache is not None:
            cached = cache.lookup(rel, fp)
            if cached is not None:
                findings.extend(cached.findings)
                continue
        file_findings = _check_file(parser, fp, rel, config)
        findings.extend(file_findings)
        _cache_put_hc(cache, rel, fp, file_findings)
    if cache is not None:
        cache.prune_unseen()
        cache.save()
    return findings


def render_findings(findings: list[Finding], fmt: str) -> str:
    """findings 포맷 렌더링."""
    # E3: 신규 포맷 → formatters.py 위임
    rendered = format_findings(findings, fmt, FormatContext(tool=XML_SOURCE_HARD_CHECK))
    if rendered is not None:
        return rendered

    if fmt == FMT_XML:
        inner = "\n".join(f.to_xml() for f in findings)
        return (
            f'<{XML_TAG_FINDINGS} source={_xml_attr(XML_SOURCE_HARD_CHECK)} count="{len(findings)}">\n'
            f'{inner}\n</{XML_TAG_FINDINGS}>\n'
        )
    if fmt != FMT_TEXT:
        raise ValueError(f"unknown format: {fmt!r}")
    # text
    if not findings:
        return "위반 없음\n"
    lines = [f.to_text_line() for f in findings]
    return "\n".join(lines) + f"\n\n총 {len(findings)}건\n"


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def _parse_args():
    """CLI 인자 파싱."""
    ap = argparse.ArgumentParser(description="C++ 기계적 거부 검사 (hard_check)")
    ap.add_argument("check", choices=[_FT_SIZE, _FT_FOLDER, _FT_XML_WELLFORMED, "all"],
                    help="검사 종류")
    ap.add_argument("--target", help="대상 디렉토리 (size/folder/all)")
    ap.add_argument("--file", help="대상 파일 (xml-wellformed 또는 단일 검사)")
    ap.add_argument("--config", help="project-config.json 경로 (없으면 기본값)")
    ap.add_argument("--format", choices=FMT_CHOICES,
                    default=FMT_TEXT, help="출력 형식")
    ap.add_argument("--output", help="출력 파일 (없으면 stdout)")
    ap.add_argument("--exit-on-fail", action="store_true",
                    help="(deprecated) --fail-on blocker 별칭")
    ap.add_argument("--fail-on", default="",
                    help="exit 1 트리거 severity (blocker,major,minor,none)")
    ap.add_argument("--cache", action="store_true",
                    help="분석 결과 캐시 활성화")
    ap.add_argument("--cache-file", default="",
                    help="캐시 파일 경로 (--cache 암시)")
    ap.add_argument("--no-cache", action="store_true",
                    help="캐시 비활성화 (--cache/config 모두 무시)")
    return ap.parse_args()


def _resolve_cache_path(raw: str, target: Path) -> Path:
    """상대 경로는 target 기반으로 해석. raw=""이면 기본 파일명."""
    p = Path(raw or _DEFAULT_CACHE_FILENAME)
    if p.is_absolute():
        return p
    base = target if target.is_dir() else target.parent
    return base / p


def _cache_path_from_config(config_data: dict | None, target: Path) -> Path | None:
    """project-config.json의 cache 섹션에서 경로 해소."""
    if not config_data:
        return None
    cache_cfg = config_data.get(_CK_CACHE, {})
    if not cache_cfg.get(_CK_CACHE_ENABLED):
        return None
    return _resolve_cache_path(
        cache_cfg.get(_CK_CACHE_HARD_CHECK_FILE, ""), target)


def _build_cache_opts(args, target: Path, config_data: dict | None) -> CacheOpts:
    """캐시 옵션 해소. --no-cache > --cache/--cache-file > config > 기본(비활성)."""
    if args.no_cache:
        return CacheOpts.disabled()
    if args.cache_file:
        return CacheOpts(enabled=True, path=_resolve_cache_path(args.cache_file, target))
    if args.cache:
        return CacheOpts(enabled=True, path=_resolve_cache_path("", target))
    p = _cache_path_from_config(config_data, target)
    if p is None:
        return CacheOpts.disabled()
    return CacheOpts(enabled=True, path=p)


def _resolve_fail_on(args) -> str:
    """--fail-on / --exit-on-fail 하위호환 해소 후 정규화."""
    fail_on = args.fail_on
    if not fail_on and args.exit_on_fail:
        fail_on = _SEV_BLOCKER
    elif not fail_on:
        fail_on = FAIL_ON_NONE
    return validate_fail_on(fail_on)


def _resolve_target(args) -> Path:
    """서브커맨드에 맞는 target Path 결정. 실패 시 SystemExit."""
    target = Path(args.target) if args.target else (Path(args.file) if args.file else None)
    if target is None:
        safe_print(f"에러: {args.check}은 --target 또는 --file 필요", file=sys.stderr)
        raise SystemExit(1)
    err = _validate_target(target)
    if err:
        safe_print(f"에러: {err}", file=sys.stderr)
        raise SystemExit(1)
    return target


def _run_for_each(target: Path, config: dict, check_fn, config_key: str) -> list[Finding]:
    """target이 파일이면 단일 검사, 디렉토리면 전체 순회."""
    if target.is_file():
        return check_fn(target, target.name, config[config_key])
    return [f for fp in _iter_cpp_files(target)
            for f in check_fn(fp, _rel_path(fp, target), config[config_key])]


def _dispatch_check(args, config, cache_opts: CacheOpts) -> list[Finding]:
    """서브커맨드별 실행. 'all'은 cache_opts 활용, 다른 서브커맨드는 캐시 미적용."""
    if args.check == _FT_XML_WELLFORMED:
        if not args.file:
            safe_print(f"에러: {_FT_XML_WELLFORMED}은 --file 필요", file=sys.stderr)
            raise SystemExit(1)
        return check_xml_wellformed(Path(args.file))

    target = _resolve_target(args)
    if args.check == "all":
        return run_all(target, config, cache_opts=cache_opts)
    if args.check == _FT_SIZE:
        parser = CppParser()
        if target.is_file():
            return check_size(parser, target, target.name, config[_CK_THRESHOLDS])
        return [f for fp in _iter_cpp_files(target)
                for f in check_size(parser, fp, _rel_path(fp, target), config[_CK_THRESHOLDS])]
    if args.check == _FT_FOLDER:
        return _run_for_each(target, config, check_folder, _CK_LAYERS)
    raise ValueError(f"unknown check: {args.check!r}")


def _load_raw_config(args) -> dict | None:
    """--config에서 원본 JSON 로드 (cache 섹션 접근용). 미지정 시 None."""
    if not args.config:
        return None
    return load_json_config(Path(args.config))


def main() -> int:
    args = _parse_args()
    try:
        fail_on = _resolve_fail_on(args)
    except ValueError as e:
        safe_print(f"에러: {e}", file=sys.stderr)
        return 1

    config = load_config(Path(args.config) if args.config else None)
    raw_config = _load_raw_config(args)
    target_for_cache = Path(args.target or args.file or ".")
    cache_opts = _build_cache_opts(args, target_for_cache, raw_config)
    findings = _dispatch_check(args, config, cache_opts)
    rendered = render_findings(findings, args.format)

    if args.output:
        write_file(args.output, rendered)
        safe_print(f"생성: {args.output} ({len(findings)}건)", file=sys.stderr)
    else:
        safe_print(rendered, end="")
    return check_fail_on(findings, fail_on)


if __name__ == "__main__":
    sys.exit(main())
