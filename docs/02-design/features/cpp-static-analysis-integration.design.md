---
template: design
version: 1.2
feature: cpp-static-analysis-integration
date: 2026-04-22
author: pdm87
project: rkit
project-version: 0.9.13
---

# cpp-static-analysis-integration Design Document

> **Summary**: `rapp_review/` 러너의 rkit 플러그인 흡수 + `/code-review` 스킬에 자동 연결. 어댑터/metrics-json merge 없이 SKILL 본문 직접 Read 경로.
>
> **Project**: rkit
> **Version**: 0.9.13
> **Author**: pdm87
> **Date**: 2026-04-22
> **Status**: Draft
> **Planning Doc**: [cpp-static-analysis-integration.plan.md](../../01-plan/features/cpp-static-analysis-integration.plan.md)
> **Base Integration Doc**: [cpp-static-analysis-integration.md](../../cpp-static-analysis-integration.md) (경로 B)

### Pipeline References

| Phase | Document | Status |
|-------|----------|--------|
| Phase 1~9 | — | N/A (플러그인 내부 통합, 9-phase 웹 파이프라인 비해당) |

---

## 1. Overview

### 1.1 Design Goals

- rapp 러너를 rkit 플러그인 자산으로 완전 흡수 (외부 배포 패키지 의존 제거)
- `/code-review` 가 C/C++ 타겟에서 rapp 산출물을 **결정론적으로 소비**
- rkit 기존 결함 3건(metrics-json violations 미저장 / import-resolver `core` 미정의 / L1→L2/L3 체인 미구현)을 **구조적으로 우회**
- 비-C++ 타겟에서 **회귀 0** 보장

### 1.2 Design Principles

- **센서-뇌 분리**: rapp = 결정론 센서, code-analyzer = AI 판정. 어댑터 층 없음
- **fail-open**: 의존성/러너 실패가 `/code-review` 전체를 실패시키지 않음
- **non-blocking 훅**: rkit 의 "never prevent tool execution" 정책 준수
- **단일 경로 호출**: 사용자는 `/code-review` 한 번만 호출. 내부에서 러너 자동 트리거
- **변수 치환 회피**: 결함 2 (import-resolver) 상태에서도 동작하는 경로 (SKILL 본문 하드 경로)

---

## 2. Architecture

### 2.1 Component Diagram

```
User
 │
 ▼
/code-review src/   (skills/code-review/SKILL.md, 본문 확장)
 │
 ├─(a) Glob: target 내 *.c/*.cpp/*.h/*.hpp/*.cc/*.cxx ?
 │   └─ 없음 → 기존 /code-review 플로우 (회귀 없음)
 │
 ├─(b) Bash: python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py
 │           --target {target}
 │     └─ 산출: .rkit/state/cpp-static-analysis/{timestamp}/
 │            ├─ findings.xml
 │            ├─ summary.md
 │            └─ structural-brief.md
 │     └─ 실패 시: stderr 로그, fail-open 분기
 │
 ├─(c) 산출물 디렉토리 결정:
 │     ┌─ .rkit/state/cpp-static-analysis/latest/ 존재 → 사용
 │     └─ 없음 → .rkit/state/cpp-static-analysis/*/ 중 max mtime 폴더 선택
 │
 ├─(d) Read {dir}/findings.xml       (또는 Grep 으로 severity/rule 필터링)
 ├─(e) Read {dir}/structural-brief.md
 │
 └─(f) Task: code-analyzer agent (subagent_type: rkit:code-analyzer)
       프롬프트 구성:
         - 기본 agent 프롬프트 (rkit 원본)
         - [첨부] findings.xml 또는 필터된 발췌
         - [첨부] structural-brief.md
         - [첨부] severity 매핑 가이드 (blocker→CRITICAL, major→HIGH, minor→MEDIUM/LOW)
       ↓
     code-analyzer 가 통합 리포트 생성
```

### 2.2 PostToolUse Flow (훅 경로)

