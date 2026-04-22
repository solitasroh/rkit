"""분석 결과 캐시 — 파일 단위 findings 캐싱.

역할:
- 파일 내용 해시 기반 증분 분석 (SonarQube 방식)
- context_hash로 전역 무효화 (tool/grammar/config 변경 감지)
- patterns.py, hard_check.py 공용 (별도 캐시 파일)

원칙:
- 캐시는 최적화이지 의존성이 아님 (손상 시 전체 재분석)
- 원자적 저장 (tmp + os.replace)
- 저장 실패는 경고 강등 (분석 결과 반환 막지 않음)

설계 근거: docs/patterns-e4-incremental-design.md §1, §3, §6
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.metadata
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = str(Path(__file__).parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
from encoding import (  # noqa: E402  -- setup_utf8_io 부작용 + I/O 래퍼
    iter_file_bytes, read_text_utf8, safe_print, write_bytes_atomic,
)
from models import CACHE_SCHEMA_VERSION, Finding  # noqa: E402

# ─────────────────────────────────────────────────────────────
# 상수 (JSON 스키마 키 + 내부 상수)
# ─────────────────────────────────────────────────────────────

# 루트 레벨 JSON 키
_JK_SCHEMA_VERSION = "schema_version"
_JK_CONTEXT_HASH = "context_hash"
_JK_CREATED_AT = "created_at"
_JK_UPDATED_AT = "updated_at"
_JK_ENTRIES = "entries"

# 엔트리 레벨 JSON 키
_EK_CONTENT_HASH = "content_hash"
_EK_SIZE = "size"
_EK_FINDINGS = "findings"
_EK_SUPPRESSED = "suppressed"
_EK_PARSE_FAILED = "parse_failed"
_EK_FINGERPRINTS = "fingerprints"

# FunctionFingerprint JSON 키
_FK_FUNC_NAME = "func_name"
_FK_LINE = "line"
_FK_HASH = "fp_hash"
_FK_STMT_COUNT = "stmt_count"
_FK_INLINE_SUPPRESSED = "inline_suppressed"

# SuppressedFinding JSON 키
_SK_FINDING = "finding"
_SK_LEVEL = "level"
_SK_REASON = "reason"

# 해시 접두사. iter_file_bytes가 chunk 크기를 담당.
_HASH_PREFIX = "sha256:"

# tree-sitter 패키지 (grammar_version용)
_GRAMMAR_PKG = "tree-sitter-cpp"
_GRAMMAR_UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────
# 해시 계산
# ─────────────────────────────────────────────────────────────

def file_content_hash(path: Path) -> str:
    """파일 SHA-256 해시. 'sha256:' 접두사 포함.

    encoding.iter_file_bytes 사용으로 대용량 파일도 고정 메모리 처리.
    호출자가 OSError를 처리해야 함.
    """
    h = hashlib.sha256()
    for chunk in iter_file_bytes(path):
        h.update(chunk)
    return f"{_HASH_PREFIX}{h.hexdigest()}"


def context_hash(**kwargs: Any) -> str:
    """분석 컨텍스트 해시. kwargs를 JSON 직렬화 후 SHA-256.

    sort_keys=True로 중첩 dict의 key 순서 무관성 보장.
    분석 결과에 영향을 주는 모든 외부 요인을 단일 해시로 결합(§1.4).
    """
    payload = json.dumps(kwargs, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def grammar_version() -> str:
    """tree-sitter-cpp 패키지 버전.

    패키지 업데이트로 AST가 바뀌면 캐시 전역 무효화(§1.4 A3).
    미설치/조회 실패 시 'unknown' — 캐시 무효화 기준으로 의미 있는 값 유지.
    """
    try:
        return importlib.metadata.version(_GRAMMAR_PKG)
    except importlib.metadata.PackageNotFoundError:
        return _GRAMMAR_UNKNOWN


# ─────────────────────────────────────────────────────────────
# 데이터 모델
# ─────────────────────────────────────────────────────────────

@dataclass
class SuppressedFinding:
    """억제된 Finding + 감사 정보.

    캐시 적중 시 waivers.log 재기록에 사용(§4.2 A4).
    - level: WAIVER_INLINE | WAIVER_IGNORE | WAIVER_CONFIG
    - reason: 억제 사유 (빈 문자열 허용)
    """
    finding: Finding
    level: str
    reason: str


@dataclass
class FunctionFingerprint:
    """함수 단위 AST 구조 fingerprint. CacheEntry에 저장.

    D1 중복 탐지용. Pass 1에서 생성, Pass 2에서 cross-file 비교.
    설계: docs/patterns-d1-duplicate-design.md §4.1
    """
    func_name: str          # 함수명 (보고용). 소멸자는 "~ClassName".
    line: int               # 함수 시작 줄 (1-based)
    fp_hash: str            # 정규화된 AST SHA-256 hex digest
    stmt_count: int         # 본문 직계 문장 수 (크기 필터용)
    inline_suppressed: bool = False  # NOPATTERN(DUP-01)로 억제됨


@dataclass
class CacheEntry:
    """단일 파일의 캐시 항목.

    - findings: post-suppression + pre-CLI-filter(A2) 상태
    - suppressed: 감사 로그 재기록용 (hard_check는 빈 리스트)
    - parse_failed=True: 파싱 실패 마커. content_hash만 의미 있음(§6.4)
    - fingerprints: D1 함수별 fingerprint (빈 리스트이면 D1 비활성 또는 함수 없음)
    """
    content_hash: str
    size: int
    findings: list[Finding] = field(default_factory=list)
    suppressed: list[SuppressedFinding] = field(default_factory=list)
    parse_failed: bool = False
    fingerprints: list[FunctionFingerprint] = field(default_factory=list)


@dataclass
class CacheStats:
    """캐시 사용 통계. 보고 + 로깅용."""
    hits: int = 0
    misses: int = 0
    global_invalidation: bool = False
    entries_before: int = 0
    entries_after: int = 0


@dataclass
class CacheOpts:
    """캐시 활성화 여부 + 파일 경로(§1.5).

    enabled=False면 AnalysisCache 생성 안 함 → 기존 동작(캐시 미사용).
    patterns.py, hard_check.py 공용.
    """
    enabled: bool = False
    path: Path | None = None

    @classmethod
    def disabled(cls) -> "CacheOpts":
        return cls(enabled=False, path=None)


# ─────────────────────────────────────────────────────────────
# 직렬화 (forward-compat: 모르는 필드 무시)
# ─────────────────────────────────────────────────────────────

# Finding dataclass의 알려진 필드 목록 — 로드 시 미지 필드 필터링용
_FINDING_FIELDS = {f.name for f in dataclasses.fields(Finding)}


def _finding_from_dict(d: dict) -> Finding:
    """dict → Finding. 모르는 필드는 무시(forward compat §1.2)."""
    return Finding(**{k: v for k, v in d.items() if k in _FINDING_FIELDS})


def _suppressed_from_dict(d: dict) -> SuppressedFinding:
    """dict → SuppressedFinding. 내부 finding도 forward-compat 처리."""
    inner = d.get(_SK_FINDING, {})
    if not isinstance(inner, dict):
        inner = {}
    return SuppressedFinding(
        finding=_finding_from_dict(inner),
        level=str(d.get(_SK_LEVEL, "")),
        reason=str(d.get(_SK_REASON, "")),
    )


def _suppressed_to_dict(sf: SuppressedFinding) -> dict:
    """SuppressedFinding → JSON-직렬화 가능 dict."""
    return {
        _SK_FINDING: dataclasses.asdict(sf.finding),
        _SK_LEVEL: sf.level,
        _SK_REASON: sf.reason,
    }


def _fingerprint_from_dict(d: dict) -> FunctionFingerprint:
    """dict → FunctionFingerprint. forward-compat: 모르는 필드 무시."""
    return FunctionFingerprint(
        func_name=str(d.get(_FK_FUNC_NAME, "")),
        line=int(d.get(_FK_LINE, 0)),
        fp_hash=str(d.get(_FK_HASH, "")),
        stmt_count=int(d.get(_FK_STMT_COUNT, 0)),
        inline_suppressed=bool(d.get(_FK_INLINE_SUPPRESSED, False)),
    )


def _fingerprint_to_dict(fp: FunctionFingerprint) -> dict:
    """FunctionFingerprint → JSON-직렬화 가능 dict."""
    return {
        _FK_FUNC_NAME: fp.func_name,
        _FK_LINE: fp.line,
        _FK_HASH: fp.fp_hash,
        _FK_STMT_COUNT: fp.stmt_count,
        _FK_INLINE_SUPPRESSED: fp.inline_suppressed,
    }


def _entry_from_dict(d: dict) -> CacheEntry:
    """dict → CacheEntry. 모르는 필드 무시. 개별 필드 타입 오류는 예외 전파."""
    return CacheEntry(
        content_hash=str(d.get(_EK_CONTENT_HASH, "")),
        size=int(d.get(_EK_SIZE, 0)),
        findings=[_finding_from_dict(x) for x in d.get(_EK_FINDINGS, [])
                  if isinstance(x, dict)],
        suppressed=[_suppressed_from_dict(x) for x in d.get(_EK_SUPPRESSED, [])
                    if isinstance(x, dict)],
        parse_failed=bool(d.get(_EK_PARSE_FAILED, False)),
        fingerprints=[_fingerprint_from_dict(x) for x in d.get(_EK_FINGERPRINTS, [])
                      if isinstance(x, dict)],
    )


def _entry_to_dict(e: CacheEntry) -> dict:
    """CacheEntry → JSON-직렬화 가능 dict."""
    return {
        _EK_CONTENT_HASH: e.content_hash,
        _EK_SIZE: e.size,
        _EK_FINDINGS: [dataclasses.asdict(f) for f in e.findings],
        _EK_SUPPRESSED: [_suppressed_to_dict(sf) for sf in e.suppressed],
        _EK_PARSE_FAILED: e.parse_failed,
        _EK_FINGERPRINTS: [_fingerprint_to_dict(fp) for fp in e.fingerprints],
    }


# ─────────────────────────────────────────────────────────────
# AnalysisCache
# ─────────────────────────────────────────────────────────────

class AnalysisCache:
    """파일 단위 분석 결과 캐시.

    초기화 시 캐시 파일 로드. context_hash 불일치 시 빈 캐시로 시작
    (전역 무효화 통계 기록). lookup/update로 접근, save로 저장.

    동시 실행: 락 없음. 원자적 저장(tmp + os.replace)으로 부분 쓰기 방지.
    Windows에서 PermissionError 등 저장 실패는 경고 강등(§6.2 B7).
    """

    def __init__(self, cache_path: Path, current_context_hash: str) -> None:
        """캐시 파일 로드. 없거나 손상되면 빈 캐시로 시작."""
        self._path = cache_path
        self._context_hash = current_context_hash
        self._entries: dict[str, CacheEntry] = {}
        # 이번 실행에서 접근된 rel_path 집합 (prune_unseen용)
        self._seen: set[str] = set()
        self._stats = CacheStats()
        self._load()

    def _read_cache_json(self) -> dict | None:
        """캐시 파일 읽기 + JSON 파싱. 실패 시 경고 + None + 전역무효화 플래그."""
        try:
            data = json.loads(read_text_utf8(self._path))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            safe_print(
                f"경고: 캐시 파일 손상 ({self._path}): {e} — 빈 캐시로 시작",
                file=sys.stderr)
            self._stats.global_invalidation = True
            return None
        if not isinstance(data, dict):
            safe_print(
                f"경고: 캐시 파일 형식 오류 ({self._path}) — 빈 캐시로 시작",
                file=sys.stderr)
            self._stats.global_invalidation = True
            return None
        return data

    def _header_valid(self, data: dict) -> bool:
        """schema_version + context_hash 검증. 불일치 시 전역 무효화.

        §6.1 정책:
          - schema_version 불일치 → stderr 경고 (포맷 의미가 다를 수 있음).
          - context_hash 불일치  → 경고 없이 플래그만 (일상 업데이트 이벤트).
        """
        found_schema = data.get(_JK_SCHEMA_VERSION)
        if found_schema != CACHE_SCHEMA_VERSION:
            safe_print(
                f"경고: 캐시 schema_version 불일치 "
                f"({found_schema!r} != {CACHE_SCHEMA_VERSION!r}) — "
                f"빈 캐시로 시작",
                file=sys.stderr)
            self._stats.global_invalidation = True
            return False
        if data.get(_JK_CONTEXT_HASH) != self._context_hash:
            self._stats.global_invalidation = True
            return False
        return True

    def _load_entries(self, entries: Any) -> None:
        """entries dict을 _entries에 적재. 개별 손상은 건너뛰고 계속."""
        if not isinstance(entries, dict):
            self._stats.global_invalidation = True
            return
        for rel, entry_dict in entries.items():
            if not isinstance(entry_dict, dict):
                continue
            try:
                self._entries[rel] = _entry_from_dict(entry_dict)
            except (TypeError, ValueError):
                continue
        self._stats.entries_before = len(self._entries)

    def _load(self) -> None:
        """캐시 파일 로드. 실패/불일치 시 전역 무효화 플래그만 설정."""
        if not self._path.is_file():
            return
        data = self._read_cache_json()
        if data is None or not self._header_valid(data):
            return
        self._load_entries(data.get(_JK_ENTRIES, {}))

    def _entry_matches(self, entry: CacheEntry, file_path: Path) -> bool:
        """size + content_hash로 엔트리 유효성 확인. I/O 실패는 불일치로 간주."""
        try:
            if file_path.stat().st_size != entry.size:
                return False
            return file_content_hash(file_path) == entry.content_hash
        except OSError:
            return False

    def lookup(self, rel_path: str, file_path: Path) -> CacheEntry | None:
        """캐시 조회. size 조기 탈락 → content_hash 비교.

        적중: CacheEntry 반환 + stats.hits 증가.
        미스(엔트리 없음/size 불일치/hash 불일치/I/O 오류): None + stats.misses 증가.
        호출 여부와 무관하게 rel_path를 seen에 기록(prune_unseen용).
        """
        self._seen.add(rel_path)
        entry = self._entries.get(rel_path)
        if entry is None or not self._entry_matches(entry, file_path):
            self._stats.misses += 1
            return None
        self._stats.hits += 1
        return entry

    def update(self, rel_path: str, entry: CacheEntry) -> None:
        """캐시 항목 추가/갱신. rel_path를 seen에 기록."""
        self._entries[rel_path] = entry
        self._seen.add(rel_path)

    def prune_unseen(self) -> int:
        """이번 실행에서 lookup/update 안 된 엔트리 제거. 제거 개수 반환.

        전체 분석 모드에서 분석 후 호출(§6.5). diff 모드에서는 호출하지 않음
        (미변경 파일이 seen에 없어 사라지면 다음 실행 캐시 적중률이 무너짐).
        """
        stale = set(self._entries) - self._seen
        for key in stale:
            del self._entries[key]
        return len(stale)

    def _build_save_payload(self) -> dict:
        """저장용 JSON 페이로드 구성."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return {
            _JK_SCHEMA_VERSION: CACHE_SCHEMA_VERSION,
            _JK_CONTEXT_HASH: self._context_hash,
            _JK_CREATED_AT: now,
            _JK_UPDATED_AT: now,
            _JK_ENTRIES: {
                rel: _entry_to_dict(e) for rel, e in self._entries.items()
            },
        }

    def save(self) -> None:
        """캐시를 파일로 원자적 저장(encoding.write_bytes_atomic 경유).

        저장 실패는 경고로 강등(§6.2 B7) — 분석 결과 반환을 막지 않음.
        tmp 정리 및 디렉토리 생성은 write_bytes_atomic이 담당.
        """
        self._stats.entries_after = len(self._entries)
        payload = json.dumps(
            self._build_save_payload(), ensure_ascii=False, indent=2,
        ).encode("utf-8")
        try:
            write_bytes_atomic(self._path, payload)
        except OSError as e:
            safe_print(
                f"경고: 캐시 저장 실패 ({self._path}): {e}. "
                "분석 결과는 정상 반환.",
                file=sys.stderr)

    @property
    def stats(self) -> CacheStats:
        return self._stats

    @property
    def context_hash_value(self) -> str:
        return self._context_hash

    @property
    def path(self) -> Path:
        return self._path
