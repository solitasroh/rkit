"""인코딩 헬퍼 — 모든 파일 I/O + 콘솔 출력의 단일 진입점.

크로스플랫폼 (Windows/WSL/PowerShell)에서 발생하는 문제들을 해결:
- C++ 소스의 인코딩 혼재 (UTF-8/CP949/EUC-KR/UTF-16)
- Windows 콘솔 한글 깨짐 (cp949 기본)
- 경로에 포함된 한글 (예: "05.하네스")
- Python subprocess에서 UTF-8 강제

**이 모듈을 import만 해도 stdout/stderr가 UTF-8로 자동 전환된다.**
별도 setup 호출 불요. 모든 스크립트는 가장 먼저 이 모듈을 import하면 됨.

핵심 원칙:
- 읽기: 인코딩 자동 감지, 실패 시 명시적 에러 (errors='replace' 금지)
- 쓰기: 항상 UTF-8, LF 줄바꿈
- tree-sitter용: 원본 바이트 오프셋 보존 경로 별도 제공
- 콘솔: UTF-8 강제, 깨지는 문자는 replace (런타임 에러 방지)

설계 근거: docs/v3-redesign.md §8
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any, Iterator, Union

try:
    import chardet
except ImportError:
    chardet = None  # type: ignore

PathLike = Union[str, Path]


# ─────────────────────────────────────────────────────────────
# stdout/stderr UTF-8 설정 (Windows 콘솔 한글 깨짐 방지)
# ─────────────────────────────────────────────────────────────

_IO_SETUP_DONE = False


def setup_utf8_io() -> None:
    """stdin/stdout/stderr를 UTF-8로 재설정.

    모듈 import 시 자동 호출됨. 여러 번 호출해도 안전 (idempotent).
    subprocess로 자식 Python 프로세스에 이 설정을 전파하려면
    subprocess_env()를 사용할 것.
    """
    global _IO_SETUP_DONE
    if _IO_SETUP_DONE:
        return

    def _wrap(stream):
        if not hasattr(stream, "buffer"):
            return stream
        # detach()로 기존 TextIOWrapper에서 buffer를 분리.
        # 이후 기존 wrapper는 buffer 참조 없이 GC되어 이중 flush/close 방지.
        try:
            buf = stream.detach()
        except (AttributeError, io.UnsupportedOperation):
            buf = stream.buffer  # detach 불가하면 공유 참조 (CPython에선 안전)
        return io.TextIOWrapper(
            buf, encoding="utf-8", errors="replace", line_buffering=True,
        )

    # stdin은 errors="strict" — 입력 데이터 손실을 조기 감지해야 함
    # (stdout/stderr는 "replace" — 출력 실패로 프로세스가 죽으면 안 됨)
    def _wrap_stdin(stream):
        if not hasattr(stream, "buffer"):
            return stream
        try:
            buf = stream.detach()
        except (AttributeError, io.UnsupportedOperation):
            buf = stream.buffer
        return io.TextIOWrapper(
            buf, encoding="utf-8", errors="strict", line_buffering=False,
        )

    sys.stdin = _wrap_stdin(sys.stdin)
    sys.stdout = _wrap(sys.stdout)
    sys.stderr = _wrap(sys.stderr)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _IO_SETUP_DONE = True


def safe_print(*args: Any, file=None, **kwargs: Any) -> None:
    """콘솔/파일 출력 시 인코딩 에러 없음을 보장.

    sys.stdout이 이미 UTF-8로 설정되어 있어도, 외부 코드가 sys.stdout을
    재지정한 경우를 대비한 최종 안전장치. 한글 경로, 이모지 등 모두 안전.
    """
    target = file if file is not None else sys.stdout
    # 객체를 문자열로 수동 변환 (print의 내부 변환 대신 명시적으로)
    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    text = sep.join(str(a) for a in args) + end
    try:
        target.write(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # 최악의 경우 — 바이트 레벨로 강제 쓰기
        data = text.encode("utf-8", errors="replace")
        if hasattr(target, "buffer"):
            target.buffer.write(data)
        else:
            # buffer 없으면 ASCII 폴백
            target.write(text.encode("ascii", errors="replace").decode("ascii"))
    if kwargs.get("flush"):
        target.flush()


def subprocess_env(extra: dict | None = None) -> dict:
    """subprocess 호출 시 사용할 환경변수. UTF-8 강제.

    Example:
        result = subprocess.run(cmd, env=subprocess_env(), ...)
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"  # Python 3.7+ UTF-8 모드
    if extra:
        env.update(extra)
    return env


