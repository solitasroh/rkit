---
name: code-review
classification: workflow
classification-reason: Process automation persists regardless of model advancement
deprecation-risk: none
description: |
  Code review skill for analyzing code quality, detecting bugs, and ensuring best practices.
  Provides comprehensive code review with actionable feedback.

  Use proactively when user requests code review, quality check, or bug detection.

  Triggers: code review, review code, check code, analyze code, bug detection,
  code 리뷰, code 검수, code 검토, 코드 검수, 코드 리뷰, 코드 검토, 버그 검사,
  コードレビュー, バグ検出, 代码审查, 代码检查,
  revisión de código, revisar código, detección de errores,
  revue de code, réviser le code, détection de bugs,
  Code-Review, Code überprüfen, Fehlererkennung,
  revisione del codice, rivedere codice, rilevamento bug

  Do NOT use for: design document creation, deployment tasks, or gap analysis (use phase-8-review).
argument-hint: "[file|directory|pr]"
user-invocable: true
agent: rkit:code-analyzer
allowed-tools:
  - Read
  - Glob
  - Grep
  - LSP
  - Task
  - Bash
imports:
  - ${PLUGIN_ROOT}/templates/pipeline/phase-8-review.template.md
  - ${PLUGIN_ROOT}/skills/rkit-rules/SKILL.md
next-skill: null
pdca-phase: check
task-template: "[Code-Review] {feature}"
hooks:
  Stop:
    - type: command
      command: "node ${CLAUDE_PLUGIN_ROOT}/scripts/code-review-stop.js"
      timeout: 10000
---
# Code Review Skill

> Skill for code quality analysis and review

## Arguments

| Argument        | Description                            | Example                          |
| --------------- | -------------------------------------- | -------------------------------- |
| `[file]`      | Review specific file                   | `/code-review src/lib/auth.ts` |
| `[directory]` | Review entire directory                | `/code-review src/features/`   |
| `[pr]`        | PR review (PR number)                  | `/code-review pr 123`          |
| `--auto-fix`  | Auto-fix Minor/Major issues (L2+ only) | `/code-review src/ --auto-fix` |

## Review Categories

### 1. Code Quality

- Duplicate code detection
- Function/file complexity analysis
- Naming convention check
- Type safety verification

### 2. Bug Detection

- Potential bug pattern detection
- Null/undefined handling check
- Error handling inspection
- Boundary condition verification

### 3. Security

- XSS/CSRF vulnerability check
- SQL Injection pattern detection
- Sensitive information exposure check
- Authentication/authorization logic review

### 4. Performance

- N+1 query pattern detection
- Unnecessary re-render check
- Memory leak pattern detection
- Optimization opportunity identification

## Review Output Format

```
## Code Review Report

### Summary
- Files reviewed: N
- Issues found: N (Critical: N, Major: N, Minor: N)
- Score: N/100

### Critical Issues
1. [FILE:LINE] Issue description
   Suggestion: ...

### Major Issues
...

### Minor Issues
...

### Recommendations
- ...
```

## C/C++ Pre-Analysis (자동)

target 내에 C/C++ 파일이 포함되면 code-analyzer 호출 **전에** 다음을 순차 수행한다. 비-C/C++ target 이면 전체 스킵 (회귀 없음).

### 1. 감지

Glob `**/*.{c,cpp,cc,cxx,h,hpp}` 로 target 하위 검사. 결과 빈 리스트면 이하 전부 스킵.

