# openproject-integration Planning Document

> **Summary**: rt-op-plugin의 OpenProject MCP 연동을 mcukit에 통합하고, 다양한 개발 케이스에서 PDCA↔OP 워크플로를 연결
>
> **Project**: mcukit
> **Version**: 0.7.0
> **Author**: soojang.roh
> **Date**: 2026-04-02
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | OpenProject 연동이 별도 플러그인으로 분리되어 있고, 신규 기능/버그 수정/리팩토링 등 다양한 개발 케이스에서 PDCA와 태스크 관리가 단절됨 |
| **Solution** | rt-op-plugin을 mcukit skill로 통합하고, 케이스별 PDCA↔OP 연동 패턴을 conventions skill에 정의 |
| **Function/UX Effect** | 신규 기능은 Plan→OP태스크 자동 제안, 버그는 OP Bug→PDCA 바로 시작, 완료 시 시간 기록까지 자연스럽게 흐름 |
| **Core Value** | 어떤 개발 케이스든 PDCA 사이클과 OpenProject 추적이 끊김 없이 연결되는 단일 워크플로 |

---

## 1. Overview

### 1.1 Purpose

mcukit PDCA 워크플로와 OpenProject 프로젝트 관리를 단일 플러그인에서 연결한다. 신규 기능 개발, 버그 수정, 리팩토링, OP 기반 작업 등 **다양한 개발 케이스**에서 자연스러운 워크플로를 제공한다.

### 1.2 Background

- `solitasroh/rt-op-plugin` v1.0.1: skill 1개, command 2개, MCP 설정
- OpenProject MCP 서버는 Docker로 이미 운영 중
- MCP 도구: `list_projects`, `list_work_packages`, `create_work_package`, `update_work_package`, `list_types`, `list_statuses`, `list_priorities`, `list_users`, `create_time_entry`, `search_work_packages` 등
- 현재 문제: 개발 케이스별로 PDCA와 OP를 수동으로 오가며 관리해야 함

---

## 2. 개발 케이스 분석

### 2.1 케이스별 워크플로 매핑

#### Case A: 신규 기능 개발 (PDCA → OP)

개발자가 새 기능을 기획하고 PDCA로 진행하는 **Top-Down** 흐름.

```
/pdca plan uart-dma
  → Plan 완료 시: "OP에 Feature 태스크를 생성하시겠습니까?" 제안
  → /op-create-task (type: Feature, subject: Plan 제목 자동 참조)

/pdca design uart-dma → /pdca do uart-dma
  → Do 시작 시: "OP 태스크를 In Progress로 변경하시겠습니까?" 제안
  → update_work_package (status: In Progress)

/pdca analyze uart-dma
  → Check < 90%: "OP 태스크에 Gap 분석 결과를 comment로 기록하시겠습니까?" 제안
  → Check ≥ 90%: 다음 단계(Report)로 진행

/pdca report uart-dma
  → Report 완료 시: "OP 태스크를 Closed로 변경하고 시간을 기록하시겠습니까?" 제안
  → update_work_package (status: Closed) + create_time_entry
```

#### Case B: 버그 수정 (OP → PDCA)

OP에 등록된 버그를 Claude Code에서 수정하는 **Bottom-Up** 흐름.

```
/op-status  또는  "내 할당 작업 보여줘"
  → OP에서 Bug #1234 확인

"Bug #1234 수정하자"  또는  /op-task 1234
  → OP에서 Bug 상세 조회 (subject, description, 재현 절차)
  → "이 버그에 대해 PDCA Plan을 생성하시겠습니까?" 제안
  → /pdca plan bug-1234 (OP Bug 컨텍스트 자동 참조)

/pdca do bug-1234 → 수정 → /pdca analyze bug-1234
  → Report 완료 시: OP Bug 상태 Closed + comment에 수정 내용 기록
```

#### Case C: 리팩토링/개선 (PDCA → OP)

PDCA로 리팩토링을 진행하면서 OP에 추적하는 흐름. Case A와 유사하나 OP type이 다름.

```
/pdca plan cleanup-hal-layer
  → Plan 완료 시: OP에 Task 타입으로 생성 제안 (Feature 아닌 Task)
  → 이후 Case A와 동일 흐름
```

#### Case D: 빠른 수정 (OP only, PDCA 없음)

PDCA 없이 간단히 처리하고 OP만 업데이트하는 흐름.

```
"OP #5678 상태 완료로 바꿔줘"
  → update_work_package (status: Closed)
  → "시간 기록도 하시겠습니까?" 제안

"OP에 새 태스크 하나 만들어줘"
  → /op-create-task (대화형)
```

