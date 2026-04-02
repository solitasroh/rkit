# mr-lifecycle Completion Report

> **Feature**: mr-lifecycle
> **Project**: mcukit v0.7.0
> **Date**: 2026-04-03
> **Author**: soojang.roh

---

## 1. Executive Summary

### 1.1 Overview

| Item | Detail |
|------|--------|
| Feature | GitLab MR 전체 라이프사이클 + AI 자동화 + PDCA 통합 |
| Duration | 2026-04-02 ~ 2026-04-03 (2 sessions) |
| PDCA Phases | Plan → Design → Do → Check → Act → Report |
| Match Rate | 99% → **100%** (1회 Design 역반영) |

### 1.2 Results

| Metric | Value |
|--------|-------|
| New Files | 4 (skill x2 + template x2) |
| Modified Files | 2 (ship, openproject-conventions) |
| Total Lines Added | +1,917 |
| Skills Added | 2 (58 → 60) |
| Templates Added | 2 (27 → 29) |
| Sub-commands | 7 (create, review, feedback, verify, status, approve, merge) |
| Code Changes | 0 (순수 markdown) |
| Gap Iterations | 1 (99% → 100%) |

### 1.3 Value Delivered

| Perspective | Result |
|-------------|--------|
| **Problem** | PDCA Check 이후 MR 생성→리뷰→피드백→승인→머지 팀 협업 구간이 없었음. 상용 도구(CodeRabbit, Qodo)도 comment→fix→reply→resolve 루프를 자동화하지 못함 |
| **Solution** | `/mr` 통합 스킬 7 sub-commands + `mr-conventions` capability + 도메인별 MR/Review templates. AI가 description 생성, 1차 리뷰, feedback 수정 제안, reply, verify까지 자동화 |
| **Function/UX** | 개발자: create→AI feedback 분석→수정→reply 자동. 리뷰어: AI 1차 리뷰→verify→resolve. Discussion thread 라이프사이클 완전 커버. 도메인별(MCU/MPU/WPF) 체크리스트 + Conventional Comments |
| **Core Value** | AI 검증(gap-detector) + AI 리뷰(도메인 특화) + 사람 리뷰(최종 판단) 3중 품질 게이트가 하나의 PDCA 흐름으로 완성. 업계 최초 "comment→fix→reply→resolve" AI 자동화 루프 |

---

## 2. PDCA Cycle Summary

### 2.1 Plan

- 업계 조사: bkit, gstack, CodeRabbit, Qodo, GitHub Copilot PR — 모두 MR 라이프사이클 미구현
- 6개 개발 케이스 정의: D1~D3 (개발자), R1~R4 (리뷰어)
- 팀 컨벤션 수집: 브랜치 네이밍, 커밋 prefix `[OP#N]`, Draft MR, squash merge
- AI 자동화 포인트 식별: description, review, feedback, reply, verify
- Conventional Comments 채택 (9 labels + 3 표준 + 6 도메인 decorators)
- MR description template: Kubernetes/React/GitLab CE/Embedded Artistry 사례 기반
- Review comment template: Google eng-practices + Conventional Comments 통합
- Plan 3차 수정: 케이스 분석 → AI 자동화 → template 추가

### 2.2 Design

- 3가지 옵션 → **Option C (Pragmatic)** 선택: 2 skill + 2 template
- `/pdca` 패턴과 동일한 통합 sub-command 구조
- PDCA Check↔Report 사이의 "비공식 구간"으로 MR 삽입 (상태 머신 미변경)
- glab CLI + `glab api` (Discussion REST API) 활용 설계

### 2.3 Do

| Step | File | Lines |
|:----:|------|:-----:|
| 1 | `templates/mr-description.template.md` | 91 |
| 2 | `templates/mr-review-comment.template.md` | 126 |
| 3 | `skills/mr-conventions/SKILL.md` | 118 |
| 4 | `skills/mr/SKILL.md` | 366 |
| 5 | `skills/ship/SKILL.md` (수정) | +6 |
| 6 | `skills/openproject-conventions/SKILL.md` (수정) | +8 |

### 2.4 Check

**1차 분석: 99%** — 8건 차이 (전부 additive improvement)
**2차 분석 (Design 업데이트 후): 100%**

8건 역반영 항목:
1. AI review rule #6 (before/after 코드 블록)
2. `MR 상태` 트리거 키워드
3. `(optional)` 표시 (match_rate, iteration_count)
4. op-{N} 자동 추출 상세
5. Changes 섹션 (file_change_list)
6. PDCA 연동 섹션 통합
7. Usage Examples 섹션
8. 실전 리뷰 예시 6건