```
Write/Edit C/C++ 파일
 │
 ▼
hooks.json: Write 매처 → unified-write-post.js
           Edit 매처 → code-quality-hook.js (직접)
 │
 ├─ (기존) handleCodeQuality(input) — metrics-collector 수치 집계
 │
 └─ (신규) handleCppStaticAnalysis(input) — 파일 확장자 체크 후 rapp 경량 분석
      └─ non-blocking. stderr 경고만. decision:block 금지
      └─ p95 > 3s 면 경량 linter(cppcheck) 로 대체 (성능 가드)
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `/code-review` SKILL | rapp_review.py, `${CLAUDE_PLUGIN_ROOT}` 환경변수 | 러너 호출 |
| rapp_review.py | tree-sitter, tree-sitter-cpp, chardet, pathspec (pip) | 파싱/분석 |
| install.py | pip, `templates/cpp-static-analysis/` | 부트스트랩 |
| cpp-post-edit.py | hard_check.py, patterns.py, models.py (같은 패키지) | 경량 체크 |
| unified-write-post.js | cpp-post-edit.py | PostToolUse 진입점 |

---

## 3. Data Model (산출물 스키마)

### 3.1 findings.xml (rapp 원본 — 변경 없음)

```xml
<findings scan="...">
  <meta timestamp="..." scope="..." git_commit="..." total_files="N"/>
  <finding type="hard|metric|pattern|arch"
           severity="blocker|major|minor"
           rule="..." symbol="..." file="..." lines_hint="..."
           confidence="HIGH|MEDIUM|LOW"
           suggestion="..." message="..."/>
  <!-- 반복 -->
</findings>
```

**본 통합에서 변환 없음** — code-review SKILL 이 Read/Grep 으로 소비.

### 3.2 structural-brief.md (rapp 원본 — 조건부 생성을 무조건 생성으로 변경)

```markdown
# Structural Brief
## Clusters
- {cluster_name}: {member_count} classes, key: {hub_class}
## Hubs
| symbol | Ca | Ce | role |
## Cycles (SCC)
- {symbols}: edge types {inherit|compose|call}
## Anomalies
- zone_of_pain: {symbols}
- fragile_base: {symbols}
```

### 3.3 `.pdca-status.json` 상태 필드 (기존)

```json
{
  "currentFeature": "cpp-static-analysis-integration",
  "features": {
    "cpp-static-analysis-integration": {
      "phase": "design",
      "matchRate": null,
      "iterationCount": 0,
      ...
    }
  }
}
```

---

## 4. File Changes (구체 diff 수준)

### 4.1 파일 이동 (git mv)

| From | To |
|------|-----|
| `rapp_review/scripts/rapp_review.py` | `scripts/cpp-static-analysis/rapp_review.py` |
| `rapp_review/scripts/hard_check.py` | `scripts/cpp-static-analysis/hard_check.py` |
| `rapp_review/scripts/patterns.py` | `scripts/cpp-static-analysis/patterns.py` |
| `rapp_review/scripts/arch_check.py` | `scripts/cpp-static-analysis/arch_check.py` |
| `rapp_review/scripts/metrics.py` | `scripts/cpp-static-analysis/metrics.py` |
| `rapp_review/scripts/cpp_parser.py` | `scripts/cpp-static-analysis/cpp_parser.py` |
| `rapp_review/scripts/project_graph.py` | `scripts/cpp-static-analysis/project_graph.py` |
| `rapp_review/scripts/structural_brief.py` | `scripts/cpp-static-analysis/structural_brief.py` |
| `rapp_review/scripts/render_review.py` | `scripts/cpp-static-analysis/render_review.py` |
| `rapp_review/scripts/formatters.py` | `scripts/cpp-static-analysis/formatters.py` |
| `rapp_review/scripts/cache.py` | `scripts/cpp-static-analysis/cache.py` |
| `rapp_review/scripts/encoding.py` | `scripts/cpp-static-analysis/encoding.py` |
| `rapp_review/scripts/models.py` | `scripts/cpp-static-analysis/models.py` |
| `rapp_review/scripts/review_config.py` | `scripts/cpp-static-analysis/review_config.py` |
| `rapp_review/scripts/install.py` | `scripts/cpp-static-analysis/install.py` (이후 재작성) |
| `rapp_review/scripts/pattern_rules/` | `scripts/cpp-static-analysis/pattern_rules/` |
| `rapp_review/activities/hooks/post-edit-implement.py` | `hooks/cpp-post-edit.py` (이후 재작성) |
| `rapp_review/project-config.example.json` | `templates/cpp-static-analysis/project-config.example.json` |

### 4.2 파일 삭제

- `rapp_review/activities/prompts/adversarial-review.md`
- `rapp_review/activities/schemas/code-review.md`
- `rapp_review/skills/rapp-review/SKILL.md`
- `rapp_review/skills/rapp-setup/SKILL.md`
- `rapp_review/settings.template.json`
- `rapp_review/README.md`
- `rapp_review/.gitattributes`
- `rapp_review/` (흡수 완료 후 디렉토리 전체)

### 4.3 `scripts/cpp-static-analysis/rapp_review.py` 수정

**수정 1**: config 자동 탐색 경로 추가
```python
# Line 102 근처
# BEFORE
_AUTO_DISCOVERY_SUBDIRS = ("", ".claude")