# 모듈 로드 시 자동 setup
setup_utf8_io()


# ─────────────────────────────────────────────────────────────
# 읽기
# ─────────────────────────────────────────────────────────────

def _strip_bom(raw: bytes) -> tuple[bytes, str | None]:
    """BOM 감지 및 제거. (내용, 인코딩) 반환. BOM 없으면 인코딩은 None."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:], "utf-8"
    if raw.startswith(b"\xff\xfe\x00\x00"):
        return raw[4:], "utf-32-le"
    if raw.startswith(b"\x00\x00\xfe\xff"):
        return raw[4:], "utf-32-be"
    if raw.startswith(b"\xff\xfe"):
        return raw[2:], "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return raw[2:], "utf-16-be"
    return raw, None


# chardet 신뢰도 임계값. 이보다 낮으면 cp949 fallback.
# 짧은 파일/저ASCII 비율 파일에서 chardet이 엉뚱한 인코딩(koi8-t 등)을
# 낮은 confidence로 반환하는 오탐을 걸러낸다.
_CHARDET_MIN_CONFIDENCE = 0.5


def _detect_encoding(raw: bytes) -> str:
    """chardet로 인코딩 감지. 실패/낮은 신뢰도 시 cp949 가정 (한국어 프로젝트 기본)."""
    if chardet is None:
        return "cp949"
    detected = chardet.detect(raw)
    encoding = detected.get("encoding")
    confidence = detected.get("confidence", 0) or 0
    if not encoding or confidence < _CHARDET_MIN_CONFIDENCE:
        return "cp949"
    # chardet가 ascii라고 하면 UTF-8 호환 가정
    if encoding.lower() == "ascii":
        return "utf-8"
    return encoding


def _decode(raw: bytes, path: PathLike) -> tuple[str, str]:
    """바이트를 UTF-8 문자열로 디코딩. (text, resolved_encoding) 반환.

    BOM 우선 → UTF-8 시도 → chardet 감지 순. errors='strict' (무손실).
    BOM이 있어도 실패할 수 있으므로 (편집기가 BOM을 잘못 붙인 경우) fallback 보장.
    모든 경로 실패 시 경로 정보를 포함한 UnicodeDecodeError 발생.
    """
    raw, bom_encoding = _strip_bom(raw)

    # BOM 기반 확정 — 실패 시 다음 단계로 fallback
    if bom_encoding:
        try:
            return raw.decode(bom_encoding), bom_encoding
        except UnicodeDecodeError:
            pass  # BOM 신뢰 불가, chardet로 진행

    # UTF-8 먼저 시도
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    # chardet 감지 (confidence 낮으면 cp949 fallback)
    encoding = _detect_encoding(raw)
    try:
        return raw.decode(encoding), encoding
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            e.encoding, e.object, e.start, e.end,
            f"{path}: {encoding}로 디코딩 실패. 원본 인코딩 확인 필요."
        ) from e


def read_file(path: PathLike) -> str:
    """파일을 읽어 UTF-8 문자열로 반환. 인코딩 자동 감지.

    Raises:
        UnicodeDecodeError: 감지된 인코딩으로도 디코딩 실패 시.
                           (errors='replace' 금지 — 손실 변환 방지)
    """
    text, _ = _decode(Path(path).read_bytes(), path)
    return text


def read_file_utf8_bytes(path: PathLike) -> tuple[bytes, str]:
    """tree-sitter용. (UTF-8 바이트, 원본 인코딩) 반환.

    원본이 UTF-8이면 바이트 변환 없이 반환 → AST 오프셋이 원본과 일치.
    비-UTF-8은 strict decode 후 UTF-8로 재인코딩.
    """
    raw = Path(path).read_bytes()
    # UTF-8 무결성 먼저 확인 (변환 없이 반환 가능한지)
    stripped, bom_encoding = _strip_bom(raw)
    if bom_encoding in (None, "utf-8"):
        try:
            stripped.decode("utf-8")
            return stripped, "utf-8"
        except UnicodeDecodeError:
            pass

    # 비-UTF-8 → 변환 (공통 디코더 재사용)
    text, encoding = _decode(raw, path)
    return text.encode("utf-8"), encoding


# 스트리밍 읽기 chunk 크기 (SHA-256 블록 배수). 해시/체크섬 등 대용량 저오버헤드용.
_DEFAULT_CHUNK_SIZE = 65536


def iter_file_bytes(
    path: PathLike, chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> Iterator[bytes]:
    """파일을 chunk 단위 raw 바이트로 스트리밍. 인코딩 변환 없음.

    해시 계산, 체크섬, 바이너리 비교 등 대용량을 고정 메모리로 다루는 용도.
    호출자가 OSError를 처리해야 함(파일 부재/권한 오류).
    """
    with open(path, "rb") as f:  # noqa: E002 — encoding.py 내부(스킵 대상)
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


# UTF-8 BOM (편집기가 자동 추가하는 경우 허용 후 제거)
_UTF8_BOM = b"\xef\xbb\xbf"


def read_text_utf8(path: PathLike) -> str:
    """엄격 UTF-8 텍스트 읽기. auto-detect 없음.

    도구 내부 파일(캐시 JSON, 로그 등)처럼 UTF-8이 보장된 파일 전용.
    UTF-8 BOM은 허용 후 제거. 그 외 인코딩은 UnicodeDecodeError 전파.
    """
    raw = Path(path).read_bytes()
    if raw.startswith(_UTF8_BOM):
        raw = raw[len(_UTF8_BOM):]
    return raw.decode("utf-8")


# ─────────────────────────────────────────────────────────────
# 쓰기
# ─────────────────────────────────────────────────────────────

def write_file(path: PathLike, content: str) -> None:
    """UTF-8 + LF 줄바꿈으로 파일 저장. 디렉토리 자동 생성."""
    _write(path, content, mode="w")


def append_file(path: PathLike, content: str) -> None:
    """UTF-8 + LF 줄바꿈으로 파일 추가. 디렉토리 자동 생성."""
    _write(path, content, mode="a")


def _write(path: PathLike, content: str, mode: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # newline='\n': Windows에서도 LF로 저장 (Python이 \n을 \r\n으로 변환하지 않게)
    with open(p, mode, encoding="utf-8", newline="\n") as f:
        f.write(content)


# 원자적 저장의 임시 파일 접미사. 같은 볼륨 rename으로 POSIX/Windows 모두 원자적.
_ATOMIC_TMP_SUFFIX = ".tmp"


def write_bytes_atomic(path: PathLike, data: bytes) -> None:
    """tmp 파일에 쓰고 os.replace로 원자적 교체. 디렉토리 자동 생성.

    부분 쓰기/크래시로부터 기존 파일을 보호한다.
    OSError는 호출자에 전파(경고 강등 여부는 호출자 판단).
    같은 볼륨 내 rename이라 POSIX + Windows 모두 원자적.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + _ATOMIC_TMP_SUFFIX)
    try:
        tmp.write_bytes(data)  # noqa: E003 — encoding.py 내부(스킵 대상)
        os.replace(tmp, p)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


