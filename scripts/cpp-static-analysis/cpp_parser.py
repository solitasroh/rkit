"""C++ AST 파서 (tree-sitter 기반).

역할:
- C++ 파일/디렉토리 → tree-sitter AST
- 구조 추출 (클래스/구조체/enum/함수/include)
- structure.xml 생성 (extract 활동 산출물)

원칙:
- 빌드 환경 불요 (불완전한 코드도 파싱)
- 임계값 판정은 하지 않음 (hard_check.py 담당)
- 인코딩은 encoding.py에 위임

설계 근거: docs/v3-redesign.md §4, POC 2/4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, NamedTuple

from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree
import tree_sitter_cpp

# encoding 모듈 import만 해도 stdout/stderr UTF-8 자동 설정됨
sys.path.insert(0, str(Path(__file__).parent))
from encoding import read_file_utf8_bytes, safe_print, write_file
from models import xml_attr, XML_TAG_SUMMARY

CPP_EXTENSIONS = {".h", ".hpp", ".hxx", ".cpp", ".cxx", ".cc"}

# ── tree-sitter field name / node type 상수 ──
# child_by_field_name() 오타 시 조용히 None → 규칙 무력화 방지.
# tree-sitter 모듈에 정의하여 hard_check.py / pattern_rules 양쪽에서 import.
F_BODY = "body"
F_TYPE = "type"
F_NAME = "name"
F_DECLARATOR = "declarator"
F_CONDITION = "condition"
F_PARAMETERS = "parameters"

N_FIELD_DECLARATION = "field_declaration"
N_FUNCTION_DEFINITION = "function_definition"
N_FUNCTION_DECLARATOR = "function_declarator"
N_CLASS_SPECIFIER = "class_specifier"
N_STRUCT_SPECIFIER = "struct_specifier"
N_CALL_EXPRESSION = "call_expression"
N_COMPOUND_STATEMENT = "compound_statement"
N_PARAMETER_DECLARATION = "parameter_declaration"
N_VIRTUAL = "virtual"

# parse_file 호출 시 공통 예외 튜플. 새 예외 추가 시 한 곳만 수정.
PARSE_FILE_ERRORS = (UnicodeDecodeError, OSError)

# 이름 없는 심볼 센티널. hard_check.py와 _shared.py에서 공유.
ANON_NAME = "<anon>"

# ── structure.xml 출력 스키마 상수 ──
# 소비자(Claude 프롬프트, review 파이프라인)가 파싱하는 태그/속성명.
XML_ROOT_STRUCTURE = "structure"
XML_TAG_FILE = "file"
XML_TAG_INCLUDE = "include"
XML_TAG_INCLUDES = "includes"


# ─────────────────────────────────────────────────────────────
# tree-sitter 래퍼
# ─────────────────────────────────────────────────────────────

class CppParser:
    """tree-sitter C++ 파서 래퍼.

    단일 인스턴스로 여러 파일 처리 (파서 재사용).
    설계: docs/v3-redesign.md §4.1
    """

    # 구조 추출 쿼리 (L1 구조)
    Q_CLASS = "(class_specifier name: (type_identifier) @name) @node"
    Q_STRUCT = "(struct_specifier name: (type_identifier) @name) @node"
    Q_ENUM = "(enum_specifier name: (type_identifier) @name) @node"
    # 함수 정의: declarator (function_declarator 노드)를 캡처 → 시그니처만
    Q_FUNCTION = "(function_definition declarator: (function_declarator) @declarator)"
    Q_INCLUDE = "(preproc_include path: (_) @path)"

    def __init__(self) -> None:
        self.language = Language(tree_sitter_cpp.language())
        self.parser = Parser(self.language)
        self._queries: dict[str, Query] = {}

    def _get_query(self, query_str: str) -> Query:
        if query_str not in self._queries:
            self._queries[query_str] = Query(self.language, query_str)
        return self._queries[query_str]

    def parse_text(self, source: bytes) -> Tree:
        """UTF-8 바이트를 직접 파싱. 파일 없이 테스트/인메모리 분석용.

        source는 반드시 UTF-8 바이트. 노드의 byte offset은 source와 정합.
        """
        return self.parser.parse(source)

    def parse_file(self, path: Path) -> tuple[Tree, bytes]:
        """파일을 파싱. (tree, source_bytes) 반환.

        source_bytes는 UTF-8이며 노드의 byte offset과 정합.
        호출자가 _node_text 등으로 재사용하여 디스크 재읽기를 방지.
        """
        source, _orig_enc = read_file_utf8_bytes(path)
        return self.parse_text(source), source

    def query(self, tree: Tree, query_str: str) -> dict[str, list[Node]]:
        """쿼리 실행. {capture_name: [node, ...]} 반환."""
        q = self._get_query(query_str)
        return QueryCursor(q).captures(tree.root_node)

    def has_errors(self, tree: Tree) -> bool:
        """파싱 에러 노드 존재 여부. 템플릿/매크로 복잡 문법에서 True 가능.

        true여도 부분 AST는 사용 가능 (tree-sitter의 에러 복구).
        """
        return tree.root_node.has_error

    def walk(
        self,
        tree: Tree,
        visitor: Callable[[Node], None],
        predicate: Callable[[Node], bool] | None = None,
    ) -> None:
        """트리 전체 순회. 스택 기반 반복.

        Args:
            tree: 파싱된 트리
            visitor: 각 노드에 적용할 콜백
            predicate: None이 아니면 True인 노드만 visitor 호출
        """
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if predicate is None or predicate(node):
                visitor(node)
            stack.extend(reversed(node.children))


# ─────────────────────────────────────────────────────────────
# structure.xml 생성
# ─────────────────────────────────────────────────────────────

def _iter_cpp_files(target: Path) -> list[Path]:
    """C++ 파일 목록 (정렬). 파일 단일 전달도 지원.

    디렉토리는 1회 순회로 모든 확장자 필터 (대규모 트리에서 O(ext 수)배 절감).
    """
    if target.is_file():
        return [target] if target.suffix.lower() in CPP_EXTENSIONS else []
    return sorted(
        f for f in target.rglob("*")
        if f.is_file() and f.suffix.lower() in CPP_EXTENSIONS
    )


def source_line_count(source: bytes) -> int:
    """소스 바이트의 줄 수. 빈 파일은 0 아닌 1(관례)."""
    return source.count(b"\n") + 1


def _node_text(node: Node, source: bytes) -> str:
    """노드의 원본 텍스트."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