#### Case E: 일일 업무 확인 (OP 조회 전용)

```
/op-status
  → 전체 프로젝트 현황 테이블

"내 작업 목록 보여줘"  또는  "기한 초과 작업 확인"
  → list_work_packages (filter: assignee=me, overdue)

"이번 주 시간 기록 현황"
  → list_time_entries (filter: this week)
```

#### Case F: 기존 OP 태스크를 PDCA로 시작 (OP → PDCA 전환)

```
"OP #3456 작업을 PDCA로 진행하고 싶어"
  → OP에서 #3456 상세 조회
  → subject, description을 참조하여 /pdca plan 자동 시작
  → OP 태스크와 PDCA feature를 연결 (conventions skill이 컨텍스트 유지)
```

### 2.2 케이스 매트릭스

| Case | 시작점 | PDCA | OP 태스크 | OP 상태 변경 | 시간 기록 | 빈도 |
|:----:|--------|:----:|:---------:|:----------:|:--------:|:----:|
| A | PDCA Plan | Full | 생성 | New→InProgress→Closed | O | 높음 |
| B | OP Bug | Full | 기존 참조 | InProgress→Closed | O | 높음 |
| C | PDCA Plan | Full | 생성 (Task) | New→InProgress→Closed | O | 중간 |
| D | OP/자연어 | 없음 | 생성/업데이트 | 직접 변경 | 선택 | 높음 |
| E | OP 조회 | 없음 | 조회만 | 없음 | 없음 | 매일 |
| F | OP 태스크 | Full | 기존 참조 | InProgress→Closed | O | 중간 |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Priority | Requirement | Description |
|----|:--------:|-------------|-------------|
| FR-01 | P0 | OpenProject conventions skill | MCP 도구 사용 규칙 + 케이스별 PDCA↔OP 매핑 규칙 (capability, auto-trigger) |
| FR-02 | P0 | op-status skill | 프로젝트/태스크 현황 조회 (user-invocable) |
| FR-03 | P0 | op-create-task skill | 대화형 태스크 생성 (user-invocable) |
| FR-04 | P0 | op-task skill | OP 태스크 상세 조회 + 상태 변경 + comment (user-invocable, Case B/D/F 지원) |
| FR-05 | P0 | userConfig + .mcp.json | MCP 서버 URL, OP 인스턴스 URL, API 키 파라미터화 |
| FR-06 | P1 | PDCA 단계별 OP 제안 | conventions skill에 6개 케이스별 연동 패턴 정의 |
| FR-07 | P1 | 자연어 트리거 | "내 작업", "기한 초과", "시간 기록" 등 자연어로 OP 도구 자동 활성화 |

### 3.2 Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-01 | 선택적 확장 | OP 미설정 시 기존 mcukit 기능에 영향 없음. OP 관련 skill은 MCP 미연결 시 graceful 안내 |
| NFR-02 | 보안 | API 키는 userConfig sensitive 필드. 코드/로그 노출 금지 |
| NFR-03 | 아키텍처 일관성 | skills/ 구조 사용 (commands/ 미사용) |
| NFR-04 | 제안 방식 | 모든 OP 연동은 **자동 실행이 아닌 제안**. 사용자 확인 후 실행 |

---

## 4. Scope

### 4.1 In Scope

| Source (rt-op-plugin) | Target (mcukit) | 변환 |
|----------------------|-----------------|------|
| `skills/openproject-conventions/SKILL.md` | `skills/openproject-conventions/SKILL.md` | 6개 케이스별 PDCA↔OP 매핑 추가 |
| `commands/op-status.md` | `skills/op-status/SKILL.md` | command → skill 변환 |
| `commands/op-create-task.md` | `skills/op-create-task/SKILL.md` | command → skill 변환 |
| — (신규) | `skills/op-task/SKILL.md` | 태스크 상세/상태변경/comment (Case B/D/F) |
| `.mcp.json` | `.mcp.json` | URL 파라미터화 |
| — | `.claude-plugin/plugin.json` | userConfig 3 필드 추가 |

### 4.2 Out of Scope

| Item | Reason |
|------|--------|
| Docker 인프라 | 이미 별도 서버 운영 |
| README/GUIDE 업데이트 | 다음 버전 범프에서 일괄 |
| rt-op-plugin 리포 삭제 | 통합 검증 완료 후 별도 |
| PDCA hook 자동 연동 코드 | v1은 skill 가이드(제안)만. hook 자동화는 v2 |

---

## 5. Design Decisions

### 5.1 command → skill 변환