# AFTER
_AUTO_DISCOVERY_SUBDIRS = ("", ".rkit/cpp-static-analysis", ".claude")
```

우선순위: 프로젝트 루트 → `.rkit/cpp-static-analysis/` → `.claude/`. 기존 rapp 배포 호환성을 위해 `.claude/` 는 유지.

**수정 2**: 산출물 경로 기본값
```python
# Line 105 근처
# BEFORE
_DEFAULT_REVIEW_DIR = ".refactor/review"

# AFTER
_DEFAULT_REVIEW_DIR = ".rkit/state/cpp-static-analysis"
```

**수정 3**: structural-brief 무조건 생성
```python
# Line 458 근처 (_main 또는 _render_artifacts 호출부)
# BEFORE
dump_graph = graph if _dump_enabled(raw_cfg) else None
xml_str, md_str, brief_str = _render_artifacts(findings, meta, now, graph=dump_graph)

# AFTER
xml_str, md_str, brief_str = _render_artifacts(findings, meta, now, graph=graph)
# _dump_enabled 는 <metrics_summary> XML 블록 삽입 여부 제어용으로만 유지
```

또는 `_render_artifacts` 시그니처를 변경해 `structural_brief_always=True` 파라미터 추가. 전자가 최소 침습.

**수정 4**: 산출물 안내 메시지 (L466 근처)
```python
# BEFORE
safe_print(f"rapp-review: {run_dir} ({len(findings)} findings)")

# AFTER
safe_print(f"cpp-static-analysis: {run_dir} ({len(findings)} findings)")
```

스킬이 이 stdout 마지막 줄을 파싱할 수 있음 — 스킬 본문의 명시적 계약.

### 4.4 `scripts/cpp-static-analysis/install.py` 재작성

**전면 재작성**. 주요 변경:

```python
# 핵심 경로 계산
# BEFORE
HARNESS_DIR = Path(__file__).resolve().parent.parent  # rapp_review/
PROJECT_ROOT = HARNESS_DIR.parent  # 대상 프로젝트 부모 루트

# AFTER
import os
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parent.parent.parent))
TEMPLATE_DIR = PLUGIN_ROOT / "templates" / "cpp-static-analysis"
PROJECT_ROOT = Path(os.getcwd())
PROJECT_CONFIG_DIR = PROJECT_ROOT / ".rkit" / "cpp-static-analysis"
```

**제거할 단계**:
- `step_settings` (settings.json 병합) — rkit 플러그인 훅이 이미 활성

**유지할 단계**:
- `step_pip` (tree-sitter 등 pip 패키지 설치)
- `step_project_config` (project-config.example → `.rkit/cpp-static-analysis/project-config.json`)

### 4.5 `hooks/cpp-post-edit.py` 재작성

**변경점**:

```python
# 경로 계산 (H-1 해결)
# BEFORE
_HOOK_DIR = Path(__file__).resolve().parent           # rapp_review/activities/hooks/
_SCRIPTS_DIR = _HOOK_DIR.parent.parent / "scripts"    # rapp_review/scripts/

# AFTER
import os
_PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT",
                                    Path(__file__).resolve().parent.parent))
_SCRIPTS_DIR = _PLUGIN_ROOT / "scripts" / "cpp-static-analysis"
```

```python
# decision:block 제거 (H-2 해결)
# BEFORE (main 함수 내)
if blockers:
    _block(_block_reason(blockers))
    return

# AFTER
if blockers:
    # non-blocking: stderr 경고만
    safe_print(_block_reason(blockers), file=sys.stderr)
