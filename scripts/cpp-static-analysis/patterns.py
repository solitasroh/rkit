"""패턴 탐지 — Claude review에 주입할 기계적 후보 생성.

역할:
- tree-sitter AST 기반 코드 패턴 탐지 (smell, idiom, anti-pattern)
- hard_check.py와 동일한 Finding 형식으로 출력
- 탐지만 수행, 판단은 Claude에 위임

설계 근거: docs/patterns-mvp.md, docs/patterns-mvp-impl-design.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

_SCRIPTS = str(Path(__file__).parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from dataclasses import dataclass, field
from cpp_parser import (
    CPP_EXTENSIONS, CppParser, _iter_cpp_files, _posix, _rel_path,
    _validate_target, PARSE_FILE_ERRORS,
)
from encoding import load_json_config, read_file, read_text_utf8, safe_print, write_file
from models import (
    Finding, FAIL_ON_NONE, VERSION,
    FMT_XML, FMT_TEXT, FMT_CHOICES,
    SEV_BLOCKER, SEV_MAJOR, SEV_MINOR, SEVERITY_RANK,
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    CAT_SMELL, CAT_IDIOM, CAT_ANTI_PATTERN, CAT_DUPLICATE,
    XML_TAG_FINDING, XML_TAG_FINDINGS, XML_TAG_SUMMARY, xml_attr as _attr,
)
from formatters import FormatContext, format_findings, severity_summary, check_fail_on, validate_fail_on
import pattern_rules
from cache import (
    AnalysisCache, CacheEntry, CacheOpts, CacheStats,
    FunctionFingerprint, SuppressedFinding,
    context_hash, file_content_hash, grammar_version,
)
from pattern_rules.suppression import (
    IgnoreRule,
    PatternsIgnoreResult,
    SuppressionMap,
    WAIVER_IGNORE,
    WAIVER_INLINE,
    WaiverLogger,
    _CK_PATTERNS,
    _CK_REQUIRE_REASON,
    _CK_REPORT_UNUSED,
    apply_project_config,
    apply_rule_options,
    is_file_ignored,
    parse_inline_suppressions,
    parse_patternsignore,
)

# inline 억제의 reason 문자열.
_REASON_INLINE = "inline suppression"

# ── cache 설정 키 (project-config.json `cache` 섹션) ──
_CK_CACHE = "cache"
_CK_CACHE_ENABLED = "enabled"
_CK_CACHE_PATTERNS_FILE = "patterns_file"

# 기본 캐시 파일명(§1.5). target 디렉토리에 생성.
_DEFAULT_CACHE_FILENAME = ".patterns-cache.json"

# rules_meta 직렬화 키 (context_hash §1.4)
_RM_RULE_ID = "rule_id"
_RM_SEVERITY = "severity"
_RM_CONFIDENCE = "confidence"
_RM_OPTIONS = "options"

# ── XML 출력 스키마 상수 ──
XML_ROOT_PATTERNS = "patterns"
TOOL_NAME = "patterns"
XML_ATTR_SUPPRESSED = "suppressed"
XML_ATTR_BLOCKERS = "blockers"
XML_ATTR_MAJORS = "majors"
XML_ATTR_MINORS = "minors"
XML_ATTR_ELAPSED_MS = "elapsed_ms"
XML_ATTR_FILES_ANALYZED = "files_analyzed"
XML_ATTR_FILES_CONSIDERED = "files_considered"
XML_ATTR_FILES_REANALYZED = "files_reanalyzed"
XML_ATTR_FILES_CACHE_HIT = "files_cache_hit"
XML_ATTR_FILES_PARSE_FAILED = "files_parse_failed"

# ─────────────────────────────────────────────────────────────
# Category 필터
# ─────────────────────────────────────────────────────────────

CAT_ALL = "all"

CATEGORY_ALIAS: dict[str, str | None] = {
    CAT_ALL:          None,
    "smells":         CAT_SMELL,
    "idioms":         CAT_IDIOM,
    "anti-patterns":  CAT_ANTI_PATTERN,
    "duplicates":     CAT_DUPLICATE,
}

CONFIDENCE_RANK = {
    CONF_HIGH: 3,
    CONF_MEDIUM: 2,
    CONF_LOW: 1,
}


def _resolve_category(cli_category: str) -> str | None:
    """CLI category를 내부 카테고리로 매핑. 미지 값은 ValueError.

    반환 None = 'all' (필터 없음). str = smell|idiom|anti-pattern.
    """
    if cli_category not in CATEGORY_ALIAS:
        raise ValueError(
            f"unknown category {cli_category!r}: "
            f"valid values are {', '.join(sorted(CATEGORY_ALIAS))}")
    return CATEGORY_ALIAS[cli_category]


def _apply_cli_filters(
    findings: list[Finding],
    cli_category: str,
    min_severity: str,
    min_confidence: str,
) -> list[Finding]:
    """category/min_severity/min_confidence를 findings에 적용(A2).

    설계 §1.4: 이 필터들은 context_hash에 포함되지 않는다.
    캐시에는 항상 pre-CLI-filter 결과가 저장되고, 본 함수는 보고 직전에만 적용.
    """
    target_cat = _resolve_category(cli_category)
    sev_threshold = SEVERITY_RANK.get(min_severity, 0) if min_severity else 0
    conf_threshold = CONFIDENCE_RANK.get(min_confidence, 0) if min_confidence else 0

    def _keep(f: Finding) -> bool:
        if target_cat is not None and f.type != target_cat:
            return False
        if sev_threshold and SEVERITY_RANK.get(f.severity, 0) < sev_threshold:
            return False
        if conf_threshold and CONFIDENCE_RANK.get(f.confidence, 0) < conf_threshold:
            return False
        return True

    return [f for f in findings if _keep(f)]


# ─────────────────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────────────────

@dataclass
class PatternResult:
    """run_patterns 결과. findings + 렌더링/감사에 필요한 메타데이터.

    §5.2 B6 필드 항등식: files_considered == files_cache_hit + files_reanalyzed
                                                + files_parse_failed
    files_analyzed 의미: 이제 "분석 성공 파일"(= considered - parse_failed).
    """
    findings: list[Finding]
    suppressed: list[Finding]
    files_analyzed: int
    elapsed_ms: int
    files_considered: int = 0
    files_reanalyzed: int = 0
    files_cache_hit: int = 0
    files_parse_failed: int = 0
    cache_stats: CacheStats | None = None


@dataclass
class SuppressionOpts:
    """suppression 관련 옵션 묶음. enabled=False이면 전건 출력."""
    enabled: bool = True
    config: dict | None = None
    ignore_entries: list[IgnoreRule] | None = None
    waivers_log: Path | None = None
    # context_hash 계산용 .patternsignore 원문 텍스트
    ignore_text: str = ""

    @classmethod
    def disabled(cls) -> SuppressionOpts:
        return cls(enabled=False)


# CacheOpts는 cache.py로 이관(공용)


def _classify_findings(
    file_findings: list[Finding],
    smap: SuppressionMap,
    logger: WaiverLogger | None,
) -> tuple[list[Finding], list[SuppressedFinding]]:
    """file_findings를 (통과, 억제)로 분류.

    억제 항목은 SuppressedFinding(finding, level=WAIVER_INLINE, reason)으로 감싸
    캐시 저장 시 감사 정보(level/reason)를 함께 보존한다(A4).
    """
    passed: list[Finding] = []
    suppressed: list[SuppressedFinding] = []
    for f in file_findings:
        try:
            line = int(f.lines_hint) if f.lines_hint else 0
        except (ValueError, TypeError):
            line = 0
        if line > 0 and smap.is_suppressed(line, f.rule):
            suppressed.append(SuppressedFinding(
                finding=f, level=WAIVER_INLINE, reason=_REASON_INLINE))
            if logger:
                logger.log(WAIVER_INLINE, f.rule, f.file, f.lines_hint,
                           _REASON_INLINE)
        else:
            passed.append(f)
    return passed, suppressed


def _warn_all(prefix: str, warnings: list[str]) -> None:
    """경고 목록을 stderr로 출력."""
    for w in warnings:
        safe_print(f"경고: {prefix}{w}", file=sys.stderr)


def _patterns_cfg(sup: SuppressionOpts) -> dict:
    """sup.config에서 patterns 섹션 추출. 없으면 빈 dict."""
    return (sup.config or {}).get(_CK_PATTERNS, {})


def _prepare_rules(
    sup: SuppressionOpts,
    logger: WaiverLogger | None,
) -> list[pattern_rules.PatternRule]:
    """config 기반 규칙 오버라이드. CLI 필터는 _apply_cli_filters로 이관(A2)."""
    rules = list(pattern_rules.RULES)

    if sup.enabled and sup.config:
        rules, opt_warnings = apply_rule_options(rules, _patterns_cfg(sup))
        _warn_all("", opt_warnings)

        rules, sev_warnings = apply_project_config(rules, sup.config, logger=logger)
        _warn_all("", sev_warnings)

    return rules


def _rules_meta(rules: list[pattern_rules.PatternRule]) -> list[dict]:
    """context_hash용 규칙 메타데이터 리스트(§1.4)."""
    return [
        {
            _RM_RULE_ID: r.rule_id,
            _RM_SEVERITY: r.severity,
            _RM_CONFIDENCE: r.confidence,
            _RM_OPTIONS: dict(r.default_options),
        }
        for r in rules
    ]


def _compute_context_hash(
    rules: list[pattern_rules.PatternRule], sup: SuppressionOpts,
    dup_enabled: bool = False,
) -> str:
    """분석 컨텍스트 해시(§1.4).

    포함: tool_version, grammar_version, rules_meta, config.patterns,
          .patternsignore 원문, suppression_enabled, D1 상태.
    """
    patterns_cfg = (sup.config or {}).get(_CK_PATTERNS, {})
    return context_hash(
        tool_version=VERSION,
        grammar_version=grammar_version(),
        rules_meta=_rules_meta(rules),
        config_patterns=patterns_cfg,
        patternsignore=sup.ignore_text,
        suppression_enabled=sup.enabled,
        dup_enabled=dup_enabled,
        dup_normalization_version=pattern_rules.DUP_NORM_V,
    )


def _init_cache(
    cache_opts: CacheOpts, rules: list[pattern_rules.PatternRule],
    sup: SuppressionOpts, dup_enabled: bool = False,
) -> AnalysisCache | None:
    """CacheOpts.enabled일 때만 AnalysisCache 생성. 아니면 None."""
    if not cache_opts.enabled or cache_opts.path is None:
        return None
    return AnalysisCache(
        cache_opts.path, _compute_context_hash(rules, sup, dup_enabled))


def _filter_rules_for_file(
    rules: list[pattern_rules.PatternRule],
    rel: str,
    sup: SuppressionOpts,
    logger: WaiverLogger | None,
) -> list[pattern_rules.PatternRule]:
    """.patternsignore 기반 파일별 규칙 필터링."""
    if not (sup.enabled and sup.ignore_entries):
        return rules
    filtered = []
    for r in rules:
        if is_file_ignored(rel, r.rule_id, sup.ignore_entries):
            if logger:
                logger.log(WAIVER_IGNORE, r.rule_id, rel, "", ".patternsignore")
        else:
            filtered.append(r)
    return filtered


def _apply_inline_suppression(
    file_findings: list[Finding],
    file_rules: list[pattern_rules.PatternRule],
    tree, source: bytes,
    parser: CppParser,
    rel: str,
    pcfg: dict,
    logger: WaiverLogger | None,
) -> tuple[list[Finding], list[SuppressedFinding]]:
    """inline suppression 적용. (통과, SuppressedFinding 리스트) 반환."""
    smap = parse_inline_suppressions(
        tree, source, parser,
        require_reason=pcfg.get(_CK_REQUIRE_REASON, False))
    smap.validate_rule_ids({r.rule_id for r in file_rules})
    _warn_all(f"{rel}: ", smap.warnings)

    passed, suppressed = _classify_findings(file_findings, smap, logger)

    if pcfg.get(_CK_REPORT_UNUSED, False):
        _warn_all(f"{rel}: ", smap.unused_suppressions())

    return passed, suppressed


def _process_file(
    fp: Path, target: Path,
    rules: list[pattern_rules.PatternRule],
    parser: CppParser,
    sup: SuppressionOpts,
    pcfg: dict,
    logger: WaiverLogger | None,
) -> tuple[list[Finding], list[SuppressedFinding]] | None:
    """단일 파일 처리. (통과, SuppressedFinding 리스트) 반환. 파싱 실패 시 None."""
    rel = _rel_path(fp, target)
    try:
        tree, source = parser.parse_file(fp)
    except PARSE_FILE_ERRORS:
        return None

    file_rules = _filter_rules_for_file(rules, rel, sup, logger)
    file_findings = [f for rule in file_rules
                     for f in rule.detect(rule, tree, source, rel, parser)]

    if not sup.enabled:
        return file_findings, []
    return _apply_inline_suppression(
        file_findings, file_rules, tree, source, parser, rel, pcfg, logger)


@dataclass
class _AnalyzeCtx:
    """파일 분석 공용 의존성 묶음. 길이 제한 회피용."""
    target: Path
    rules: list[pattern_rules.PatternRule]
    parser: CppParser
    sup: SuppressionOpts
    pcfg: dict
    logger: WaiverLogger | None
    cache: AnalysisCache | None
    force_reanalyze: set[str]
    dup_enabled: bool = False
    dup_min_stmts: int = 3


@dataclass
class _AnalyzeAccum:
    """파일 분석 누적 결과."""
    findings: list[Finding] = field(default_factory=list)
    suppressed: list[SuppressedFinding] = field(default_factory=list)
    files_reanalyzed: int = 0
    files_cache_hit: int = 0
    files_parse_failed: int = 0
    # D1: file → list[FunctionFingerprint] (Pass 2 입력)
    file_fingerprints: dict[str, list[FunctionFingerprint]] = field(
        default_factory=dict)


def _cache_put(
    cache: AnalysisCache | None, rel: str, fp: Path,
    findings: list[Finding], suppressed: list[SuppressedFinding],
    parse_failed: bool,
    fingerprints: list[FunctionFingerprint] | None = None,
) -> None:
    """캐시 엔트리 갱신. stat/hash 실패 시 조용히 건너뜀."""
    if cache is None:
        return
    try:
        size = fp.stat().st_size
        h = file_content_hash(fp)
    except OSError:
        return
    cache.update(rel, CacheEntry(
        content_hash=h, size=size,
        findings=findings, suppressed=suppressed, parse_failed=parse_failed,
        fingerprints=fingerprints or [],
    ))


def _reemit_cached_logs(
    cached: CacheEntry, rel: str, ctx: _AnalyzeCtx,
) -> None:
    """캐시 적중 시 waivers.log 재기록(§4.2 A4) — IGNORE + INLINE.

    IGNORE 재발행: _filter_rules_for_file의 부수효과(logger.log)만 이용.
    INLINE 재발행: cached.suppressed의 level/reason으로 logger.log.
    """
    # IGNORE 로그 재발행 (반환 rules는 버림)
    _filter_rules_for_file(ctx.rules, rel, ctx.sup, ctx.logger)
    if ctx.logger is None:
        return
    for sf in cached.suppressed:
        ctx.logger.log(
            sf.level, sf.finding.rule, sf.finding.file,
            sf.finding.lines_hint, sf.reason)


def _apply_cache_hit(
    cached: CacheEntry, rel: str,
    ctx: _AnalyzeCtx, accum: _AnalyzeAccum,
) -> None:
    """캐시 적중 엔트리 처리. parse_failed 마커와 정상 엔트리를 구분."""
    if cached.parse_failed:
        accum.files_parse_failed += 1
        return
    accum.files_cache_hit += 1
    _reemit_cached_logs(cached, rel, ctx)
    accum.findings.extend(cached.findings)
    accum.suppressed.extend(cached.suppressed)
    # D1: 캐시된 fingerprint를 글로벌 인덱스에 수집
    if ctx.dup_enabled and cached.fingerprints:
        accum.file_fingerprints[rel] = cached.fingerprints


def _analyze_single_core(
    fp: Path, rel: str, ctx: _AnalyzeCtx,
) -> tuple[list[Finding], list[SuppressedFinding],
           list[FunctionFingerprint]] | None:
    """파싱 1회 → 규칙 실행 + D1 fingerprint. 파싱 실패 시 None.

    접근 C: _process_file 호출 대신 파싱 결과를 규칙/fingerprint 양쪽에 공유.
    """
    try:
        tree, source = ctx.parser.parse_file(fp)
    except PARSE_FILE_ERRORS:
        return None
    file_rules = _filter_rules_for_file(ctx.rules, rel, ctx.sup, ctx.logger)
    file_findings = [f for rule in file_rules
                     for f in rule.detect(rule, tree, source, rel, ctx.parser)]
    if ctx.sup.enabled:
        passed, suppressed = _apply_inline_suppression(
            file_findings, file_rules, tree, source, ctx.parser,
            rel, ctx.pcfg, ctx.logger)
        smap = parse_inline_suppressions(
            tree, source, ctx.parser,
            require_reason=ctx.pcfg.get(_CK_REQUIRE_REASON, False))
    else:
        passed, suppressed = file_findings, []
        smap = None
    fps = _compute_fingerprints(tree, source, rel, smap, ctx)
    return passed, suppressed, fps


def _compute_fingerprints(
    tree, source: bytes, rel: str,
    smap: SuppressionMap | None, ctx: _AnalyzeCtx,
) -> list[FunctionFingerprint]:
    """D1 Pass 1: fingerprint 계산 + logger 기록. 비활성이면 빈 리스트."""
    if not ctx.dup_enabled:
        return []
    fps = pattern_rules.compute_fingerprints(tree, source, rel, smap)
    # WaiverLogger 기록 (설계 §7.4)
    if ctx.logger:
        for fp in fps:
            if fp.inline_suppressed:
                ctx.logger.log(
                    WAIVER_INLINE, pattern_rules.DUP_RULE_ID,
                    rel, str(fp.line), _REASON_INLINE)
    return fps


def _analyze_single(
    fp: Path, rel: str, ctx: _AnalyzeCtx, accum: _AnalyzeAccum,
) -> None:
    """캐시 미스 파일 실제 분석 + D1 fingerprint + 캐시 저장."""
    result = _analyze_single_core(fp, rel, ctx)
    if result is None:
        accum.files_parse_failed += 1
        _cache_put(ctx.cache, rel, fp, [], [], parse_failed=True)
        return
    file_findings, file_suppressed, fingerprints = result
    accum.files_reanalyzed += 1
    accum.findings.extend(file_findings)
    accum.suppressed.extend(file_suppressed)
    if fingerprints:
        accum.file_fingerprints[rel] = fingerprints
    _cache_put(ctx.cache, rel, fp, file_findings, file_suppressed,
               parse_failed=False, fingerprints=fingerprints)


def _process_one(fp: Path, ctx: _AnalyzeCtx, accum: _AnalyzeAccum) -> None:
    """단일 파일 처리. 캐시 적중 시 재사용, 아니면 분석."""
    rel = _rel_path(fp, ctx.target)
    cached = None
    if ctx.cache is not None and rel not in ctx.force_reanalyze:
        cached = ctx.cache.lookup(rel, fp)
    if cached is not None:
        _apply_cache_hit(cached, rel, ctx, accum)
        return
    _analyze_single(fp, rel, ctx, accum)


def _analyze_files(
    files: list[Path], ctx: _AnalyzeCtx,
) -> _AnalyzeAccum:
    """파일 목록을 순회하여 누적 결과 반환."""
    accum = _AnalyzeAccum()
    for fp in files:
        _process_one(fp, ctx, accum)
    return accum



def _finalize_cache(cache: AnalysisCache | None, full_mode: bool) -> None:
    """전체 모드면 stale 정리(§6.5) 후 저장. 비활성이면 no-op."""
    if cache is None:
        return
    if full_mode:
        cache.prune_unseen()
    cache.save()


def _build_pattern_result(
    accum: _AnalyzeAccum, files_count: int,
    findings: list[Finding], suppressed: list[Finding],
    elapsed_ms: int, cache: AnalysisCache | None,
) -> PatternResult:
    """PatternResult 구성. files_analyzed는 '분석 성공'(=considered-parse_failed)."""
    return PatternResult(
        findings=findings,
        suppressed=suppressed,
        files_analyzed=files_count - accum.files_parse_failed,
        elapsed_ms=elapsed_ms,
        files_considered=files_count,
        files_reanalyzed=accum.files_reanalyzed,
        files_cache_hit=accum.files_cache_hit,
        files_parse_failed=accum.files_parse_failed,
        cache_stats=cache.stats if cache else None,
    )


def _finalize_findings(
    accum: _AnalyzeAccum,
    cli_category: str, min_severity: str, min_confidence: str,
) -> tuple[list[Finding], list[Finding]]:
    """CLI 필터 적용(§1.4 A2) + suppressed를 A5 계약에 맞춰 list[Finding]로 평면화."""
    sup_flat = [sf.finding for sf in accum.suppressed]
    return (
        _apply_cli_filters(accum.findings, cli_category, min_severity, min_confidence),
        _apply_cli_filters(sup_flat, cli_category, min_severity, min_confidence),
    )


def _maybe_warn_full_fallback(
    cache: AnalysisCache | None, force: set[str],
) -> None:
    """--cache --diff 모드에서 캐시 비었거나 무효화되면 경고(§2.3 B2)."""
    if cache is None or not force:
        return
    if cache.stats.global_invalidation or cache.stats.entries_before == 0:
        safe_print(
            "캐시: 초기화 또는 컨텍스트 변경 — 전체 파일 분석 "
            "(다음 실행부터 증분)",
            file=sys.stderr,
        )


def _is_dup_configured(rules: list[pattern_rules.PatternRule]) -> bool:
    """DUP_RULE이 config에 의해 활성 상태인지 (context_hash용, category 무관)."""
    return any(r.rule_id == pattern_rules.DUP_RULE_ID for r in rules)


def _is_dup_active(rules: list[pattern_rules.PatternRule],
                   cli_category: str) -> bool:
    """D1이 실제 실행 대상인지 (config 활성 + category 필터 통과)."""
    if not _is_dup_configured(rules):
        return False
    target_cat = _resolve_category(cli_category)
    return target_cat is None or target_cat == CAT_DUPLICATE


def _get_dup_min_stmts(rules: list[pattern_rules.PatternRule]) -> int:
    """DUP_RULE의 options에서 min_stmts 조회."""
    for r in rules:
        if r.rule_id == pattern_rules.DUP_RULE_ID:
            return r.default_options.get("min_stmts", pattern_rules.MIN_STMT_COUNT)
    return pattern_rules.MIN_STMT_COUNT


def _build_analyze_ctx(
    target: Path, sup: SuppressionOpts,
    cache_opts: CacheOpts, force: set[str],
    no_dup: bool = False, cli_category: str = CAT_ALL,
    cli_dup_min_stmts: int = 0,
) -> _AnalyzeCtx:
    """분석 컨텍스트(rules/parser/logger/cache) 구성."""
    parser = CppParser()
    logger = WaiverLogger(sup.waivers_log) if sup.waivers_log else None
    pcfg = _patterns_cfg(sup)
    rules = _prepare_rules(sup, logger)
    # context_hash에는 config 상의 활성 여부만 반영 (category는 보고 필터)
    dup_configured = (not no_dup) and _is_dup_configured(rules)
    dup_on = (not no_dup) and _is_dup_active(rules, cli_category)
    min_stmts = cli_dup_min_stmts if cli_dup_min_stmts > 0 \
        else _get_dup_min_stmts(rules)
    cache = _init_cache(cache_opts, rules, sup, dup_enabled=dup_configured)
    _maybe_warn_full_fallback(cache, force)
    return _AnalyzeCtx(
        target, rules, parser, sup, pcfg, logger, cache, force,
        dup_enabled=dup_on, dup_min_stmts=min_stmts)


def _select_files(
    target: Path, changed: set[str] | None, cache_enabled: bool,
) -> list[Path]:
    """--diff 모드 파일 필터링(§3.5).

    diff + 캐시 있음: 전체 순회(미변경 파일은 캐시 적중으로 skip).
    diff + 캐시 없음: 변경 파일만 순회.
    diff 아님: 전체.
    """
    files = _iter_cpp_files(target)
    if changed is not None and not cache_enabled:
        files = [f for f in files if _rel_path(f, target) in changed]
    return files


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    """결정적 출력 순서."""
    return sorted(findings, key=lambda f: (f.file, f.lines_hint, f.rule))


def _run_analysis(
    files: list[Path], ctx: _AnalyzeCtx,
) -> tuple[_AnalyzeAccum, int]:
    """분석 실행 + elapsed_ms."""
    t0 = time.monotonic()
    accum = _analyze_files(files, ctx)
    if ctx.logger:
        ctx.logger.flush()
    return accum, int((time.monotonic() - t0) * 1000)


def _dup_rule_from_ctx(ctx: _AnalyzeCtx) -> pattern_rules.PatternRule | None:
    """현재 rules에서 DUP_RULE 조회. E2 오버라이드 반영된 인스턴스."""
    return next((r for r in ctx.rules
                 if r.rule_id == pattern_rules.DUP_RULE_ID), None)


def _run_dup_pass2(ctx: _AnalyzeCtx, accum: _AnalyzeAccum) -> None:
    """D1 Pass 2: cross-file 중복 매칭. findings를 accum에 추가."""
    if not ctx.dup_enabled or not accum.file_fingerprints:
        return
    dup_rule = _dup_rule_from_ctx(ctx)
    dup_index = pattern_rules.build_fingerprint_index(
        accum.file_fingerprints,
        ctx.sup.ignore_entries if ctx.sup.enabled else None,
        ctx.dup_min_stmts,
    )
    dup_findings = pattern_rules.detect_duplicates(
        dup_index, severity=dup_rule.severity if dup_rule else SEV_MAJOR)
    accum.findings.extend(dup_findings)


def _warn_diff_only_dup(ctx: _AnalyzeCtx, changed: set[str] | None) -> None:
    """--diff only + D1 활성 시 경고 (§3.5)."""
    if ctx.dup_enabled and changed is not None:
        safe_print(
            "경고: --diff 모드(캐시 없음)에서 DUP-01은 변경 파일 간에서만 "
            "비교합니다. 전체 중복 탐지는 --cache --diff를 사용하세요.",
            file=sys.stderr)


def _init_run(
    target: Path, sup: SuppressionOpts | None,
    cache_opts: CacheOpts | None, changed_files: set[str] | None,
    no_dup: bool, dup_min_stmts: int, cli_category: str,
) -> tuple[SuppressionOpts, CacheOpts, _AnalyzeCtx]:
    """run_patterns 초기화. (sup, cache_opts, ctx) 반환."""
    sup = sup or SuppressionOpts()
    co = cache_opts or CacheOpts.disabled()
    force = changed_files if changed_files is not None else set()
    ctx = _build_analyze_ctx(
        target, sup, co, force, no_dup=no_dup,
        cli_category=cli_category, cli_dup_min_stmts=dup_min_stmts)
    if changed_files is not None and not co.enabled:
        _warn_diff_only_dup(ctx, changed_files)
    return sup, co, ctx


def run_patterns(
    target: Path, cli_category: str = CAT_ALL,
    min_severity: str = "", min_confidence: str = "",
    sup: SuppressionOpts | None = None,
    cache_opts: CacheOpts | None = None,
    changed_files: set[str] | None = None,
    no_dup: bool = False,
    dup_min_stmts: int = 0,
) -> PatternResult:
    """target 하위 C++ 파일 분석."""
    sup, co, ctx = _init_run(
        target, sup, cache_opts, changed_files,
        no_dup, dup_min_stmts, cli_category)
    files = _select_files(target, changed_files, co.enabled)
    accum, elapsed_ms = _run_analysis(files, ctx)
    _run_dup_pass2(ctx, accum)
    _finalize_cache(ctx.cache, full_mode=(changed_files is None))
    findings, suppressed = _finalize_findings(
        accum, cli_category, min_severity, min_confidence)
    return _build_pattern_result(
        accum, len(files), _sort_findings(findings),
        _sort_findings(suppressed), elapsed_ms, ctx.cache)


# ─────────────────────────────────────────────────────────────
# 렌더링
# ─────────────────────────────────────────────────────────────

def _xml_summary_attrs(result: PatternResult) -> list[tuple[str, int]]:
    """XML summary 속성 튜플 목록. 캐시/파싱실패 필드는 조건부(§5.2)."""
    findings = result.findings
    sev = severity_summary(findings)
    attrs: list[tuple[str, int]] = [
        (XML_TAG_FINDINGS, len(findings)),
        (XML_ATTR_SUPPRESSED, len(result.suppressed)),
        (XML_ATTR_BLOCKERS, sev[SEV_BLOCKER]),
        (XML_ATTR_MAJORS, sev[SEV_MAJOR]),
        (XML_ATTR_MINORS, sev[SEV_MINOR]),
        (XML_ATTR_ELAPSED_MS, result.elapsed_ms),
        (XML_ATTR_FILES_CONSIDERED, result.files_considered),
        (XML_ATTR_FILES_ANALYZED, result.files_analyzed),
    ]
    if result.files_parse_failed:
        attrs.append((XML_ATTR_FILES_PARSE_FAILED, result.files_parse_failed))
    if result.cache_stats is not None:
        attrs.append((XML_ATTR_FILES_REANALYZED, result.files_reanalyzed))
        attrs.append((XML_ATTR_FILES_CACHE_HIT, result.files_cache_hit))
    return attrs


def _render_xml(result: PatternResult, mod: str, target: Path) -> str:
    """PatternResult를 기존 XML 포맷으로 렌더링."""
    summary_str = " ".join(
        f'{k}={_attr(str(v))}' for k, v in _xml_summary_attrs(result))
    inner = "\n".join(f.to_xml() for f in result.findings)
    return (
        f'<{XML_ROOT_PATTERNS} module={_attr(mod)} path={_attr(_posix(str(target)))}>\n'
        f'  <{XML_TAG_SUMMARY} {summary_str}/>\n{inner}\n</{XML_ROOT_PATTERNS}>\n'
    )


def _render_text(result: PatternResult) -> str:
    """PatternResult를 텍스트 포맷으로 렌더링."""
    if not result.findings:
        return "패턴 탐지 없음\n"
    lines = [f.to_text_line() for f in result.findings]
    sup = len(result.suppressed)
    sup_str = f" (억제 {sup}건)" if sup else ""
    return "\n".join(lines) + f"\n\n총 {len(result.findings)}건{sup_str}\n"


def _make_format_context(result: PatternResult, mod: str) -> FormatContext:
    """PatternResult → FormatContext. 캐시 활성 여부 포함(§5.2)."""
    return FormatContext(
        tool=TOOL_NAME, module=mod,
        files_analyzed=result.files_analyzed,
        elapsed_ms=result.elapsed_ms,
        suppressed_count=len(result.suppressed),
        files_considered=result.files_considered,
        files_reanalyzed=result.files_reanalyzed,
        files_cache_hit=result.files_cache_hit,
        files_parse_failed=result.files_parse_failed,
        cache_enabled=result.cache_stats is not None,
    )


def render_findings(
    result: PatternResult, fmt: str, target: Path, module: str = "",
) -> str:
    """PatternResult를 지정 포맷으로 렌더링."""
    mod = module or target.name
    ctx = _make_format_context(result, mod)
    rendered = format_findings(result.findings, fmt, ctx)
    if rendered is not None:
        return rendered
    if fmt == FMT_XML:
        return _render_xml(result, mod, target)
    if fmt == FMT_TEXT:
        return _render_text(result)
    raise ValueError(f"unknown format: {fmt!r}")


# ─────────────────────────────────────────────────────────────
# --diff / --changed-files (증분 분석)
# ─────────────────────────────────────────────────────────────

# git diff 필터: Added, Copied, Modified, Renamed — Deleted 제외(§2.1)
_GIT_DIFF_FILTER = "ACMR"


def _run_git(cmd: list[str], cwd: Path) -> str:
    """git 서브프로세스 실행. returncode != 0 → RuntimeError. stdout 반환."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(cwd))
    except FileNotFoundError as e:
        raise RuntimeError(f"git 실행 실패: {e}") from e
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} 실패: {result.stderr.strip()}")
    return result.stdout


