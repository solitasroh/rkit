"""rapp-review 스킬 전용 config 스키마 검증·기본값.

project-config.json의 `review` 섹션을 안전하게 로드한다.
타입/값 오류 시 stderr 경고 + 기본값 사용 (기존 _validate_thresholds 패턴과 동일).

leaf 모듈: encoding만 import. models/hard_check에 의존하지 않음.

설계 근거: docs/rapp-review-plan.md §단계 1
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from encoding import safe_print

# ── 기본값 상수 ──
DEFAULT_TARGET = "src"
DEFAULT_SUBDIR_FORMAT = "%Y%m%d-%H%M%S"
DEFAULT_KEEP_LATEST_SYMLINK = True
DEFAULT_RETENTION = 10
DEFAULT_GROUP_BY = "severity"
DEFAULT_SPLIT_BY_LAYER = False

# ── retention 상한: 디렉토리 개수가 현실적 수준을 넘으면 오탈자 가능성 ↑ ──
MAX_RETENTION = 10_000

# ── subdir_format 금지 문자: 경로 traversal / 분리자 방지 ──
# strftime 결과가 단일 디렉토리명이 되어야 하므로 '/', '\\', '..' 거부.
_FORBIDDEN_SUBDIR_TOKENS = ("/", "\\", "..")

# ── 허용값 ──
GROUP_BY_SEVERITY = "severity"
GROUP_BY_FILE = "file"
GROUP_BY_LAYER = "layer"
VALID_GROUP_BY = (GROUP_BY_SEVERITY, GROUP_BY_FILE, GROUP_BY_LAYER)

# ── config 섹션 키 ──
_CK_REVIEW = "review"
_CK_DEFAULT_TARGET = "default_target"
_CK_OUTPUT = "output"
_CK_SUBDIR_FORMAT = "subdir_format"
_CK_KEEP_LATEST_SYMLINK = "keep_latest_symlink"
_CK_RETENTION = "retention"
_CK_RENDER = "render"
_CK_GROUP_BY = "group_by"
_CK_SPLIT_BY_LAYER = "split_by_layer"


@dataclass(frozen=True)
class ReviewConfig:
    """review 섹션 정규화 결과. 항상 유효값 보장."""
    default_target: str
    subdir_format: str
    keep_latest_symlink: bool
    retention: int
    group_by: str
    split_by_layer: bool


def load_review_config(config: dict[str, Any] | None) -> ReviewConfig:
    """project-config.json의 review 섹션을 검증해 ReviewConfig 반환.

    config가 None이거나 review 키 없거나 타입 불일치면 전부 기본값.
    개별 필드 타입/값 오류 시 stderr 경고 + 해당 필드만 기본값.
    """
    section = _dict_or_empty(config, _CK_REVIEW) if isinstance(config, dict) else {}
    output = _dict_or_empty(section, _CK_OUTPUT)
    render = _dict_or_empty(section, _CK_RENDER)
    return _build_review_config(section, output, render)


def _dict_or_empty(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    return value if isinstance(value, dict) else {}


def _build_review_config(
    section: dict[str, Any],
    output: dict[str, Any],
    render: dict[str, Any],
) -> ReviewConfig:
    kp = _CK_REVIEW
    kpo = f"{_CK_REVIEW}.{_CK_OUTPUT}"
    kpr = f"{_CK_REVIEW}.{_CK_RENDER}"
    return ReviewConfig(
        default_target=_str_or_default(
            section.get(_CK_DEFAULT_TARGET), DEFAULT_TARGET, f"{kp}.{_CK_DEFAULT_TARGET}"),
        subdir_format=_subdir_format_or_default(
            output.get(_CK_SUBDIR_FORMAT), DEFAULT_SUBDIR_FORMAT, f"{kpo}.{_CK_SUBDIR_FORMAT}"),
        keep_latest_symlink=_bool_or_default(
            output.get(_CK_KEEP_LATEST_SYMLINK), DEFAULT_KEEP_LATEST_SYMLINK,
            f"{kpo}.{_CK_KEEP_LATEST_SYMLINK}"),
        retention=_positive_int_or_default(
            output.get(_CK_RETENTION), DEFAULT_RETENTION, f"{kpo}.{_CK_RETENTION}",
            max_value=MAX_RETENTION),
        group_by=_enum_or_default(
            render.get(_CK_GROUP_BY), VALID_GROUP_BY, DEFAULT_GROUP_BY,
            f"{kpr}.{_CK_GROUP_BY}"),
        split_by_layer=_bool_or_default(
            render.get(_CK_SPLIT_BY_LAYER), DEFAULT_SPLIT_BY_LAYER,
            f"{kpr}.{_CK_SPLIT_BY_LAYER}"),
    )


def _str_or_default(value: Any, default: str, key: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        safe_print(
            f"경고: {key} 값 {value!r} 이 비어있지 않은 문자열이 아님, 기본값 {default!r} 사용",
            file=sys.stderr,
        )
        return default
    return value


def _bool_or_default(value: Any, default: bool, key: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        safe_print(
            f"경고: {key} 값 {value!r} 이 bool이 아님, 기본값 {default} 사용",
            file=sys.stderr,
        )
        return default
    return value


def _positive_int_or_default(
    value: Any, default: int, key: str, max_value: int | None = None,
) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        # bool은 int의 서브클래스이므로 명시 거부
        safe_print(f"경고: {key} 값 {value!r} 이 bool임(int 필요), 기본값 {default} 사용", file=sys.stderr)
        return default
    try:
        v = int(value)
    except (TypeError, ValueError):
        safe_print(f"경고: {key} 값 {value!r} 이 정수가 아님, 기본값 {default} 사용", file=sys.stderr)
        return default
    if v < 1:
        safe_print(f"경고: {key} 값 {v} 는 1 이상이어야 함, 기본값 {default} 사용", file=sys.stderr)
        return default
    if max_value is not None and v > max_value:
        safe_print(f"경고: {key} 값 {v} 가 상한 {max_value} 초과, 기본값 {default} 사용", file=sys.stderr)
        return default
    return v


def _subdir_format_or_default(value: Any, default: str, key: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        safe_print(
            f"경고: {key} 값 {value!r} 이 비어있지 않은 문자열이 아님, 기본값 {default!r} 사용",
            file=sys.stderr,
        )
        return default
    for bad in _FORBIDDEN_SUBDIR_TOKENS:
        if bad in value:
            safe_print(
                f"경고: {key} 값 {value!r} 에 금지 토큰 {bad!r} 포함(경로 분리자/traversal), "
                f"기본값 {default!r} 사용",
                file=sys.stderr,
            )
            return default
    try:
        datetime.now().strftime(value)
    except (ValueError, TypeError) as e:
        safe_print(
            f"경고: {key} 값 {value!r} 의 strftime 포맷 오류({e}), 기본값 {default!r} 사용",
            file=sys.stderr,
        )
        return default
    return value


def _enum_or_default(value: Any, valid: tuple[str, ...], default: str, key: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or value not in valid:
        safe_print(
            f"경고: {key} 값 {value!r} 이 허용값 {valid} 중 하나가 아님, 기본값 {default!r} 사용",
            file=sys.stderr,
        )
        return default
    return value
