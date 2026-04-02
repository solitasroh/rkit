---
template: mr-review-comment
version: 1.0
description: Conventional Comments format guide for AI-assisted code review
---

# MR Review Comment Template

AI 코드 리뷰 및 사람 리뷰 시 이 형식을 따른다.

## 형식

```
label (decorators): subject

discussion body (선택)
```

## Labels (9개)

| Label | 의미 | Blocking? | 예시 |
|-------|------|:---------:|------|
| `praise` | 잘한 부분 칭찬 | No | 깔끔한 구현, 좋은 패턴 |
| `nitpick` | 사소한 스타일 | No | 변수명, 포맷, 공백 |
| `suggestion` | 개선 제안 | No | 더 나은 방법 제안 |
| `issue` | 문제 발견 — 반드시 수정 | **Yes** | 버그, 보안 취약점 |
| `todo` | 필수 변경 사항 | **Yes** | 누락된 체크, 필수 추가 |
| `question` | 질문/확인 필요 | No | 의도 확인, 근거 질문 |
| `thought` | 아이디어 공유 | No | 향후 개선 아이디어 |
| `chore` | 단순 정리 작업 | Yes | include 정렬, 로그 제거 |
| `note` | 참고 정보 | No | 배경 지식, errata 정보 |

## Decorators

### 표준 (3개)

| Decorator | 의미 |
|-----------|------|
| `(blocking)` | 반드시 해결 — 머지 차단 |
| `(non-blocking)` | 머지 차단 안 함 |
| `(if-minor)` | 사소한 변경이면 적용, 아니면 무시 |

### mcukit 도메인 (6개)

| Decorator | 의미 | 도메인 |
|-----------|------|--------|
| `(safety)` | ISR, 스택, watchdog, 전원 관련 | MCU |
| `(memory)` | Flash/RAM 예산, 메모리 레이아웃 | MCU |
| `(timing)` | 실시간성, 타이밍 제약 | MCU/MPU |
| `(misra)` | MISRA C:2012 규칙 관련 | MCU |
| `(dt-binding)` | Device Tree 바인딩 호환성 | MPU |
| `(mvvm)` | MVVM 패턴, ViewModel/View 분리 | WPF |

Decorator는 쉼표로 조합 가능: `issue (blocking, safety): ...`

## AI 리뷰 규칙

1. **blocking issue는 반드시 코드 위치(file:line)와 수정 제안을 함께 제시**
2. **리뷰당 praise를 최소 1건 포함** (Google eng-practices 권장)
3. **사람에 대한 comment 금지** — 코드에 대해서만 (Google 규칙)
4. **"왜" 문제인지 설명** — label만 붙이지 않음
5. **도메인 decorator는 해당 도메인일 때만 사용**
6. **수정 제안 시 before/after 코드 블록 포함 권장**

## 실전 예시

### MCU — ISR 안전성

```
issue (blocking, safety): ISR 핸들러 내에서 HAL_Delay()를 호출하면 안 됩니다.

HAL_Delay()는 내부적으로 SysTick을 사용하는데, ISR 컨텍스트에서는
SysTick 인터럽트가 처리되지 못해 무한 대기에 빠집니다.

대안: 타이머 기반 non-blocking 딜레이를 사용하거나,
DMA 전송 완료를 폴링하세요.

참고: MISRA C:2012 Rule 21.2
```

### MCU — 메모리 최적화

```
suggestion (memory, non-blocking): 이 lookup 테이블을 `const`로 선언하면
Flash에 배치되어 RAM 48바이트를 절약할 수 있습니다.

Before: `uint8_t crc_table[256];`  → RAM
After:  `const uint8_t crc_table[256];`  → Flash
```

### MCU — 칭찬

```
praise: DMA 더블 버퍼링 구현이 교과서적입니다.
Half-transfer와 transfer-complete 인터럽트 분리가 정확해요.
```

### MPU — Device Tree

```
issue (blocking, dt-binding): compatible 문자열이 바인딩 문서와 다릅니다.

DT: compatible = "vendor,my-sensor-v2";
바인딩 문서: compatible = "vendor,my-sensor";

버전 접미사를 제거하거나 바인딩 문서를 업데이트하세요.
```

### WPF — MVVM 패턴

```
issue (blocking, mvvm): ViewModel에서 System.Windows.Controls.MessageBox를
직접 참조하고 있습니다.

ViewModel은 View에 의존하면 안 됩니다.
IDialogService 인터페이스를 주입하여 사용하세요.
```

### 공통 — 질문

```
question (non-blocking): 이 타임아웃 값(500ms)의 근거가 있나요?

하드웨어 스펙에서 최대 응답 시간이 정의되어 있다면
매직 넘버 대신 #define으로 명시하면 좋겠습니다.
```