def _git_repo_root(start: Path) -> Path:
    """start에서 상위로 올라가며 git repo root 탐색(§2.1)."""
    anchor = start if start.is_dir() else start.parent
    out = _run_git(["git", "rev-parse", "--show-toplevel"], anchor)
    return Path(out.strip())


def _git_changed_files(target: Path, ref: str) -> list[Path]:
    """git diff로 변경 파일 절대 경로 목록 획득(§2.1 B3)."""
    repo_root = _git_repo_root(target)
    try:
        rel_target = target.resolve().relative_to(repo_root.resolve())
    except ValueError as e:
        raise RuntimeError(
            f"target({target})이 repo({repo_root}) 바깥에 있습니다") from e
    pathspec = str(rel_target).replace("\\", "/") or "."
    out = _run_git(
        ["git", "diff", "--name-only", f"--diff-filter={_GIT_DIFF_FILTER}",
         ref, "--", pathspec],
        repo_root,
    )
    return [repo_root / line for line in out.splitlines() if line]


def _read_changed_files(path: str, target: Path) -> list[Path]:
    """파일 목록 파일 파싱(§2.2). 빈 줄/`#` 주석 무시. 상대경로는 target 기준."""
    base = target if target.is_dir() else target.parent
    text = read_file(Path(path))
    result: list[Path] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line)
        result.append(p if p.is_absolute() else base / p)
    return result


