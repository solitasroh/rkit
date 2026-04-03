# mr-lifecycle Planning Document

> **Summary**: GitLab MR 전체 라이프사이클을 AI 자동화와 함께 PDCA 워크플로에 자연스럽게 통합
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
| **Problem** | PDCA Check 이후 MR 생성→리뷰→피드백 대응→승인→머지까지의 팀 협업 구간이 없음. 상용 AI 리뷰 도구(CodeRabbit, Qodo)도 comment→수정→reply→resolve 루프를 자동화하지 못함 |
| **Solution** | `/mr` 통합 스킬(7개 sub-command) + `mr-conventions` capability skill + 도메인별 MR/Review template. AI가 template 기반 MR description 자동 생성, 도메인 특화 리뷰, reviewer comment 분석→수정→reply, resolve 대상 식별까지 자동화 |
| **Function/UX Effect** | 개발자: create→AI가 feedback 분석·수정 제안→reply 자동. 리뷰어: AI가 1차 리뷰→사람이 판단→verify로 resolve. Discussion thread 라이프사이클 완전 커버 |
| **Core Value** | AI 검증(gap-detector) + AI 리뷰(도메인 특화) + 사람 리뷰(최종 판단)가 하나의 PDCA 흐름으로 완성. 어떤 상용 도구도 제공하지 않는 "comment→fix→reply→resolve" 자동화 루프 |

---

## 1. Overview

### 1.1 Purpose

PDCA의 Check(AI) → Report 사이에 팀 코드 리뷰(MR 라이프사이클)를 자연스럽게 삽입한다. AI가 리뷰 보조, 피드백 대응, thread reply를 자동화하여 개발자와 리뷰어 모두의 부담을 줄인다.

### 1.2 PDCA↔MR 자연 통합 설계

**기존 PDCA 흐름 (1인 개발):**
```
Plan → Design → Do → Check(AI) → Report → Archive
```

**확장 PDCA 흐름 (팀 개발 + AI 자동화):**
```
Plan → Design → Do → Check(AI, ≥90%)
  → /mr create (Draft, 리뷰어 지정, AI가 description 자동 생성)
    → /mr review   [리뷰어] AI 1차 리뷰 + 사람 판단 → discussion 생성
    → /mr feedback  [개발자] AI가 comment 분석 → 수정 제안 → 커밋 → thread reply
    → /mr verify    [리뷰어] AI가 수정 확인 → resolve 대상 식별 → 사람이 resolve
    → /mr approve   [리뷰어] unresolved 0 + CI 통과 → 승인
    → /mr merge     squash merge + 브랜치 삭제
  → /pdca report → Archive
```

핵심: **MR은 PDCA의 공식 단계가 아니라, Check와 Report 사이의 팀 검증 구간**. MR 없이도 기존 PDCA 정상 동작 (1인 개발 호환).

### 1.3 상용 도구 대비 차별화

| 기능 | CodeRabbit | Qodo | Copilot PR | **mcukit /mr** |
|------|:---------:|:----:|:----------:|:--------------:|
| MR description 자동 생성 | O | O | O | O (PDCA Report 기반) |
| 코드 리뷰 comment | O | O | O | O (**도메인 특화**: MISRA, DTS, MVVM) |
| 코드 수정 제안 | O | O | O | O |
| Conventional Comments | X | X | X | **O** |
| reviewer comment → 자동 수정 | **X** | **X** | **X** | **O** |
| 수정 후 thread reply | **X** | **X** | **X** | **O** |
| 수정 확인 → resolve 대상 식별 | **X** | **X** | **X** | **O** |
| 증분 리뷰 (새 변경만) | O | O | O | O |
| 도메인별 체크리스트 (MCU/MPU/WPF) | **X** | **X** | **X** | **O** |

### 1.4 Background

- 현재 `/ship mr`은 MR 생성만 지원 (단방향, 리뷰어 미지정)
- GitLab ↔ OpenProject 연동: `[OP#N]` prefix로 양쪽 자동 추적
- `glab` CLI: MR 생성, note, approve, merge 지원. Discussion resolve는 `glab api` 필요
- bkit/gstack 포함 어떤 프레임워크도 MR 리뷰 라이프사이클을 구현하지 않음

