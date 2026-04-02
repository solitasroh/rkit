# openproject-integration Design Document

> **Summary**: Option C (Pragmatic) — 4 skill + 구조화된 PDCA↔OP conventions로 6개 케이스 커버
>
> **Project**: mcukit
> **Version**: 0.7.0
> **Author**: soojang.roh
> **Date**: 2026-04-02
> **Status**: Draft
> **Planning Doc**: [openproject-integration.plan.md](../01-plan/features/openproject-integration.plan.md)

---

## 1. Architecture Overview

### 1.1 선택된 설계: Option C — Pragmatic Balance

4개 skill + 1개 설정 파일 + plugin.json 수정으로 구성.

```
mcukit/
├── skills/
│   ├── openproject-conventions/SKILL.md  ← capability (auto-trigger)
│   ├── op-status/SKILL.md               ← user-invocable
│   ├── op-create-task/SKILL.md          ← user-invocable
│   └── op-task/SKILL.md                 ← user-invocable (신규)
├── .mcp.json                            ← OpenProject MCP 서버 설정
└── .claude-plugin/
    └── plugin.json                      ← userConfig 3 필드 추가
```

### 1.2 컴포넌트 역할

```
┌─────────────────────────────────────────────────┐
│ Claude Code Session                              │
│                                                  │
│  ┌──────────────┐    ┌────────────────────────┐ │
│  │ PDCA Skills   │    │ OpenProject Skills     │ │
│  │ /pdca plan    │───▶│ conventions (auto)     │ │
│  │ /pdca do      │    │ /op-status             │ │
│  │ /pdca report  │◀───│ /op-create-task        │ │
│  └──────────────┘    │ /op-task               │ │
│                       └───────────┬────────────┘ │
│                                   │              │
│                    ┌──────────────▼──────────┐   │
│                    │ .mcp.json               │   │
│                    │ openproject MCP (HTTP)   │   │
│                    └──────────────┬──────────┘   │
└───────────────────────────────────┼──────────────┘
                                    │ HTTP
                    ┌───────────────▼──────────┐
                    │ OpenProject MCP Server    │
                    │ (Docker, 외부 운영)        │
                    └───────────────┬──────────┘
                                    │
                    ┌───────────────▼──────────┐
                    │ OpenProject Instance      │
                    └──────────────────────────┘
```

---

## 2. File Specifications

### 2.1 `skills/openproject-conventions/SKILL.md`

**역할**: OpenProject MCP 도구 사용 규칙 + 6개 케이스별 PDCA↔OP 연동 패턴

```yaml
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
```

**내용 구성:**

| Section | 내용 | 출처 |
|---------|------|------|
| 유형/상태/우선순위 조회 규칙 | ID 하드코딩 금지, MCP 도구로 조회 필수 | rt-op-plugin (그대로) |
| 작업 패키지 규칙 | 생성/수정/관계/삭제 규칙 | rt-op-plugin (그대로) |
| 시간 기록 규칙 | 활동 유형, 0.5시간 단위, comment 필수 | rt-op-plugin (그대로) |
| 검색/필터 참고 | filter, search 사용법 | rt-op-plugin (그대로) |
| **PDCA↔OP 연동 규칙** | 6개 케이스별 매핑 (신규) | Plan 섹션 5.3 |
| **OP 미연결 시 동작** | graceful 안내 후 PDCA만 계속 (신규) | Plan NFR-01 |

**PDCA↔OP 연동 규칙 상세:**

