---
name: op-standup
classification: workflow
classification-reason: OpenProject 일일 스탠드업 보고서 자동 생성 에이전트 스킬
description: |
  어제와 오늘 처리한 OpenProject 작업과 커밋 내역을 분석하여 스탠드업 보고서를 마크다운 형태로 반환합니다.
  사용자가 /op-standup 명령을 실행하면 이 스킬이 동작합니다.

  Triggers: op-standup, 스탠드업, standup, 데일리 스크럼, 아침 회의록, 
  일일 보고서, daily report, 오늘 할 일
user-invocable: true
argument-hint: ""
---

# op-standup — 일일 스탠드업 보고서 생성기

이 기능은 OpenProject MCP 도구와 Bash 환경을 활용하여 팀의 일일 스탠드업 회의록을 작성한다.

## 1. 최근 커밋 지식 획득
`Bash` 도구를 사용하여 최근 커밋 내역을 조회하라:
\`\`\`bash
git log --since="yesterday" --oneline
\`\`\`
- 결과를 로드하여 사용자의 최근 작업 범위를 파악하라.

## 2. OpenProject 상태 조회
OpenProject MCP 도구 모음을 사용하여 다음 정보를 가져온다. (OpenProject URL 및 API 키는 시스템 내부에서 MCP 구동 시 이미 주입되어 있다. 연결 불가 시 플러그인 설정 가이드 제공)
1. `list_work_packages`를 호출하되, `assignee=me` 필터를 적용하여 현재 사용자에게 할당된 태스크를 가져온다.
2. (필요 시) `list_statuses`를 통해 "Closed"와 "In Progress/Open" 상태의 의미를 분리한다.

## 3. 보고서 형식 생성
아래 내용을 깔끔한 마크다운 형식으로 작성하여 사용자에게 반환하라.
- **보고서 양식 예시**:

\`\`\`markdown
======================================================
🎙️ DAILY STANDUP REPORT (YYYY. M. D.)
======================================================

## ⏪ 어제/오늘 완료한 일 (Yesterday / Completed)
- [OP#N] 태스크 제목 ✅ (완료 또는 merge 완료된 커밋 기록 포함)
  *(관련 커밋 해시 요약)*

## ⏩ 현재 진행/오늘 할 일 (Today)
- [OP#M] 태스크 제목 🏃

## 🚧 블로커 (Blockers / Issues)
- (특별한 이슈가 있는 경우 기재, 없으면 '없음')

======================================================
\`\`\`

## 제약 사항
- 절대 임의의 태스크를 만들어내거나 추측하지 말 것.
- MCP 도구 조회 실패 시, 플러그인 또는 MCP 서버 설정을 점검해달라는 친절한 에러 메시지를 응답할 것.
