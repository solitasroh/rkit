"""메트릭 rule 모듈 — 5종 구조 신호 탐지.

설계 근거: docs/metrics-plan.md §6 P1, §4
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from encoding import safe_print
from models import Finding, SEV_MAJOR, SEV_MINOR, CONF_HIGH
from project_graph import ProjectGraph, ClassNode

# ── rule id 상수 ──

RULE_DIT_HIGH = "class_DIT_high"
RULE_NOC_HIGH = "class_NOC_high"
RULE_ABSTRACTNESS_LOW = "class_abstractness_low"
RULE_THIN_CLASS = "thin_class"
RULE_SPECULATIVE = "speculative_generality"

# P5 (2단계) rule
RULE_CA_HIGH = "class_Ca_high"
RULE_CE_HIGH = "class_Ce_high"
RULE_ZONE_OF_PAIN = "zone_of_pain"
RULE_CLASS_CYCLE = "class_cycle"
RULE_DEAD_CLASS = "dead_class"
RULE_MIDDLEMAN = "middleman"
RULE_MIDDLEMAN_CHAIN = "middleman_chain"

# C 축소판 — 설계 smell (2026-04-21 추가)
RULE_GOD_CLASS = "god_class"
RULE_INAPPROPRIATE_INTIMACY = "inappropriate_intimacy"

# ── finding type ──

FT_METRIC = "metric"

# ── threshold 기본값 ──

DEFAULT_METRICS_THRESHOLDS: dict[str, float] = {
    "class_DIT": 5,
    "class_NOC_concrete": 12,
    "class_Ca": 20,
    "class_Ce": 10,
    "class_I_low": 0.1,
    "class_I_high": 0.9,
    "class_D": 0.7,
    "thin_class_methods": 2,
    "thin_class_fields": 1,
    "middleman_delegation_ratio": 0.8,
    "middleman_min_methods": 3,
    # 임계 50은 Martin/Fowler 관례 (30 methods + 20 fields 근처) 근거.
    "god_class_size": 50,
}

# ── rule 메타 (기본 enabled + severity) ──

DEFAULT_METRIC_RULES: dict[str, dict] = {
    RULE_DIT_HIGH:          {"enabled": True,  "severity": SEV_MAJOR},
    RULE_NOC_HIGH:          {"enabled": True,  "severity": SEV_MINOR},
    RULE_ABSTRACTNESS_LOW:  {"enabled": False, "severity": SEV_MINOR},  # 미구현
    RULE_THIN_CLASS:        {"enabled": True,  "severity": SEV_MINOR},
    RULE_SPECULATIVE:       {"enabled": True,  "severity": SEV_MINOR},
    # 2단계 rule (P5)
    RULE_CA_HIGH:           {"enabled": True,  "severity": SEV_MINOR},
    RULE_CE_HIGH:           {"enabled": True,  "severity": SEV_MINOR},
    RULE_ZONE_OF_PAIN:      {"enabled": True,  "severity": SEV_MAJOR},
    RULE_CLASS_CYCLE:       {"enabled": True,  "severity": SEV_MAJOR},
    # dead_class: open-world 가정 시 오탐 범람 가능 — 기본 비활성, dogfooding 이후 재검토
    RULE_DEAD_CLASS:        {"enabled": False, "severity": SEV_MINOR},
    # heuristic 정밀도 낮음 — 기본 비활성, dogfooding 이후 재검토
    RULE_MIDDLEMAN:         {"enabled": False, "severity": SEV_MINOR},
    RULE_MIDDLEMAN_CHAIN:   {"enabled": False, "severity": SEV_MAJOR},
    # C 축소판 — 크기 임계 + 양방향 결합 (오탐 위험 낮은 2종만 활성)
    RULE_GOD_CLASS:              {"enabled": True, "severity": SEV_MAJOR},
    RULE_INAPPROPRIATE_INTIMACY: {"enabled": True, "severity": SEV_MAJOR},
}

# ── config 키 상수 ──

_CK_METRICS = "metrics"
_CK_ENABLED = "enabled"
_CK_THRESHOLDS = "thresholds"
_CK_RULES = "rules"
_CK_SEVERITY = "severity"


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼 — 설정 로드 / 검증
# ─────────────────────────────────────────────────────────────

def _th_warn(key: str, reason: str) -> float:
    """threshold 기본값 폴백 + 경고 출력. 반환값: 기본 float."""
    default = DEFAULT_METRICS_THRESHOLDS[key]
    safe_print(
        f"경고: metrics.thresholds['{key}'] {reason}"
        f" — 기본값 {default} 사용",
        file=sys.stderr,
    )
    return float(default)


def _validate_one_threshold(key: str, value: object) -> float | None:
    """단일 threshold 값 검증. 유효하면 float, 무효하면 None(폴백 필요).

    설계 근거: docs/metrics-plan.md §4.1 이슈 #10
    """
    # bool은 int 서브클래스이므로 먼저 거부
    if isinstance(value, bool):
        return _th_warn(key, "bool 값 거부")
    if not isinstance(value, (int, float)):
        return _th_warn(key, f"숫자가 아님 ({type(value).__name__})")
    if value <= 0:
        return _th_warn(key, f"음수/0 거부 ({value})")
    return float(value)


def _validate_thresholds(raw: dict) -> dict[str, float]:
    """메트릭 threshold dict 검증 + 정규화.

    알 수 없는 키 → 경고 후 무시.
    반환: 검증된 float dict (기본값 폴백 포함).
    설계 근거: docs/metrics-plan.md §4.1 이슈 #10
    """
    result: dict[str, float] = {}
    for key, value in raw.items():
        if key not in DEFAULT_METRICS_THRESHOLDS:
            safe_print(
                f"경고: metrics.thresholds 알 수 없는 키 '{key}' — 무시",
                file=sys.stderr,
            )
            continue
        validated = _validate_one_threshold(key, value)
        result[key] = validated if validated is not None \
            else float(DEFAULT_METRICS_THRESHOLDS[key])
    return result


def _merge_rule(defaults: dict, override: dict) -> dict:
    """단일 rule 기본값에 사용자 override 병합. 새 dict 반환."""
    merged = dict(defaults)
    if _CK_ENABLED in override:
        merged[_CK_ENABLED] = bool(override[_CK_ENABLED])
    if _CK_SEVERITY in override:
        merged[_CK_SEVERITY] = override[_CK_SEVERITY]
    return merged


def _build_rules(user_rules: dict) -> dict[str, dict]:
    """DEFAULT_METRIC_RULES 기반으로 사용자 override를 병합한 rules dict 반환."""
    return {
        rule_name: _merge_rule(defaults, user_rules.get(rule_name, {}))
        for rule_name, defaults in DEFAULT_METRIC_RULES.items()
    }


def _load_metrics_config(raw_cfg: dict) -> tuple[bool, dict[str, float], dict[str, dict]]:
    """raw config dict에서 metrics 섹션 추출 + 검증.

    반환: (enabled, thresholds, rules).
    설계 근거: docs/metrics-plan.md §4.1
    """
    metrics_cfg = raw_cfg.get(_CK_METRICS, {})
    enabled: bool = bool(metrics_cfg.get(_CK_ENABLED, True))
    validated = _validate_thresholds(metrics_cfg.get(_CK_THRESHOLDS, {}))
    thresholds: dict[str, float] = {**DEFAULT_METRICS_THRESHOLDS, **validated}
    rules = _build_rules(metrics_cfg.get(_CK_RULES, {}))
    return enabled, thresholds, rules


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼 — 개별 rule 체크 함수
# ─────────────────────────────────────────────────────────────

def _check_class_dit_high(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """DIT 초과 시 측정값 반환, 아니면 None.

    설계 근거: docs/metrics-plan.md §6 P1 rule 1
    """
    d = graph.dit(cls.qualified_name)
    limit = int(thresholds["class_DIT"])
    return d if d > limit else None


def _check_class_noc_high(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """NOC 초과 시 측정값 반환. abstract 클래스는 제외.

    설계 근거: docs/metrics-plan.md §6 P1 rule 2
    """
    if cls.is_abstract:
        # abstract 클래스는 부모 역할이 목적이므로 NOC 높음이 자연스러움 → 제외
        return None
    noc = graph.noc(cls.qualified_name)
    limit = int(thresholds["class_NOC_concrete"])
    return noc if noc > limit else None


def _check_abstractness_low(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """클래스 추상성 낮음 탐지. P5에서 모듈/디렉토리 단위로 설계 예정.

    P1은 slot 유지 — 항상 None 반환.
    설계 근거: docs/metrics-plan.md §6 P1 rule 3 (P5 스코프)
    """
    return None  # P5 구현 예정


def _check_thin_class(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """thin_class 탐지: methods 적음 AND fields 적음 AND NOT abstract AND NOC=0.

    value로 메서드 수를 반환. abstract / 자식 있는 클래스는 제외 (interface / Strategy 등).
    설계 근거: docs/metrics-plan.md §6 P1 rule 4
    """
    if cls.is_abstract:
        return None
    if graph.noc(cls.qualified_name) != 0:
        return None

    method_limit = int(thresholds["thin_class_methods"])
    field_limit = int(thresholds["thin_class_fields"])

    method_count = len(cls.methods)
    field_count = len(cls.fields)

    if method_count <= method_limit and field_count <= field_limit:
        return method_count  # value = 메서드 수 (책임 크기 참고용)
    return None


def _check_speculative_generality(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """speculative_generality 탐지: abstract + NOC=0.

    **P5 설계 노트**: "Ca=0 조건까지 요구"하는 완전 판정 승급을 §6 P5에서 계획했으나,
    dogfooding(test source/platform) 결과 open-world 가정 문제로 오탐 범람(DI
    인터페이스가 외부 소비자에 의해 참조되는 정상 구조도 Ca=0으로 잡힘).
    따라서 P1 기준(abstract + NOC=0) 유지. Ca=0 교차는 AI 리뷰어가 DEFERRED로
    처리 (§5.1 교차 조회).
    설계 근거: docs/metrics-plan.md §6 P5 — 본 조정은 §10.5 P5 로그에 기록.
    """
    if not cls.is_abstract:
        return None
    if graph.noc(cls.qualified_name) != 0:
        return None
    return 1  # 플래그: abstract + 구현체 없음


# ─────────────────────────────────────────────────────────────
# P5 rule 체크 함수
# ─────────────────────────────────────────────────────────────

def _check_class_ca_high(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """Ca(Afferent Couplings) 초과 시 Ca 값 반환."""
    ca = len(graph.afferent(cls.qualified_name))
    limit = int(thresholds["class_Ca"])
    return ca if ca > limit else None


def _check_class_ce_high(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """Ce(Efferent Couplings) 초과 시 Ce 값 반환."""
    ce = len(graph.efferent(cls.qualified_name))
    limit = int(thresholds["class_Ce"])
    return ce if ce > limit else None


def _check_zone_of_pain(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """Zone of Pain: Martin 좌표상 (I<0.2 AND A<0.2) AND Ca > limit.

    zone() 반환값이 "pain"이면서 피의존 규모도 임계 초과해야 finding 생성.
    이중 조건으로 "Martin 정의상 Pain"(좌표) + "실제 변경 파급 규모"(절대값) 둘 다 확보.
    설계 근거: Martin I/A/D + docs/metrics-plan.md §4.1
    """
    if graph.zone(cls.qualified_name) != "pain":
        return None
    ca = len(graph.afferent(cls.qualified_name))
    limit = int(thresholds["class_Ca"])
    return ca if ca > limit else None


def _check_dead_class(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """Dead class: Ca=0 AND NOC=0 AND NOT abstract.

    abstract + NOC=0 + Ca=0은 speculative_generality가 잡음 (중복 방지).
    """
    if cls.is_abstract:
        return None
    if graph.noc(cls.qualified_name) != 0:
        return None
    if len(graph.afferent(cls.qualified_name)) != 0:
        return None
    return 1  # 플래그


def _check_class_cycle(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """순환 의존 그룹 멤버 여부. 그룹 크기를 value로 반환.

    주의: 같은 순환 그룹의 모든 멤버가 개별 emit — 대표 통합은 rapp_review 쪽
    adversarial-review.md §2.5.4("같은 클래스의 여러 메트릭 finding은 대표 1건")에 위임.
    """
    for group in graph.class_cycles():
        if cls.qualified_name in group:
            return len(group)
    return None


def _check_middleman(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """middleman 탐지 (heuristic 정밀도 낮음 — 기본 disabled).

    P5 1차: methods ≥ middleman_min_methods AND method_call_targets 다수 AND
    필드 수 작은 경우를 middleman 의심 신호로. 실제 위임률 계산은 body 분석 필요 — P7.
    """
    min_methods = int(thresholds["middleman_min_methods"])
    if len(cls.methods) < min_methods:
        return None
    if len(cls.method_call_targets) == 0:
        return None
    # 매우 러프한 지표: methods 대비 호출 타겟 비율
    if len(cls.method_call_targets) >= len(cls.methods) // 2:
        return len(cls.method_call_targets)
    return None


def _check_middleman_chain(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """middleman_chain: middleman 클래스가 선형 체인으로 연결 (heuristic, 기본 disabled).

    P5 스텁 — 실제 체인 탐지는 P7로 연기. 현재는 항상 None 반환.
    """
    return None


def _check_god_class(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """God class: methods + fields 합계가 임계(god_class_size) 초과.

    단일 차원 임계 — 복합 조건(methods AND fields)은 Strategy/Visitor 등
    패턴에서 오탐 가능. 단일 합계는 "클래스가 단순히 너무 크다" 판정에 집중.
    """
    size = len(cls.methods) + len(cls.fields)
    limit = int(thresholds["god_class_size"])
    return size if size > limit else None


def _check_inappropriate_intimacy(
    graph: ProjectGraph, cls: ClassNode, thresholds: dict[str, float]
) -> int | None:
    """Inappropriate Intimacy: 두 클래스 간 양방향 compose+call 결합.

    상속은 제외 (parent-child 의도된 결합). 중복 방지를 위해 사전순 낮은 쪽에서만
    finding 생성 — value는 양방향 파트너 수. Observer/Visitor 같은 단방향
    interface 경유 결합은 이 rule을 발동하지 않음 (efferent는 해소된 참조만).
    """
    qn = cls.qualified_name
    parents_in_graph = {p for p in cls.parents if p in graph.classes}
    my_deps = graph.efferent(qn) - parents_in_graph
    intimate = 0
    for other_qn in my_deps:
        if qn >= other_qn:  # 사전순 낮은 쪽에서만 emit
            continue
        other = graph.classes.get(other_qn)
        if other is None:
            continue
        other_parents_in_graph = {p for p in other.parents if p in graph.classes}
        other_deps = graph.efferent(other_qn) - other_parents_in_graph
        if qn in other_deps:
            intimate += 1
    return intimate if intimate > 0 else None


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼 — Finding 생성
# ─────────────────────────────────────────────────────────────

_SUGGESTION_MAP: dict[str, str] = {
    RULE_DIT_HIGH: (
        "상속 깊이 {{value}}단 — Fragile Base Class 리스크."
        " 상속 축 분해 or 컴포지션 대체 검토 (참조: C++ Core Guidelines C.120)"
    ),
    RULE_NOC_HIGH: (
        "자식 클래스 {{value}}개 — 책임 집중 징후."
        " concrete 베이스에 과도한 파생 여부 판별"
    ),
    RULE_THIN_CLASS: (
        "껍데기 클래스 — 책임 부족이 설계 분해 과다의 신호인지,"
        " 의도된 경량 타입인지 판별"
    ),
    RULE_SPECULATIVE: (
        "추상 인터페이스에 구현체·참조자 부재 — 미래 대비 추상화가 실제 필요한지 재검토"
    ),
    RULE_CA_HIGH: (
        "피의존 {{value}}건 — 변경 파급 범위 큼."
        " 인터페이스 분리 or stability(A=1) 승급 검토"
    ),
    RULE_CE_HIGH: (
        "의존 {{value}}건 — 책임 분산 과다 징후."
        " 한 클래스가 너무 많은 협력자에 결합됐는지 판별"
    ),
    RULE_ZONE_OF_PAIN: (
        "Zone of Pain — concrete 클래스인데 피의존 {{value}}건."
        " 추상화(interface 도입) 없이 변경 시 광범위 영향. 리팩터 우선순위 높음"
    ),
    RULE_CLASS_CYCLE: (
        "순환 의존 그룹({{value}}개 클래스) 멤버 — 테스트/변경 단위가 그룹 전체로 커짐."
        " 엣지 방향 재설계 or DIP 적용 검토"
    ),
    RULE_DEAD_CLASS: (
        "사용처·자식 없음 — 삭제 후보."
        " 외부 export / test-only / 동적 로드 여부 확인"
    ),
    RULE_MIDDLEMAN: (
        "위임 중심 클래스 (heuristic) — 래퍼 가치 재검토."
        " 실제 추가 가치(경계 번역·lifecycle 관리)가 있는지 판별"
    ),
    RULE_GOD_CLASS: (
        "규모 과다 (methods+fields {{value}}개) — 책임 집중 징후."
        " 단일 책임 축으로 3분할 후보 식별 (도메인 축 / lifecycle 축 / 상태-행위 축)"
    ),
    RULE_INAPPROPRIATE_INTIMACY: (
        "양방향 결합 {{value}}쌍 — 두 클래스가 서로를 compose/call 함."
        " 인터페이스 분리로 단방향화 또는 공통 상위 타입으로 중재 검토"
    ),
}


# 수치 초과(value > limit) 성격 rule — message에 수치 표기
_NUMERIC_RULES = frozenset({
    RULE_DIT_HIGH, RULE_NOC_HIGH,
    RULE_CA_HIGH, RULE_CE_HIGH, RULE_ZONE_OF_PAIN,
    RULE_GOD_CLASS,
})


def _finding_message(rule_name: str, value: int, limit: int, qn: str) -> str:
    """rule 성격에 따라 finding message 문자열 반환."""
    if rule_name in _NUMERIC_RULES:
        return f"{rule_name} signal: {value} exceeds threshold {limit}"
    if rule_name == RULE_CLASS_CYCLE:
        return f"{rule_name} signal: {qn} in cycle of {value} classes"
    if rule_name == RULE_INAPPROPRIATE_INTIMACY:
        return f"{rule_name} signal: {qn} bidirectional with {value} other class(es)"
    # thin_class / speculative / dead_class / middleman: 플래그 성격
    return f"{rule_name} signal: {qn}"


def _make_finding(
    rule_name: str,
    severity: str,
    cls: ClassNode,
    value: int,
    limit: int,
) -> Finding:
    """메트릭 Finding 생성. type="metric", tool="" 고정.

    설계 근거: docs/metrics-plan.md §1.2
    """
    suggestion = _SUGGESTION_MAP.get(rule_name, "").replace("{{value}}", str(value))
    message = _finding_message(rule_name, value, limit, cls.qualified_name)
    return Finding(
        type=FT_METRIC,
        severity=severity,
        file=cls.file,
        message=message,
        rule=rule_name,
        symbol=cls.qualified_name,
        value=int(value),
        limit=int(limit),
        confidence=CONF_HIGH,
        suggestion=suggestion,
        lines_hint=str(cls.line),
        tool="",  # rapp_review에서 주입
    )


# ── rule 체크 함수 레지스트리 ──
# (rule_id → (check_fn, limit_key))
# limit_key가 None인 경우 limit=0 (플래그 성격 rule)

_RULE_REGISTRY: list[tuple[str, object, str | None]] = [
    (RULE_DIT_HIGH,         _check_class_dit_high,        "class_DIT"),
    (RULE_NOC_HIGH,         _check_class_noc_high,        "class_NOC_concrete"),
    (RULE_ABSTRACTNESS_LOW, _check_abstractness_low,      None),
    (RULE_THIN_CLASS,       _check_thin_class,            None),
    (RULE_SPECULATIVE,      _check_speculative_generality, None),
    # P5
    (RULE_CA_HIGH,          _check_class_ca_high,         "class_Ca"),
    (RULE_CE_HIGH,          _check_class_ce_high,         "class_Ce"),
    (RULE_ZONE_OF_PAIN,     _check_zone_of_pain,          "class_Ca"),
    (RULE_CLASS_CYCLE,      _check_class_cycle,           None),
    (RULE_DEAD_CLASS,       _check_dead_class,            None),
    (RULE_MIDDLEMAN,        _check_middleman,             None),
    (RULE_MIDDLEMAN_CHAIN,  _check_middleman_chain,       None),
    # C 축소판
    (RULE_GOD_CLASS,             _check_god_class,                "god_class_size"),
    (RULE_INAPPROPRIATE_INTIMACY, _check_inappropriate_intimacy,  None),
]


# ─────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────

def _check_cls_all_rules(
    graph: ProjectGraph,
    cls: ClassNode,
    thresholds: dict[str, float],
    rules: dict[str, dict],
) -> list[Finding]:
    """단일 클래스에 모든 활성 rule 적용 → Finding 목록 반환."""
    findings: list[Finding] = []
    for rule_id, check_fn, limit_key in _RULE_REGISTRY:
        rule_meta = rules.get(rule_id, {})
        if not rule_meta.get(_CK_ENABLED, False):
            continue
        severity = rule_meta.get(_CK_SEVERITY, SEV_MINOR)
        limit = int(thresholds[limit_key]) if limit_key else 0
        value = check_fn(graph, cls, thresholds)  # type: ignore[operator]
        if value is not None:
            findings.append(_make_finding(rule_id, severity, cls, value, limit))
    return findings


def run_all(
    target: Path,
    graph: ProjectGraph,
    hc_cfg: dict,
) -> list[Finding]:
    """모든 활성 메트릭 rule을 전체 클래스에 적용 → Finding 목록 반환.

    정렬은 호출자(rapp_review) 책임. graph.classes가 비면 빈 리스트 반환.
    설계 근거: docs/metrics-plan.md §3.1, §7.1
    """
    if not graph.classes:
        return []
    enabled, thresholds, rules = _load_metrics_config(hc_cfg)
    if not enabled:
        return []
    findings: list[Finding] = []
    for cls in graph.classes.values():
        findings.extend(_check_cls_all_rules(graph, cls, thresholds, rules))
    return findings