### 2. 러너 실행

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py --target <target>
```

- **정상**: stdout 마지막 줄이 `cpp-static-analysis: <run_dir> (N findings)` 형식 — 이 `<run_dir>` 을 반드시 캡처 (Step 3 입력)
- **ModuleNotFoundError** (pip 의존성 미설치): `python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py` 1회 시도 후 러너 재실행. 여전히 실패하면 fail-open
- **기타 exit != 0**: stderr 로그를 사용자에게 전달, fail-open. code-analyzer 는 SQ 기반으로 계속 실행

### 3. 산출물 디렉토리 결정 (stdout 동적 파싱)

**우선**: Step 2 stdout 마지막 줄에서 `<run_dir>` 파싱. 사용자가 `project-config.json` 의 `paths.review` 를 커스터마이징할 수 있으므로 경로 하드코딩 금지.

예시:

- stdout: `cpp-static-analysis: .rkit\state\cpp-static-analysis\20260422-092153 (12 findings)`
- 파싱 `run_dir = .rkit/state/cpp-static-analysis/20260422-092153` (cwd 기준 상대, 또는 절대 경로 가능)

**fallback** (stdout 파싱 실패 또는 러너 미실행 시):

1. `.rkit/state/cpp-static-analysis/latest/` 존재하면 사용
2. 없으면 `.rkit/state/cpp-static-analysis/*/` 중 디렉토리 mtime 가장 큰 것 선택 (Windows symlink fallback)
3. 어떤 timestamp 폴더도 없으면 fail-open

정규식 힌트: stdout 마지막 줄에 `^cpp-static-analysis:\s*(\S.*?)\s*\(\d+ findings\)$` 매칭하여 그룹 1 추출.

### 4. 산출물 로드

- **findings.xml**: Read 또는 Grep. target 규모 크면 `grep 'severity="blocker\|major"' findings.xml` 로 발췌
- **structural-brief.md**: Read 전문 (대형 프로젝트에서 토큰 이슈 나면 헤더 섹션만 추출)

### 5. code-analyzer Task 프롬프트 구성

기본 agent 프롬프트 뒤에 다음 컨텍스트 블록을 첨부해 Task 호출:

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
(코드 대조 후 최종 severity 결정. 위는 신호일 뿐.)
=== end ===
```

### 6. rule 네임스페이스

- rkit SQ-001~008: `.rkit/state/code-quality-metrics.json` 로 기존대로 로드
- rapp rule (`class_DIT_high`, `AP-*`, `zone_of_pain`, `IDIOM-*` 등): 위 첨부 블록으로만 전달
- 두 카탈로그는 독립적으로 판정. 리포트에서 통합 severity 테이블로 출력

### 7. fail-open 원칙

위 절차 중 어느 단계든 실패 시 **code-analyzer 호출은 그대로 진행** 한다. 러너/Read/첨부 모두 보조 — 필수 아님. 기존 `/code-review` 플로우 회귀 금지.

---

## Agent Integration

This Skill calls the `code-analyzer` Agent for in-depth code analysis.

| Agent         | Role                                         |
| ------------- | -------------------------------------------- |
| code-analyzer | Code quality, security, performance analysis |

## Usage Examples

```bash
# Review specific file
/code-review src/lib/auth.ts

# Review entire directory
/code-review src/features/user/

# PR review
/code-review pr 42

# Review current changes
/code-review staged
```

## Confidence-Based Filtering

code-analyzer Agent uses confidence-based filtering:

| Confidence      | Display           | Description           |
| --------------- | ----------------- | --------------------- |
| High (90%+)     | Always shown      | Definite issues       |
| Medium (70-89%) | Selectively shown | Possible issues       |
| Low (<70%)      | Hidden            | Uncertain suggestions |

## Auto-Fix Mode (--auto-fix)

When `--auto-fix` flag is provided:

1. **Requirement**: Automation level L2+ (Semi-Auto or higher)
2. **Scope**: Only Minor and Major issues are auto-fixed
3. **Critical issues**: Always require manual review (never auto-fixed)
4. **Process**:
   - Run normal code review first
   - Present findings summary
   - Auto-apply fixes for Minor/Major issues
   - Re-run review to verify fixes
   - Report remaining issues (Critical only)
5. **Guard mode**: Auto-fix is disabled when guard mode is active

## PDCA Integration

- **Phase**: Check (Quality verification)
- **Trigger**: Auto-suggested after implementation
- **Output**: docs/03-analysis/code-review-{date}.md
