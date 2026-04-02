# mr-lifecycle Design Document

> **Summary**: Option C (Pragmatic) — 2 skill + 2 template + 2 수정. /pdca 패턴 일관성 유지
>
> **Project**: mcukit
> **Version**: 0.7.0
> **Author**: soojang.roh
> **Date**: 2026-04-02
> **Status**: Draft
> **Planning Doc**: [mr-lifecycle.plan.md](../01-plan/features/mr-lifecycle.plan.md)

---

## 1. Architecture Overview

### 1.1 파일 구조

```
mcukit/
├── skills/
│   ├── mr-conventions/SKILL.md       ← capability (auto-trigger)
│   ├── mr/SKILL.md                   ← user-invocable (7 sub-commands)
│   ├── ship/SKILL.md                 ← 수정: /ship mr → /mr create 안내
│   └── openproject-conventions/SKILL.md ← 수정: MR↔OP 연동 규칙 추가
└── templates/
    ├── mr-description.template.md    ← MR description (도메인별 Impact 포함)
    └── mr-review-comment.template.md ← Conventional Comments 형식 가이드
```

### 1.2 컴포넌트 관계

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code Session                                      │
│                                                          │
│  ┌──────────────┐    ┌────────────────────────────────┐ │
│  │ PDCA Skills   │    │ MR Skills                      │ │
│  │               │    │                                │ │
│  │ /pdca analyze │──▶│ mr-conventions (auto-trigger)  │ │
│  │   ≥90% 제안   │    │   ├ 브랜치/커밋/MR 팀 규칙     │ │
│  │               │    │   ├ Conventional Comments 형식  │ │
│  │               │    │   └ 리뷰 프로토콜 (AI+사람)     │ │
│  │               │    │                                │ │
│  │ /pdca report ◀│───│ /mr (7 sub-commands)           │ │
│  │   merge 후     │    │   ├ create  [개발자]           │ │
│  └──────────────┘    │   ├ review  [리뷰어]           │ │
│                       │   ├ feedback [개발자]           │ │
│  ┌──────────────┐    │   ├ verify  [리뷰어]           │ │
│  │ OP Skills     │    │   ├ status  [공통]             │ │
│  │               │    │   ├ approve [리뷰어]           │ │
│  │ op-conventions│◀──│   └ merge   [공통]             │ │
│  │  [OP#N] 연동  │    └──────────────┬─────────────────┘ │
│  └──────────────┘                   │                    │
│                                      │ imports            │
│                    ┌─────────────────▼──────────────┐    │
│                    │ templates/                      │    │
│                    │  mr-description.template.md     │    │
│                    │  mr-review-comment.template.md  │    │
│                    └─────────────────┬──────────────┘    │
└──────────────────────────────────────┼───────────────────┘
                                       │ glab CLI + glab api
                    ┌──────────────────▼──────────────┐
                    │ GitLab Instance                  │
                    │  MR, Discussions, CI Pipeline     │
                    └──────────────────────────────────┘
```

---

## 2. File Specifications

### 2.1 `skills/mr-conventions/SKILL.md`

**역할**: 팀 MR 규칙 + Conventional Comments + 리뷰 프로토콜 (capability, auto-trigger)

```yaml
---
name: mr-conventions
classification: capability
classification-reason: 팀별 MR 규칙 제공, 모델 능력과 무관
description: |
  GitLab MR 팀 규칙과 코드 리뷰 프로토콜.
  MR 관련 작업 시 자동으로 참조됩니다.

  Triggers: MR, merge request, 코드 리뷰, code review, 리뷰, review,
  브랜치, branch, 커밋, commit, draft, squash, approve, 승인, 머지
user-invocable: false
---
```

**내용 구성:**

| Section | 내용 |
|---------|------|
| 브랜치 네이밍 | `feature/op-{N}-{desc}`, `bugfix/op-{N}-{desc}` |
| 커밋 메시지 | `[OP#N] type: description` 형식 |
| MR 규칙 | 항상 Draft, 리뷰어 필수, squash merge, 브랜치 삭제 |
| Conventional Comments | 9 labels + 3 표준 decorators + 6 도메인 decorators |
| 리뷰 프로토콜 | 6단계 (AI 1차→사람 판단→피드백→검증→승인→머지) |
| AI 보조 원칙 | AI는 제안만, 모든 실행은 사용자 확인 후 |

### 2.2 `skills/mr/SKILL.md`

**역할**: 통합 MR 스킬 — 7개 sub-command (user-invocable)

```yaml
---
name: mr
classification: workflow
classification-reason: glab CLI 기반 구조화된 MR 라이프사이클 워크플로
description: |
  GitLab MR 전체 라이프사이클을 관리합니다.
  생성, 리뷰, 피드백, 검증, 상태 확인, 승인, 머지를 지원합니다.
  개발자와 리뷰어 모두 사용할 수 있습니다.

  Triggers: mr, merge request, MR 생성, MR 리뷰, MR 피드백, MR 머지,
  리뷰 확인, 피드백 확인, draft MR, MR 승인, MR 상태
user-invocable: true
argument-hint: "[create|review|feedback|verify|status|approve|merge] [MR-IID]"
imports:
  - mr-description.template.md
  - mr-review-comment.template.md
---
```

**sub-command 상세:**

#### `/mr create [feature]`

**역할**: Draft MR 생성 + AI description + 리뷰어 지정

```markdown
## 절차

### Step 1: 브랜치 확인/생성

- 현재 브랜치가 `feature/*` 또는 `bugfix/*`인지 확인
- 아니면 mr-conventions 규칙에 따라 브랜치 생성 제안:
  - OP 태스크 연결: `feature/op-{N}-{description}` 또는 `bugfix/op-{N}-{description}`
  - OP 없음: `feature/{description}` 또는 `bugfix/{description}`
- `git checkout -b {branch}` 실행 (사용자 확인 후)

### Step 2: 변경사항 확인

- `git status` + `git diff --stat`으로 변경 범위 확인
- 미커밋 변경이 있으면: "커밋하시겠습니까?" 제안
- 커밋 메시지: `[OP#N] type: description` 형식 적용

### Step 3: AI MR Description 생성

- `templates/mr-description.template.md`를 로드
- AI가 자동 채움:
  - Summary: PDCA Plan Executive Summary 또는 diff 기반 요약
  - Type of Change: 브랜치명에서 추론 (feature/ → Feature, bugfix/ → Bugfix)
  - Related: OP 태스크 링크, PDCA Plan 경로
  - PDCA Report: match rate, iteration count (있는 경우)
  - Domain Impact: 도메인 감지 후 해당 섹션만 포함
  - Test Evidence: 비워둠 (사용자가 채움)
- 생성된 description을 사용자에게 보여주고 확인/수정 요청

### Step 4: 리뷰어 선택

- `glab api projects/:id/members`로 프로젝트 멤버 조회
- AskUserQuestion으로 리뷰어 선택 (필수, 최소 1명)

### Step 5: Push + Draft MR 생성

- `git push -u origin {branch}`
- MR 제목: `[OP#N] type: description` (브랜치명 + 커밋에서 추출)
- `glab mr create --draft --title "{title}" --description "{description}" --reviewer "{reviewer}" --target-branch main`
- 결과 출력: MR URL, IID

### 오류 처리

- glab 미설치: "glab CLI가 필요합니다. 설치: https://gitlab.com/gitlab-org/cli"
- 인증 실패: "glab auth login으로 인증하세요."
- push 실패: "원격 브랜치 충돌. git pull --rebase 후 재시도하세요."
```

#### `/mr review [MR-IID]`

**역할**: AI 1차 코드 리뷰 + 도메인 체크리스트 + Conventional Comments discussion

```markdown
## 절차

### Step 1: MR 정보 조회

- `glab mr view {iid}`로 MR 메타데이터 조회
- `glab mr diff {iid}`로 diff 조회

### Step 2: AI 코드 분석

- diff를 분석하여:
  1. **변경 요약**: 파일별 변경 목적 1줄 설명
  2. **도메인별 체크리스트 검증**:
     - MCU: MISRA 준수, Flash/RAM, ISR 안전성, 스택, 페리퍼럴, HAL 반환값
     - MPU: DT 바인딩, 커널 ABI, probe/remove, 메모리 매핑, 에러 경로
     - WPF: MVVM 준수, {x:Bind} 금지, ObservableProperty, async/await, IDisposable
  3. **문제 발견**: Conventional Comments 형식으로 분류
  4. **칭찬**: 잘 작성된 코드에 praise: comment

### Step 3: 리뷰 결과 제시

- AI 분석 결과를 리뷰어에게 요약 테이블로 제시:
  | # | Label | Blocking | File:Line | 내용 |
  |---|-------|:--------:|-----------|------|
  | 1 | issue | Yes | src/uart.c:42 | ISR 내 HAL_Delay 사용 |
  | 2 | suggestion | No | src/dma.c:87 | const 선언으로 RAM 절약 |
  | 3 | praise | — | src/ring_buffer.c:15 | 깔끔한 구현 |
- "AI가 N건의 comment를 생성했습니다. 검토 후 수정/삭제/추가하세요."

### Step 4: Discussion 생성 (사용자 확인 후)

- 리뷰어가 확인/수정한 comment를 GitLab discussion으로 생성:
  ```bash
  glab api --method POST \
    "projects/:id/merge_requests/:iid/discussions" \
    --field body="issue (blocking, safety): ISR 내 HAL_Delay() 사용 금지..."
  ```
- `templates/mr-review-comment.template.md` 형식 적용

### 오류 처리

- MR 미발견: "MR !{iid}를 찾을 수 없습니다."
- diff 없음: "이 MR에 변경사항이 없습니다."
```

#### `/mr feedback [MR-IID]`

**역할**: 리뷰 comment 조회 + AI 수정 제안 + 커밋 + thread reply

```markdown
## 절차

### Step 1: Unresolved Discussion 조회

- `glab api "projects/:id/merge_requests/:iid/discussions"`로 discussion 목록 조회
- unresolved discussion만 필터링
- Conventional Comments label 파싱: blocking(issue/todo/chore) vs non-blocking

### Step 2: 요약 테이블 출력

  | # | Label | Blocking | File | 내용 | 상태 |
  |---|-------|:--------:|------|------|:----:|
  | 1 | issue (blocking) | Yes | src/uart.c:42 | ISR 내 HAL_Delay | 미해결 |
  | 2 | todo | Yes | src/main.c:15 | null check 추가 | 미해결 |
  | 3 | suggestion (non-blocking) | No | src/dma.c:87 | const 선언 | 미해결 |

### Step 3: Discussion별 AI 대응 (blocking 우선)

- blocking discussion부터 순서대로:
  1. AI가 해당 코드를 읽고 수정 방안 제안
  2. AskUserQuestion: "이 수정을 적용하시겠습니까?"
  3. 확인 → 코드 수정
  4. 커밋: `[OP#N] fix: {discussion 내용 요약}`
  5. Thread reply 생성:
     ```bash
     glab api --method POST \
       "projects/:id/merge_requests/:iid/discussions/:discussion_id/notes" \
       --field body="Fixed in {commit-hash}. {수정 설명}"
     ```
- non-blocking은 목록만 표시하고 선택적으로 대응

### Step 4: Push + 재요청

- 모든 blocking 처리 후:
  - `git push`
  - AskUserQuestion: "리뷰 재요청 하시겠습니까?"
  - 확인 → Draft 해제 또는 리뷰어에게 알림

### 오류 처리

- Discussion 0건: "미해결 discussion이 없습니다."
- API 호출 실패: "GitLab API에 연결할 수 없습니다."
```

#### `/mr verify [MR-IID]`

**역할**: reply vs diff 비교 → resolve 대상 식별 → 리뷰어 resolve

```markdown
## 절차

### Step 1: Unresolved Discussion 조회

- discussion 목록에서 reply가 있는 unresolved discussion 필터링

### Step 2: Discussion별 AI 검증

- 각 discussion에 대해:
  1. 원래 comment 내용 확인
  2. 개발자 reply 내용 확인
  3. 현재 diff에서 해당 코드 변경 여부 확인
  4. AI 판단: "수정 확인됨" / "수정 미확인" / "부분 수정"

### Step 3: 검증 결과 테이블

  | # | Label | Comment 요약 | Reply | 수정 상태 | Resolve 권장 |
  |---|-------|-------------|-------|:--------:|:----------:|
  | 1 | issue | ISR HAL_Delay | Fixed abc123 | 수정됨 | 권장 |
  | 2 | todo | null check | Fixed def456 | 수정됨 | 권장 |
  | 3 | suggestion | const 선언 | 다음 버전 | 스킵 | 리뷰어 판단 |

### Step 4: Resolve 실행 (리뷰어 선택)

- AskUserQuestion: resolve할 discussion 선택 (복수 선택 가능)
- 선택된 discussion resolve:
  ```bash
  glab api --method PUT \
    "projects/:id/merge_requests/:iid/discussions/:discussion_id" \
    --field resolved=true
  ```
- 모든 discussion resolved → "/mr approve 하시겠습니까?" 제안

### 오류 처리

- Reply 없는 discussion: "개발자 reply가 없는 discussion N건. 피드백을 기다리세요."
```

#### `/mr status [MR-IID]`

**역할**: 내 MR 목록 또는 특정 MR 상세 상태

```markdown
## 절차

### 인자 없음: 내 MR 목록

- `glab mr list --author=@me`로 내 MR 목록 조회
- 테이블 출력:
  | MR | 제목 | 리뷰어 | 승인 | CI | Unresolved | Draft |
  |-----|------|--------|:----:|:---:|:---------:|:-----:|
  | !42 | [OP#123] feat: ... | @user | ⏳ | ✅ | 3건 | Yes |

### 인자 있음: 특정 MR 상세

- `glab mr view {iid}`로 상세 조회
- Discussion 요약: resolved N건, unresolved N건 (blocking N건)
- CI 파이프라인 상태: `glab ci status`
- 승인 상태: approved / pending
```

#### `/mr approve [MR-IID]`

**역할**: 사전 확인 후 승인

```markdown
## 절차

1. 사전 확인:
   - Unresolved discussion: 0건? (blocking 남아있으면 차단)
   - CI 파이프라인: 통과?
   - Draft 상태: 해제되었는가?
2. 모든 조건 충족:
   - `glab mr approve {iid}`
   - "MR !{iid}가 승인되었습니다."
3. 조건 미충족:
   - 구체적 사유 안내:
     "blocking discussion {N}건 미해결", "CI 파이프라인 실패", "Draft 상태"
```

#### `/mr merge [MR-IID]`

**역할**: squash merge + 브랜치 삭제 + PDCA/OP 연동

```markdown
## 절차

1. 사전 확인:
   - Approved 상태?
   - CI 통과?
   - Unresolved discussion 0건?
2. 모든 조건 충족:
   - `glab mr merge {iid} --squash --remove-source-branch`
   - "MR !{iid}가 squash merge 되었습니다. 브랜치 삭제 완료."
3. PDCA 연동 제안:
   - "/pdca report를 생성하시겠습니까?" (PDCA feature 활성화 시)
4. OP 연동 제안:
   - "OP 태스크를 Closed로 변경하시겠습니까?" (OP 연결 시)
   - "시간을 기록하시겠습니까?"
5. 조건 미충족:
   - "승인되지 않았습니다", "CI 실패", "미해결 discussion N건"
```

#### PDCA 연동 (mr/SKILL.md 내 섹션)

Check ≥ 90% → `/mr create` 제안, merge → `/pdca report` 제안을
mr/SKILL.md 내 독립 섹션으로 기술. openproject-conventions + mr-conventions가 함께 트리거.

#### Usage Examples (mr/SKILL.md 내 섹션)

개발자/리뷰어 양쪽 사용 예시를 mr/SKILL.md 하단에 포함.

### 2.3 `templates/mr-description.template.md`

Plan 섹션 5.1의 template을 그대로 사용. 도메인별 Impact 섹션은 하나의 파일에 모두 포함하되, `/mr create` 실행 시 AI가 감지된 도메인의 섹션만 남기고 나머지를 제거.

```yaml
---
template: mr-description
version: 1.0
description: GitLab MR description template with domain-specific impact sections
variables:
  - feature: Feature name
  - op_number: OpenProject task number (optional)
  - domain: Detected domain (MCU/MPU/WPF)
  - match_rate: PDCA gap-detector match rate (optional)
  - iteration_count: PDCA iteration count (optional)
---
```

**AI 자동 채움 필드:**

| 필드 | 소스 | 자동화 수준 |
|------|------|:----------:|
| Summary | PDCA Plan Executive Summary / diff 분석 | AI 생성, 사용자 확인 |
| Type of Change | 브랜치명 (`feature/` → Feature) | 완전 자동 |
| Related (OP) | 브랜치명에서 `op-{N}` 추출 | 완전 자동 |
| Related (PDCA) | PDCA Plan 경로 | 완전 자동 |
| PDCA Report | gap-detector 결과 | 완전 자동 |
| Changes | `git diff --stat` 기반 파일 변경 목록 | 완전 자동 |
| Domain Impact | 도메인 감지 → 해당 섹션만 포함 | 완전 자동 |
| MCU Memory Budget | `arm-none-eabi-size` 출력 (가능 시) | AI 시도 |
| Test Evidence | — | 사용자 수동 |
| Checklist | — | 사용자 체크 |
| Breaking Changes | diff 분석 | AI 제안, 사용자 확인 |

### 2.4 `templates/mr-review-comment.template.md`

리뷰 comment 작성 시 AI가 참조하는 형식 가이드.

```yaml
---
template: mr-review-comment
version: 1.0
description: Conventional Comments format guide for AI-assisted code review
---
```

**내용:**

```markdown
# MR Review Comment Template

## 형식

label (decorators): subject

discussion body (선택)

## Labels (9개)

| Label | 의미 | Blocking |
|-------|------|:--------:|
| praise | 잘한 부분 칭찬 | No |
| nitpick | 사소한 스타일 | No |
| suggestion | 개선 제안 | No |
| issue | 문제 발견 | Yes |
| todo | 필수 변경 | Yes |
| question | 질문/확인 | No |
| thought | 아이디어 | No |
| chore | 단순 정리 | Yes |
| note | 참고 정보 | No |

## Decorators (표준 3 + 도메인 6)

### 표준
- (blocking): 반드시 해결 필요
- (non-blocking): 머지 차단 안 함
- (if-minor): 사소한 경우에만 적용

### mcukit 도메인
- (safety): ISR, 스택, watchdog 관련 [MCU]
- (memory): Flash/RAM 예산 관련 [MCU]
- (timing): 실시간성/타이밍 관련 [MCU/MPU]
- (misra): MISRA C 규칙 관련 [MCU]
- (dt-binding): Device Tree 바인딩 관련 [MPU]
- (mvvm): MVVM 패턴 관련 [WPF]

## AI 리뷰 규칙

1. blocking issue는 반드시 코드 위치(file:line)와 수정 제안을 함께 제시
2. 리뷰당 praise를 최소 1건 포함 (Google eng-practices 권장)
3. 사람에 대한 comment 금지 — 코드에 대해서만 comment (Google 규칙)
4. "왜" 문제인지 설명 — label만 붙이지 않음
5. 도메인 decorator는 해당 도메인일 때만 사용
6. 수정 제안 시 before/after 코드 블록 포함 권장

## 실전 예시

MCU ISR 안전성, 메모리 최적화, 칭찬, MPU DT 바인딩, WPF MVVM 패턴, 
공통 질문 등 도메인별 실전 예시를 포함하여 AI가 참조할 수 있게 한다.
```

### 2.5 `skills/ship/SKILL.md` 수정

기존 `/ship mr` 섹션에 `/mr create` 안내 추가:

```markdown
### mr {feature} (→ /mr create 권장)

> **Note**: MR 생성은 `/mr create`를 사용하세요.
> `/mr create`는 AI description 자동 생성, 리뷰어 지정, Draft 모드,
> Conventional Comments 리뷰까지 전체 MR 라이프사이클을 지원합니다.
>
> `/ship mr`은 하위 호환을 위해 유지되지만, 기본 MR 생성만 수행합니다.
```

### 2.6 `skills/openproject-conventions/SKILL.md` 수정

기존 PDCA↔OP 연동 규칙에 MR 관련 규칙 추가:

```markdown
### MR↔OP 연동 규칙

- 브랜치명에 OP 번호 포함: `feature/op-{N}-{description}`
- 커밋 prefix: `[OP#N] type: description` → GitLab↔OP 양쪽 이력
- MR 제목: `[OP#N] type: description` → OP에서 MR 추적 가능
- MR merge 후: OP 태스크 Closed + 시간 기록 제안
- `/mr create` 시 브랜치명에서 `op-{N}` 자동 추출하여 MR 제목에 prefix 적용
```

---

## 3. Implementation Order

| Step | File | 의존 | 설명 |
|:----:|------|:----:|------|
| 1 | `templates/mr-description.template.md` | — | MR description template |
| 2 | `templates/mr-review-comment.template.md` | — | 리뷰 comment 형식 가이드 |
| 3 | `skills/mr-conventions/SKILL.md` | — | 팀 MR 규칙 + 리뷰 프로토콜 |
| 4 | `skills/mr/SKILL.md` | Step 1,2,3 | 통합 MR 스킬 (7 sub-commands) |
| 5 | `skills/ship/SKILL.md` | Step 4 | /ship mr → /mr create 안내 |
| 6 | `skills/openproject-conventions/SKILL.md` | Step 4 | MR↔OP 연동 규칙 추가 |

---

## 4. 케이스별 검증 시나리오

| Case | 시나리오 | 기대 결과 |
|:----:|---------|----------|
| D1 | `/mr create uart-dma` | Draft MR + AI description + 리뷰어 + [OP#123] |
| D2 | `/mr feedback 42` | unresolved 조회 → 수정 제안 → 커밋 → reply |
| D3 | `/mr status` | 내 MR 목록 (승인/CI/unresolved 상태) |
| R1 | `/mr review 42` | AI diff 분석 → Conventional Comments discussion |
| R2 | `/mr verify 42` | reply vs diff 비교 → resolve 대상 → resolve |
| R3 | `/mr approve 42` | unresolved 0 + CI 확인 → 승인 |
| R4 | `/mr merge 42` | squash merge + 브랜치 삭제 + PDCA/OP 제안 |
| T1 | `/mr create` (MCU 프로젝트) | Memory Budget Impact 섹션 자동 포함 |
| T2 | `/mr review 42` (MCU) | MISRA/ISR/Flash/RAM 체크리스트 적용 |
| T3 | `/ship mr` 실행 | "/mr create를 사용하세요" 안내 |
| — | glab 미설치 | graceful 안내 메시지 |
| — | PDCA 없이 `/mr create` | PDCA 섹션 비워둠, 정상 동작 |
