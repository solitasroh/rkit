"""pattern_rules 패키지 — 범주별 규칙 aggregate.

설계 근거: docs/patterns-mvp-impl-design.md §3.3
D1 sentinel: docs/patterns-d1-duplicate-design.md §9.4
"""
from .smells import SMELL_RULES
from .idioms import IDIOM_RULES
from .anti_patterns import ANTI_PATTERN_RULES
from ._shared import (  # 재노출
    PatternRule, Detector, line_hint,
    SEV_BLOCKER, SEV_MAJOR, SEV_MINOR,
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    CAT_SMELL, CAT_IDIOM, CAT_ANTI_PATTERN,
)
from .duplicates import (
    DUP_RULE_ID, DUP_NORM_V, MIN_STMT_COUNT,
    compute_fingerprints, build_fingerprint_index, detect_duplicates,
)

# D1 sentinel PatternRule — per-file 루프에서 noop, E2 연동용(§9.4)
from models import CAT_DUPLICATE


def _noop_detect(rule, tree, source, rel, parser):  # type: ignore[override]
    """sentinel — per-file 루프에서 호출되지만 항상 빈 리스트 반환."""
    return []


DUP_RULE = PatternRule(
    rule_id=DUP_RULE_ID,
    category=CAT_DUPLICATE,
    severity=SEV_MAJOR,
    confidence=CONF_HIGH,
    detect=_noop_detect,
    default_options={"min_stmts": MIN_STMT_COUNT},
    known_options=frozenset({"min_stmts"}),
)

RULES: list[PatternRule] = [
    *SMELL_RULES, *IDIOM_RULES, *ANTI_PATTERN_RULES, DUP_RULE,
]

__all__ = [
    "RULES", "PatternRule", "Detector", "line_hint",
    "SEV_BLOCKER", "SEV_MAJOR", "SEV_MINOR",
    "CONF_HIGH", "CONF_MEDIUM", "CONF_LOW",
    "CAT_SMELL", "CAT_IDIOM", "CAT_ANTI_PATTERN", "CAT_DUPLICATE",
    "SMELL_RULES", "IDIOM_RULES", "ANTI_PATTERN_RULES", "DUP_RULE",
    "DUP_RULE_ID", "DUP_NORM_V", "MIN_STMT_COUNT",
    "compute_fingerprints", "build_fingerprint_index", "detect_duplicates",
]