```markdown
## PDCA↔OpenProject 연동 규칙

OpenProject MCP 서버가 연결되어 있을 때, PDCA 단계별로 아래 연동을 **제안**한다.
모든 제안은 사용자 확인 후 실행한다. 자동 실행하지 않는다.

### Top-Down: PDCA에서 시작 (Case A/C)

| PDCA 시점 | 제안 내용 | OP MCP 도구 |
|-----------|----------|-------------|
| /pdca plan 완료 | "OP에 [Feature/Task] 태스크를 생성하시겠습니까?" | create_work_package |
| /pdca do 시작 | "OP 태스크 상태를 In Progress로 변경하시겠습니까?" | update_work_package |
| /pdca analyze (< 90%) | "Gap 분석 결과를 OP comment로 기록하시겠습니까?" | update_work_package (comment) |
| /pdca report 완료 | "OP 태스크를 Closed로 변경하고 시간을 기록하시겠습니까?" | update_work_package + create_time_entry |

- Plan 문서의 제목/Executive Summary를 OP 태스크 subject/description에 자동 참조
- Feature 신규 개발: type=Feature, 리팩토링/개선: type=Task

### Bottom-Up: OP에서 시작 (Case B/F)

| 시점 | 제안 내용 | 연동 |
|------|----------|------|
| OP 태스크 조회 후 | "이 태스크에 대해 PDCA를 시작하시겠습니까?" | /pdca plan {op-subject} |
| Bug 태스크일 때 | Plan에 재현 절차·예상/실제 결과를 자동 포함 | OP description → Plan context |
| PDCA 완료 후 | OP 상태 Closed + 수정 내용 comment | update_work_package |

- Bug의 description(재현 절차)을 PDCA Plan의 배경/문제 정의에 활용
- Feature/Task의 description을 Plan의 요구사항에 활용

### OP 단독 사용 (Case D/E)

PDCA 없이 OP 도구를 직접 사용하는 것은 항상 허용.
자연어 요청("OP #1234 완료 처리", "시간 2시간 기록")에 직접 응답.

### OP 미연결 시

OpenProject MCP 서버에 연결되어 있지 않으면:
- PDCA 단계별 OP 제안을 생략하고 PDCA만 진행
- OP 명령(/op-status 등) 실행 시: "OpenProject MCP 서버에 연결되어 있지 않습니다. plugin 설정에서 OpenProject URL과 API Key를 확인하세요." 안내
- mcukit 기본 기능에는 영향 없음
```

### 2.2 `skills/op-status/SKILL.md`

**역할**: 프로젝트/태스크 현황 조회 (rt-op-plugin `commands/op-status.md` 변환)

```yaml
---
name: op-status
classification: workflow
classification-reason: OpenProject MCP 도구를 사용한 구조화된 프로젝트 현황 조회
description: |
  OpenProject 프로젝트 현황을 요약합니다.
  프로젝트별 열린 작업 수, 기한 초과 작업을 표 형태로 보여줍니다.
  인자 없이 실행하면 전체 프로젝트, 인자가 있으면 해당 프로젝트만 조회합니다.

  Triggers: op-status, 프로젝트 현황, project status, 작업 현황, 기한 초과,
  overdue, 열린 작업, open tasks, OP 현황
user-invocable: true
argument-hint: "[project-identifier]"
---
```

**내용**: rt-op-plugin `commands/op-status.md`의 절차/오류처리/출력형식을 그대로 포함.

변환 시 변경점:
- `allowed-tools` 제거 (skill은 MCP 도구 제한 없음)
- `Triggers:` 추가 (자연어 자동 트리거)
- 나머지 절차/오류처리/출력형식은 동일

### 2.3 `skills/op-create-task/SKILL.md`

**역할**: 대화형 태스크 생성 (rt-op-plugin `commands/op-create-task.md` 변환)

```yaml
---
name: op-create-task
classification: workflow
classification-reason: OpenProject MCP 도구를 사용한 구조화된 태스크 생성 워크플로
description: |
  OpenProject에 새 작업 패키지를 대화형으로 생성합니다.
  프로젝트, 유형, 우선순위, 담당자를 MCP 도구로 조회하여 선택하고,
  팀 규칙(담당자 필수, Bug는 재현 절차 포함)을 자동 적용합니다.

  Triggers: op-create-task, 태스크 생성, 작업 생성, create task, 새 작업,
  OP 태스크 만들어, work package 생성, 작업 만들어줘
user-invocable: true
argument-hint: "[project-identifier]"
---
```

