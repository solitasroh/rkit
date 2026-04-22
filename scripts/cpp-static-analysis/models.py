"""공용 데이터 모델 + 상수 — 순환 import 방지를 위한 leaf 모듈.

hard_check.py, patterns.py, pattern_rules/_shared.py 모두
이 모듈에서 Finding과 상수를 import한다.
이 모듈은 프로젝트 내 다른 모듈을 import하지 않는다 (leaf).

설계 근거: severity 이중 정의 해소 (hard_check._SEV_* ↔ _shared.SEV_*)
"""
from __future__ import annotations

import re
import xml.sax.saxutils as saxutils
from dataclasses import dataclass


# ── 도구 버전 ──
VERSION = "1.0.0"

# ── 캐시 스키마 버전 ──
# JSON 레이아웃(필드 rename/삭제) 승격용. 의미 변경은 VERSION이 담당.
# 설계: docs/patterns-e4-incremental-design.md §7.1
CACHE_SCHEMA_VERSION = "1"

# ── Severity 상수 ──
SEV_BLOCKER = "blocker"
SEV_MAJOR = "major"
SEV_MINOR = "minor"

# severity desc 순서 (심각도 높음 → 낮음). formatters/render_review/patterns 가
# 동일한 단일 진실을 공유. 새 severity 추가 시 두 상수 모두 갱신.
ALL_SEVERITIES: tuple[str, ...] = (SEV_BLOCKER, SEV_MAJOR, SEV_MINOR)
# 심각도 점수 (클수록 심각). --fail-on 비교 등에 사용.
SEVERITY_RANK: dict[str, int] = {SEV_BLOCKER: 3, SEV_MAJOR: 2, SEV_MINOR: 1}

# ── --fail-on 정책 상수 ──
FAIL_ON_NONE = "none"

# ── 출력 포맷 상수 ──
FMT_XML = "xml"
FMT_TEXT = "text"
FMT_SARIF = "sarif"
FMT_JUNIT = "junit"
FMT_JSON = "json"
FMT_CHOICES = [FMT_XML, FMT_TEXT, FMT_SARIF, FMT_JUNIT, FMT_JSON]

# ── Confidence 상수 ──
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"

# ── Category 상수 ──
CAT_SMELL = "smell"
CAT_IDIOM = "idiom"
CAT_ANTI_PATTERN = "anti-pattern"
CAT_DUPLICATE = "duplicate"

# ── XML 출력 스키마 상수 ──
XML_TAG_FINDING = "finding"
XML_TAG_FINDINGS = "findings"
XML_TAG_SUMMARY = "summary"


# XML 1.0 금지 제어문자: \x00-\x08, \x0b, \x0c, \x0e-\x1f
_XML_ILLEGAL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def xml_attr(value: str) -> str:
    """XML 속성값 안전 인코딩. 프로젝트 전역 단일 정의."""
    cleaned = _XML_ILLEGAL_RE.sub('\ufffd', str(value))
    return saxutils.quoteattr(cleaned, entities={"\n": "&#10;", "\r": "&#13;"})


# ─────────────────────────────────────────────────────────────
# Finding
# ─────────────────────────────────────────────────────────────

@dataclass
class Finding:
    type: str          # size | nesting | folder | xml-wellformed | params | cast | pattern | ...
    severity: str      # SEV_BLOCKER | SEV_MAJOR | SEV_MINOR
    file: str          # 상대 경로 (POSIX)
    message: str
    rule: str = ""     # 예: function_complexity, SMELL-03
    symbol: str = ""   # 예: Foo::bar
    value: int = 0
    limit: int = 0
    # patterns.py 전용 (hard_check에서는 default 비움)
    confidence: str = ""    # CONF_HIGH | CONF_MEDIUM | CONF_LOW | ""
    suggestion: str = ""
    lines_hint: str = ""
    # rapp_review 통합 시 origin 표식 (hard_check | patterns | arch_check).
    # 각 도구의 독립 CLI 경로에서는 비움 → to_xml에서 attr 자체가 생략되어 backward compatible.
    tool: str = ""

    @property
    def location(self) -> str:
        """파일:줄 위치 문자열. lines_hint 없으면 파일명만."""
        return f"{self.file}:{self.lines_hint}" if self.lines_hint else self.file

    def to_text_line(self) -> str:
        """텍스트 포맷 한 줄 표현. rule 우선, 없으면 type."""
        identifier = self.rule or self.type
        return f"[{self.severity.upper()}] {identifier} {self.location}: {self.message}"

    def to_xml(self) -> str:
        attrs = [f'type={xml_attr(self.type)}', f'severity={xml_attr(self.severity)}',
                 f'file={xml_attr(self.file)}']
        for name in ("tool", "rule", "symbol", "confidence", "suggestion", "lines_hint"):
            v = getattr(self, name)
            if v:
                attrs.append(f"{name}={xml_attr(v)}")
        for name in ("value", "limit"):
            v = getattr(self, name)
            if v != 0:
                attrs.append(f'{name}="{v}"')
        attrs.append(f'message={xml_attr(self.message)}')
        return f"  <{XML_TAG_FINDING} {' '.join(attrs)}/>"
