---
name: op-sync-time
classification: workflow
classification-reason: 로컬 커밋 내역을 분석하여 OpenProject 시간에 동기화하는 에이전트 스킬
description: |
  Git 커밋 내역에 포함된 #time Xh 구문을 파싱하여 OpenProject에 직접 작업 시간을 기록합니다.
  사용자가 /op-sync-time 명령을 실행하면 이 스킬이 동작합니다.

  Triggers: op-sync-time, sync time, 시간 기록, 시간 동기화, time tracking
user-invocable: true
argument-hint: ""
---

# op-sync-time — Git 커밋 기반 시간 자동 기록

이 기능은 로컬 Git 로그를 분석하여 OpenProject MCP 도구를 통해 직접 수행 시간을 청구(Log time)한다.

## 1. 최근 커밋 지식 획득
`Bash` 도구를 사용하여 최근 커밋 내역 10개를 조회하라:
\`\`\`bash
git log -n 10 --oneline
\`\`\`
- 결과를 분석하여 `[OP#숫자]` 와 `#time 숫자h` 형식이 동시에 존재하는 커밋 메시지를 찾는다. (예: `[OP#123] 코드 리팩토링 #time 2.5h`)

## 2. 파싱 및 기록 대상 식별
1. 검색된 커밋 목록 중, 사용자가 기록을 승인하지 않은 새 커밋들만 대상으로 필터링한다. (사용자에게 "이 커밋들에 대해 {N}시간을 OP#XXX 에 등록하시겠습니까?" 와 같이 목록을 보여주며 컨펌을 요청한다.)
2. 사용자가 승인하면, 해당 태스크에 시간을 기록하기 위한 활동표(activities)를 조회한다. (`list_time_entry_activities` MCP 도구 사용)

## 3. OpenProject 시간에 기록하기
승인된 각 커밋마다 OpenProject MCP 도구를 통해 시간을 기록한다.
- `create_time_entry` 도구 사용.
- **workPackageId**: `[OP#N]` 에서 추출한 N
- **hours**: `#time Xh` 패턴에서 추출한 X (ISO 8601의 PT2H 형태 등 필요 시 지정된 표준 규약으로 환산, 기본적으로는 float 숫자로 전달)
- **activityId**: 개발(Development) 등에 해당하는 ID
- **comment**: 커밋 메시지의 요약본 (예: `[Sync] 코드 리팩토링 및 테스트 추가`)
- **spentOn**: 오늘 날짜 또는 커밋의 해당 날짜

## 4. 완료 보고
- 성공적으로 시간이 기록된 태스크와 시간 요약 리스트를 사용자에게 응답한다.
- 오류가 발생한 경우 오류 내역을 안내하고 종료한다.