# ─────────────────────────────────────────────────────────────
# JSON config 로딩 공용 헬퍼
# ─────────────────────────────────────────────────────────────

def load_json_config(path: PathLike) -> dict | None:
    """JSON 파일을 읽어 dict로 반환. 실패 시 None + stderr 경고.

    공통 관심사: 파일 읽기 + JSON 파싱 + dict 타입 검증 + 에러 처리.
    hard_check.py, patterns.py 양쪽에서 사용.
    """
    import json
    try:
        raw = json.loads(read_file(path))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        safe_print(f"경고: config 로드 실패 ({path}): {e}", file=sys.stderr)
        return None
    if not isinstance(raw, dict):
        safe_print(f"경고: config 최상위가 dict가 아님 ({type(raw).__name__}) — {path}",
                   file=sys.stderr)
        return None
    return raw


# ─────────────────────────────────────────────────────────────
# 엔트리 포인트 (직접 실행 시 자가 테스트)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # setup_utf8_io()는 import 시점에 자동 호출됨

    # 자가 테스트
    import tempfile
    safe_print("encoding.py 자가 테스트")
    safe_print(f"  chardet: {'OK' if chardet else '미설치 (cp949 fallback)'}")
    safe_print(f"  stdin  인코딩: {sys.stdin.encoding}")
    safe_print(f"  stdout 인코딩: {sys.stdout.encoding}")
    safe_print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING')}")
    safe_print(f"  현재 경로 출력 테스트: {Path.cwd()} (✓)")

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".txt", delete=False
    ) as f:
        tmp = Path(f.name)

    try:
        # UTF-8 왕복
        write_file(tmp, "한글 테스트 αβγ\n두 번째 줄")
        assert read_file(tmp) == "한글 테스트 αβγ\n두 번째 줄"
        print("  UTF-8 왕복: OK")

        # UTF-8 바이트 (tree-sitter용)
        data, enc = read_file_utf8_bytes(tmp)
        assert enc == "utf-8"
        assert data.decode("utf-8") == "한글 테스트 αβγ\n두 번째 줄"
        print("  UTF-8 바이트 반환: OK")

        # CP949 쓰기 → 읽기
        tmp.write_bytes("한글".encode("cp949"))
        assert read_file(tmp) == "한글"
        print("  CP949 자동 감지: OK")

        # UTF-8 BOM
        tmp.write_bytes(b"\xef\xbb\xbf" + "BOM 포함".encode("utf-8"))
        assert read_file(tmp) == "BOM 포함"
        print("  UTF-8 BOM 제거: OK")

        # LF 저장 확인
        write_file(tmp, "line1\nline2")
        assert tmp.read_bytes() == b"line1\nline2"
        safe_print("  LF 저장: OK")

        # safe_print 이모지/특수문자
        safe_print("  safe_print: ✓ 한글 αβγ 🎉")

        # subprocess_env
        env = subprocess_env()
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert env["PYTHONUTF8"] == "1"
        safe_print("  subprocess_env: OK")

        # iter_file_bytes: 스트리밍
        write_file(tmp, "abc" * 10000)
        chunks = list(iter_file_bytes(tmp, chunk_size=1024))
        assert b"".join(chunks) == b"abc" * 10000
        safe_print("  iter_file_bytes: OK")

        # read_text_utf8: 엄격 UTF-8
        write_file(tmp, "한글 αβγ")
        assert read_text_utf8(tmp) == "한글 αβγ"
        safe_print("  read_text_utf8: OK")

        # read_text_utf8: BOM 허용
        tmp.write_bytes(b"\xef\xbb\xbf" + "BOM".encode("utf-8"))
        assert read_text_utf8(tmp) == "BOM"
        safe_print("  read_text_utf8 BOM: OK")

        # write_bytes_atomic: tmp 누출 없음
        write_bytes_atomic(tmp, b"atomic")
        assert tmp.read_bytes() == b"atomic"
        assert not tmp.with_name(tmp.name + ".tmp").exists()
        safe_print("  write_bytes_atomic: OK")

        safe_print("\n✓ 모든 테스트 통과")
    finally:
        tmp.unlink(missing_ok=True)