def _filter_cpp_in_target(paths: list[Path], target: Path) -> set[str]:
    """C++ 확장자 + target 내부 필터. rel_path(POSIX) 집합 반환(§2.4)."""
    bounds = (target if target.is_dir() else target.parent).resolve()
    result: set[str] = set()
    for p in paths:
        if p.suffix.lower() not in CPP_EXTENSIONS:
            continue
        try:
            p.resolve().relative_to(bounds)
        except (OSError, ValueError):
            continue
        result.add(_rel_path(p, target))
    return result


def _changed_files_from_args(args, target: Path) -> set[str] | None:
    """CLI 인자로부터 변경 파일 rel_path 집합 생성. diff 모드 아니면 None."""
    if args.diff:
        abs_paths = _git_changed_files(target, args.diff)
    elif args.changed_files:
        abs_paths = _read_changed_files(args.changed_files, target)
    else:
        return None
    return _filter_cpp_in_target(abs_paths, target)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def _ignore_dir(args, target: Path) -> Path:
    """.patternsignore 탐색 디렉토리. config 지정 시 config 디렉토리, 아니면 target."""
    d = Path(args.config).parent if args.config else target
    return d.parent if d.is_file() else d


def _read_ignore_text(path: Path) -> str:
    """.patternsignore 원문(UTF-8). context_hash용. 없으면/오류 시 빈 문자열.

    UTF-8이 아닌 파일은 사용자 오류로 간주하여 빈 문자열 처리(hash 안정성보다
    정책상 UTF-8 강제가 우선).
    """
    if not path.is_file():
        return ""
    try:
        return read_text_utf8(path)
    except (OSError, UnicodeDecodeError):
        return ""


