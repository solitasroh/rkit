---
name: op-standup
classification: workflow
classification-reason: OpenProject 일일 스탠드업 보고서 자동 생성 스크립트 실행
description: |
  어제 완료한 OP 작업, 오늘 할 작업, 하루 동안의 커밋 내역을 종합하여 일일 스탠드업 보고서를 마크다운 형태로 생성합니다.
  /op-standup 명령어나 스탠드업 요청 시 호출됩니다.

  Triggers: op-standup, 스탠드업, standup, 데일리 스크럼, 아침 회의록, 
  일일 보고서, daily report, 오늘 할 일
user-invocable: true
argument-hint: ""
---

# op-standup — 일일 스탠드업 생성기

사용자가 스탠드업 보고서를 요청하거나 `/op-standup` 명령을 내리면 다음 절차에 따라 터미널 스크립트를 실행한다.

## 절차

1. 특별한 인자 검증 없이, 터미널 환경에서 다음 명령어를 즉시 실행하라:
   \`\`\`bash
   node scripts/op-standup.js
   \`\`\`

2. 스크립트 실행이 정상적으로 완료되면(출력 결과 수집), 터미널 표준 출력(stdout)으로 반환된 마크다운 결과물을 그대로 사용자에게 응답 텍스트로 예쁘게 렌더링해주어 슬랙이나 회의록에 곧바로 복사할 수 있게 지원하라.

## 유의사항

- 이 기능은 MCP 통신으로 LLM 토큰을 소진하는 대신 로컬 `op-standup.js` 제로 토큰 스크립트를 사용하여 OP API와 Git Log를 백그라운드 매쉬업(Mashup)합니다. 절대 자체적으로 OP 컨텍스트를 조회해서 만들지 말고 **무조건 `node scripts/op-standup.js`를 실행**하세요.
- 환경변수 부족 오류가 스크립트에서 반환될 경우: 
  "프로젝트 최상단 .env 파일 또는 Rkit 환경변수에 `OPENPROJECT_URL` 및 `OPENPROJECT_API_KEY` 설정이 필요합니다." 라고 안내해주어 사용자가 조치할 수 있게 돕는다.
