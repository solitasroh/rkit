---
template: plan
version: 1.2
feature: cpp-static-analysis-integration
date: 2026-04-21
author: pdm87
project: rkit
project-version: 0.9.13
---

# cpp-static-analysis-integration Planning Document

> **Summary**: `rapp_review/` 패키지의 tree-sitter 기반 C++ 정적 분석 러너를 rkit 플러그인에 흡수하여 `/code-review` 스킬의 분석 근거로 활용.
>
> **Project**: rkit
> **Version**: 0.9.13
> **Author**: pdm87
> **Date**: 2026-04-21
> **Status**: Draft
> **Base Document**: [docs/cpp-static-analysis-integration.md](../../cpp-static-analysis-integration.md) (경로 B 채택 기준)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | rkit 의 C/C++ 리뷰가 정량 메트릭(SQ-001~008) 수준에 머물러, 클래스 그래프 메트릭(DIT/Ca/Ce/zone_of_pain/cycle)·패턴 카탈로그(SMELL/IDIOM/AP)·아키텍처 레이어 위반 같은 **심층 신호를 놓침**. 별도 개발된 `rapp_review/` 러너가 이 공백을 메울 수 있으나 자기완결 `.claude/` 배포 패키지라 rkit 과 연결이 안 됨. |
| **Solution** | rapp 러너(Python + tree-sitter-cpp)를 플러그인 자산으로 흡수하고, `/code-review` 스킬이 C/C++ 파일 감지 시 러너를 자동 호출 → 산출물(`findings.xml` + `structural-brief.md`)을 **SKILL 본문에서 직접 Read** 하여 code-analyzer Task 프롬프트에 컨텍스트로 삽입. rkit metrics JSON 과 design-rules 카탈로그는 건드리지 않는 **경로 B(보수적)** 채택. |
| **Function/UX Effect** | 사용자는 `/code-review src/` 한 번만 호출하면 C++ 심층 정적 분석(클래스 그래프·패턴·메트릭)이 리뷰 근거로 자동 포함됨. 비-C++ 프로젝트에서는 기존 플로우 회귀 없음. 의존성 미설치·러너 실패 시 fail-open 으로 SQ 기반 리뷰 지속. |
| **Core Value** | 리뷰 품질 향상과 rkit 기존 결함(metrics-json violations 미저장, import-resolver `core` 미정의, L1→L2/L3 체인 미구현) **3건 동시 우회**. 결정론 정적 분석(센서)과 AI 판정(뇌) 역할 분리 원칙 강화. |

---

## 1. Overview

### 1.1 Purpose

- rkit 의 `/code-review` 스킬이 C/C++ 코드에 대해 제공하는 분석 깊이를 한 단계 끌어올린다.
- 별도 개발된 `rapp_review/` 결정론 정적 분석기를 "센서" 로 편입하되, 판정 책임은 rkit 기존 L1 reviewer(code-analyzer) 가 유지.
- 결함이 많은 rkit 내부 기능(metrics-json merge, agent imports, L2 체인)에 의존하지 않고 안전하게 통합.

### 1.2 Background

- `rapp_review/` 는 tree-sitter-cpp 기반 정밀 C++ 파싱, 10종 클래스 그래프 메트릭, 패턴 카탈로그, 아키텍처 레이어 검증을 제공. 자체 "적대적 검수" 프롬프트도 포함.
- rkit 의 기존 code-analyzer agent 체크리스트는 범용(SOLID/DRY/명명/함수 크기)이라 C++ 심층 신호 누락.
- rapp 의 적대적 검수 프롬프트는 rkit 의 L1/L2/L3 리뷰 아키텍처(opus/effort:high/maxTurns:15)에 비해 품질 열위 → **제거**하고 판정은 rkit 에 위임.
- 서브에이전트 적대적 검수로 기존 통합안(어댑터 + metrics JSON merge)의 10건 결함 발견 → 경로 B(SKILL 본문 직접 Read) 채택.

### 1.3 Related Documents