# qualified_name 부모 추적 대상.
# template_declaration·linkage_specification 등 컨텍스트가 없는 노드는 스킵.
_QUALIFIER_NODE_TYPES = frozenset({
    "namespace_definition", "class_specifier", "struct_specifier",
})


def _qualifier_prefix(node: Node, source: bytes) -> str:
    """노드의 부모 namespace/class/struct를 모아 'A::B::' 형태 prefix 생성.

    익명 namespace는 ANON_NAME 토큰으로 표시. 부모 없으면 빈 문자열.
    """
    parts: list[str] = []
    cur = node.parent
    while cur is not None:
        if cur.type in _QUALIFIER_NODE_TYPES:
            name_node = cur.child_by_field_name(F_NAME)
            parts.append(_node_text(name_node, source) if name_node else ANON_NAME)
        cur = cur.parent
    if not parts:
        return ""
    return "::".join(reversed(parts)) + "::"


def qualified_name(fn_node: Node, source: bytes, declarator_text: str) -> str:
    """function_definition에 대한 qualified name.

    declarator_text가 이미 '::'를 포함하면 (외부 정의) prefix 생략 — 중복 방지.
    template/linkage 등 컨텍스트 없는 부모는 자동 스킵 (_QUALIFIER_NODE_TYPES 외).
    """
    if "::" in declarator_text:
        return declarator_text
    return _qualifier_prefix(fn_node, source) + declarator_text


_xml_attr = xml_attr


# 심볼 종류 정의 — 새 종류 추가 시 이 리스트에 한 줄만 추가하면 extract_structure 로직 자동 확장.

class SymbolKind(NamedTuple):
    xml_tag: str
    attr_name: str
    query: str
    capture: str
    formatter: Callable
    summary_key: str


def _fmt_name(n, source: bytes) -> str:
    """식별자만 (class/struct/enum용)."""
    return _node_text(n, source)

_MAX_SIGNATURE_LEN = 150