---

## 2. 팀 컨벤션 (mr-conventions)

### 2.1 브랜치 네이밍

| 유형 | 패턴 | 예시 |
|------|------|------|
| 신규 기능 | `feature/op-{N}-{description}` | `feature/op-123-uart-dma` |
| 버그 수정 | `bugfix/op-{N}-{description}` | `bugfix/op-456-spi-timeout` |

- OP 태스크 번호가 없으면: `feature/{description}` 또는 `bugfix/{description}`
- description은 kebab-case

### 2.2 커밋 메시지

```
[OP#123] feat: DMA 기반 UART 드라이버 구현
[OP#123] fix: SPI 타임아웃 처리 누락 수정
[OP#456] refactor: HAL 추상화 레이어 정리
```

- prefix `[OP#N]`은 OpenProject 태스크 번호 — GitLab↔OP 양쪽 이력 연동
- OP 태스크가 없으면 prefix 생략

### 2.3 MR 규칙

| 규칙 | 내용 |
|------|------|
| 생성 방식 | **항상 Draft**로 생성 |
| MR 제목 | `[OP#123] feat: description` (커밋 prefix와 동일) |
| 리뷰어 | **필수 지정** (최소 1명) |
| 머지 방식 | **Squash merge** |
| 머지 후 | 소스 브랜치 삭제 |
| CI 통과 | 머지 전 파이프라인 통과 필수 |
| Discussion | 모든 thread resolved 필수 |

### 2.4 Conventional Comments (업계 표준 채택)