- 기반 통합 설계: `docs/cpp-static-analysis-integration.md` (경로 B 채택, 결함 10건 정리)
- rapp 원본 README: `rapp_review/README.md`
- rkit code-review 스킬: `skills/code-review/SKILL.md`
- rkit L1 agent: `agents/code-analyzer.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] `rapp_review/scripts/*.py` 를 `scripts/cpp-static-analysis/` 로 이동 (git mv)
- [ ] `rapp_review.py` 수정: `_AUTO_DISCOVERY_SUBDIRS` 에 `.rkit/cpp-static-analysis` 추가
- [ ] `rapp_review.py` 수정: `_dump_enabled` 기본 True 또는 `_render_artifacts` 재작성으로 `structural-brief.md` 무조건 생성
- [ ] `rapp_review.py` 수정: 산출물 경로 기본값 `.rkit/state/cpp-static-analysis/`
- [ ] `skills/code-review/SKILL.md` 본문 확장: C/C++ 감지 + 러너 자동 호출 + 산출물 Read/Grep + 프롬프트 삽입
- [ ] `skills/cpp-static-analysis/SKILL.md` (얇은 래퍼, CI/수동 실행용)
- [ ] `scripts/cpp-static-analysis/install.py` 재작성: `HARNESS_DIR` 절대 경로, `settings.json` 병합 단계 제거
- [ ] `hooks/cpp-post-edit.py` 재작성: `decision: block` 제거(non-blocking), `_SCRIPTS_DIR` 절대 경로
- [ ] `hooks.json` 통합: `unified-write-post.js` 또는 `code-quality-hook.js` 내부에 `handleCppStaticAnalysis` 분기 (이중 실행 방지)
- [ ] `templates/cpp-static-analysis/project-config.example.json` 생성
- [ ] `rapp_review/` 디렉토리 삭제 (흡수 완료 후)
- [ ] `.gitignore` 에 `.rkit/state/cpp-static-analysis/` 추가
- [ ] 단일 파일 훅 실행 시간 p95 < 3s 벤치마크

### 2.2 Out of Scope

- **결함 2 (import-resolver `core` 미정의) 수정** — 본 통합과 독립된 버그픽스. 별도 이슈로 분리. 본 통합은 이 수정 없이도 동작 (agent imports 사용 안 함).
- **결함 10 (L1 → L2/L3 리뷰 체인 활성화)** — `review-orchestrator.js` 의 building block 유틸이 호출 경로에 연결되지 않은 별도 이슈. c-cpp-reviewer / safety-auditor 자동 호출은 본 범위 밖. 완료 후 후속 PR 로 rapp 산출물을 L2/L3 에도 공급 가능.
- **rapp adversarial-review 프롬프트 보존** — rkit 리뷰 아키텍처 품질이 우수하므로 제거.
- **rapp rule 카탈로그 → rkit `design-rules.js` 정식 통합** — 경로 B 는 rule id 변환 없이 원본 그대로 리포트에 노출. 장기적 통합은 별도.
- **대형 프로젝트용 증분 실행 전략** — 본 통합은 target 전체 분석. mtime 기반 캐시 / 변경 파일 필터는 Phase 2.
- **rkit `code-quality-metrics.json` 확장** — metrics-collector 가 violations 를 저장하지 않는 문제는 본 통합 범위 밖. 경로 B 가 이를 우회.

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `rapp_review/scripts/*.py` 를 `scripts/cpp-static-analysis/` 로 이동, 내부 경로 참조 치환 | High | Pending |
| FR-02 | `rapp_review.py` config 자동 탐색에 `.rkit/cpp-static-analysis/` 추가 | High | Pending |
| FR-03 | `rapp_review.py` 가 `structural-brief.md` 를 기본 설정에서도 생성 | High | Pending |
| FR-04 | `/code-review` 스킬이 target 내 C/C++ 파일 감지 시 rapp 러너 자동 실행 | High | Pending |
| FR-05 | `/code-review` 스킬이 러너 산출물(`findings.xml` + `structural-brief.md`)을 Read/Grep 으로 로드 후 code-analyzer Task 프롬프트에 첨부 | High | Pending |
| FR-06 | `/code-review` 가 `latest/` symlink 부재 시 timestamp 폴더 glob → max mtime fallback | High | Pending |
| FR-07 | `cpp-post-edit.py` 훅이 `decision: block` 대신 non-blocking 경고 출력 (rkit 정책 준수) | High | Pending |
| FR-08 | `hooks.json` 에서 C++ 훅이 기존 `unified-write-post.js`/`code-quality-hook.js` 와 이중 실행되지 않음 | High | Pending |
| FR-09 | `install.py` 가 rkit 경로 기반으로 동작 (`HARNESS_DIR` 절대 경로, `settings.json` 병합 제거) | Medium | Pending |
| FR-10 | `/cpp-static-analysis` 얇은 래퍼 스킬 (러너만 실행, 리뷰 단계 없음) | Medium | Pending |
| FR-11 | pip 의존성 미설치 시 러너 graceful skip, 리뷰는 SQ 기반으로 계속 | Medium | Pending |
| FR-12 | `rapp_review/` 디렉토리 흡수 완료 후 삭제 | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 성능 | 단일 파일 PostToolUse 훅 실행 시간 p95 < 3s | 로컬 벤치마크 스크립트 |
| Windows 호환 | cp949 환경에서 UTF-8 출력 정상, symlink 실패 시 timestamp fallback | Windows 11 환경 수동 검증 |
| 안정성 | 러너 실패/의존성 부재 시 fail-open — `/code-review` 는 SQ 기반으로 완료 | 의존성 제거 환경에서 리뷰 실행 |
| 결정론 | 러너 산출물은 코드 입력에 대해 동일 결과 (seed 무관) | 동일 target 2회 실행 비교 |
| 회귀 방지 | 비-C++ 프로젝트에서 기존 `/code-review` 동작 100% 유지 | JS/TS/Python 프로젝트에서 회귀 테스트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] C/C++ 파일 포함 target 으로 `/code-review` 호출 시 rapp 러너 자동 실행 로그 확인
- [ ] code-analyzer 리포트에 rapp rule id (`class_DIT_high`, `zone_of_pain`, `AP-*` 등) 및 structural-brief 신호 반영
- [ ] 비-C++ target 에서 `/code-review` 호출 시 기존 플로우 그대로 (회귀 없음)
- [ ] Windows symlink 미지원 환경에서 timestamp fallback 동작
- [ ] pip 의존성 미설치 환경에서 fail-open
- [ ] PostToolUse 훅 이중 실행 없음
- [ ] `rapp_review/` 디렉토리 제거 완료
- [ ] 플러그인 설치(`/plugin install`)만으로 러너 사용 가능 (rapp-setup 별도 호출 불필요)

### 4.2 Quality Criteria

- [ ] 본 통합 관련 `rapp_review.py` / 신규 스크립트 / SKILL.md 변경에서 ruff / shellcheck 경고 없음
- [ ] Windows/Linux/macOS 3종 플랫폼에서 러너 + 훅 실행 성공 (수동 스모크 테스트)
- [ ] `docs/cpp-static-analysis-integration.md` 의 검증 체크리스트 Phase 1 항목 모두 통과

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| SKILL 본문 비결정성 (Claude 가 Bash→Read→Task 단계 건너뜀) | Medium | Medium | 결정적 부분은 PostToolUse 훅 또는 Stop 훅으로 이관 검토. 초기엔 스킬 본문 + 명시적 단계 번호로 감수. |
| 단일 파일 훅에서 tree-sitter 파싱 > 3s | Medium | Medium | 벤치마크 먼저. 초과 시 경량 linter(cppcheck)로 대체하고 rapp 전체 분석은 `/code-review` 에서만 실행. |
| structural-brief 가 대형 프로젝트에서 prompt 비대 | Medium | Low | 초기엔 전문 삽입, 토큰 이슈 관찰 후 헤더 섹션(클러스터·허브·cycle) 요약만 삽입으로 축소. |
| 결함 10 (L2 체인) 미해결로 c-cpp-reviewer 관점 공백 | Low | High | 부분 완화 수용 — code-analyzer 가 rapp 신호를 프롬프트로 받아 C++ 관점 일부 흡수. 완전 해결은 별도 이슈. |
| 결함 2 (import-resolver) 로 기존 profile.md imports 미로드 | Low | High | 본 통합과 독립. 별도 버그픽스 우선순위 낮음 (경로 B 는 agent imports 사용 안 함). |
| Windows 개발자 모드 미활성 환경에서 symlink 실패 | Low | Medium | FR-06 (timestamp fallback) 필수 구현. |
| rapp pip 의존성(tree-sitter-cpp 등) 설치 실패 | Low | Low | `install.py` 로 부트스트랩, 실패 시 `/code-review` fail-open. |

---

## 6. Architecture Considerations

> **Note**: 본 feature 는 웹/앱 서비스 개발이 아닌 **Claude Code 플러그인 내부 통합**이므로 템플릿의 Framework/상태관리/Form 같은 항목은 해당 없음. 아래는 플러그인 아키텍처 결정으로 재정의.

### 6.1 Project Level

| Level | Selected | Rationale |
|-------|:--------:|-----------|
| Plugin Internal | ✅ | rkit 플러그인 내부 기능 확장. 대상 프로젝트 타입과 무관 (MCU/MPU/WPF/Generic 모두에서 C/C++ 파일이 있으면 동작). |

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 통합 전략 | (A) agent imports 확장 / (B) /cpp-static-analysis 수동 / (C) 어댑터 + metrics-json merge / (D) SKILL 본문 직접 Read | **D** | A/C 는 rkit 기존 결함 의존, B 는 UX 부담. D 는 결함 3종 동시 우회. |
| 판정 책임 | rapp adversarial-review 프롬프트 / rkit L1 reviewer | **rkit L1** | rkit 은 opus/effort:high/maxTurns:15 + profile.md import 로 품질 우위. rapp 적대적 프롬프트 제거. |
| 산출물 전달 경로 | agent frontmatter `imports:` / SKILL 본문 Read / adapter 로 metrics-json merge | **SKILL 본문 Read** | 결함 B-2(import-resolver core 미정의), B-1(metrics-json 에 violations 미저장) 우회. |
| rule id 변환 | `CPP-*` prefix 로 네임스페이스 분리 / 원본 그대로 | **원본 그대로** | 경로 B 는 merge 없음. rkit 카탈로그 충돌 없음. |
| 얇은 래퍼 스킬 `/cpp-static-analysis` | 제거 / 유지 | **유지** | CI/수동 실행/디버깅 경로 보존. 메인 경로는 `/code-review`. |
| post-edit 훅 정책 | blocking (rapp 원본 `decision: block`) / non-blocking (rkit 정책) | **non-blocking** | `scripts/code-quality-hook.js` 의 "never prevent tool execution" 정책 준수. |

### 6.3 Integration Layout

```
rkit/
├── scripts/cpp-static-analysis/        [신규 — rapp_review/scripts/*.py 이동]
│   ├── rapp_review.py                   (수정: config 탐색 + structural-brief 항상 생성)
│   ├── install.py                       (재작성: HARNESS_DIR 절대 경로)
│   ├── hard_check.py, patterns.py, ...  (기존 유지)
│   └── pattern_rules/                   (기존 유지)
├── hooks/
│   ├── cpp-post-edit.py                 [신규 — non-blocking 재작성]
│   └── hooks.json                       (수정: 이중 실행 방지 통합)
├── skills/
│   ├── code-review/SKILL.md             (수정: C/C++ 감지 + 러너 호출 + 산출물 Read)
│   └── cpp-static-analysis/SKILL.md     [신규 — 얇은 래퍼]
├── templates/cpp-static-analysis/       [신규]
│   └── project-config.example.json
└── docs/
    ├── cpp-static-analysis-integration.md  (기반 통합 문서, 유지)
    └── 01-plan/features/cpp-static-analysis-integration.plan.md  (본 문서)

PROJECT (대상 프로젝트 CWD):
└── .rkit/
    ├── cpp-static-analysis/
    │   └── project-config.json          (install.py 가 생성)
    └── state/
        └── cpp-static-analysis/
            ├── {timestamp}/             (러너 실행마다)
            │   ├── findings.xml
            │   ├── summary.md
            │   └── structural-brief.md
            └── latest/                   (symlink, Windows 실패 시 timestamp fallback)
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] `CLAUDE.md` 에 rkit 도메인별 코딩 컨벤션 (MCU/MPU/WPF) 명시
- [x] `docs/` 디렉토리 구조 확립 (`00-pm/`, `01-plan/`, `02-design/`, `03-analysis/`, `04-report/`, `archive/`)
- [x] `rkit.config.json` — 플러그인 설정
- [x] Node.js 코드: JS (훅/스크립트는 vanilla JS, CommonJS)
- [x] Python 코드: 3.10+, PEP 8, UTF-8 self-reexec 가드 (rapp 원본 유지)

### 7.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| 스킬 네이밍 | 기능 기반(`misra-c`, `stm32-hal`) | `cpp-static-analysis` 채택, `rapp-*` 브랜드 제거 | High |
| 산출물 경로 | 도구별 하위 디렉토리 | `.rkit/state/cpp-static-analysis/` 로 통일 | High |
| 훅 정책 | Non-blocking (`code-quality-hook.js:144` 명시) | `cpp-post-edit.py` 도 동일 준수 | High |
| Python 스크립트 위치 | `scripts/*.js` 주류 | C++ 분석은 Python 허용 — `scripts/cpp-static-analysis/` 네임스페이스 | Medium |

### 7.3 Environment Variables Needed

| Variable | Purpose | Scope | To Be Created |
|----------|---------|-------|:-------------:|
| `CLAUDE_PLUGIN_ROOT` | 플러그인 루트 (Claude Code 자동 주입) | Plugin runtime | 기존 |
| `PYTHONUTF8` | Windows cp949 환경 UTF-8 강제 (rapp self-reexec 가드) | Runner | 기존 (rapp 원본 유지) |

### 7.4 Pipeline Integration

9-phase Development Pipeline 은 웹 앱 개발용이라 본 feature 해당 없음. PDCA 라이프사이클만 사용.

---

## 8. Next Steps

1. [ ] `/rkit:pdca design cpp-static-analysis-integration` — 구체적 설계 문서 (Phase 1 11단계를 파일/함수 단위로 구체화)
2. [ ] 기반 통합 문서 `docs/cpp-static-analysis-integration.md` 내용을 Design 에 편입
3. [ ] `/rkit:pdca do cpp-static-analysis-integration` — 실제 구현
4. [ ] `/rkit:pdca analyze cpp-static-analysis-integration` — Gap 분석 (검증 체크리스트 실행)
5. [ ] 필요 시 `/rkit:pdca iterate` 반복
6. [ ] `/rkit:pdca report cpp-static-analysis-integration` — 완료 리포트

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-21 | Initial draft (기반 문서 `docs/cpp-static-analysis-integration.md` 경로 B 채택 반영) | pdm87 |
