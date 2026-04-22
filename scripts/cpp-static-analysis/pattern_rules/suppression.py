"""Suppression 3계층 — inline · .patternsignore · project-config.

설계 근거: docs/patterns-e1-suppression-design.md
"""
from __future__ import annotations

import dataclasses
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

_SCRIPTS = str(Path(__file__).parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from encoding import append_file, read_file  # noqa: E402
from cpp_parser import _node_text  # noqa: E402
from models import SEV_BLOCKER, SEV_MAJOR, SEV_MINOR  # noqa: E402

if TYPE_CHECKING:
    from cpp_parser import CppParser
    from tree_sitter import Tree

    from ._shared import PatternRule

# ─────────────────────────────────────────────────────────────
# 1계층: Inline Suppression
# ─────────────────────────────────────────────────────────────

def _nopattern_re(name: str) -> re.Pattern:
    """NOPATTERN 지시어 정규식 생성. group(1)=rule IDs, group(2)=reason."""
    return re.compile(rf"{name}\(([^)]+)\)(?:\s*:\s*(.*))?")

_RE_NEXT_LINE = _nopattern_re("NOPATTERN_NEXT_LINE")
_RE_NOPATTERN = _nopattern_re("NOPATTERN")
_RE_BEGIN = _nopattern_re("NOPATTERN_BEGIN")
_RE_END = re.compile(r"NOPATTERN_END\b")

# 감사 로그 level 상수 (H1 해결)
WAIVER_INLINE = "inline"
WAIVER_IGNORE = "ignore"
WAIVER_CONFIG = "config"

# project-config.json patterns 섹션 키
_CK_PATTERNS = "patterns"
_CK_CATEGORIES = "categories"
_CK_RULES = "rules"
_CK_ENABLED = "enabled"
_CK_REASON = "reason"
_CK_SEVERITY = "severity"           # E2: severity 오버라이드
_CK_OPTIONS = "options"             # E2: 규칙별 옵션
_CK_REQUIRE_REASON = "require_reason"           # E2: NOPATTERN 사유 필수
_CK_REPORT_UNUSED = "report_unused_suppressions"  # E2: 미사용 감지

_VALID_SEVERITIES = {SEV_BLOCKER, SEV_MAJOR, SEV_MINOR}

# NOPATTERN 와일드카드 (전규칙 억제)
_WILDCARD = "*"


def _parse_rule_ids(m: re.Match) -> set[str]:
    """정규식 매치의 group(1)에서 rule ID set 파싱."""
    return {r.strip() for r in m.group(1).split(",")}


def _rules_match(rules: set[str], rule_id: str) -> bool:
    """rule set에 wildcard("*") 또는 해당 rule_id가 포함되는지."""
    return _WILDCARD in rules or rule_id in rules


@dataclass
class SuppressionMap:
    """파일 1개의 inline suppression 맵."""

    # 라인별 억제: {line_number: set[rule_id]}  (rule_id="*"이면 전규칙)
    line_rules: dict[int, set[str]] = field(default_factory=dict)
    # 범위 억제: [(start_line, end_line, set[rule_id])]
    ranges: list[tuple[int, int, set[str]]] = field(default_factory=list)
    # 파싱 경고 (중첩 BEGIN, 미닫힌 범위, unknown rule ID 등)
    warnings: list[str] = field(default_factory=list)
    # E2: 미사용 suppression 추적
    _used_lines: set[int] = field(default_factory=set)
    _used_ranges: set[int] = field(default_factory=set)

    def is_suppressed(self, line: int, rule_id: str) -> bool:
        """해당 라인의 해당 규칙이 억제되는지."""
        if line in self.line_rules and _rules_match(self.line_rules[line], rule_id):
            self._used_lines.add(line)
            return True
        for i, (start, end, rules) in enumerate(self.ranges):
            if start <= line <= end and _rules_match(rules, rule_id):
                self._used_ranges.add(i)
                return True
        return False

    def unused_suppressions(self) -> list[str]:
        """사용되지 않은 suppression 경고 목록. E2: report_unused_suppressions용."""
        result: list[str] = []
        for line in sorted(set(self.line_rules.keys()) - self._used_lines):
            result.append(f"line {line}: unused NOPATTERN")
        for i, (start, end, _rules) in enumerate(self.ranges):
            if i not in self._used_ranges:
                result.append(f"line {start}-{end}: unused NOPATTERN_BEGIN/END range")
        return result

    def validate_rule_ids(self, known_ids: set[str]) -> None:
        """지시어에 사용된 rule ID가 유효한지 검증. 오타 시 경고 추가."""
        all_ids: set[str] = set()
        for rules in self.line_rules.values():
            all_ids.update(rules)
        for _, _, rules in self.ranges:
            all_ids.update(rules)
        all_ids.discard(_WILDCARD)
        for rid in all_ids:
            if rid not in known_ids:
                self.warnings.append(
                    f"unknown rule ID in NOPATTERN: {rid!r} (오타?)"
                )


def _has_reason(m: re.Match) -> bool:
    """지시어 매치에서 사유(group 2) 존재 여부."""
    return bool((m.group(2) or "").strip())


def _reject_no_reason(
    line: int, directive: str, warnings: list[str],
) -> bool:
    """사유 없는 지시어를 거부하고 경고 추가. True면 거부됨."""
    warnings.append(f"line {line}: {directive} without reason — 억제 거부")
    return True


def _nopattern_target_line(
    line: int, comment_node, source: bytes,
) -> int:
    """NOPATTERN의 억제 대상 라인 결정 (위치 휴리스틱).

    같은 줄에 코드가 있으면 해당 줄, 주석 전용 줄이면 다음 줄.
    """
    line_start = source.rfind(b"\n", 0, comment_node.start_byte) + 1
    prefix = source[line_start : comment_node.start_byte]
    return line if prefix.strip() != b"" else line + 1


@dataclass
class _ParseState:
    """parse_inline_suppressions의 파싱 상태. SuppressionMap + open_begin."""
    smap: SuppressionMap = field(default_factory=SuppressionMap)
    open_begin: tuple[int, set[str]] | None = None


def _apply_begin(m, line, comment_node, source, st: _ParseState) -> None:
    st.open_begin = (line, _parse_rule_ids(m))


def _add_line_suppression(m, line, comment_node, source, st: _ParseState) -> None:
    """NOPATTERN: 위치 휴리스틱으로 target 라인 결정."""
    target = _nopattern_target_line(line, comment_node, source)
    st.smap.line_rules.setdefault(target, set()).update(_parse_rule_ids(m))


def _apply_next_line(m, line, comment_node, source, st: _ParseState) -> None:
    st.smap.line_rules.setdefault(line + 1, set()).update(_parse_rule_ids(m))


# 지시어 이름 상수
_DN_BEGIN = "NOPATTERN_BEGIN"
_DN_NEXT_LINE = "NOPATTERN_NEXT_LINE"
_DN_NOPATTERN = "NOPATTERN"

# (regex, 지시어명, 적용함수)
_DIRECTIVE_TABLE = [
    (_RE_BEGIN,     _DN_BEGIN,     _apply_begin),
    (_RE_NEXT_LINE, _DN_NEXT_LINE, _apply_next_line),
    (_RE_NOPATTERN, _DN_NOPATTERN, _add_line_suppression),
]


def _process_comment(
    text: str, line: int, comment_node, source: bytes,
    require_reason: bool, st: _ParseState,
) -> None:
    """단일 comment 처리."""
    # END는 별도 (rule_ids/reason 없음)
    if _RE_END.search(text):
        if st.open_begin is None:
            st.smap.warnings.append(f"line {line}: NOPATTERN_END without BEGIN")
        else:
            st.smap.ranges.append((st.open_begin[0], line, st.open_begin[1]))
            st.open_begin = None
        return

    for regex, name, apply_fn in _DIRECTIVE_TABLE:
        m = regex.search(text)
        if not m:
            continue
        # BEGIN 전용: 중첩 검사 (reason보다 우선)
        if name == _DN_BEGIN and st.open_begin is not None:
            st.smap.warnings.append(f"line {line}: nested NOPATTERN_BEGIN (ignored)")
            return
        # 공통: reason 검증
        if require_reason and not _has_reason(m):
            _reject_no_reason(line, name, st.smap.warnings)
            return
        apply_fn(m, line, comment_node, source, st)
        return


def parse_inline_suppressions(
    tree: Tree, source: bytes, parser: CppParser,
    require_reason: bool = False,
) -> SuppressionMap:
    """tree-sitter comment 노드에서 NOPATTERN 지시어 파싱."""
    st = _ParseState()

    for c in parser.query(tree, "(comment) @c").get("c", []):
        text = _node_text(c, source)
        line = c.start_point[0] + 1
        _process_comment(text, line, c, source, require_reason, st)

    if st.open_begin is not None:
        last_line = tree.root_node.end_point[0] + 1
        st.smap.ranges.append((st.open_begin[0], last_line, st.open_begin[1]))
        st.smap.warnings.append(
            f"line {st.open_begin[0]}: NOPATTERN_BEGIN without END (applied to EOF)")

    return st.smap


# ─────────────────────────────────────────────────────────────
# 2계층: .patternsignore
# ─────────────────────────────────────────────────────────────

import fnmatch as _fnmatch

try:
    import pathspec as _pathspec
except ImportError:
    _pathspec = None  # type: ignore[assignment]


@dataclass
class IgnoreRule:
    """컴파일된 .patternsignore 엔트리."""

    spec: object  # pathspec.PathSpec 또는 fnmatch 기반 fallback
    rule_ids: set[str]  # 비어있으면 전규칙
    _use_pathspec: bool = True

    def matches(self, rel_path: str) -> bool:
        """패턴이 파일 경로에 매칭되는지."""
        if self._use_pathspec:
            return self.spec.match_file(rel_path)  # type: ignore[union-attr]
        return _fnmatch.fnmatch(rel_path, self.spec)  # type: ignore[arg-type]


def _make_spec(pattern: str, warnings: list[str]) -> tuple[object, bool]:
    """패턴을 매칭 객체로 컴파일. pathspec 있으면 사용, 없으면 fnmatch fallback."""
    if _pathspec is not None:
        return _pathspec.PathSpec.from_lines("gitwildmatch", [pattern]), True
    # fallback: fnmatch (** 미지원, 모듈 레벨 import 완료)
    if "**" in pattern:
        warnings.append(
            f"pathspec 미설치. '**' glob({pattern})은 지원 불가. "
            "pip install pathspec 권장."
        )
    return pattern, False


@dataclass
class PatternsIgnoreResult:
    """parse_patternsignore 결과."""
    entries: list[IgnoreRule]
    warnings: list[str]


def parse_patternsignore(path: Path) -> PatternsIgnoreResult:
    """`.patternsignore` 파일 파싱."""
    if not path.is_file():
        return PatternsIgnoreResult([], [])
    entries: list[IgnoreRule] = []
    warnings: list[str] = []
    for raw_line in read_file(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # 절대 경로 / Windows 경로 감지
        if line[0] in ("/", "\\") or (len(line) > 1 and line[1] == ":"):
            warnings.append(f".patternsignore — 절대/Windows 경로 무시: {line!r}")
            continue
        # 규칙 ID 분리: 마지막 `:` 뒤가 대문자로 시작하면 규칙 ID
        rule_ids: set[str] = set()
        if ":" in line:
            pattern_part, maybe_rules = line.rsplit(":", 1)
            if maybe_rules and maybe_rules.strip()[0].isupper():
                rule_ids = {r.strip() for r in maybe_rules.split(",")}
                line = pattern_part.strip()
        spec, use_ps = _make_spec(line, warnings)
        entries.append(IgnoreRule(spec, rule_ids, use_ps))
    return PatternsIgnoreResult(entries, warnings)


def is_file_ignored(
    rel_path: str, rule_id: str, entries: list[IgnoreRule]
) -> bool:
    """파일+규칙 조합이 .patternsignore에 매칭되는지."""
    for entry in entries:
        if entry.matches(rel_path):
            if not entry.rule_ids or rule_id in entry.rule_ids:
                return True
    return False


# ─────────────────────────────────────────────────────────────
# 3계층: project-config.json
# ─────────────────────────────────────────────────────────────


def _merge_options(
    rule: PatternRule, opts: dict, warnings: list[str],
) -> PatternRule:
    """규칙에 config options 병합. unknown 키는 경고 + 무시."""
    unknown = set(opts.keys()) - rule.known_options
    for k in sorted(unknown):
        warnings.append(f"{rule.rule_id}: unknown option {k!r} (오타?)")
    valid_opts = {k: v for k, v in opts.items() if k in rule.known_options}
    if not valid_opts:
        return rule
    return dataclasses.replace(
        rule, default_options={**rule.default_options, **valid_opts})


def apply_rule_options(
    rules: list[PatternRule], patterns_cfg: dict,
) -> tuple[list[PatternRule], list[str]]:
    """config의 rules.<ID>.options로 PatternRule.default_options를 병합."""
    rules_cfg = patterns_cfg.get(_CK_RULES, {})
    warnings: list[str] = []
    result = []
    for rule in rules:
        opts = rules_cfg.get(rule.rule_id, {}).get(_CK_OPTIONS, {})
        if opts:
            rule = _merge_options(rule, opts, warnings)
        result.append(rule)
    return result, warnings


def _resolve_config(key: str, rule_setting: dict, cat_setting: dict):
    """rule > category 우선순위로 config 값 조회. 없으면 None."""
    if key in rule_setting:
        return rule_setting[key]
    if key in cat_setting:
        return cat_setting[key]
    return None


def _is_disabled(
    rule: PatternRule, rule_setting: dict, cat_setting: dict,
    logger: WaiverLogger | None,
) -> bool:
    """규칙이 config에 의해 비활성화되는지. True면 필터 대상."""
    enabled = _resolve_config(_CK_ENABLED, rule_setting, cat_setting)
    if enabled is not False:
        return False
    if not logger:
        return True
    # 감사 로그: rule-level이면 reason 포함, category-level이면 카테고리명
    if _CK_ENABLED in rule_setting:
        reason = rule_setting.get(_CK_REASON, "project-config: enabled=false")
    else:
        reason = f"category {rule.category!r} disabled"
    logger.log(WAIVER_CONFIG, rule.rule_id, "*", "", reason)
    return True


def _override_severity(
    rule: PatternRule, rule_setting: dict, cat_setting: dict,
    warnings: list[str],
) -> PatternRule:
    """severity 오버라이드. 잘못된 값은 경고 + 원본 유지."""
    new_sev = _resolve_config(_CK_SEVERITY, rule_setting, cat_setting)
    if not new_sev:
        return rule
    if new_sev not in _VALID_SEVERITIES:
        warnings.append(f"{rule.rule_id}: invalid severity {new_sev!r}")
        return rule
    return dataclasses.replace(rule, severity=new_sev)


def apply_project_config(
    rules: list[PatternRule], config: dict,
    logger: WaiverLogger | None = None,
) -> tuple[list[PatternRule], list[str]]:
    """project-config의 patterns 섹션으로 규칙 필터링 + severity 오버라이드."""
    patterns_cfg = config.get(_CK_PATTERNS, {})
    if not patterns_cfg:
        return rules, []
    categories_cfg = patterns_cfg.get(_CK_CATEGORIES, {})
    rules_cfg = patterns_cfg.get(_CK_RULES, {})

    filtered = []
    warnings: list[str] = []
    for rule in rules:
        rule_setting = rules_cfg.get(rule.rule_id, {})
        cat_setting = categories_cfg.get(rule.category, {})

        if _is_disabled(rule, rule_setting, cat_setting, logger):
            continue
        rule = _override_severity(rule, rule_setting, cat_setting, warnings)
        filtered.append(rule)
    return filtered, warnings


# ─────────────────────────────────────────────────────────────
# 감사 로그 (Waiver Audit)
# ─────────────────────────────────────────────────────────────


def _format_waiver(level: str, rule_id: str, file: str, line: str, reason: str) -> str:
    """감사 로그 1건의 포맷. 단일 정의 (DRY)."""
    ts = datetime.now().isoformat(timespec="seconds")
    return f"{ts} SUPPRESS {level:8s} {rule_id} {file}:{line} {reason!r}\n"


def _append_log(log_path: Path, data: str) -> None:
    """UTF-8 + LF로 감사 로그 append."""
    append_file(log_path, data)


class WaiverLogger:
    """감사 로그 버퍼. flush()로 일괄 기록."""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        self._buf: list[str] = []

    def log(self, level: str, rule_id: str, file: str, line: str, reason: str) -> None:
        self._buf.append(_format_waiver(level, rule_id, file, line, reason))

    def flush(self) -> None:
        if not self._buf:
            return
        _append_log(self._path, "".join(self._buf))
        self._buf.clear()