def _load_config(args) -> dict | None:
    """--config 지정 시 project-config.json 로드."""
    if not args.config:
        return None
    return load_json_config(Path(args.config))


def _build_suppression_opts(args, target: Path, config: dict | None) -> SuppressionOpts:
    """CLI 인자 + 사전 로드된 config로부터 SuppressionOpts 구성."""
    if args.no_suppress:
        return SuppressionOpts.disabled()
    ignore_path = _ignore_dir(args, target) / ".patternsignore"
    ignore_text = _read_ignore_text(ignore_path)
    ignore_result = parse_patternsignore(ignore_path)
    _warn_all("", ignore_result.warnings)
    return SuppressionOpts(
        config=config,
        ignore_entries=ignore_result.entries,
        waivers_log=Path(args.waivers_log) if args.waivers_log else None,
        ignore_text=ignore_text,
    )


def _resolve_cache_path(
    raw: str, target: Path, default: str = _DEFAULT_CACHE_FILENAME,
) -> Path:
    """상대 경로는 target 기반(target이 파일이면 부모)으로 해석. raw=""이면 default."""
    p = Path(raw or default)
    if p.is_absolute():
        return p
    base = target if target.is_dir() else target.parent
    return base / p


def _cache_path_from_cli(args, target: Path) -> Path | None:
    """--cache-file 또는 --cache 플래그에서 캐시 경로 해소."""
    if args.cache_file:
        return _resolve_cache_path(args.cache_file, target)
    if args.cache:
        return _resolve_cache_path("", target)
    return None