# return/fallthrough 로 _warn_summary 실행
```

`_block` 함수 자체는 보존 (호출만 제거) 또는 완전 삭제 (권장: 삭제 — 죽은 코드 방지).

```python
# 파일 확장자 early-return (비-C++ 파일 성능 가드)
def main():
    data = json.load(sys.stdin)
    fp_str = _extract_file_path(data)
    fp = Path(fp_str) if fp_str else None
    if fp is None or fp.suffix not in CPP_EXTENSIONS:
        return  # 조용히 종료
    # ... 기존 로직
```

### 4.6 `hooks/hooks.json` — 신규 엔트리 추가하지 않음

**이중 실행 방지 (H-5 해결)**. 기존 매처 재사용:
- **Write 매처**: `unified-write-post.js` 내부에 `handleCppStaticAnalysis` 호출 분기 추가 (`scripts/unified-write-post.js:161` 부근 `handleCodeQuality` 호출 직후)
- **Edit 매처**: `scripts/code-quality-hook.js` 내부에 동일 분기 추가 (Edit 매처가 이 파일을 직접 호출하므로)

또는 더 단순: **Edit 매처도 `unified-write-post.js` 로 통합** → 한 곳에만 `handleCppStaticAnalysis` 호출. hooks.json 의 Edit 매처 교체 필요.

**권장**: 후자 (단일 진입점). 단 기존 Edit 매처 호출 의존성 확인 필요. 안전한 대안은 두 파일 모두에 Node.js 로 Python 훅을 호출하는 thin wrapper 추가.

**구체 코드 (scripts/unified-write-post.js L161 이후 삽입)**:
```javascript
// Code quality check on every code file write
try {
  const { handleCodeQuality } = require('./code-quality-hook');
  handleCodeQuality(input);
} catch (e) {
  debugLog('UnifiedWritePost', 'code-quality-hook failed', { error: e.message });
}

// [신규] C++ static analysis (rapp adapter)
try {
  const { handleCppStaticAnalysis } = require('./cpp-static-analysis-hook');
  handleCppStaticAnalysis(input);
} catch (e) {
  debugLog('UnifiedWritePost', 'cpp-static-analysis-hook failed', { error: e.message });
}
```

### 4.7 `scripts/cpp-static-analysis-hook.js` 신규

Node.js → Python 브릿지. `cpp-post-edit.py` 를 자식 프로세스로 호출:

```javascript
// scripts/cpp-static-analysis-hook.js
const { spawn } = require('child_process');
const path = require('path');

const CPP_EXTENSIONS = new Set(['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp']);

function handleCppStaticAnalysis(input) {
  const filePath = input?.tool_input?.file_path;
  if (!filePath) return false;
  const ext = path.extname(filePath).toLowerCase();
  if (!CPP_EXTENSIONS.has(ext)) return false;

  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT ||
                     path.resolve(__dirname, '..');
  const hookPath = path.join(pluginRoot, 'hooks', 'cpp-post-edit.py');

  // 비동기 non-blocking 호출 (10초 타임아웃, stdout/stderr 수집)
  const proc = spawn('python', [hookPath], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
    timeout: 10000,
  });
  proc.stdin.write(JSON.stringify(input));
  proc.stdin.end();
  // stderr 만 수집해서 Claude 에게 전달, stdout 은 무시 (decision:block 안 씀)
  let stderr = '';
  proc.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
  return new Promise((resolve) => {
    proc.on('close', () => {
      if (stderr) process.stderr.write(stderr);
      resolve(true);
    });
    proc.on('error', () => resolve(false));
  });
}