**내용**: rt-op-plugin `commands/op-create-task.md`의 8-step 절차를 그대로 포함.

변환 시 변경점:
- `allowed-tools` 제거
- `Triggers:` 추가
- 절차 앞에 `## PDCA 연동` 섹션 추가: PDCA Plan 활성화 시 Plan 제목/요약을 subject/description에 자동 참조
- Bug 재현 절차 템플릿을 Step 7에 전문 포함

### 2.4 `skills/op-task/SKILL.md` (신규)

**역할**: 기존 태스크 조회 + 상태 변경 + comment + 시간 기록

```yaml
---
name: op-task
classification: workflow
classification-reason: OpenProject MCP 도구를 사용한 구조화된 태스크 관리 워크플로
description: |
  OpenProject 태스크를 조회하고 관리합니다.
  상태 변경, comment 추가, 시간 기록, 담당자 변경을 지원합니다.
  "my"를 인자로 주면 본인 할당 태스크 목록을 조회합니다.

  Triggers: op-task, 태스크 조회, 작업 상세, task detail, OP #,
  상태 변경, 완료 처리, 시간 기록, time entry, comment 추가,
  내 작업, my tasks, 할당된 작업, 내 할일
user-invocable: true
argument-hint: "[work-package-id or 'my']"
---
```

**내용 구조:**

```markdown
# op-task — 태스크 관리

OpenProject MCP 도구를 사용하여 태스크를 조회하고 관리한다.

## 사용법

- `/op-task 1234` — 태스크 #1234 상세 조회
- `/op-task my` — 내 할당 태스크 목록
- "OP #1234 완료 처리해줘" — 자연어 상태 변경
- "시간 2시간 기록해줘" — 자연어 시간 기록

## 절차

### 태스크 상세 조회 (인자: work-package-id)

1. `get_work_package` (또는 `search_work_packages`)로 태스크를 조회한다.
   - 숫자 ID: 직접 조회
   - 텍스트: `search_work_packages`로 검색
2. 상세 정보를 테이블로 출력한다:
   | 항목 | 값 |
   |------|-----|
   | ID | #{id} |
   | 프로젝트 | {project} |
   | 제목 | {subject} |
   | 유형 | {type} |
   | 상태 | {status} |
   | 우선순위 | {priority} |
   | 담당자 | {assignee} |
   | 시작일 | {start_date} |
   | 기한 | {due_date} |
   | 완료율 | {percentageDone}% |
3. 설명이 있으면 요약하여 표시한다.
4. 다음 동작을 제안한다: "상태 변경 / comment 추가 / 시간 기록 / PDCA 시작 중 원하시는 게 있나요?"

### 내 할당 태스크 (인자: 'my')

1. `list_work_packages`로 조회한다 (filter: assignee=current user, status=open).
2. 목록을 테이블로 출력한다:
   | # | 프로젝트 | 제목 | 유형 | 우선순위 | 기한 |
   |---|---------|------|------|---------|------|
3. 기한 초과 태스크는 기한을 **굵게** 표시한다.
4. 태스크가 0개이면: "할당된 열린 작업이 없습니다." 출력.

### 상태 변경

1. `list_statuses`로 가용 상태 목록 조회
2. 사용자에게 선택하게 함
3. `update_work_package` (status_id)
4. **팀 규칙**: comment에 변경 사유 기록 필수

### comment 추가

1. 사용자에게 comment 내용 입력받음
2. `update_work_package` (comment)

### 시간 기록

1. `list_time_entry_activities`로 활동 유형 조회
2. 시간(hours), 활동 유형, comment 입력
3. `create_time_entry`
4. **팀 규칙**: 0.5시간 단위, comment에 작업 내용 기술

## PDCA 연동

태스크 상세 조회 후 사용자가 "PDCA 시작"을 선택하면:
- Bug 태스크: description의 재현 절차·예상/실제 결과를 PDCA Plan 컨텍스트로 전달
- Feature/Task 태스크: subject + description을 Plan 요구사항 컨텍스트로 전달
- `/pdca plan {feature-name}` 실행을 안내 (feature-name은 OP subject 기반)

PDCA Report 완료 후 OP 태스크가 연결되어 있으면:
- "OP 태스크 #{id}를 Closed로 변경하시겠습니까?" 제안
- "시간을 기록하시겠습니까?" 제안

## 오류 처리

- MCP 연결 오류: "OpenProject MCP 서버에 연결할 수 없습니다. /mcp 명령으로 서버 상태를 확인하세요."
- 인증 오류 (401): "API 키가 유효하지 않습니다. 플러그인을 재설치하여 API 키를 다시 입력하세요."
- 권한 오류 (403): "해당 태스크에 대한 접근 권한이 없습니다. OpenProject 관리자에게 권한을 요청하세요."
- 태스크 미발견 (404): "태스크 #{id}를 찾을 수 없습니다. 번호를 확인해주세요."
```