| 비교 항목 | commands/ (rt-op-plugin) | skills/ (mcukit) |
|-----------|------------------------|-----------------|
| mcukit 일관성 | 새 디렉토리 필요 | 기존 54개 skill과 동일 |
| 자동 트리거 | 불가 | `Triggers:` frontmatter |
| **결론** | — | **채택** |

### 5.2 op-task skill 추가 이유

rt-op-plugin에는 **조회(op-status)**와 **생성(op-create-task)**만 있음. 실제 워크플로에서 필요한 **상태 변경, comment 추가, 시간 기록**이 빠져 있음. Case B/D/F를 커버하려면 기존 태스크를 조작하는 skill이 필수.

| 기능 | op-status | op-create-task | op-task (신규) |
|------|:---------:|:--------------:|:-------------:|
| 프로젝트 현황 조회 | O | — | — |
| 태스크 생성 | — | O | — |
| 태스크 상세 조회 | — | — | O |
| 상태 변경 | — | — | O |
| comment 추가 | — | — | O |
| 시간 기록 | — | — | O |
| 담당자 변경 | — | — | O |

### 5.3 PDCA↔OP conventions 매핑 설계

openproject-conventions skill에 포함할 케이스별 규칙:

```
## PDCA↔OpenProject 연동 규칙

### Case A/C: PDCA에서 시작하는 경우 (Top-Down)
- /pdca plan 완료 → "OP에 [Feature|Task] 태스크를 생성하시겠습니까?" 제안
  - subject: Plan 문서 제목 참조
  - description: Executive Summary 4관점 테이블 포함
- /pdca do 시작 → "OP 태스크 상태를 In Progress로 변경하시겠습니까?" 제안
- /pdca analyze (< 90%) → "OP 태스크에 Gap 분석 결과를 comment로 기록하시겠습니까?" 제안
- /pdca report 완료 → "OP 태스크를 Closed로 변경하고 시간을 기록하시겠습니까?" 제안

### Case B/F: OP에서 시작하는 경우 (Bottom-Up)
- OP 태스크 조회 후 → "이 태스크에 대해 PDCA를 시작하시겠습니까?" 제안
  - Bug: Plan에 재현 절차·예상/실제 결과를 자동 포함
  - Feature/Task: subject+description을 Plan 컨텍스트로 활용
- PDCA 완료 → OP 태스크 상태 Closed + 수정 내용 comment

### Case D: PDCA 없이 OP만 사용
- 자연어로 OP 도구 직접 호출 (제한 없음)
- "OP #1234 완료 처리" → update_work_package
- "시간 1.5시간 기록" → create_time_entry

### 공통: 제안 규칙
- 모든 OP 연동은 AskUserQuestion으로 확인 후 실행
- OP MCP 서버 미연결 시: "OpenProject 서버에 연결되어 있지 않습니다" 안내 후 PDCA만 계속
```

### 5.4 userConfig 설계

```json
{
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
```

---

## 6. Affected Files

### 6.1 New Files (5개)

| File | Purpose | 커버 케이스 |
|------|---------|:----------:|
| `skills/openproject-conventions/SKILL.md` | OP 규칙 + 6개 케이스별 PDCA↔OP 매핑 | A~F 전체 |
| `skills/op-status/SKILL.md` | 프로젝트/태스크 현황 조회 | D, E |
| `skills/op-create-task/SKILL.md` | 대화형 태스크 생성 | A, C, D |
| `skills/op-task/SKILL.md` | 태스크 상세/상태변경/comment/시간기록 | B, D, F |
| `.mcp.json` | OP MCP 서버 엔드포인트 | 전체 |

### 6.2 Modified Files (1개)

| File | Change |
|------|--------|
| `.claude-plugin/plugin.json` | userConfig에 3개 필드 추가 |

---

## 7. Success Criteria

| Criteria | 커버 케이스 | Target |
|----------|:----------:|:------:|
| `/op-status` → 프로젝트 현황 정상 반환 | E | Pass |
| `/op-create-task` → 태스크 생성 성공 | A, C, D | Pass |
| `/op-task 1234` → 태스크 상세 + 상태 변경 | B, D, F | Pass |
| "내 할당 작업" 자연어 → skill 자동 트리거 | E | Pass |
| `/pdca plan` 완료 후 → OP 태스크 생성 제안 발생 | A | Pass |
| OP Bug 조회 후 → PDCA Plan 시작 제안 발생 | B | Pass |
| `/pdca report` 완료 후 → OP Closed + 시간 기록 제안 | A, B, C, F | Pass |
| OP 미설정 시 → mcukit PDCA 정상 동작 | — | Pass |
