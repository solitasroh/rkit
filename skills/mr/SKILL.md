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

# /mr — GitLab MR Lifecycle

MR 전체 라이프사이클을 관리하는 통합 스킬. `glab` CLI + GitLab API 사용.

## Prerequisites

- `glab` CLI 설치 및 인증 (`glab auth login`)
- Git remote가 GitLab에 설정
- glab 미설치 시: "glab CLI가 필요합니다. 설치: https://gitlab.com/gitlab-org/cli" 안내

## Arguments

| Argument | 역할 | 사용자 | 예시 |
|----------|------|:------:|------|
| `create [feature]` | Draft MR 생성 + 리뷰어 지정 | 개발자 | `/mr create uart-dma` |
| `review [MR-IID]` | AI 코드 리뷰 + discussion 생성 | 리뷰어 | `/mr review 42` |
| `feedback [MR-IID]` | 리뷰 comment 조회 + 수정 + reply | 개발자 | `/mr feedback 42` |
| `verify [MR-IID]` | 수정 확인 + resolve | 리뷰어 | `/mr verify 42` |
| `status [MR-IID]` | MR 상태 확인 | 공통 | `/mr status` |
| `approve [MR-IID]` | 승인 | 리뷰어 | `/mr approve 42` |
| `merge [MR-IID]` | Squash merge + 브랜치 삭제 | 공통 | `/mr merge 42` |

---

## create [feature]

Draft MR 생성. AI가 description을 자동 생성하고 리뷰어를 지정한다.

### 절차

#### Step 1: 브랜치 확인/생성

- 현재 브랜치가 `feature/*` 또는 `bugfix/*`인지 확인한다.
- 해당하지 않으면 mr-conventions 규칙에 따라 브랜치 생성을 제안한다:
  - OP 태스크 연결 시: `feature/op-{N}-{description}` 또는 `bugfix/op-{N}-{description}`
  - OP 없음: `feature/{description}` 또는 `bugfix/{description}`
- AskUserQuestion으로 확인 후 `git checkout -b {branch}` 실행.

#### Step 2: 변경사항 확인

- `git status` + `git diff --stat`으로 변경 범위 확인한다.
- 미커밋 변경이 있으면: "커밋하시겠습니까?" 제안.
- 커밋 메시지: `[OP#N] type: description` 형식 적용 (mr-conventions 참조).

#### Step 3: AI MR Description 생성

- `templates/mr-description.template.md`를 로드한다.
- AI가 자동 채움:

  | 필드 | 소스 | 자동화 수준 |
  |------|------|:----------:|
  | Summary | PDCA Plan Executive Summary / diff 분석 | AI 생성 |
  | Type of Change | 브랜치명에서 추론 | 완전 자동 |
  | Related (OP) | 브랜치명 `op-{N}` 추출 | 완전 자동 |
  | Related (PDCA) | Plan 문서 경로 | 완전 자동 |
  | PDCA Report | gap-detector 결과 | 완전 자동 |
  | Domain Impact | 도메인 감지 → 해당 섹션만 포함 | 완전 자동 |
  | Test Evidence | — | 사용자 수동 |
  | Breaking Changes | diff 분석 | AI 제안 |

- 생성된 description을 사용자에게 보여주고 확인/수정 요청한다.

#### Step 4: 리뷰어 선택

- `glab api "projects/:id/members"`로 프로젝트 멤버를 조회한다.
- AskUserQuestion으로 리뷰어 선택 (필수, 최소 1명).

#### Step 5: Push + Draft MR 생성

- `git push -u origin {branch}`
- MR 제목: `[OP#N] type: description`
- ```bash
  glab mr create \
    --draft \
    --title "{title}" \
    --description "{description}" \
    --reviewer "{reviewer}" \
    --target-branch main
  ```
- 결과 출력: MR URL, IID.

### 오류 처리

- glab 미설치: "glab CLI가 필요합니다."
- 인증 실패: "`glab auth login`으로 인증하세요."
- push 실패: "원격 브랜치 충돌. `git pull --rebase` 후 재시도하세요."

---

## review [MR-IID]

AI 1차 코드 리뷰 + 도메인별 체크리스트 + Conventional Comments discussion 생성.

### 절차

#### Step 1: MR 정보 조회

- `glab mr view {iid}`로 MR 메타데이터를 조회한다.
- `glab mr diff {iid}`로 diff를 조회한다.

