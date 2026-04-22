"""CI/CD 출력 포맷터 — SARIF, JUnit XML, JSON + --fail-on 정책.

렌더링 leaf 모듈: models.py만 import한다.
외부 의존성 없음 (stdlib json, xml.etree.ElementTree만 사용).

설계 근거: docs/patterns-e3-cicd-design.md
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

from models import (
    VERSION,
    FAIL_ON_NONE,
    FMT_SARIF, FMT_JUNIT, FMT_JSON,
    Finding,
    SEV_BLOCKER,
    SEV_MAJOR,
    SEV_MINOR,
    ALL_SEVERITIES,
    XML_TAG_FINDINGS,
    XML_TAG_SUMMARY,
)

# 단일 진실은 models.ALL_SEVERITIES. 로컬 alias로 줄여 쓰기.
_SEVERITIES = ALL_SEVERITIES

# ── SARIF severity 매핑 ──
_SARIF_LEVEL = {
    SEV_BLOCKER: "error",
    SEV_MAJOR: "warning",
    SEV_MINOR: "note",
}

# ── --fail-on 유효값 ──
_VALID_FAIL_ON = {*_SEVERITIES, FAIL_ON_NONE}


def severity_summary(findings: list[Finding]) -> dict[str, int]:
    """severity별 카운트 dict. {SEV_BLOCKER: n, SEV_MAJOR: n, SEV_MINOR: n}."""
    return {sev: sum(1 for f in findings if f.severity == sev) for sev in _SEVERITIES}


@dataclass
class FormatContext:
    """포맷터에 전달하는 메타데이터. 없는 필드는 출력에서 생략.

    캐시 비활성 시: files_reanalyzed/files_cache_hit 출력에서 생략(§5.2 B6).
    files_analyzed 의미: 이제 '분석 성공 파일'(= considered - parse_failed).
    """
    tool: str                        # "patterns" | "hard_check"
    module: str = ""                 # patterns.py의 모듈명
    version: str = VERSION           # models.VERSION 참조
    files_analyzed: int = 0          # 0이면 출력 생략. 분석 성공 파일 수.
    elapsed_ms: int = 0              # 0이면 출력 생략
    suppressed_count: int = 0        # 0이면 출력 생략
    files_considered: int = 0        # 순회 대상 (0이면 생략)
    files_reanalyzed: int = 0        # 캐시 미스 (cache_enabled=False면 생략)
    files_cache_hit: int = 0         # 캐시 적중 (cache_enabled=False면 생략)
    files_parse_failed: int = 0      # 파싱 실패 수 (0이면 생략)
    cache_enabled: bool = False      # 캐시 필드 출력 제어


# ─────────────────────────────────────────────────────────────
# SARIF 2.1.0
# ─────────────────────────────────────────────────────────────

_SARIF_PROP_FIELDS = ("type", "confidence", "suggestion", "value", "limit")


def _sarif_rules(findings: list[Finding]) -> tuple[list[dict], dict[str, int]]:
    """rule 목록과 rule→index 매핑 반환."""
    sorted_rules = sorted({f.rule or f.type for f in findings})
    index = {rid: i for i, rid in enumerate(sorted_rules)}
    rules = [{"id": rid, "shortDescription": {"text": rid}} for rid in sorted_rules]
    return rules, index


def _sarif_location(f: Finding) -> dict:
    """단일 Finding의 SARIF location 객체."""
    phys: dict = {"artifactLocation": {"uri": f.file}}
    if f.lines_hint:
        try:
            phys["region"] = {"startLine": int(f.lines_hint)}
        except (ValueError, TypeError):
            pass
    loc: dict = {"physicalLocation": phys}
    if f.symbol:
        loc["logicalLocations"] = [{"name": f.symbol, "kind": "function"}]
    return loc


def _sarif_result(f: Finding, rule_index: dict[str, int]) -> dict:
    """단일 Finding → SARIF result 객체."""
    rid = f.rule or f.type
    result: dict = {
        "ruleId": rid,
        "ruleIndex": rule_index[rid],
        "level": _SARIF_LEVEL.get(f.severity, "note"),
        "message": {"text": f.message},
        "locations": [_sarif_location(f)],
    }
    props = {k: getattr(f, k) for k in _SARIF_PROP_FIELDS
             if getattr(f, k) not in (0, "")}
    if props:
        result["properties"] = props
    return result


def to_sarif(findings: list[Finding], ctx: FormatContext) -> str:
    """findings를 SARIF 2.1.0 JSON 문자열로 변환."""
    rules, rule_index = _sarif_rules(findings)
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": ctx.tool, "version": ctx.version, "rules": rules}},
            "results": [_sarif_result(f, rule_index) for f in findings],
        }],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# JUnit XML
# ─────────────────────────────────────────────────────────────

def to_junit(findings: list[Finding], ctx: FormatContext) -> str:
    """findings를 JUnit XML 문자열로 변환."""
    testsuites = ET.Element("testsuites")
    suite_name = f"{ctx.tool}:{ctx.module}" if ctx.module else ctx.tool
    testsuite = ET.SubElement(testsuites, "testsuite",
                              name=suite_name,
                              tests=str(len(findings)),
                              failures=str(len(findings)),
                              errors="0")
    if ctx.elapsed_ms:
        testsuite.set("time", f"{ctx.elapsed_ms / 1000:.3f}")

    for f in findings:
        tc = ET.SubElement(testsuite, "testcase",
                           name=f.rule or f.type,
                           classname=f.file,
                           time="0")
        sev = f.severity.upper()
        fail_msg = f"[{sev}] {f.message}"
        failure = ET.SubElement(tc, "failure", message=fail_msg, type=f.severity)

        parts = [f"{f.location}: {f.message}"]
        if f.suggestion:
            parts.append(f"Suggestion: {f.suggestion}")
        failure.text = "\n".join(parts)

    ET.indent(testsuites)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        testsuites, encoding="unicode")


# ─────────────────────────────────────────────────────────────
# JSON
# ─────────────────────────────────────────────────────────────

_JSON_SCHEMA_VERSION = "1.0"


def _json_metadata(ctx: FormatContext) -> dict:
    """FormatContext로부터 JSON metadata 섹션 구성. 0 필드 + 캐시 비활성 필드 생략."""
    metadata: dict = {
        "tool": ctx.tool, "module": ctx.module, "version": ctx.version,
    }
    if ctx.files_considered:
        metadata["files_considered"] = ctx.files_considered
    if ctx.files_analyzed:
        metadata["files_analyzed"] = ctx.files_analyzed
    if ctx.files_parse_failed:
        metadata["files_parse_failed"] = ctx.files_parse_failed
    if ctx.cache_enabled:
        metadata["files_reanalyzed"] = ctx.files_reanalyzed
        metadata["files_cache_hit"] = ctx.files_cache_hit
    if ctx.elapsed_ms:
        metadata["elapsed_ms"] = ctx.elapsed_ms
    if ctx.suppressed_count:
        metadata["suppressed_count"] = ctx.suppressed_count
    return metadata


def to_json(findings: list[Finding], ctx: FormatContext) -> str:
    """findings를 구조화된 JSON 문자열로 변환."""
    summary = {"total": len(findings), **severity_summary(findings)}
    output = {
        "version": _JSON_SCHEMA_VERSION,
        "metadata": _json_metadata(ctx),
        XML_TAG_SUMMARY: summary,
        XML_TAG_FINDINGS: [asdict(f) for f in findings],
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# 포맷 dispatch
# ─────────────────────────────────────────────────────────────

_FORMAT_DISPATCH = {
    FMT_SARIF: to_sarif,
    FMT_JUNIT: to_junit,
    FMT_JSON: to_json,
}


def format_findings(findings: list[Finding], fmt: str, ctx: FormatContext) -> str | None:
    """fmt가 SARIF/JUnit/JSON이면 렌더링 결과 반환, 아니면 None (기존 포맷 위임)."""
    fn = _FORMAT_DISPATCH.get(fmt)
    return fn(findings, ctx) if fn else None


# ─────────────────────────────────────────────────────────────
# --fail-on 정책
# ─────────────────────────────────────────────────────────────

def validate_fail_on(value: str) -> str:
    """검증 후 정규화된 값 반환. 실패 시 ValueError."""
    parts = {s.strip().lower() for s in value.split(",")}
    bad = parts - _VALID_FAIL_ON
    if bad:
        raise ValueError(
            f"invalid --fail-on {bad!r}: "
            f"valid values are {', '.join(sorted(_VALID_FAIL_ON))}")
    if FAIL_ON_NONE in parts and len(parts) > 1:
        raise ValueError("--fail-on 'none' cannot be combined with other values")
    return ",".join(sorted(parts))


def check_fail_on(findings: list[Finding], fail_on: str) -> int:
    """--fail-on 정책에 따른 exit code. 'none' -> 항상 0."""
    if fail_on == FAIL_ON_NONE:
        return 0
    trigger = {s.strip() for s in fail_on.split(",")}
    return 1 if any(f.severity in trigger for f in findings) else 0