def _cache_path_from_config(config: dict | None, target: Path) -> Path | None:
    """project-config.json의 cache 섹션에서 캐시 경로 해소."""
    if not config:
        return None
    cache_cfg = config.get(_CK_CACHE, {})
    if not cache_cfg.get(_CK_CACHE_ENABLED):
        return None
    filename = cache_cfg.get(_CK_CACHE_PATTERNS_FILE, _DEFAULT_CACHE_FILENAME)
    return _resolve_cache_path(filename, target)


def _build_cache_opts(args, target: Path, config: dict | None) -> CacheOpts:
    """캐시 옵션 해소. --no-cache > --cache/--cache-file > config > 기본(비활성)."""
    if args.no_cache:
        return CacheOpts.disabled()
    p = _cache_path_from_cli(args, target) or _cache_path_from_config(config, target)
    if p is None:
        return CacheOpts.disabled()
    return CacheOpts(enabled=True, path=p)


def _print_cache_stats(result: PatternResult) -> None:
    """stderr로 캐시 통계 출력(§5.1). cache_stats 없으면 no-op."""
    stats = result.cache_stats
    if stats is None:
        return
    invalidated = "있음" if stats.global_invalidation else "없음"
    safe_print(
        f"캐시: 적중 {result.files_cache_hit}/{result.files_considered}, "
        f"미스 {result.files_reanalyzed}, 전역 무효화 {invalidated}",
        file=sys.stderr,
    )