def _fmt_signature(n, source: bytes) -> str:
    """함수 시그니처: 한 줄 정규화 + 길이 제한."""
    sig = " ".join(_node_text(n, source).split())
    return sig if len(sig) <= _MAX_SIGNATURE_LEN else sig[:_MAX_SIGNATURE_LEN - 3] + "..."

SYMBOL_KINDS: list[SymbolKind] = [
    SymbolKind("class",    "name", CppParser.Q_CLASS,    "name",       _fmt_name,      "classes"),
    SymbolKind("struct",   "name", CppParser.Q_STRUCT,   "name",       _fmt_name,      "structs"),
    SymbolKind("enum",     "name", CppParser.Q_ENUM,     "name",       _fmt_name,      "enums"),
    SymbolKind("function", "sig",  CppParser.Q_FUNCTION, "declarator", _fmt_signature, "functions"),
]


class _Aggregator:
    """extract_structure의 상태 누적. 파일 순회 중 참조로 공유."""
    def __init__(self) -> None:
        self.totals: dict[str, int] = {k.summary_key: 0 for k in SYMBOL_KINDS}
        self.parse_errors = 0
        self.read_errors = 0
        self.file_blocks: list[str] = []
        self.includes: list[tuple[str, str]] = []


def _posix(path_str: str) -> str:
    """Windows 백슬래시를 POSIX 슬래시로 정규화. XML/이식성용."""
    return path_str.replace("\\", "/")


def _rel_path(fp: Path, target: Path) -> str:
    """target 기준 상대 경로 (POSIX 슬래시)."""
    rel = str(fp.relative_to(target)) if target.is_dir() else fp.name
    return _posix(rel)


# tag → summary_key 매핑 (SYMBOL_KINDS 1회 순회로 충분하도록 사전 계산)
_TAG_TO_SUMMARY_KEY: dict[str, str] = {k.xml_tag: k.summary_key for k in SYMBOL_KINDS}


def _extract_symbols(parser: CppParser, tree, source: bytes) -> tuple[dict[str, list], list[str]]:
    """심볼 종류별 노드 수집 + 내부 XML 라인 생성. (symbols dict, xml lines)."""
    symbols: dict[str, list] = {}
    lines: list[str] = []
    for tag, attr, query, capture, fmt, _key in SYMBOL_KINDS:
        nodes = parser.query(tree, query).get(capture, [])
        symbols[tag] = nodes
        for n in nodes:
            lines.append(f'    <{tag} {attr}={_xml_attr(fmt(n, source))}/>')
    return symbols, lines


def _render_file_header(rel: str, lines: int, symbols: dict, has_err: bool) -> str:
    """<file> 헤더 태그 렌더링."""
    attrs = {
        "path": _xml_attr(rel),
        "lines": f'"{lines}"',
        **{k.summary_key: f'"{len(symbols[k.xml_tag])}"' for k in SYMBOL_KINDS},
    }
    if has_err:
        attrs["parse_error"] = '"true"'
    attrs_str = " ".join(f"{k}={v}" for k, v in attrs.items())
    return f"  <{XML_TAG_FILE} {attrs_str}>"


def _analyze_file(parser: CppParser, fp: Path, target: Path, agg: _Aggregator) -> None:
    """파일 1개 분석하여 agg에 누적. 읽기 실패는 기록만 하고 통과."""
    rel = _rel_path(fp, target)
    try:
        tree, source = parser.parse_file(fp)
    except PARSE_FILE_ERRORS as e:
        agg.read_errors += 1
        err_attrs = f'path={_xml_attr(rel)} read_error={_xml_attr(f"{type(e).__name__}: {e}")}'
        agg.file_blocks.append(f'  <{XML_TAG_FILE} {err_attrs}/>')
        return

    has_err = parser.has_errors(tree)
    if has_err:
        agg.parse_errors += 1

    symbols, inner = _extract_symbols(parser, tree, source)
    for tag, nodes in symbols.items():
        agg.totals[_TAG_TO_SUMMARY_KEY[tag]] += len(nodes)
    for inc in parser.query(tree, CppParser.Q_INCLUDE).get("path", []):
        agg.includes.append((rel, _node_text(inc, source).strip().strip('"<>')))

    agg.file_blocks.append(_render_file_header(rel, source_line_count(source), symbols, has_err))
    agg.file_blocks.extend(inner)
    agg.file_blocks.append(f"  </{XML_TAG_FILE}>")