#### Step 2: AI 코드 분석

diff를 분석하여:

1. **변경 요약**: 파일별 변경 목적 1줄 설명.
2. **도메인별 체크리스트 검증**:
   - MCU: MISRA 준수, Flash/RAM 영향, ISR 안전성, 스택 사용량, 페리퍼럴 충돌, HAL 반환값
   - MPU: DT 바인딩 호환, 커널 ABI 영향, probe/remove 순서, 메모리 매핑, 에러 경로
   - WPF: MVVM 준수, `{x:Bind}` 금지, ObservableProperty, async/await, IDisposable
3. **문제 발견**: `templates/mr-review-comment.template.md` 형식으로 분류.
4. **칭찬**: 잘 작성된 코드에 `praise:` comment 최소 1건.

#### Step 3: 리뷰 결과 제시

AI 분석 결과를 리뷰어에게 요약 테이블로 제시한다:

| # | Label | Blocking | File:Line | 내용 |
|---|-------|:--------:|-----------|------|
| 1 | issue | Yes | src/uart.c:42 | ISR 내 HAL_Delay 사용 |
| 2 | suggestion | No | src/dma.c:87 | const 선언으로 RAM 절약 |
| 3 | praise | — | src/ring_buffer.c:15 | 깔끔한 구현 |

"AI가 N건의 comment를 생성했습니다. 검토 후 수정/삭제/추가하세요."

#### Step 4: Discussion 생성 (사용자 확인 후)

리뷰어가 확인/수정한 comment를 GitLab discussion으로 생성한다:

```bash
glab api --method POST \
  "projects/:id/merge_requests/:iid/discussions" \
  --field body="issue (blocking, safety): ISR 내 HAL_Delay() 사용 금지..."
```

### 오류 처리

- MR 미발견: "MR !{iid}를 찾을 수 없습니다."
- diff 없음: "이 MR에 변경사항이 없습니다."

---

## feedback [MR-IID]

리뷰 comment 조회 + AI 수정 제안 + 커밋 + thread reply.

### 절차

#### Step 1: Unresolved Discussion 조회

- `glab api "projects/:id/merge_requests/:iid/discussions"`로 discussion 목록을 조회한다.
- unresolved discussion만 필터링한다.
- Conventional Comments label 파싱: blocking(issue/todo/chore) vs non-blocking.

#### Step 2: 요약 테이블 출력

| # | Label | Blocking | File | 내용 | 상태 |
|---|-------|:--------:|------|------|:----:|
| 1 | issue (blocking) | Yes | src/uart.c:42 | ISR 내 HAL_Delay | 미해결 |
| 2 | todo | Yes | src/main.c:15 | null check 추가 | 미해결 |
| 3 | suggestion (non-blocking) | No | src/dma.c:87 | const 선언 | 미해결 |

#### Step 3: Discussion별 AI 대응 (blocking 우선)

blocking discussion부터 순서대로:

1. AI가 해당 코드를 읽고 수정 방안을 제안한다.
2. AskUserQuestion: "이 수정을 적용하시겠습니까?"
3. 확인 → 코드를 수정한다.
4. 커밋: `[OP#N] fix: {discussion 내용 요약}`
5. Thread reply를 생성한다:
   ```bash
   glab api --method POST \
     "projects/:id/merge_requests/:iid/discussions/:discussion_id/notes" \
     --field body="Fixed in {commit-hash}. {수정 설명}"
   ```

non-blocking discussion은 목록만 표시하고 선택적으로 대응한다.

#### Step 4: Push + 재요청

모든 blocking discussion 처리 후:
- `git push`
- AskUserQuestion: "리뷰 재요청 하시겠습니까?"

### 오류 처리

- Discussion 0건: "미해결 discussion이 없습니다."
- API 호출 실패: "GitLab API에 연결할 수 없습니다."

---

## verify [MR-IID]

Reply vs diff 비교 → resolve 대상 식별 → 리뷰어 resolve.

### 절차

#### Step 1: Unresolved Discussion 조회

discussion 목록에서 reply가 있는 unresolved discussion을 필터링한다.

#### Step 2: Discussion별 AI 검증

각 discussion에 대해:

1. 원래 comment 내용을 확인한다.
2. 개발자 reply 내용을 확인한다.
3. 현재 diff에서 해당 코드 변경 여부를 확인한다.
4. AI 판단: "수정 확인됨" / "수정 미확인" / "부분 수정".