---

## 3. Deliverables

### 3.1 Skills

| Skill | Type | Sub-commands | Triggers |
|-------|------|:------------:|:--------:|
| `mr` | workflow (invocable) | 7 | 11 keywords |
| `mr-conventions` | capability (auto) | — | 15 keywords |

### 3.2 Templates

| Template | Purpose | Sections |
|----------|---------|:--------:|
| `mr-description.template.md` | MR description (도메인별 Impact) | 11 |
| `mr-review-comment.template.md` | Review comment 형식 (Conventional Comments) | 6 |

### 3.3 MR Sub-commands

| Command | Role | AI 자동화 |
|---------|------|:---------:|
| `/mr create` | Draft MR + 리뷰어 | description 생성, 브랜치명 |
| `/mr review` | AI 1차 리뷰 + discussion | diff 분석, comment 생성 |
| `/mr feedback` | comment 대응 + reply | 분석, 수정 제안, reply |
| `/mr verify` | 수정 확인 + resolve | 비교 분석, resolve 식별 |
| `/mr status` | MR 상태 확인 | — |
| `/mr approve` | 승인 | 사전 확인 |
| `/mr merge` | squash merge | 사전 확인, PDCA/OP 연동 |

### 3.4 Conventional Comments

- 9 labels: praise, nitpick, suggestion, issue, todo, question, thought, chore, note
- 9 decorators: blocking, non-blocking, if-minor + safety, memory, timing, misra, dt-binding, mvvm

---

## 4. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `/pdca` 패턴 통합 skill | `/mr` 단일 진입점 | 사용자 학습 비용 최소화, 일관된 UX |
| MR은 PDCA 비공식 구간 | 상태 머신 미변경 | 기존 20개 전이 호환, 1인 개발 호환 |
| Conventional Comments | 업계 표준 채택 | `[Critical]` 독자 형식 대신 검증된 표준 |
| 도메인 decorator 6개 | mcukit 고유 확장 | MCU(safety/memory/timing/misra), MPU(dt-binding), WPF(mvvm) |
| AI 보조 원칙 | 제안만, 사람 확인 | 자동 실행 위험 방지 |
| Template 별도 파일 | imports 참조 | 재사용 + 유지보수 용이 |

---

## 5. Research & Innovation

### 5.1 업계 조사

| 조사 대상 | 발견 | mcukit 적용 |
|-----------|------|------------|
| CodeRabbit, Qodo, Copilot | MR description + 1차 리뷰 자동화 있음 | 기본 기능 포함 |
| 모든 상용 도구 | comment→fix→reply→resolve 루프 미자동화 | **차별화 포인트** |
| Google eng-practices | Kind tone, explain why, praise 필수 | AI 리뷰 규칙 반영 |
| Conventional Comments | 9 labels + 3 decorators 표준 | 전면 채택 + 도메인 확장 |
| Kubernetes/React/GitLab CE | MR template 사례 | 통합 template 설계 |
| Embedded Artistry | Hardware/Memory/Toolchain 섹션 | MCU/MPU Impact 섹션 |
| Linux Kernel | Signed-off-by, Fixes: 태그 | [OP#N] prefix 설계 참조 |

### 5.2 mcukit 고유 혁신

| 혁신 | 설명 |
|------|------|
| Comment→Fix→Reply→Resolve 자동화 | 업계 최초. CodeRabbit/Qodo도 미지원 |
| 도메인별 리뷰 체크리스트 | MCU(MISRA, ISR, Flash/RAM), MPU(DT, ABI), WPF(MVVM, Binding) |
| PDCA↔MR 자연 통합 | Check ≥ 90% → MR → merge → Report 흐름 |
| OP↔GitLab 양방향 추적 | `[OP#N]` prefix로 커밋/MR/태스크 자동 연결 |

---

## 6. Lessons Learned

| 항목 | 교훈 |
|------|------|
| 업계 조사 우선 | 상용 도구 분석으로 차별화 포인트(comment→fix→reply→resolve)를 발견 |
| Plan 반복 수정 | 3차 수정(케이스 분석→AI 자동화→template)으로 깊이 확보 |
| Conventional Comments | 독자 형식 대신 업계 표준 채택이 장기적으로 유리 |
| Design 역반영 | 구현에서 개선한 부분을 Design에 동기화하여 100% 달성 |
| 리뷰어 케이스 | 개발자뿐 아니라 리뷰어 관점의 스킬(review, verify)이 워크플로 완성에 필수 |
