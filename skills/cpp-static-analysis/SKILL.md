---
name: cpp-static-analysis
description: |
  C++ 정적 분석 러너(tree-sitter-cpp 기반) 단독 실행.
  CI/수동/디버깅용 — 일반 사용자는 `/code-review` 내부에서 자동 호출되므로 직접 부를 필요 없음.

  산출물: findings.xml (rule 위반), summary.md (사람용), structural-brief.md (클래스 그래프 narrative).
  위치: `.rkit/state/cpp-static-analysis/{timestamp}/` + `latest/` symlink.

  Triggers: cpp static analysis, rapp review, C++ 정적 분석, C++ 리뷰 분석,
  코드 감사, static analysis, 静的解析, 静态分析, análisis estático, analyse statique, statische Analyse

  Do NOT use for: 코드 리뷰 전체 (use code-review), 단일 파일 훅 (PostToolUse 자동),
  판정/suggestion 해석 (code-analyzer agent 담당).
argument-hint: "[target-dir]"
user-invocable: true
allowed-tools:
  - Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py *)
  - Bash(python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py)
  - Read
---

# cpp-static-analysis Skill

> C++ 결정론 정적 분석 러너의 얇은 래퍼. 리뷰 판정은 수행하지 않음.

## 사용 시나리오

- CI 파이프라인에서 리뷰 없이 산출물만 원할 때
- 러너 자체 디버깅 (exit code, 로그 확인)
- `.rkit/state/cpp-static-analysis/latest/` 산출물을 외부 도구로 후처리할 때

일반 코드 리뷰는 **`/code-review`** 를 사용 — 내부에서 본 러너를 자동 호출한다.

## 실행

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/rapp_review.py --target <target-dir>
```

인자 없으면 `project-config.json` 의 `review.default_target` 사용.

## 부트스트랩 (첫 실행 시)

`ModuleNotFoundError` 발생 시 (pip 의존성 미설치) 자동 시도:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/cpp-static-analysis/install.py
```

- pip install: tree-sitter, tree-sitter-cpp, chardet, pathspec
- `.rkit/cpp-static-analysis/project-config.json` 없으면 템플릿에서 생성

`install.py` 재실행은 멱등 (기존 config 보존).

## 산출물

| 파일 | 용도 |
|---|---|
| `findings.xml` | rule 위반 원본 (hard/metric/pattern/arch). Grep 가능한 self-closing XML 요소. |
| `summary.md` | per-file count + finding 목록 (사람용) |
| `structural-brief.md` | 클래스 그래프 narrative (클러스터/허브/cycle/anomalies) |

위치: `.rkit/state/cpp-static-analysis/{timestamp}/`.
`latest/` symlink 는 최신 run 을 가리킴 (Windows 권한 미비 시 실패 — 이 경우 timestamp 폴더 중 max mtime 직접 사용).

## 결과 안내

stdout 마지막 줄이 러너 계약:

```
cpp-static-analysis: <run_dir> (N findings)
```

이 줄을 사용자에게 그대로 전달. 리뷰 판정(CONFIRMED/DISMISSED 등) 수행 안 함.

## 계약

- 러너 exit code 0: 정상 (findings 0건 포함)
- exit code != 0: 러너 내부 오류. stderr 원문 전달. 임의 재해석 금지.
- stdout 마지막 줄 포맷 위반: 계약 위반 — 사용자에게 보고.

## `/code-review` 와의 관계

`/code-review` 는 C/C++ 타겟 감지 시 본 러너를 내부에서 직접 호출 (이 스킬을 부르지 않음).
두 경로는 같은 러너 스크립트를 공유하지만 호출자가 다름 — 역할 분리.

- `/cpp-static-analysis`: 결정론 센서만
- `/code-review`: 센서 호출 + AI 판정 (code-analyzer agent)