def _add_core_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("category", choices=list(CATEGORY_ALIAS.keys()),
                    help="탐지 범주")
    ap.add_argument("--target", required=True, help="대상 디렉토리 또는 파일")
    ap.add_argument("--format", choices=FMT_CHOICES,
                    default=FMT_TEXT, help="출력 형식")
    ap.add_argument("--output", help="출력 파일 (없으면 stdout)")
    ap.add_argument("--module", default="", help="모듈명 (기본: target 이름)")
    ap.add_argument("--config", default="", help="project-config.json 경로")
    ap.add_argument("--fail-on", default=FAIL_ON_NONE,
                    help="exit 1 트리거 severity (blocker,major,minor,none)")


def _add_filter_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--min-severity", choices=list(SEVERITY_RANK),
                    default="", help="최소 심각도 필터")
    ap.add_argument("--min-confidence", choices=list(CONFIDENCE_RANK),
                    default="", help="최소 신뢰도 필터")
    ap.add_argument("--no-suppress", action="store_true",
                    help="모든 suppression 비활성화 (전건 출력)")
    ap.add_argument("--waivers-log", default="", help="감사 로그 파일 경로")


def _add_cache_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--cache", action="store_true",
                    help="분석 결과 캐시 활성화")
    ap.add_argument("--cache-file", default="",
                    help="캐시 파일 경로 (--cache 암시)")
    ap.add_argument("--no-cache", action="store_true",
                    help="캐시 비활성화 (--cache/config 모두 무시)")
    ap.add_argument("--diff", default="",
                    help="git REF과의 변경 파일만 분석 (예: HEAD~1, main)")
    ap.add_argument("--changed-files", default="",
                    help="분석 대상 파일 목록 (줄당 경로 하나, # 주석 허용)")