기존 `[Critical]`, `[Suggestion]` 대신 [Conventional Comments](https://conventionalcomments.org/) 형식 사용:

**형식**: `label (decorator): 내용`

| Label | 의미 | Blocking? |
|-------|------|:---------:|
| `issue:` | 문제 발견 — 반드시 수정 필요 | **Yes** |
| `todo:` | 필수 변경 사항 | **Yes** |
| `suggestion:` | 개선 제안 | No |
| `question:` | 질문/확인 필요 | No |
| `nitpick:` | 사소한 스타일 | No |
| `praise:` | 잘한 부분 칭찬 | No |
| `thought:` | 아이디어 공유 | No |
| `chore:` | 단순 정리 작업 | Yes |

**Decorator**: `(blocking)`, `(non-blocking)`, `(if-minor)`

**예시:**
```
issue (blocking): 이 ISR 핸들러에서 malloc을 사용하면 안 됩니다.
  MCU 도메인에서 ISR 내 동적 메모리 할당은 정의되지 않은 동작을 유발합니다.
  `static` 버퍼를 사용하세요.

suggestion (non-blocking): DMA 완료 콜백을 weak 함수로 선언하면
  사용자가 override할 수 있어 확장성이 좋아집니다.

praise: 링 버퍼 구현이 깔끔합니다. head/tail 인덱싱이 명확해요.
```

### 2.5 리뷰 프로토콜

| 단계 | 역할 | 동작 |
|------|------|------|
| 1. AI 1차 리뷰 | AI | diff 분석 → 도메인별 체크리스트 → Conventional Comments로 discussion 생성 |
| 2. 사람 리뷰 | 리뷰어 | AI comment 확인 + 자신의 comment 추가/수정/삭제 |
| 3. 피드백 대응 | 개발자(+AI) | blocking comment별 수정 → 커밋 → thread reply |
| 4. 수정 검증 | 리뷰어(+AI) | reply 확인 → 코드 검증 → discussion resolve |
| 5. 승인 | 리뷰어 | unresolved 0건 + CI 통과 → approve |
| 6. 머지 | 리뷰어/개발자 | squash merge + 브랜치 삭제 |

**원칙: AI는 보조, 사람이 최종 판단**
- AI가 리뷰 comment를 작성하지만, 리뷰어가 수정/삭제 가능
- AI가 수정 코드를 제안하지만, 개발자가 확인 후 커밋
- AI가 resolve 대상을 식별하지만, 리뷰어가 최종 resolve

---

## 3. 역할별 사용 케이스

### 3.1 개발자 케이스

#### Case D1: PDCA 완료 후 MR 생성

```
/pdca analyze feature (Check ≥ 90%)
  → "MR을 생성하시겠습니까?" 제안
  → /mr create
    → AI가 MR description 자동 생성 (diff + PDCA Report + OP 컨텍스트)
    → Draft MR 생성 + 리뷰어 지정
    → [OP#123] prefix 자동 적용
    → 브랜치: feature/op-123-feature-name (자동 생성/확인)
```

#### Case D2: 리뷰 피드백 확인 및 AI 자동 대응

```
/mr feedback 42  또는  "MR 리뷰 확인해줘"
  → glab API로 unresolved discussion 목록 조회
  → discussion별 분류: blocking(issue/todo) / non-blocking(suggestion/nitpick)
  → blocking discussion 요약 테이블 출력

  → discussion별 AI 자동 대응:
    1. AI가 수정 코드 제안
    2. 사용자 확인: "이 수정을 적용하시겠습니까?"
    3. 확인 → 커밋 [OP#123] fix: {description}
    4. 해당 thread에 reply: "Fixed in {commit-hash}. {수정 설명}"
  
  → 모든 blocking 처리 후:
    → push
    → "리뷰 재요청 하시겠습니까?" 제안
```

#### Case D3: MR 상태 확인

```
/mr status  또는  "내 MR 상태 확인"
  → 내가 생성한 MR 목록:
    | MR | 제목 | 리뷰어 | 승인 | CI | Unresolved |
    |-----|------|--------|------|-----|-----------|
    | !42 | [OP#123] feat: ... | @reviewer | ⏳ | ✅ | 3건 |
```

### 3.2 리뷰어 케이스

#### Case R1: AI 보조 코드 리뷰

```
/mr review 42  또는  "MR !42 리뷰해줘"
  → glab mr diff로 diff 조회
  → AI 분석:
    1. 변경 요약 (파일별 목적 설명)
    2. 도메인별 체크리스트 자동 생성 및 검증:
       MCU: MISRA 준수, Flash/RAM 영향, ISR 안전성, 스택 사용량
       MPU: DT 바인딩 호환, 커널 ABI 영향, 드라이버 인터페이스
       WPF: MVVM 패턴 준수, XAML 바인딩, ViewModel View 참조 금지
    3. 문제 발견 시 Conventional Comments로 discussion 생성
    4. 잘한 부분은 praise: comment
  → 리뷰어에게 AI 리뷰 결과 요약 제시
  → "AI가 N건의 comment를 생성했습니다. 검토 후 수정/삭제하세요."
  → 리뷰어가 추가 comment 작성 가능
```

#### Case R2: 수정 검증 + resolve

```
/mr verify 42  또는  "MR !42 수정 확인해줘"
  → unresolved discussion 목록 조회
  → discussion별:
    1. 원래 comment 내용
    2. 개발자의 reply 내용
    3. 현재 diff에서 해당 코드 변경 여부 확인
    4. AI 판단: "수정 확인됨" / "수정 미확인" / "부분 수정"
  → 결과 테이블:
    | # | Label | 원래 Comment | Reply | 수정 상태 | Resolve? |
    |---|-------|-------------|-------|----------|----------|
    | 1 | issue | ISR malloc 금지 | Fixed in abc123 | ✅ 수정됨 | 권장 |
    | 2 | todo | null check 추가 | Fixed in def456 | ✅ 수정됨 | 권장 |
    | 3 | suggestion | weak 함수 사용 | 다음 버전에서 적용 | ⏭️ 스킵 | 리뷰어 판단 |
  → 리뷰어가 resolve할 discussion 선택
  → 선택된 discussion resolve (glab API)
```

#### Case R3: 승인

```
/mr approve 42  또는  "MR !42 승인해줘"
  → 사전 확인:
    - unresolved discussion: 0건? (blocking 남아있으면 차단)
    - CI 파이프라인: 통과?
    - Draft 상태: 해제되었는가?
  → 모두 통과: glab mr approve
  → 실패 시: 구체적 사유 안내 ("blocking discussion 2건 미해결")
```

#### Case R4: 머지

```
/mr merge 42  또는  "MR !42 머지해줘"
  → 사전 확인:
    - approved 상태?
    - CI 통과?
    - unresolved 0건?
  → glab mr merge --squash --remove-source-branch
  → "MR !42가 squash merge 되었습니다. 브랜치 삭제 완료."
  → PDCA 연동: "/pdca report를 생성하시겠습니까?" 제안
  → OP 연동: "OP 태스크를 Closed로 변경하시겠습니까?" 제안
```

### 3.3 케이스 매트릭스

| Case | 역할 | AI 자동화 | 사람 판단 | glab 명령/API |
|:----:|------|:--------:|:---------:|--------------|
| D1 | 개발자 | description 생성, 브랜치명 제안 | 리뷰어 선택, 확인 | `glab mr create --draft --reviewer` |
| D2 | 개발자 | comment 분석, 수정 제안, reply 생성 | 수정 확인 후 커밋 | `glab api discussions`, `glab api notes` |
| D3 | 개발자 | — | — | `glab mr list --author` |
| R1 | 리뷰어 | diff 분석, 도메인 체크리스트, comment 생성 | comment 수정/삭제/추가 | `glab mr diff`, `glab api discussions` |
| R2 | 리뷰어 | 수정 확인 비교, resolve 대상 식별 | resolve 결정 | `glab api discussions PUT resolved` |
| R3 | 리뷰어 | 사전 확인 자동화 | 최종 승인 결정 | `glab mr approve` |
| R4 | 리뷰어/개발자 | 사전 확인 자동화 | 최종 머지 결정 | `glab mr merge --squash --remove-source-branch` |

---

## 4. AI 자동화 상세

### 4.1 AI가 하는 것 vs 사람이 하는 것

| 단계 | AI 자동화 | 사람 필수 |
|------|:---------:|:---------:|
| MR description 생성 | **AI** (diff + PDCA Report + OP 컨텍스트) | 확인 |
| 브랜치명 생성 | **AI** (OP 번호 + feature name) | 확인 |
| 1차 코드 리뷰 | **AI** (도메인 특화 분석) | 수정/삭제/추가 |
| 도메인별 체크리스트 | **AI** (MCU: MISRA, Flash/RAM 등) | 확인 |
| reviewer comment 분류 | **AI** (blocking/non-blocking) | — |
| reviewer comment 수정 대응 | **AI** (코드 수정 제안) | 확인 후 커밋 |
| thread reply 생성 | **AI** ("Fixed in {hash}. {설명}") | 확인 |
| 수정 확인 (reply vs diff) | **AI** (비교 분석) | — |
| resolve 대상 식별 | **AI** | resolve 최종 결정 |
| 승인 결정 | — | **사람** (리뷰어) |
| 머지 결정 | — | **사람** |

### 4.2 도메인별 AI 리뷰 체크리스트

#### MCU 리뷰 체크리스트
- [ ] MISRA C:2012 Required 규칙 위반 없음
- [ ] ISR 내 동적 메모리 할당/printf/mutex 사용 없음
- [ ] Flash/RAM 예산 초과 없음 (Flash < 85%, RAM < 75%)
- [ ] 스택 사용량 확인 (FreeRTOS 태스크별)
- [ ] 페리퍼럴 충돌 없음 (DMA 채널, GPIO 핀)
- [ ] 에러 핸들링 (HAL_StatusTypeDef 반환값 체크)

#### MPU 리뷰 체크리스트
- [ ] Device Tree 바인딩 호환성
- [ ] 커널 ABI 변경 여부 (ioctl/sysfs 인터페이스)
- [ ] 드라이버 probe/remove 순서
- [ ] 메모리 매핑 (ioremap/dma_alloc_coherent)
- [ ] 에러 경로에서 리소스 해제

#### WPF 리뷰 체크리스트
- [ ] ViewModel에서 System.Windows.Controls 참조 없음
- [ ] `{x:Bind}` 사용 없음 (WPF는 `{Binding}` 사용)
- [ ] [ObservableProperty] Source Generator 활용
- [ ] async/await 패턴 (UI 스레드 블로킹 없음)
- [ ] IDisposable 구현 (SerialPort 등 리소스)

### 4.3 Discussion Thread 라이프사이클 (glab API)

```
1. 리뷰어 (또는 AI): discussion 생성
   POST /api/v4/projects/:id/merge_requests/:iid/discussions
   body: "issue (blocking): ISR 내 malloc 금지"

2. 개발자 (또는 AI): thread에 reply
   POST /api/v4/projects/:id/merge_requests/:iid/discussions/:discussion_id/notes
   body: "Fixed in abc123. static 버퍼로 변경했습니다."

3. 리뷰어: discussion resolve
   PUT /api/v4/projects/:id/merge_requests/:iid/discussions/:discussion_id
   body: { "resolved": true }
```

---

## 5. Templates

### 5.1 MR Description Template

MR 생성 시 항상 동일한 구조로 description이 작성되도록 template을 적용한다. 도메인(MCU/MPU/WPF)에 따라 Impact 섹션이 달라진다.

**설계 원칙** (업계 사례 분석 기반):
- Kubernetes: "What" + "Why"를 반드시 분리 (motivation 중심)
- React: 테스트 증거 필수 (빈 섹션 = MR 거절)
- GitLab CE: Before/After 비교 테이블, 로컬 검증 절차
- Embedded Artistry: Hardware/Toolchain/Memory Budget 명시
- Linux Kernel: 변경 이력(v2, v3), Fixes: 태그로 추적성

**MR Description Template:**

```markdown
## Summary

<!-- 무엇을 변경했고, 왜 필요한지. 동기(motivation)를 명확히. -->

## Type of Change

- [ ] Feature (신규 기능)
- [ ] Bugfix (버그 수정)
- [ ] Refactoring (기능 변경 없음)
- [ ] Configuration (Kconfig, DTS, linker script, .csproj)
- [ ] Documentation

## Related

- OpenProject: [OP#N](link)
- PDCA Plan: `docs/01-plan/features/{feature}.plan.md`
- Fixes: #{issue}

## PDCA Report

| Metric | Value |
|--------|-------|
| AI Check (gap-detector) | {match_rate}% |
| Iterations | {count} |

## Domain Impact

<!-- AI가 도메인을 감지하여 해당 섹션만 포함 -->

### MCU Impact

| Region | Before | After | Delta | Budget |
|--------|--------|-------|-------|--------|
| Flash  |        |       |       | < 85%  |
| RAM    |        |       |       | < 75%  |

- **Peripheral changes:** <!-- DMA 채널, GPIO 핀 변경 -->
- **Interrupt changes:** <!-- 새 ISR, 우선순위 변경 -->
- **MISRA compliance:** <!-- Required 위반 0건 -->

### MPU Impact

- **Kernel ABI:** <!-- ioctl/sysfs 인터페이스 변경 여부 -->
- **Device Tree:** <!-- DT 바인딩 호환성 -->
- **Driver interface:** <!-- probe/remove, platform_data 변경 -->

### WPF Impact

- **NuGet packages:** <!-- 추가/변경/삭제 -->
- **XAML binding:** <!-- 바인딩 경로 변경 여부 -->
- **.NET target:** <!-- net8.0-windows 호환성 -->

## Test Evidence

- [ ] On-target test / Unit test 통과
- [ ] Regression test 범위: <!-- scope -->

**Test Configuration:**
- Hardware: <!-- 보드, 리비전 -->
- Toolchain: <!-- arm-none-eabi-gcc 12.3, dotnet 8.0 등 -->
- SDK: <!-- STM32Cube FW v1.28.0, MCUXpresso SDK 2.14 등 -->

## Checklist

- [ ] Self-review 완료
- [ ] 코딩 컨벤션 준수
- [ ] 에러 경로 리소스 정리 확인
- [ ] 링커 스크립트 / DTS / .csproj 변경 없음 (또는 리뷰 완료)
- [ ] Breaking change 없음 (또는 아래 기술)

## Breaking Changes

<!-- 없으면 "None" 기입. 있으면 영향 범위와 마이그레이션 방법 기술. -->

None
```

**AI 자동 채움 규칙:**
- `Summary`: PDCA Plan의 Executive Summary 참조
- `Type of Change`: 브랜치명(`feature/` → Feature, `bugfix/` → Bugfix)에서 추론
- `Related`: OP 태스크 번호, PDCA Plan 경로 자동 링크
- `PDCA Report`: gap-detector 결과에서 match rate, iteration count
- `Domain Impact`: 도메인 감지 후 해당 섹션만 포함, 나머지 제거
- `MCU Memory Budget`: `arm-none-eabi-size` 출력 파싱 (가능한 경우)
- `Test Configuration`: 프로젝트 파일에서 툴체인/SDK 버전 감지

### 5.2 Review Comment Template

리뷰 comment는 Conventional Comments 형식을 기반으로, mcukit 도메인 decorator를 확장한다.

**형식:**
```
label (decorators): subject

discussion body (선택)
```

**Labels (Conventional Comments 표준 9개):**

| Label | 의미 | Blocking? | 예시 |
|-------|------|:---------:|------|
| `issue` | 문제 발견 | **Yes** | `issue (blocking): ISR 내 malloc 금지` |
| `todo` | 필수 변경 | **Yes** | `todo: 에러 반환값 체크 추가 필요` |
| `suggestion` | 개선 제안 | No | `suggestion: DMA 완료 콜백을 weak로 선언하면 확장성 향상` |
| `question` | 질문/확인 | No | `question: 이 타임아웃 값의 근거가 있나요?` |
| `nitpick` | 사소한 스타일 | No | `nitpick: 변수명 camelCase로 통일` |
| `praise` | 칭찬 | No | `praise: 링 버퍼 구현이 깔끔합니다` |
| `thought` | 아이디어 | No | `thought: 향후 상태 머신 패턴 적용 고려` |
| `chore` | 단순 정리 | Yes | `chore: include 순서 정렬` |
| `note` | 참고 정보 | No | `note: 이 레지스터는 errata에 언급된 workaround입니다` |

**Decorators (표준 3개 + mcukit 도메인 6개):**

| Decorator | 의미 | 적용 |
|-----------|------|------|
| `(blocking)` | 머지 차단 — 반드시 해결 | 표준 |
| `(non-blocking)` | 머지 차단 안 함 | 표준 |
| `(if-minor)` | 사소한 변경이면 적용 | 표준 |
| `(safety)` | 안전 관련 (ISR, 스택, watchdog) | MCU |
| `(memory)` | 메모리 예산 관련 (Flash/RAM) | MCU |
| `(timing)` | 타이밍/실시간성 관련 | MCU/MPU |
| `(misra)` | MISRA C 규칙 관련 | MCU |
| `(dt-binding)` | Device Tree 바인딩 관련 | MPU |
| `(mvvm)` | MVVM 패턴 관련 | WPF |

**Review Comment 전체 예시:**

```
issue (blocking, safety): ISR 핸들러 내에서 HAL_Delay()를 호출하면 안 됩니다.

HAL_Delay()는 내부적으로 SysTick을 사용하는데, ISR 컨텍스트에서는
SysTick 인터럽트가 처리되지 못해 무한 대기에 빠집니다.

대안: 타이머 기반 non-blocking 딜레이를 사용하거나,
DMA 전송 완료를 폴링하세요.

참고: MISRA C:2012 Rule 21.2 — 표준 라이브러리 함수의 ISR 사용 제한
```

```
suggestion (memory, non-blocking): 이 lookup 테이블을 `const`로 선언하면
Flash에 배치되어 RAM 48바이트를 절약할 수 있습니다.

현재: `uint8_t crc_table[256]` → RAM
제안: `const uint8_t crc_table[256]` → Flash
```

```
praise: DMA 더블 버퍼링 구현이 교과서적입니다.
Half-transfer와 transfer-complete 인터럽트 분리가 정확해요.
```

### 5.3 Template 파일 구조

| Template 파일 | 용도 | 사용 시점 |
|---------------|------|----------|
| `templates/mr-description.template.md` | MR description 기본 구조 | `/mr create` |
| `templates/mr-description-mcu.template.md` | MCU 도메인 Impact 섹션 | `/mr create` (MCU) |
| `templates/mr-description-mpu.template.md` | MPU 도메인 Impact 섹션 | `/mr create` (MPU) |
| `templates/mr-description-wpf.template.md` | WPF 도메인 Impact 섹션 | `/mr create` (WPF) |
| `templates/mr-review-comment.template.md` | 리뷰 comment 형식 가이드 | `/mr review` |

**또는 통합 방식**: 하나의 `templates/mr-description.template.md`에 도메인별 섹션을 조건부 포함. Design 단계에서 결정.

---

## 6. Requirements

### 5.1 Functional Requirements

| ID | Priority | Requirement | Description |
|----|:--------:|-------------|-------------|
| FR-01 | P0 | mr-conventions skill | 브랜치/커밋/MR/Conventional Comments/리뷰 프로토콜 (capability) |
| FR-02 | P0 | /mr create | AI가 description 생성 + Draft MR + 리뷰어 + [OP#N] + 브랜치 자동 |
| FR-03 | P0 | /mr review | AI 1차 리뷰 + 도메인 체크리스트 + Conventional Comments discussion 생성 |
| FR-04 | P0 | /mr feedback | AI가 comment 분석 → 수정 제안 → 커밋 → thread reply |
| FR-05 | P0 | /mr verify | AI가 reply vs diff 비교 → resolve 대상 식별 → 리뷰어가 resolve |
| FR-06 | P1 | /mr status | 내 MR 목록 + 승인/CI/unresolved 상태 |
| FR-07 | P1 | /mr approve | unresolved 0 + CI 통과 확인 → 승인 |
| FR-08 | P1 | /mr merge | squash merge + 브랜치 삭제 + PDCA/OP 연동 제안 |
| FR-09 | P1 | PDCA 연동 | Check ≥ 90% → /mr create 제안, merge → /pdca report 제안 |
| FR-10 | P0 | MR description template | 도메인별 MR description template 적용 — AI가 자동 채움 |
| FR-11 | P0 | Review comment template | Conventional Comments + 도메인 decorator로 구조화된 리뷰 |

### 5.2 Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-01 | 기존 /ship 호환 | `/ship mr` → `/mr create` 안내. `/ship release`, `/ship tag` 유지 |
| NFR-02 | glab 필수 | glab CLI 미설치 시 graceful 안내 |
| NFR-03 | 선택적 사용 | MR 미사용해도 기존 PDCA 워크플로 영향 없음 |
| NFR-04 | OP 연동 선택적 | OP 태스크 없어도 MR 생성 가능 (prefix 생략) |
| NFR-05 | AI 보조 원칙 | AI는 제안만, 모든 실행은 사용자 확인 후 |

---

## 6. Scope

### 6.1 In Scope

| 신규 파일 | 역할 |
|-----------|------|
| `skills/mr-conventions/SKILL.md` | 팀 MR 규칙 + Conventional Comments + 리뷰 프로토콜 |
| `skills/mr/SKILL.md` | 통합 MR 스킬 — 7개 sub-command |
| `templates/mr-description.template.md` | MR description template (도메인별 Impact 섹션 포함) |
| `templates/mr-review-comment.template.md` | 리뷰 comment 형식 가이드 (Conventional Comments + decorator) |

### 6.2 기존 파일 수정

| 파일 | 변경 |
|------|------|
| `skills/ship/SKILL.md` | `/ship mr` → `/mr create` 안내 추가 |
| `skills/openproject-conventions/SKILL.md` | MR↔OP 연동 규칙 (브랜치, [OP#N], merge 후 OP Closed) |

### 6.3 Out of Scope

| Item | Reason |
|------|--------|
| GitHub PR 지원 | GitLab 전용 (glab). GitHub은 별도 피처 |
| Webhook/CI 기반 자동 트리거 | v1은 수동 호출. CI 연동은 v2 |
| MR 자동 머지 | 사람 승인/머지 필수 |
| PDCA 상태 머신 변경 | MR은 Check↔Report "사이 구간". 상태 전이 추가 안 함 |

---

## 7. PDCA 통합 설계 (핵심)

### 7.1 전체 흐름도

```
[Plan] → [Design] → [Do] → [Check]
                               │
                               ├── ≥ 90%: "MR을 생성하시겠습니까?"
                               │    │
                               │    └── /mr create (Draft, AI description)
                               │         │
                               │         ├── /mr review (AI 1차 리뷰 + 사람 추가)
                               │         │
                               │         ├── /mr feedback (AI 수정 제안 + reply)
                               │         │    └── (반복 가능)
                               │         │
                               │         ├── /mr verify (AI 수정 확인 + 사람 resolve)
                               │         │
                               │         ├── /mr approve (사람 승인)
                               │         │
                               │         └── /mr merge (squash + 삭제)
                               │              │
                               │              └── "/pdca report 생성하시겠습니까?"
                               │                   └── [Report] → [Archive]
                               │
                               └── < 90%: /pdca iterate (기존대로)
```

### 7.2 MR은 PDCA의 공식 단계가 아님

| 원칙 | 이유 |
|------|------|
| PDCA 상태 머신 변경 안 함 | 기존 20개 상태 전이 호환성 보존 |
| MR은 Check↔Report "사이 구간" | MR 없이도 Report 생성 가능 (1인 개발) |
| conventions skill의 제안으로만 연결 | 강제하지 않음 |

### 7.3 openproject-conventions + mr-conventions 연동

| 시점 | OP 제안 | MR 제안 |
|------|---------|---------|
| Plan 완료 | OP 태스크 생성 | 브랜치 생성 (`feature/op-N-name`) |
| Do 시작 | OP In Progress | — |
| Check ≥ 90% | — | `/mr create` (Draft, [OP#N]) |
| MR merge 후 | OP Closed + 시간 기록 | `/pdca report` |

---

## 8. Success Criteria

| Criteria | 역할 | AI 자동화 |
|----------|:----:|:---------:|
| `/mr create` → AI description + Draft + 리뷰어 + [OP#N] | 개발자 | description, 브랜치명 |
| `/mr review 42` → AI 도메인 리뷰 + Conventional Comments discussion | 리뷰어 | diff 분석, comment 생성 |
| `/mr feedback 42` → comment 분석 + 수정 제안 + 커밋 + reply | 개발자 | 분석, 수정 제안, reply |
| `/mr verify 42` → reply vs diff 비교 + resolve 대상 식별 | 리뷰어 | 비교 분석 |
| `/mr status` → MR 목록 + 승인/CI/unresolved 상태 | 공통 | — |
| `/mr approve 42` → unresolved 0 + CI 확인 → 승인 | 리뷰어 | 사전 확인 |
| `/mr merge 42` → squash merge + 브랜치 삭제 | 공통 | 사전 확인 |
| Check ≥ 90% → /mr create 자연스러운 제안 | — | PDCA 연동 |
| merge → /pdca report 자연스러운 제안 | — | PDCA 연동 |
| `/mr create` → template 기반 description 자동 생성 | 개발자 | template + AI 채움 |
| `/mr review` → Conventional Comments 형식으로 discussion 생성 | 리뷰어 | comment template |
| MCU MR → Memory Budget Impact 섹션 자동 포함 | 개발자 | 도메인 감지 |
| MR 미사용 시 → 기존 PDCA 정상 동작 | — | 호환성 |
