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

# GitLab MR 팀 규칙

MR 관련 작업 시 이 규칙을 자동으로 적용한다.

## 브랜치 네이밍

| 유형 | 패턴 | 예시 |
|------|------|------|
| 신규 기능 | `feature/op-{N}-{description}` | `feature/op-123-uart-dma` |
| 버그 수정 | `bugfix/op-{N}-{description}` | `bugfix/op-456-spi-timeout` |

- OP 태스크 번호가 없으면: `feature/{description}` 또는 `bugfix/{description}`
- description은 kebab-case
- 브랜치 유형은 작업 성격에 따라 선택:
  - feature: 신규 기능, 개선, 리팩토링
  - bugfix: 버그 수정, 핫픽스

## 커밋 메시지

```
[OP#123] feat: DMA 기반 UART 드라이버 구현
[OP#123] fix: SPI 타임아웃 처리 누락 수정
[OP#456] refactor: HAL 추상화 레이어 정리
```

- prefix `[OP#N]`은 OpenProject 태스크 번호 — GitLab↔OP 양쪽 이력 연동
- OP 태스크가 없으면 prefix 생략
- type: feat, fix, refactor, docs, test, chore

## MR 규칙

| 규칙 | 내용 |
|------|------|
| 생성 방식 | **항상 Draft**로 생성 (`glab mr create --draft`) |
| MR 제목 | `[OP#123] type: description` (커밋 prefix와 동일) |
| MR description | `templates/mr-description.template.md` 형식 필수 |
| 리뷰어 | **필수 지정** (최소 1명, `--reviewer`) |
| 머지 방식 | **Squash merge** (`--squash`) |
| 머지 후 | 소스 브랜치 삭제 (`--remove-source-branch`) |
| CI 통과 | 머지 전 파이프라인 통과 필수 |
| Discussion | 모든 thread resolved 필수 (특히 blocking) |

## Conventional Comments

리뷰 comment는 [Conventional Comments](https://conventionalcomments.org/) 형식을 따른다.

**형식**: `label (decorators): subject`

### Labels (9개)

| Label | 의미 | Blocking? |
|-------|------|:---------:|
| `praise` | 잘한 부분 칭찬 | No |
| `nitpick` | 사소한 스타일 | No |
| `suggestion` | 개선 제안 | No |
| `issue` | 문제 발견 — 반드시 수정 | **Yes** |
| `todo` | 필수 변경 사항 | **Yes** |
| `question` | 질문/확인 필요 | No |
| `thought` | 아이디어 공유 | No |
| `chore` | 단순 정리 작업 | Yes |
| `note` | 참고 정보 | No |

### Decorators (표준 3 + 도메인 6)

| Decorator | 의미 | 도메인 |
|-----------|------|--------|
| `(blocking)` | 반드시 해결 — 머지 차단 | 공통 |
| `(non-blocking)` | 머지 차단 안 함 | 공통 |
| `(if-minor)` | 사소한 변경이면 적용 | 공통 |
| `(safety)` | ISR, 스택, watchdog 관련 | MCU |
| `(memory)` | Flash/RAM 예산 관련 | MCU |
| `(timing)` | 실시간성/타이밍 관련 | MCU/MPU |
| `(misra)` | MISRA C:2012 규칙 관련 | MCU |
| `(dt-binding)` | Device Tree 바인딩 관련 | MPU |
| `(mvvm)` | MVVM 패턴 관련 | WPF |

## 리뷰 프로토콜

| 단계 | 역할 | 동작 | AI 보조 |
|:----:|------|------|:-------:|
| 1 | 리뷰어 | `/mr review` — diff 분석 + discussion 생성 | AI 1차 리뷰 |
| 2 | 리뷰어 | AI comment 확인/수정/삭제/추가 | — |
| 3 | 개발자 | `/mr feedback` — blocking 수정 + reply | AI 수정 제안 |
| 4 | 리뷰어 | `/mr verify` — 수정 확인 + resolve | AI 비교 분석 |
| 5 | 리뷰어 | `/mr approve` — 승인 | 사전 확인 |
| 6 | 공통 | `/mr merge` — squash merge + 브랜치 삭제 | 사전 확인 |

**원칙: AI는 보조, 사람이 최종 판단**
- AI가 리뷰 comment를 생성하지만, 리뷰어가 수정/삭제 가능
- AI가 수정 코드를 제안하지만, 개발자가 확인 후 커밋
- AI가 resolve 대상을 식별하지만, 리뷰어가 최종 resolve

## Discussion Thread 라이프사이클

```
1. 리뷰어/AI → discussion 생성 (Conventional Comments 형식)
2. 개발자/AI → thread reply ("Fixed in {hash}. {설명}")
3. 리뷰어 → discussion resolve (수정 확인 후)
4. 모든 blocking thread resolved → approve 가능
```

**glab API:**
- 생성: `POST /api/v4/projects/:id/merge_requests/:iid/discussions`
- Reply: `POST /api/v4/projects/:id/merge_requests/:iid/discussions/:did/notes`
- Resolve: `PUT /api/v4/projects/:id/merge_requests/:iid/discussions/:did` `resolved=true`