#### Step 3: 검증 결과 테이블

| # | Label | Comment 요약 | Reply | 수정 상태 | Resolve 권장 |
|---|-------|-------------|-------|:--------:|:----------:|
| 1 | issue | ISR HAL_Delay | Fixed abc123 | 수정됨 | 권장 |
| 2 | todo | null check | Fixed def456 | 수정됨 | 권장 |
| 3 | suggestion | const 선언 | 다음 버전 | 스킵 | 리뷰어 판단 |

#### Step 4: Resolve 실행 (리뷰어 선택)

- AskUserQuestion: resolve할 discussion을 선택한다 (복수 선택 가능).
- 선택된 discussion을 resolve한다:
  ```bash
  glab api --method PUT \
    "projects/:id/merge_requests/:iid/discussions/:discussion_id" \
    --field resolved=true
  ```
- 모든 discussion resolved → "/mr approve 하시겠습니까?" 제안.

### 오류 처리

- Reply 없는 discussion만 있음: "개발자 reply가 없는 discussion N건. 피드백을 기다리세요."

---

## status [MR-IID]

내 MR 목록 또는 특정 MR 상세 상태.

### 인자 없음: 내 MR 목록

- `glab mr list --author=@me`로 내 MR 목록을 조회한다.
- 테이블 출력:

| MR | 제목 | 리뷰어 | 승인 | CI | Unresolved | Draft |
|-----|------|--------|:----:|:---:|:---------:|:-----:|
| !42 | [OP#123] feat: ... | @user | ⏳ | ✅ | 3건 | Yes |

### 인자 있음: 특정 MR 상세

- `glab mr view {iid}`로 상세를 조회한다.
- Discussion 요약: resolved N건, unresolved N건 (blocking N건).
- CI 파이프라인 상태: `glab ci status`.
- 승인 상태: approved / pending.

---

## approve [MR-IID]

사전 확인 후 승인.

### 절차

1. 사전 확인:
   - Unresolved discussion: 0건? (blocking이 남아있으면 차단)
   - CI 파이프라인: 통과?
   - Draft 상태: 해제되었는가?

2. 모든 조건 충족:
   - `glab mr approve {iid}`
   - "MR !{iid}가 승인되었습니다."

3. 조건 미충족:
   - 구체적 사유 안내:
     - "blocking discussion {N}건 미해결"
     - "CI 파이프라인 실패"
     - "Draft 상태입니다. Ready로 변경 후 진행하세요."

---

## merge [MR-IID]

Squash merge + 브랜치 삭제 + PDCA/OP 연동 제안.

### 절차

1. 사전 확인:
   - Approved 상태?
   - CI 통과?
   - Unresolved discussion 0건?

2. 모든 조건 충족:
   - `glab mr merge {iid} --squash --remove-source-branch`
   - "MR !{iid}가 squash merge 되었습니다. 브랜치 삭제 완료."

3. PDCA 연동 제안 (PDCA feature 활성화 시):
   - "/pdca report를 생성하시겠습니까?"

4. OP 연동 제안 (OP 태스크 연결 시):
   - "OP 태스크 #N을 Closed로 변경하시겠습니까?"
   - "시간을 기록하시겠습니까?"

5. 조건 미충족:
   - "승인되지 않았습니다."
   - "CI 파이프라인 실패"
   - "미해결 discussion {N}건"

---

## PDCA 연동

### Check ≥ 90% → /mr create 제안

`/pdca analyze`에서 match rate ≥ 90% 달성 시:
- "MR을 생성하시겠습니까? `/mr create {feature}`"
- 이 제안은 openproject-conventions + mr-conventions가 함께 트리거된다.

### merge → /pdca report 제안

`/mr merge` 완료 시:
- "/pdca report {feature}를 생성하시겠습니까?"
- OP 태스크 Closed + 시간 기록도 함께 제안한다.

## Usage Examples

```bash
# 개발자: MR 생성
/mr create uart-dma

# 리뷰어: AI 코드 리뷰
/mr review 42

# 개발자: 리뷰 피드백 대응
/mr feedback 42

# 리뷰어: 수정 확인 + resolve
/mr verify 42

# MR 상태 확인
/mr status
/mr status 42

# 리뷰어: 승인
/mr approve 42

# 머지
/mr merge 42
```
