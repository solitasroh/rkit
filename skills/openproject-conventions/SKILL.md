---
name: openproject-conventions
classification: capability
classification-reason: OpenProject 인스턴스별 규칙 제공, 모델 능력과 무관
description: |
  OpenProject MCP 도구 사용 규칙과 PDCA 워크플로 연동 패턴.
  OpenProject 관련 MCP 도구 사용 시 자동으로 참조됩니다.

  Triggers: OpenProject, 작업 패키지, work package, 시간 기록, time entry,
  프로젝트 현황, 작업 생성, OP, 태스크, task tracking
user-invocable: false
---

# OpenProject 사용 규칙

이 프로젝트는 OpenProject MCP 서버에 연결되어 있습니다.

## 유형/상태/우선순위 조회 규칙 (필수)

> **중요**: 유형, 상태, 우선순위, 활동 ID는 인스턴스마다 다릅니다.
> **절대 ID를 추측하거나 임의로 사용하지 마세요.**
> 반드시 아래 MCP 도구로 실제 값을 조회한 후 사용하세요.

| 필요한 정보 | 조회 도구 | 사용 시점 |
|-------------|----------|----------|
| 유형 (Task, Bug 등) | `list_types` | 작업 패키지 생성/필터링 전 |
| 상태 (New, Closed 등) | `list_statuses` | 상태 변경/필터링 전 |
| 우선순위 (Normal, High 등) | `list_priorities` | 작업 패키지 생성 전 |
| 시간 기록 활동 | `list_time_entry_activities` | 시간 기록 전 |
| 프로젝트 목록 | `list_projects` | 프로젝트 지정 전 |
| 사용자 목록 | `list_users` | 담당자 지정 전 |
| 역할 목록 | `list_roles` | 멤버십 관리 전 |

- 세션 내 첫 호출 시 한 번 조회하면 이후 재조회 불필요
- 조회 결과에서 이름과 ID를 매핑하여 사용할 것

## 작업 패키지 규칙

### 생성 규칙

- **담당자(assignee_id)는 반드시 지정**할 것 (미지정 금지)
- Bug 유형은 description에 **재현 절차**(재현 단계, 예상 결과, 실제 결과)를 포함할 것
- Feature 및 Task 유형은 description에 **기능 명세**(목적, 동작 설명)를 포함할 것
- 날짜 형식은 반드시 **YYYY-MM-DD** (예: 2026-04-15)

### 업데이트 규칙

- 상태 변경 시 comment에 변경 사유를 기록할 것
- 완료율(percentageDone) 변경은 10% 단위를 권장
- **삭제는 원칙적으로 금지** — 잘못 생성한 경우 상태를 Rejected로 변경

### 관계 규칙

- 작업 패키지 간 의존성이 있으면 **relation을 반드시 설정**
- 관계 유형: follows(선행), blocks(차단), relates(관련)
- follows 관계에는 lag(대기 근무일)를 설정할 수 있음

## 시간 기록 규칙

- 기본 활동 유형은 개발 관련 활동을 사용 (`list_time_entry_activities`로 조회)
- comment에는 **수행한 작업 내용을 간략히 기술** (예: "ADC 드라이버 코드 리뷰 및 수정")
- hours는 0.5 단위로 기록 권장 (0.5, 1.0, 1.5, ...)
- spent_on 날짜 형식: YYYY-MM-DD

## 검색/필터 참고

- `list_work_packages`의 필터 파라미터로 status, assignee, type 등을 지정 가능
- `search_work_packages`로 제목/ID 기반 검색 가능
- 날짜 기반 필터 시 ISO 8601 형식(YYYY-MM-DD) 사용

---

## PDCA↔OpenProject 연동 규칙

OpenProject MCP 서버가 연결되어 있을 때, PDCA 단계별로 아래 연동을 **제안**한다.
모든 제안은 사용자 확인 후 실행한다. 자동 실행하지 않는다.

### Case A/C: PDCA에서 시작 (Top-Down — 신규 기능, 리팩토링)

| PDCA 시점 | 제안 내용 | OP MCP 도구 |
|-----------|----------|-------------|
| /pdca plan 완료 | "OP에 [Feature/Task] 태스크를 생성하시겠습니까?" | create_work_package |
| /pdca do 시작 | "OP 태스크 상태를 In Progress로 변경하시겠습니까?" | update_work_package |
| /pdca analyze (< 90%) | "Gap 분석 결과를 OP comment로 기록하시겠습니까?" | update_work_package (comment) |
| /pdca report 완료 | "OP 태스크를 Closed로 변경하고 시간을 기록하시겠습니까?" | update_work_package + create_time_entry |

- Plan 문서의 제목/Executive Summary를 OP 태스크 subject/description에 자동 참조
- Feature 신규 개발: type=Feature, 리팩토링/개선: type=Task

### Case B/F: OP에서 시작 (Bottom-Up — 버그 수정, 기존 태스크)

| 시점 | 제안 내용 | 연동 |
|------|----------|------|
| OP 태스크 조회 후 | "이 태스크에 대해 PDCA를 시작하시겠습니까?" | /pdca plan {op-subject} |
| Bug 태스크일 때 | Plan에 재현 절차·예상/실제 결과를 자동 포함 | OP description → Plan context |
| PDCA 완료 후 | OP 상태 Closed + 수정 내용 comment | update_work_package |

- Bug의 description(재현 절차)을 PDCA Plan의 배경/문제 정의에 활용
- Feature/Task의 description을 Plan의 요구사항에 활용

### Case D: 빠른 수정 (PDCA 없이 OP만)

PDCA 없이 OP 도구를 직접 사용하는 것은 항상 허용.
자연어 요청("OP #1234 완료 처리", "시간 2시간 기록")에 직접 응답.

### Case E: 일일 업무 확인 (OP 조회 전용)

- `/op-status` — 전체 프로젝트 현황
- "내 할당 작업" — list_work_packages (filter: assignee=me)
- "기한 초과 작업" — list_work_packages (filter: overdue)

### MR↔OP 연동 규칙

- 브랜치명에 OP 번호 포함: `feature/op-{N}-{description}` 또는 `bugfix/op-{N}-{description}`
- 커밋 prefix: `[OP#N] type: description` → GitLab↔OP 양쪽 이력
- MR 제목: `[OP#N] type: description` → OP에서 MR 추적 가능
- MR merge 후: OP 태스크 Closed + 시간 기록 제안
- `/mr create` 시 브랜치명에서 `op-{N}` 자동 추출하여 MR 제목에 prefix 적용

### OP 미연결 시

OpenProject MCP 서버에 연결되어 있지 않으면:
- PDCA 단계별 OP 제안을 생략하고 PDCA만 진행
- OP 명령(/op-status 등) 실행 시: "OpenProject MCP 서버에 연결되어 있지 않습니다. plugin 설정에서 OpenProject URL과 API Key를 확인하세요." 안내
- mcukit 기본 기능에는 영향 없음