def _render_summary(files_count: int, agg: _Aggregator) -> str:
    summary_attrs = {"files": files_count, **agg.totals,
                     "parse_errors": agg.parse_errors, "read_errors": agg.read_errors}
    attrs_str = " ".join(f'{k}="{v}"' for k, v in summary_attrs.items())
    return f'  <{XML_TAG_SUMMARY} {attrs_str}/>'


def _render_includes(includes: list[tuple[str, str]]) -> list[str]:
    if not includes:
        return []
    return (
        [f"  <{XML_TAG_INCLUDES}>"]
        + [f'    <{XML_TAG_INCLUDE} from={_xml_attr(f)} to={_xml_attr(t)}/>' for f, t in includes]
        + [f"  </{XML_TAG_INCLUDES}>"]
    )


def extract_structure(target: Path, module_name: str | None = None) -> str:
    """대상 디렉토리의 구조를 structure.xml로 반환."""
    parser = CppParser()
    files = _iter_cpp_files(target)
    agg = _Aggregator()
    for fp in files:
        _analyze_file(parser, fp, target, agg)

    header = (
        f'<{XML_ROOT_STRUCTURE} module={_xml_attr(module_name or target.name)} '
        f'path={_xml_attr(_posix(str(target)))}>'
    )
    lines = [header, _render_summary(len(files), agg)]
    lines.extend(agg.file_blocks)
    lines.extend(_render_includes(agg.includes))
    lines.append(f"</{XML_ROOT_STRUCTURE}>")
    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

# 시스템 파일시스템 루트 접근 방지용 경로 목록 (의도적 하드코딩).
# 실수로 --target 에 시스템 루트를 넘겼을 때 대규모 I/O를 차단.
# 프로젝트별 설정이 아닌 OS 보편 규약이므로 상수로 충분 — project-config에 둘 필요 없음.
_DANGEROUS_TARGETS = {
    # POSIX (Linux/macOS/WSL)
    Path("/"), Path("/etc"), Path("/usr"), Path("/bin"), Path("/sbin"),
    Path("/home"), Path("/Users"),
    # Windows
    Path("C:/"), Path("C:/Windows"), Path("C:/Program Files"),
}


def _validate_target(target: Path) -> str | None:
    """target이 안전한 분석 범위인지 검증. 문제 있으면 에러 메시지 반환."""
    if not target.exists():
        return f"{target} 없음"
    try:
        resolved = target.resolve()
    except (OSError, RuntimeError) as e:
        return f"{target} 경로 해석 실패: {e}"
    # 시스템 루트 차단
    for bad in _DANGEROUS_TARGETS:
        try:
            if resolved == bad.resolve() or resolved == bad:
                return f"{target}은 시스템 디렉토리. 분석 거부."
        except OSError:
            continue
    return None


def _warn_slow_fs(target: Path) -> None:
    """크로스 파일시스템 경로는 I/O가 매우 느림. 사용자에게 경고만 출력."""
    s = _posix(str(target))
    if s.startswith(("//wsl", "//WSL")) or s.lower().startswith("//wsl.localhost"):
        safe_print(
            "경고: UNC 경로 (WSL 네트워크 공유) 감지. "
            "9P 프로토콜 경유로 매우 느립니다. WSL 내에서 직접 실행 권장.",
            file=sys.stderr,
        )
    elif s.startswith("/mnt/") and len(s) > 6 and s[5].isalpha() and s[6:7] == "/":
        safe_print(
            "경고: WSL drvfs 경로 감지. Windows 파일시스템 접근은 "
            "WSL 네이티브 대비 5~10배 느립니다.",
            file=sys.stderr,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="C++ 구조 추출 (tree-sitter 기반)")
    ap.add_argument("--target", required=True, help="대상 디렉토리 또는 파일")
    ap.add_argument("--output", help="출력 파일 경로 (없으면 stdout)")
    ap.add_argument("--module", help="모듈명 (기본: target 이름)")
    args = ap.parse_args()

    target = Path(args.target)
    err = _validate_target(target)
    if err:
        safe_print(f"에러: {err}", file=sys.stderr)
        return 1

    _warn_slow_fs(target)
    xml = extract_structure(target, module_name=args.module)

    if args.output:
        write_file(args.output, xml)
        safe_print(f"생성: {args.output} ({len(xml)} bytes)")
    else:
        safe_print(xml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