def _add_dup_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--no-dup", action="store_true",
                    help="D1 중복 탐지 비활성화")
    ap.add_argument("--dup-min-stmts", type=int, default=0,
                    help="D1 최소 문장 수 (기본 3)")


def _parse_args():
    """CLI 인자 파싱."""
    ap = argparse.ArgumentParser(description="C++ 패턴 탐지 (patterns)")
    _add_core_args(ap)
    _add_filter_args(ap)
    _add_cache_args(ap)
    _add_dup_args(ap)
    return ap.parse_args()


def _preflight(args) -> tuple[str, Path] | int:
    """fail_on 검증 + target 존재 검증. 실패 시 exit code 반환."""
    try:
        fail_on = validate_fail_on(args.fail_on)
    except ValueError as e:
        safe_print(f"에러: {e}", file=sys.stderr)
        return 1
    target = Path(args.target)
    err = _validate_target(target)
    if err:
        safe_print(f"에러: {err}", file=sys.stderr)
        return 1
    return fail_on, target


def _emit(result: PatternResult, rendered: str, args) -> None:
    """결과를 파일 또는 stdout에 출력 + 캐시 통계를 stderr로."""
    if args.output:
        write_file(args.output, rendered)
        safe_print(
            f"생성: {args.output} ({len(result.findings)}건)", file=sys.stderr)
    else:
        safe_print(rendered, end="")
    _print_cache_stats(result)


def _resolve_changed(args, target: Path) -> set[str] | None | int:
    """--diff/--changed-files 해소. 에러 발생 시 exit code 반환."""
    try:
        return _changed_files_from_args(args, target)
    except (RuntimeError, OSError, UnicodeDecodeError) as e:
        safe_print(f"에러: {e}", file=sys.stderr)
        return 1


def main() -> int:
    args = _parse_args()
    pf = _preflight(args)
    if isinstance(pf, int):
        return pf
    fail_on, target = pf

    config = _load_config(args)
    sup = _build_suppression_opts(args, target, config)
    cache_opts = _build_cache_opts(args, target, config)
    changed = _resolve_changed(args, target)
    if isinstance(changed, int):
        return changed

    result = run_patterns(
        target, args.category, args.min_severity, args.min_confidence,
        sup=sup, cache_opts=cache_opts, changed_files=changed,
        no_dup=args.no_dup, dup_min_stmts=args.dup_min_stmts)
    rendered = render_findings(result, args.format, target, module=args.module)
    _emit(result, rendered, args)
    return check_fail_on(result.findings, fail_on)


if __name__ == "__main__":
    sys.exit(main())