module.exports = { handleCppStaticAnalysis };
```

**비동기 주의**: `unified-write-post.js` 는 동기 훅이므로 `handleCppStaticAnalysis` 도 동기로 감싸거나 await 지원 확인 필요. 대안: `execFileSync` 사용 (간결, 타임아웃 10초):

```javascript
const { execFileSync } = require('child_process');
try {
  const out = execFileSync('python', [hookPath], {
    input: JSON.stringify(input),
    encoding: 'utf-8',
    timeout: 10000,
    env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
} catch (e) {
  if (e.stderr) process.stderr.write(e.stderr.toString());
}
```

### 4.8 `skills/code-review/SKILL.md` 본문 확장

기존 SKILL 내용 유지하면서 C/C++ 자동 오케스트레이션 섹션 **추가**. 위치: `## Agent Integration` 전후.

```markdown
## C/C++ Pre-Analysis (자동)

target 내 C/C++ 파일이 포함되면 code-analyzer 호출 전에 다음을 수행한다:

### 1. 감지
Glob `*.c`, `*.cpp`, `*.cc`, `*.cxx`, `*.h`, `*.hpp` 로 target 하위 검사. 없으면 이하 전부 스킵 (기존 플로우 유지).

### 2. 러너 실행
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py --target {target}
```
- 실패 (exit code != 0 또는 stdout 마지막 줄이 `cpp-static-analysis:` 로 시작 안 함): fail-open. 후속 Read 생략하고 code-analyzer 만 호출.
- pip 의존성 미설치 (ModuleNotFoundError): `python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py` 1회 시도 후 재실행. 여전히 실패 시 fail-open.

### 3. 산출물 디렉토리 결정
1. `.rkit/state/cpp-static-analysis/latest/` 존재? → 사용.
2. 없으면 `.rkit/state/cpp-static-analysis/*/` 중 디렉토리 mtime 이 가장 큰 것 선택 (Windows symlink fallback).

### 4. 산출물 로드
- **findings.xml**: Read 또는 target 규모 따라 Grep 으로 severity=blocker|major 필터만 발췌
- **structural-brief.md**: Read 전문 (토큰 이슈 관찰 시 헤더 섹션만)

### 5. code-analyzer Task 호출 시 프롬프트 구성
기본 agent 프롬프트 뒤에 다음을 컨텍스트로 첨부:

```
=== cpp-static-analysis findings ===
<findings.xml 발췌 또는 전문>

=== cpp-static-analysis structural-brief ===
<structural-brief.md 내용>

=== severity 매핑 가이드 ===
- blocker → CRITICAL 후보
- major + 클래스 그래프 이상치(zone_of_pain, cycle) → HIGH
- major 단독 → MEDIUM
- minor → LOW
(agent 가 코드 대조 후 최종 severity 결정 — rapp 라벨은 신호일 뿐)
=== end ===
```

### 6. rkit 과 rapp rule 네임스페이스 분리
- rkit SQ-001~008 은 기존대로 code-analyzer 가 `.rkit/state/code-quality-metrics.json` 에서 로드
- rapp rule (`class_DIT_high`, `AP-*`, `zone_of_pain` 등)은 위 첨부 프롬프트에서만 노출
- agent 는 둘을 독립적으로 판정하고 통합 severity 테이블 생성
```

### 4.9 `skills/cpp-static-analysis/SKILL.md` 신규 (얇은 래퍼)

```markdown
---
name: cpp-static-analysis
description: C++ 정적 분석 러너 단독 실행 (CI/수동/디버깅용). `/code-review` 내부에서 자동 호출되므로 일반 사용자는 직접 부를 필요 없음.
when_to_use: CI 파이프라인, 러너 자체 디버깅, 리뷰 없이 산출물만 원할 때.
allowed-tools:
  - Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py *)
  - Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py)
  - Read
---

# cpp-static-analysis

러너 단독 실행.

## 실행
`python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py --target {args}`

첫 호출 시 `install.py` 자동 실행 (pip 의존성 부트스트랩).

## 결과 안내
stdout 마지막 줄 `cpp-static-analysis: <run_dir> (N findings)` 을 사용자에게 전달. 리뷰 단계 없음.