### 2.5 `.mcp.json`

```json
{
  "mcpServers": {
    "openproject": {
      "type": "http",
      "url": "${user_config.openproject_mcp_url}",
      "headers": {
        "X-OpenProject-URL": "${user_config.openproject_url}",
        "X-OpenProject-API-Key": "${user_config.openproject_api_key}"
      }
    }
  }
}
```

### 2.6 `.claude-plugin/plugin.json` 변경

기존 `userConfig` 없음 → 3개 필드 추가:

```json
{
  "userConfig": {
    "openproject_mcp_url": {
      "type": "string",
      "title": "OpenProject MCP Server URL",
      "description": "OpenProject MCP 서버 주소 (예: http://10.10.20.33:9090/mcp)",
      "required": true
    },
    "openproject_url": {
      "type": "string",
      "title": "OpenProject Instance URL",
      "description": "OpenProject 인스턴스 주소 (예: http://10.10.20.32:8080)",
      "required": true
    },
    "openproject_api_key": {
      "type": "string",
      "title": "OpenProject API Key",
      "description": "본인의 OpenProject API 토큰 (My account → Access tokens)",
      "required": true,
      "sensitive": true
    }
  }
}
```

---

## 3. Implementation Order

| Step | File | 의존 | 설명 |
|:----:|------|:----:|------|
| 1 | `.claude-plugin/plugin.json` | — | userConfig 3 필드 추가 |
| 2 | `.mcp.json` | Step 1 | MCP 서버 엔드포인트 (userConfig 참조) |
| 3 | `skills/openproject-conventions/SKILL.md` | — | OP 규칙 + PDCA↔OP 매핑 |
| 4 | `skills/op-status/SKILL.md` | Step 3 | 프로젝트 현황 조회 |
| 5 | `skills/op-create-task/SKILL.md` | Step 3 | 태스크 생성 |
| 6 | `skills/op-task/SKILL.md` | Step 3 | 태스크 관리 (신규) |

---

## 4. 케이스별 검증 시나리오

| Case | 시나리오 | 기대 결과 |
|:----:|---------|----------|
| A | `/pdca plan feature` → 완료 | "OP에 Feature 태스크를 생성하시겠습니까?" 제안 |
| B | `/op-task 1234` (Bug) → "PDCA 시작" | Bug description을 참조하여 `/pdca plan` 시작 |
| C | `/pdca plan refactor` → 완료 | "OP에 Task 태스크를 생성하시겠습니까?" 제안 |
| D | "OP #5678 완료 처리해줘" | `update_work_package` 직접 실행 |
| E | `/op-status` | 프로젝트 현황 테이블 출력 |
| E | "내 할당 작업" | `/op-task my` 자동 트리거 |
| F | `/op-task 3456` → "PDCA로 진행" | OP 컨텍스트 참조하여 PDCA Plan 시작 |
| — | OP 미연결 + `/pdca plan` | OP 제안 없이 PDCA만 정상 진행 |