## 언제 쓰나
- CI 에서 리뷰 없이 산출물만 필요
- 러너 자체 이슈 진단
- `/code-review` 는 이 스킬을 부르지 않고 러너를 직접 호출 — 두 경로는 독립
```

### 4.10 `.gitignore` 추가

```
# Added:
.rkit/state/cpp-static-analysis/
```

### 4.11 `templates/cpp-static-analysis/project-config.example.json`

`rapp_review/project-config.example.json` 을 그대로 이동. 변경 없음. 단 최상위 `_comment` 에 "install.py 가 자동 복사. `.rkit/cpp-static-analysis/project-config.json` 에 배치됨" 으로 안내 갱신.

---

## 5. Error Handling / Fail Modes

| 시나리오 | 감지 | 동작 |
|---------|------|------|
| target 에 C/C++ 없음 | Glob 결과 빈 리스트 | 러너 스킵, 기존 /code-review 그대로 진행 |
| pip 의존성 미설치 | rapp_review.py 실행 시 ModuleNotFoundError (stderr) | install.py 1회 시도 → 실패 시 fail-open |
| 러너 실행 타임아웃 | 60초 초과 | stderr 경고, fail-open |
| 러너 crash | exit code != 0 | stderr 로그, fail-open |
| stdout 포맷 위반 | 마지막 줄 `cpp-static-analysis:` 미일치 | fail-open (계약 위반이므로 결과 신뢰 안 함) |
| latest/ 부재 | 파일시스템 체크 | timestamp max mtime fallback |
| 어떤 timestamp 도 없음 | `.rkit/state/cpp-static-analysis/` 빈 디렉토리 | Read 스킵, fail-open |
| findings.xml 파싱 실패 | XML 파서 에러 (SKILL 본문에선 발생 안 함, agent 가 처리) | agent 가 "rapp 산출물 읽기 실패" 로 리포트에 주석 |
| cpp-post-edit.py hook 타임아웃 | 10초 | Node.js 래퍼가 kill, stderr 경고 |

---

## 6. UI/UX Design

해당 없음 (플러그인 내부 통합, 사용자 대면 UI 없음). 사용자 접점은 `/code-review` 명령과 리포트 출력뿐.

---

## 7. Security Considerations

- [ ] Bash 툴로 Python 실행 — `${CLAUDE_PLUGIN_ROOT}` 절대 경로 사용, 사용자 입력 직접 shell 에 삽입 금지
- [ ] target 파라미터는 Bash 인자로 quote 처리 (shell injection 방지)
- [ ] pip install 은 install.py 내부에서만, 사용자 임의 패키지 설치 경로 없음
- [ ] `.rkit/state/cpp-static-analysis/` 는 프로젝트 내부 상태 — git 추적 안 함 (.gitignore)
- [ ] structural-brief / findings.xml 에 코드 경로·심볼 노출 — 정상 범위

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Tool |
|------|--------|------|
| 스모크 | `/code-review` 전체 플로우 | Claude Code 세션 수동 실행 |
| 단위 | rapp_review.py 러너 | rapp 기존 test (`rapp_review/tests/` 있다면 이동) |
| 단위 | adapter(없음 — 미적용) | N/A |
| 통합 | SKILL 본문이 Bash→Read→Task 순서 수행 | 실제 세션 로그 확인 |
| 회귀 | JS/TS/Python 프로젝트 `/code-review` | Claude Code 세션 수동 실행 |
| 플랫폼 | Windows 11 cp949 환경 | 수동 검증 (symlink fallback, UTF-8) |
| 성능 | cpp-post-edit.py 단일 파일 p95 | `time` 명령 또는 bench 스크립트 |

### 8.2 Test Cases

**Happy path**:
- [ ] C++ 프로젝트에서 `/code-review src/` → rapp 러너 실행 로그 + 리포트에 rapp rule / structural-brief 반영
- [ ] 두 번째 `/code-review` 호출 시 `latest/` 덮어씀, 기존 timestamp 폴더 retention 정책대로 유지

**Fail-open**:
- [ ] pip 의존성 제거한 환경에서 `/code-review src/` → install.py 자동 실행 → 실패 시 SQ 기반 리뷰 완료
- [ ] rapp_review.py 를 임의 exit 1 로 바꿔서 실행 → 리뷰는 완료됨

**회귀**:
- [ ] TypeScript/React 프로젝트에서 `/code-review` → rapp 러너 스킵, 기존 리포트 포맷 동일
- [ ] Python 프로젝트에서 `/code-review` → 동일

**Edge**:
- [ ] Windows 비관리자 모드 → symlink 실패, timestamp fallback 동작 확인
- [ ] 빈 target (파일 없음) → 러너 0건 종료, agent 리포트는 "검토 파일 없음"

**성능**:
- [ ] 50 파일 단일 `.cpp` 저장 이벤트 각각 훅 실행 시간 측정 → p95 < 3s 여야 함

---

## 9. Clean Architecture (플러그인 레이어 관점)

### 9.1 Layer Structure

| Layer | 역할 | 위치 |
|-------|-----|------|
| **Presentation** | SKILL 본문, slash command 진입점 | `skills/code-review/SKILL.md`, `skills/cpp-static-analysis/SKILL.md` |
| **Application** | 오케스트레이션 로직 (C/C++ 감지, 러너 호출, 산출물 로드) | SKILL 본문 절차 |
| **Domain** | 분석 도메인 (rule, severity, finding 모델) | `scripts/cpp-static-analysis/models.py`, rapp 원본 유지 |
| **Infrastructure** | Python 러너, tree-sitter, 파일시스템, Node.js 훅 래퍼 | `scripts/cpp-static-analysis/*.py`, `scripts/cpp-static-analysis-hook.js`, `hooks/cpp-post-edit.py` |

### 9.2 Dependency Rules

```
/code-review SKILL (Presentation)
       │
       ▼
Bash 호출 / Read / Task (Claude Code 프레임워크 — 외부)
       │
       ▼
rapp_review.py (Infrastructure)  ──(depends on)──▶  models.py (Domain)
       │                                                  ▲
       ▼                                                  │
cpp_parser.py / tree-sitter (Infrastructure) ─────────────┘
```

rule: SKILL → Python runner (단방향). runner 가 SKILL 에 의존 없음.

### 9.3 Import Rules

| From | Can Import | Cannot Import |
|------|-----------|---------------|
| `scripts/cpp-static-analysis/rapp_review.py` | 동 패키지 모듈, 표준 라이브러리, pip 패키지 | rkit `lib/` 전역 유틸 |
| `scripts/cpp-static-analysis-hook.js` | `child_process`, `path`, `fs`, rkit `lib/core/*` (선택) | rapp Python 내부 모듈 |
| `hooks/cpp-post-edit.py` | 동 패키지 (scripts/cpp-static-analysis), stdlib | rkit Node.js `lib/` |
| `skills/code-review/SKILL.md` | Claude Code tools (Bash/Read/Grep/Task), `${CLAUDE_PLUGIN_ROOT}` | 직접 Python 모듈 import 불가 |

Python 과 Node.js 간 경계는 **프로세스 경계** (child process spawn) 로 명확히 분리.

### 9.4 Layer Assignment

| Component | Layer | Location |
|-----------|-------|----------|
| C/C++ 감지 로직 | Application | `skills/code-review/SKILL.md` (본문 Step 1) |
| 러너 호출 | Application | `skills/code-review/SKILL.md` (본문 Step 2), `scripts/cpp-static-analysis-hook.js` |
| rapp 러너 | Infrastructure | `scripts/cpp-static-analysis/rapp_review.py` |
| rule/finding 모델 | Domain | `scripts/cpp-static-analysis/models.py` |
| structural-brief 렌더러 | Infrastructure | `scripts/cpp-static-analysis/structural_brief.py` |
| PostToolUse 브릿지 | Infrastructure | `scripts/cpp-static-analysis-hook.js` |
| Python 경량 훅 | Infrastructure | `hooks/cpp-post-edit.py` |

---

## 10. Coding Convention Reference

### 10.1 Naming Conventions

| Target | Rule | Example |
|--------|------|---------|
| Python 모듈 | snake_case.py | `rapp_review.py`, `cpp_parser.py` |
| Python 함수 | snake_case | `hc_run_all()`, `_extract_file_path()` |
| Python 상수 | UPPER_SNAKE_CASE | `_AUTO_DISCOVERY_SUBDIRS`, `CPP_EXTENSIONS` |
| Node.js 모듈 | kebab-case.js | `cpp-static-analysis-hook.js` |
| Node.js 함수 | camelCase | `handleCppStaticAnalysis()` |
| SKILL 디렉토리 | kebab-case | `cpp-static-analysis/`, `code-review/` |
| 훅 파일 | kebab-case.py/.js | `cpp-post-edit.py` |

### 10.2 Python Conventions (rapp 원본 유지)

- UTF-8 self-reexec 가드 (`if __name__ == "__main__" and os.environ.get("PYTHONUTF8") != "1":`) 유지
- `safe_print` 를 통한 Windows cp949 안전 출력
- `from __future__ import annotations` 로 forward reference 활용

### 10.3 Node.js Conventions (rkit 기존 유지)

- CommonJS (`require/module.exports`) — ESM 아님
- Lazy require (`function getIo() { return require('...'); }`) — 순환 의존 회피
- `debugLog` 로 silent log (Claude 프롬프트 오염 방지)
- 훅은 `outputAllow()` 또는 `outputBlock()` 명시적 출력 — 양쪽 비동기 경로 모두 `outputAllow()` 로 마감 (non-blocking 정책)

### 10.4 Environment Variables

| Variable | Purpose | Scope |
|----------|---------|-------|
| `CLAUDE_PLUGIN_ROOT` | 플러그인 설치 루트 | rkit 훅/스킬 전역 |
| `PYTHONUTF8` | Windows UTF-8 강제 | rapp Python 러너 |
| `PYTHONIOENCODING` | stdout/stderr 인코딩 | rapp Python 러너 |

---

## 11. Implementation Guide

### 11.1 File Structure (최종)

```
rkit/
├── scripts/cpp-static-analysis/
│   ├── rapp_review.py               (수정)
│   ├── install.py                   (재작성)
│   ├── hard_check.py
│   ├── patterns.py
│   ├── arch_check.py
│   ├── metrics.py
│   ├── cpp_parser.py
│   ├── project_graph.py
│   ├── structural_brief.py
│   ├── render_review.py
│   ├── formatters.py
│   ├── cache.py
│   ├── encoding.py
│   ├── models.py
│   ├── review_config.py
│   └── pattern_rules/
├── scripts/cpp-static-analysis-hook.js  (신규 — Node bridge)
├── hooks/cpp-post-edit.py              (재작성)
├── skills/
│   ├── code-review/SKILL.md            (수정 — 본문 섹션 추가)
│   └── cpp-static-analysis/SKILL.md    (신규 — 얇은 래퍼)
├── templates/cpp-static-analysis/
│   └── project-config.example.json
├── docs/
│   ├── cpp-static-analysis-integration.md
│   ├── 01-plan/features/cpp-static-analysis-integration.plan.md
│   └── 02-design/features/cpp-static-analysis-integration.design.md  (본 문서)
└── .gitignore                           (수정 — .rkit/state/cpp-static-analysis/ 추가)

(삭제)
└── rapp_review/                         (흡수 후 제거)
```

### 11.2 Implementation Order

1. [ ] **브랜치 분기**: 현재 `feat/add-cpp-static-analysis` 브랜치에서 작업 계속
2. [ ] **파일 이동 (git mv)**: 4.1 표대로. history 보존. 1 commit (`chore: move rapp_review → scripts/cpp-static-analysis (no code change)`)
3. [ ] **rapp_review.py 수정**: 4.3 의 수정 1~4. 1 commit (`feat(cpp-static-analysis): adapt runner paths and structural-brief default`)
4. [ ] **install.py 재작성**: 4.4. 1 commit (`feat(cpp-static-analysis): rewrite install.py for rkit plugin layout`)
5. [ ] **cpp-post-edit.py 재작성**: 4.5. 1 commit (`feat(cpp-static-analysis): non-blocking hook, absolute path resolution`)
6. [ ] **cpp-static-analysis-hook.js 신규**: 4.7. 1 commit (`feat(cpp-static-analysis): add Node bridge for PostToolUse`)
7. [ ] **unified-write-post.js 수정**: 4.6. 1 commit (`feat(cpp-static-analysis): integrate into unified-write-post`)
8. [ ] **얇은 래퍼 스킬**: 4.9. 1 commit (`feat(cpp-static-analysis): add thin skill wrapper`)
9. [ ] **code-review SKILL 확장**: 4.8. 1 commit (`feat(code-review): auto cpp-static-analysis for C/C++ targets`)
10. [ ] **templates 배치**: 4.11. `.gitignore` 추가 (4.10). 1 commit
11. [ ] **스모크 테스트**: C++ / TS / Python 프로젝트 각각 `/code-review` 실행. 로그 확인
12. [ ] **rapp_review/ 삭제**: 흡수 완료 확인 후. 1 commit (`chore: remove rapp_review/ after integration`)

### 11.3 Key Dependencies to Install

```bash
# 대상 프로젝트에서 (install.py 가 자동 수행)
pip install tree-sitter==0.25.2 tree-sitter-cpp==0.23.4 chardet pathspec
```

### 11.4 Rollback Plan

통합 실패 시:
- Git revert 로 마지막 8~10 단계 되돌림
- `rapp_review/` 는 단계 12 이전엔 유지되므로 복구 가능
- `.rkit/state/cpp-static-analysis/` 는 런타임 산출물이라 삭제해도 재생성

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-22 | Initial draft. 경로 B 기준 FR-01~FR-12 를 파일/함수/line 단위로 구체화. 신규 `cpp-static-analysis-hook.js` Node 브릿지 설계 추가. | pdm87 |
