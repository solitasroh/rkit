# mcukit 사용 가이드

> **mcukit v0.6.0** — AI Native 임베디드 개발 키트
>
> MCU / MPU(Embedded Linux) / WPF 3개 도메인을 위한 PDCA 기반 AI 개발 워크플로

---

## 목차

1. [설치 및 업데이트](#1-설치-및-업데이트)
2. [기본 개념](#2-기본-개념)
3. [빠른 시작](#3-빠른-시작)
4. [PDCA 워크플로](#4-pdca-워크플로)
5. [안전 기능](#5-안전-기능)
6. [품질 기능](#6-품질-기능)
7. [보안 기능](#7-보안-기능)
8. [딜리버리 기능](#8-딜리버리-기능)
9. [도메인별 전문 에이전트](#9-도메인별-전문-에이전트)
10. [스킬 전체 목록](#10-스킬-전체-목록)
11. [자주 묻는 질문](#11-자주-묻는-질문)

---

## 1. 설치 및 업데이트

### 1.1 최초 설치

#### 방법 A: Plugin Marketplace (권장)

```bash
# 1. 마켓플레이스 등록
/plugin marketplace add solitasroh/mcukit

# 2. 플러그인 설치
/plugin install mcukit@solitasroh-mcukit
```

#### 방법 B: 수동 클론 + 심볼릭 링크

```bash
# 1. 저장소 클론
git clone https://github.com/solitasroh/mcukit.git ~/.claude/plugins/mcukit

# 2. 심볼릭 링크 생성
ln -s ~/.claude/plugins/mcukit/skills ~/.claude/skills
ln -s ~/.claude/plugins/mcukit/agents ~/.claude/agents
```

#### 방법 C: 프로젝트 로컬 (서브모듈)

```bash
# 1. 서브모듈로 추가
cd my-stm32-project
git submodule add https://github.com/solitasroh/mcukit.git .mcukit

# 2. .claude/ 디렉토리에 심볼릭 링크
mkdir -p .claude
ln -s ../.mcukit/skills .claude/skills
ln -s ../.mcukit/agents .claude/agents
cp .mcukit/CLAUDE.md ./CLAUDE.md
```

### 1.2 기존 설치 업데이트

플러그인을 이미 설치한 경우, 설치 방법에 따라 업데이트 절차가 다릅니다.

#### Marketplace로 설치한 경우

```bash
# Claude Code 세션에서 실행
/plugin update mcukit
```

플러그인 캐시가 자동으로 최신 버전을 가져옵니다. Claude Code를 재시작하면 새 버전이 적용됩니다.

#### 수동 클론으로 설치한 경우

```bash
# 1. 플러그인 디렉토리로 이동 후 pull
cd ~/.claude/plugins/mcukit
git pull origin main

# 2. Claude Code 세션 재시작 (새 터미널에서)
claude
```

심볼릭 링크가 유지되어 있으므로 `git pull`만으로 모든 스킬과 에이전트가 업데이트됩니다.

#### 서브모듈로 설치한 경우

```bash
# 1. 프로젝트 루트에서 서브모듈 업데이트
cd my-stm32-project
git submodule update --remote .mcukit

# 2. CLAUDE.md가 변경된 경우 재복사
cp .mcukit/CLAUDE.md ./CLAUDE.md

# 3. Claude Code 세션 재시작
claude
```

#### 업데이트 확인

```bash
# 설치된 버전 확인 (Claude Code 세션 내에서)
/skill-status
```

v0.6.0에서 추가된 스킬 6개(`/freeze`, `/guard`, `/reframe`, `/arch-lock`, `/security-review`, `/ship`)가 목록에 표시되면 업데이트가 완료된 것입니다.

---

## 2. 기본 개념

### 2.1 지원 도메인

mcukit은 프로젝트 파일을 분석하여 자동으로 도메인을 감지합니다.

| 도메인 | 대상 플랫폼 | 자동 감지 파일 |
|--------|------------|---------------|
| **MCU** | STM32, NXP Kinetis K | `.ioc`, `.ld`, `startup_*.s`, `stm32*.h`, `fsl_*.h` |
| **MPU** | i.MX6, i.MX6ULL, i.MX28 | `.dts`, `.dtsi`, `bblayers.conf`, `*.bb` |
| **WPF** | C#/XAML/.NET 8 | `.csproj` + `<UseWPF>true</UseWPF>` |

### 2.2 PDCA 방법론

mcukit의 모든 개발 워크플로는 PDCA(Plan-Do-Check-Act) 사이클을 따릅니다.

```
[PM] → [Plan] → [Design] → [Do] → [Check] → [Act] → [Report]
  │       │         │         │        │         │        │
  PRD   계획서    설계서    구현    Gap분석  자동수정   보고서
```

각 단계에서 문서가 자동 생성되며, Check 단계에서 설계 대비 구현 일치율(Match Rate)을 측정합니다. 90% 이상이면 완료, 미만이면 Act(자동 수정)를 반복합니다.

### 2.3 자동화 레벨 (L0-L4)

| 레벨 | 이름 | 설명 |
|:----:|------|------|
| L0 | Manual | 모든 작업에 사용자 확인 필요 |
| L1 | Assisted | 문서 작업만 자동, 코드 변경은 확인 |
| **L2** | **Semi-Auto** | 표준 작업 자동, 위험 작업만 확인 (기본값) |
| L3 | Auto | 대부분 자동, Critical만 확인 |
| L4 | Full-Auto | 완전 자동 (주의: 위험) |

```bash
# 자동화 레벨 변경
/control level 3

# 현재 상태 확인
/control status
```

---

## 3. 빠른 시작

### 3.1 MCU 프로젝트 예시 (STM32 UART DMA)

```bash
# 1. STM32 프로젝트 디렉토리에서 Claude Code 시작
cd my-stm32-project
claude

# 2. mcukit이 자동 감지 → MCU 도메인 활성화
# 3. 새 기능 개발 시작
/pdca plan uart-dma

# 4. 설계 문서 생성 (3가지 아키텍처 옵션 제시)
/pdca design uart-dma

# 5. 구현 가이드 확인 후 코딩
/pdca do uart-dma

# 6. 설계 대비 구현 검증
/pdca analyze uart-dma

# 7. 완료 보고서
/pdca report uart-dma
```

### 3.2 MPU 프로젝트 예시 (i.MX6 SPI 드라이버)

```bash
cd my-imx6-project
claude

/pdca plan spi-driver
/pdca design spi-driver
/pdca do spi-driver
/pdca analyze spi-driver
/pdca report spi-driver
```

### 3.3 WPF 프로젝트 예시 (시리얼 모니터)

```bash
cd my-wpf-project
claude

/pdca plan serial-monitor
/pdca design serial-monitor
/pdca do serial-monitor
/pdca analyze serial-monitor
/pdca report serial-monitor
```

---

## 4. PDCA 워크플로

### 4.1 `/pdca` — 통합 PDCA 관리

모든 PDCA 명령은 `/pdca` 하위 커맨드로 통합되어 있습니다.

| 명령 | 설명 | 출력 파일 |
|------|------|-----------|
| `/pdca pm {feature}` | PM 분석 (PRD 생성) | `docs/00-pm/{feature}.prd.md` |
| `/pdca plan {feature}` | 계획서 작성 | `docs/01-plan/features/{feature}.plan.md` |
| `/pdca design {feature}` | 설계서 작성 (3가지 옵션) | `docs/02-design/features/{feature}.design.md` |
| `/pdca do {feature}` | 구현 가이드 | (가이드만 제공) |
| `/pdca analyze {feature}` | Gap 분석 (Check) | `docs/03-analysis/{feature}.analysis.md` |
| `/pdca iterate {feature}` | 자동 수정 (Act) | 코드 자동 수정 |
| `/pdca report {feature}` | 완료 보고서 | `docs/04-report/features/{feature}.report.md` |
| `/pdca status` | 현재 상태 확인 | — |
| `/pdca next` | 다음 단계 안내 | — |
| `/pdca archive {feature}` | 완료 문서 아카이브 | `docs/archive/YYYY-MM/{feature}/` |

### 4.2 PDCA 단계별 상세

#### PM 분석 (선택사항)

```bash
/pdca pm uart-dma
```

PM Agent Team(5개 에이전트)이 시장 분석, 경쟁사 분석, 사용자 페르소나, 가치 제안을 수행합니다. 결과로 PRD(Product Requirements Document)가 생성됩니다.

> 참고: Agent Teams 기능이 필요합니다 (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)

#### Plan (계획)

```bash
/pdca plan uart-dma
```

- PRD가 있으면 자동 참조하여 품질 향상
- **Checkpoint 1**: 요구사항 이해 확인 → 사용자 승인 대기
- **Checkpoint 2**: 불명확한 요소에 대한 질문 → 답변 대기 후 문서 생성

더 깊은 계획이 필요하면:

```bash
/plan-plus uart-dma
```

Plan Plus는 의도 탐색, 대안 브레인스토밍, YAGNI 검토를 추가합니다.

#### Design (설계)

```bash
/pdca design uart-dma
```

- 3가지 아키텍처 옵션 제시:
  - **Option A**: 최소 변경 (빠르지만 결합도 높음)
  - **Option B**: Clean Architecture (분리 최적, 파일 많음)
  - **Option C**: 실용적 균형 (권장 기본값)
- **Checkpoint 3**: 아키텍처 선택 → 사용자 결정 대기

#### Do (구현)

```bash
/pdca do uart-dma
```

- 설계서 기반으로 구현 범위 요약 (파일 수, 예상 라인 수)
- **Checkpoint 4**: 구현 범위 승인 → 사용자 승인 없이 구현 시작 안 함

#### Check (검증)

```bash
/pdca analyze uart-dma
```

- `gap-detector` 에이전트가 설계서 vs 구현 코드 비교
- Match Rate 계산 및 Gap 목록 생성
- **Checkpoint 5**: 이슈 심각도별 표시 후 수정 방법 선택
  - "지금 모두 수정" → iterate 진행
  - "Critical만 수정" → Critical만 수정
  - "그대로 진행" → 현재 상태 수용

#### Act (자동 수정)

```bash
/pdca iterate uart-dma
```

- Match Rate < 90%일 때 자동 수정
- 최대 5회 반복, 90% 이상 달성 시 중단
- 매 반복마다 gap-detector 재실행

#### Report (보고서)

```bash
/pdca report uart-dma
```

- Plan, Design, Implementation, Analysis 통합 보고서
- Executive Summary + Value Delivered 4관점 테이블
- 교훈 및 개선사항 포함

---

## 5. 안전 기능

### 5.1 `/freeze` — 파일 동결

핵심 파일을 보호하여 실수로 변경하는 것을 방지합니다.

```bash
# 도메인 프리셋으로 한 번에 동결
/freeze preset mcu
/freeze preset mpu
/freeze preset wpf

# 개별 파일/패턴 동결
/freeze add "*.ld"
/freeze add "startup_*.s"

# 동결 해제
/freeze unfreeze "*.ld"

# 동결 목록 확인
/freeze list
```

#### 도메인별 프리셋

| 도메인 | 동결 대상 | 이유 |
|--------|----------|------|
| **MCU** | `*.ld`, `startup_*.s`, `*.ioc`, `system_*.c`, `stm32*_hal_conf.h` | 링커/스타트업/HAL 설정 변경 시 부팅 실패 위험 |
| **MPU** | `*.dts`, `*.dtsi`, `Kconfig`, 커널 `Makefile`, `include/linux/*.h` | DT/커널 설정 변경 시 드라이버 전체 영향 |
| **WPF** | `App.xaml`, `*.csproj`, `AssemblyInfo.cs`, `app.manifest` | 프로젝트 설정/진입점 변경 시 전체 앱 영향 |

동결된 파일에 Write/Edit을 시도하면 `pre-write.js` 훅이 차단합니다.

### 5.2 `/guard` — 통합 안전모드

freeze + 자동화 레벨 제한 + 파괴적 명령 차단을 하나로 통합합니다.

```bash
# 안전모드 활성화
/guard on

# 안전모드 비활성화
/guard off

# 상태 확인
/guard status
```

#### 가드 모드 활성화 시 동작

1. **자동화 레벨 L2 캡**: L3 이상으로 올릴 수 없음
2. **도메인 프리셋 자동 적용**: 현재 도메인의 freeze 프리셋 활성화
3. **파괴적 명령 전면 차단**: 일반 모드에서 경고만 하던 명령도 차단

#### 도메인별 차단 명령 (가드 모드)

| 도메인 | 차단 명령 | 규칙 ID |
|--------|----------|---------|
| **MCU** | `openocd`, `st-flash`, `STM32_Programmer_CLI`, `JLinkExe`, `pyocd` | G-009 |
| **MPU** | `dd if=.*of=/dev/`, `insmod`/`rmmod`, `mknod`, `echo.*>/proc/`, `devmem` | G-010 |
| **WPF** | `signtool`, `certutil`, `sn.exe` | G-011 |

### 5.3 `/arch-lock` — 아키텍처 락

설계 문서의 아키텍처 결정을 동결하고, 해당 영역 파일 변경을 제한합니다.

```bash
# 설계 결정 잠금
/arch-lock lock uart-dma

# 잠금 해제
/arch-lock unlock uart-dma

# 상태 확인
/arch-lock status

# Mermaid 다이어그램 생성
/arch-lock diagram uart-dma
```

#### 도메인별 다이어그램

| 도메인 | 생성 다이어그램 |
|--------|---------------|
| **MCU** | 메모리 맵(Flash/RAM), 페리퍼럴 할당표, 인터럽트 우선순위, 소프트웨어 레이어 |
| **MPU** | SW 스택(Kernel→Driver→Library→App), DT 노드 트리, IPC 구조(ioctl/sysfs/socket) |
| **WPF** | MVVM 구조도, DI 컨테이너 그래프, 네비게이션 맵 |

잠긴 아키텍처 영역의 파일을 변경하려 하면 `pre-write.js`와 `scope-limiter.js`에서 경고 또는 차단합니다.

---

## 6. 품질 기능

### 6.1 `/reframe` — 임베디드 챌린지 프로토콜

PDCA 시작 **전에** 문제 정의와 가정을 체계적으로 검증하는 5단계 21개 질문입니다. 6개 검증된 프레임워크를 통합했습니다.

```bash
# 전체 모드 (21개 질문) — 신규 기능, 아키텍처 변경
/reframe uart-dma --mode full

# 표준 모드 (15개 질문: Q1-Q15) — 중간 규모 작업
/reframe uart-dma --mode standard

# 빠른 모드 (핵심 7개 질문) — 버그 수정, 소규모 개선
/reframe uart-dma --mode quick
```

#### 5단계 질문 구조

**Phase 1: 문제 검증** (Q1-Q4)
- Q1: "어떤 문제를 해결하려는가?" — 한 문장으로 명확화
- Q2: "누가 이 문제를 경험하는가?" — 증거/데이터 필수
- Q3: "아무것도 안 하면 어떻게 되는가?" — 비용 정량화
- Q4: "완전히 다르게 프레이밍할 수 있는가?" — 관점 전환

도메인별 리프레이밍 예시:

| 도메인 | 기존 질문 | 리프레이밍 |
|--------|----------|-----------|
| MCU | "이 ISR을 어떻게 빠르게 하지?" | "이 작업이 ISR에 있어야 하나, deferred 처리가 맞지 않나?" |
| MPU | "ioctl을 어떻게 추가하지?" | "sysfs/configfs로 충분하지 않은가?" |
| WPF | "UI가 왜 느리지?" | "이 처리가 ViewModel에 있어야 하나, 백그라운드 서비스가 맞지 않나?" |

**Phase 2: 가정 수면화** (Q5-Q8)
- Q5: "솔루션이 작동하려면 무엇이 참이어야 하는가?" — 가정 나열
- Q6: "증거 없는 가정은?" — Leap of Faith 식별
- Q7: "3개월 후 실패했다면 무엇이 잘못되었는가?" — Pre-Mortem
- Q8: "가장 위험한 실패 모드는?" — 핵심 리스크 대응

**Phase 3: 솔루션 챌린지** (Q9-Q12)
- Q9: "왜 이 솔루션인가?" — Five Whys
- Q10: "모든 대안을 고려했는가?" — MECE 체크
- Q11: "가장 작은 버전은?" — MVP 정의
- Q12: "2차 영향은?" — Flash/RAM, CPU, 전력, 빌드시간

**Phase 4: 측정 계약** (Q13-Q15)
- Q13: "'완료'를 어떻게 아는가?" — Pass/Fail 기준
- Q14: "어떻게 측정하는가?" — 도구 명시
- Q15: "최악의 경우는?" — 경계 조건 확인

**Phase 5: 코드 품질 챌린지** (Q16-Q21)
- Q16: 기존 코드 패턴과의 일관성
- Q17: 의존성 방향 검증
- Q18: 에러 핸들링 전략
- Q19: 동시성/공유 자원 문제
- Q20: 테스트 가능한 구조인가
- Q21: API/인터페이스 계약 명확성

출력: `docs/00-pm/{feature}.reframe.md`

### 6.2 `/code-review` — 코드 리뷰 (자동 수정 지원)

```bash
# 기본 코드 리뷰
/code-review

# 자동 수정 모드 (v0.6.0 신규, L2 이상에서만)
/code-review --auto-fix
```

자동 수정 모드:
- **Critical 이슈**: 수동 리뷰 유지 (자동 수정 안 함)
- **Major/Minor 이슈**: 자동 수정 적용
- **가드 모드에서**: 비활성화 (안전 우선)

### 6.3 Design Validator — 설계 점수 (0-10)

설계 문서를 5개 차원으로 정량 평가합니다 (자동 실행).

| 차원 | 비중 | MCU | MPU | WPF |
|------|:----:|-----|-----|-----|
| 메모리 효율성 | 20% | Flash/RAM 예산 명확성 | 커널 메모리, 앱 RSS | 힙 사용량 분석 |
| 실시간성/응답성 | 20% | ISR 지연 명세 | 드라이버 응답, 앱 처리량 | UI 응답성 목표 |
| 추상화 품질 | 25% | HAL 분리 명확성 | Kernel↔User 인터페이스 | MVVM 준수 |
| 이식성 | 15% | 칩 독립성 수준 | 커널/보드 독립성 | .NET 버전 호환 |
| 테스트 용이성 | 20% | 모킹 가능성 | 드라이버 유닛테스트 격리 | ViewModel 테스트 |

점수 해석:

| 점수 | 등급 | 의미 |
|:----:|:----:|------|
| 9-10 | A | 우수 — 즉시 구현 가능 |
| 7-8 | B | 양호 — 경미한 개선 권장 |
| 5-6 | C | 보통 — 중요한 갭 보완 필요 |
| 3-4 | D | 부족 — 대폭 수정 필요 |
| 0-2 | F | 미완성 — 구현 불가 |

---

## 7. 보안 기능

### 7.1 `/security-review` — STRIDE 위협 모델링

임베디드 시스템에 특화된 STRIDE 분석을 수행합니다.

```bash
# 기본 보안 리뷰
/security-review uart-dma

# 도메인 지정
/security-review uart-dma --domain mcu

# 신뢰도 임계값 조정 (기본 8/10)
/security-review uart-dma --confidence 7
```

#### STRIDE 위협 매트릭스

| 카테고리 | MCU 위협 | MPU 위협 | WPF 위협 |
|----------|---------|---------|---------|
| **Spoofing** | 펌웨어 위조, 부트로더 변조 | 커널 모듈 위장, 공유라이브러리 교체 | 인증서 위조, DLL injection |
| **Tampering** | Flash 직접 변조, OTP 영역 | DT overlay 변조, /etc 파일 | config 변조, 레지스트리 |
| **Repudiation** | 센서 데이터 부인, 로그 부재 | syslog 삭제, audit trail 부재 | EventLog 미기록 |
| **Info Disclosure** | JTAG/SWD 개방, UART 디버그 | /proc 정보 노출, core dump | 메모리 덤프, 시리얼 스니핑 |
| **DoS** | 인터럽트 스톰, 워치독 트리거 | fork bomb, OOM killer | UI 블로킹, 포트 독점 |
| **EoP** | 스택 오버플로, MPU 미설정 | 커널 취약점, setuid 남용 | UAC bypass, 권한 상승 |

- 신뢰도 8/10 이상만 보고 (노이즈 최소화)
- 테스트/목업/예시 디렉토리는 자동 제외 (false-positive 방지)

---

## 8. 딜리버리 기능

### 8.1 `/ship` — GitLab MR 자동화

PDCA 완료 후 GitLab Merge Request를 자동 생성합니다. `glab` CLI를 사용합니다.

```bash
# 기능 브랜치에서 MR 생성
/ship mr uart-dma

# 현재 브랜치에서 MR 생성
/ship mr

# 릴리스 생성 (태그 + MR + 체인지로그)
/ship release v1.2.0

# 태그만 생성
/ship tag v1.2.0
```

#### 사전 요구사항

```bash
# glab CLI 설치 (https://gitlab.com/gitlab-org/cli)
brew install glab          # macOS
sudo apt install glab      # Ubuntu

# GitLab 인증
glab auth login
```

#### MR 워크플로

```
/ship mr uart-dma
  1. glab --version 확인
  2. git status 확인 (미커밋 변경 경고)
  3. PDCA Report 읽기 (있으면)
  4. git checkout -b feature/uart-dma
  5. git add + commit (PDCA 기반 메시지)
  6. git push -u origin feature/uart-dma
  7. glab mr create --title --description (도메인별 템플릿)
  8. glab mr view --web (결과 확인)
```

#### 도메인별 MR 섹션

| 도메인 | MR에 자동 포함되는 섹션 |
|--------|----------------------|
| **MCU** | Flash/RAM 변화량, 페리퍼럴 변경, 인터럽트 변경, MISRA 준수 상태 |
| **MPU** | 커널 ABI 영향, 드라이버 인터페이스 변경(ioctl/sysfs), DT 바인딩 변경, 라이브러리 API/ABI 호환성 |
| **WPF** | NuGet 패키지 변경, XAML 바인딩 영향, .NET 타겟 호환성 |

### 8.2 `/audit` — 감사 로그 및 회고

```bash
# 최근 감사 로그 조회
/audit

# 기능별 결정 추적
/audit trace uart-dma

# 일일/주간 요약
/audit summary

# 주간 회고 (v0.6.0 신규)
/audit retro

# 로그 검색
/audit search "phase_transition"
```

#### 주간 회고 (`/audit retro`)

```
--- Weekly Retrospective (2026-03-18 ~ 2026-03-25) ---
PDCA Completion Rate : 3/4 (75%)     [prev: 2/3 (67%) +8%]
Avg Match Rate       : 92%           [prev: 88%        +4%]
Total Iterations     : 7             [prev: 9          -2]

Match Rate Trend (7 days):
  100|                    *
   90|    *       *  *
   80|  *   *  *
   70|
      Mon Tue Wed Thu Fri Sat Sun

Features Completed:
  [x] uart-dma      | 95% | 2 iter
  [x] spi-config    | 91% | 1 iter
  [ ] can-protocol  | 82% | 3 iter (in progress)
------------------------------------------------------
```

---

## 9. 도메인별 전문 에이전트

mcukit은 40개의 AI 에이전트를 제공합니다. 키워드를 입력하면 자동으로 적합한 에이전트가 활성화됩니다.

### 9.1 MCU 전문 에이전트

| 에이전트 | 전문 분야 | 트리거 키워드 |
|---------|----------|-------------|
| `fw-architect` | 펌웨어 아키텍처, SW 레이어, 인터럽트 맵 | firmware architecture, FW 설계 |
| `hw-interface-expert` | GPIO, SPI, I2C, UART, CAN, ADC, DMA | peripheral, 페리페럴 설정 |
| `safety-auditor` | MISRA C:2012, 스택 오버플로, 초기화 검증 | MISRA, safety, 코딩 표준 |

### 9.2 MPU 전문 에이전트

| 에이전트 | 전문 분야 | 트리거 키워드 |
|---------|----------|-------------|
| `linux-bsp-expert` | Device Tree, 커널 설정, 부팅 시퀀스 | BSP, Device Tree, DTS |
| `kernel-module-dev` | platform_driver, sysfs/ioctl, DMA | kernel module, driver |
| `yocto-expert` | 레시피 작성, 레이어 관리, 이미지 빌드 | Yocto, bitbake, recipe |

### 9.3 WPF 전문 에이전트

| 에이전트 | 전문 분야 | 트리거 키워드 |
|---------|----------|-------------|
| `wpf-architect` | MVVM, DI 컨테이너, 네비게이션 설계 | WPF architecture, MVVM |
| `xaml-expert` | DataTemplate, Style, Converter, 바인딩 | XAML, binding, style |
| `dotnet-expert` | CommunityToolkit.Mvvm, DI, xUnit, SerialPort | .NET, C#, DI, xUnit |

### 9.4 공통 에이전트

| 에이전트 | 역할 | 트리거 키워드 |
|---------|------|-------------|
| `gap-detector` | 설계-구현 Gap 분석 | 검증, verify, 확인 |
| `pdca-iterator` | 자동 수정 반복 | 개선, improve, 고쳐줘 |
| `code-analyzer` | 코드 품질 분석 | 분석, analyze, 품질 |
| `report-generator` | PDCA 보고서 생성 | 보고서, report, 요약 |
| `security-architect` | 보안 아키텍처 + STRIDE | 보안, security, 취약점 |
| `design-validator` | 설계 문서 검증 + 점수 | 설계 검증, validate design |
| `cto-lead` | CTO 레벨 팀 오케스트레이션 | team, 팀 구성, CTO |

---

## 10. 스킬 전체 목록

### 10.1 PDCA 워크플로 스킬

| 스킬 | 명령 | 설명 |
|------|------|------|
| `pdca` | `/pdca {action}` | 통합 PDCA 관리 (plan/design/do/analyze/iterate/report) |
| `plan-plus` | `/plan-plus {feature}` | 브레인스토밍 강화 계획 |
| `reframe` | `/reframe {feature}` | 임베디드 챌린지 프로토콜 (21Q) |
| `pdca-batch` | `/pdca-batch` | 다중 기능 일괄 관리 |

### 10.2 안전/보안 스킬

| 스킬 | 명령 | 설명 |
|------|------|------|
| `freeze` | `/freeze {action}` | 파일 동결 (도메인 프리셋 지원) |
| `guard` | `/guard {on/off/status}` | 통합 안전모드 |
| `arch-lock` | `/arch-lock {action}` | 아키텍처 결정 동결 |
| `security-review` | `/security-review {feature}` | STRIDE 위협 모델링 |
| `control` | `/control {action}` | 자동화 레벨/안전 상태 관리 |

### 10.3 도메인 전문 스킬

| 스킬 | 도메인 | 설명 |
|------|--------|------|
| `stm32-hal` | MCU | STM32 HAL/LL API 가이드 |
| `freertos` | MCU | FreeRTOS 태스크/동기화 설계 |
| `cmake-embedded` | MCU | 임베디드 CMake 빌드 시스템 |
| `communication` | MCU | UART/SPI/I2C/CAN 통신 패턴 |
| `rootfs-config` | MPU | 루트파일시스템 구성 |
| `xaml-design` | WPF | XAML UI 디자인/스타일 가이드 |
| `serial-bridge` | MCU+WPF | MCU↔WPF 시리얼 통신 브릿지 |

### 10.4 딜리버리/유틸리티 스킬

| 스킬 | 명령 | 설명 |
|------|------|------|
| `ship` | `/ship {mr/release/tag}` | GitLab MR 자동화 (glab) |
| `code-review` | `/code-review [--auto-fix]` | 코드 리뷰 (자동 수정 지원) |
| `audit` | `/audit {action}` | 감사 로그/회고 |
| `skill-status` | `/skill-status` | 설치된 스킬 목록 |
| `claude-code-learning` | `/claude-code-learning` | Claude Code 사용법 학습 |

---

## 11. 자주 묻는 질문

### Q: mcukit은 어떤 Claude Code 버전이 필요한가요?

**A:** v2.1.78 이상이 필요합니다. `claude --version`으로 확인하세요.

### Q: 도메인을 수동으로 지정할 수 있나요?

**A:** mcukit은 프로젝트 파일 기반으로 자동 감지합니다. `.ioc` 파일이 있으면 MCU, `.dts`가 있으면 MPU, `.csproj`에 `UseWPF`가 있으면 WPF로 인식합니다.

### Q: GitHub를 쓰는데 `/ship`을 사용할 수 있나요?

**A:** `/ship`은 GitLab `glab` CLI 전용입니다. GitHub의 경우 Claude Code 내장 `gh` 명령을 직접 사용하세요:
```bash
gh pr create --title "제목" --body "설명"
```

### Q: Guard 모드에서 긴급하게 파일을 수정해야 하면?

**A:** `/guard off`로 비활성화한 후 수정하세요. 작업 후 `/guard on`으로 다시 활성화하는 것을 권장합니다.

### Q: PDCA를 꼭 다 거쳐야 하나요?

**A:** 아닙니다. 간단한 버그 수정이나 소규모 변경은 PDCA 없이 바로 진행해도 됩니다. mcukit은 변경 규모에 따라 자동으로 PDCA 필요성을 판단합니다:
- **Quick Fix** (10줄 미만): PDCA 불필요
- **Minor Change** (10-50줄): PDCA 선택
- **Feature** (50-200줄): PDCA 권장
- **Major Feature** (200줄 이상): PDCA 강력 권장

### Q: Agent Teams란 무엇인가요?

**A:** 여러 AI 에이전트가 병렬로 작업하는 기능입니다. CTO Lead가 전체를 오케스트레이션합니다. 사용하려면:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
/pdca team uart-dma
```

### Q: 플러그인을 제거하려면?

**A:**
```bash
# Marketplace 설치의 경우
/plugin uninstall mcukit

# 수동 설치의 경우
rm -rf ~/.claude/plugins/mcukit
rm ~/.claude/skills    # 심볼릭 링크 제거
rm ~/.claude/agents    # 심볼릭 링크 제거
```

---

## 요구사항

- **Claude Code**: v2.1.78 이상
- **Node.js**: 18 이상 (Hook 스크립트 실행용)
- **glab CLI**: GitLab MR 기능 사용 시 (선택사항)

## 라이센스

MIT

## 기반 기술

PDCA 코어 엔진은 [bkit-claude-code](https://github.com/popup-studio-ai/bkit-claude-code) (Apache 2.0, POPUP STUDIO)에서 포팅되었습니다. v0.6.0 안전/품질 기능은 [gstack](https://github.com/garrytan/gstack) (Garry Tan)의 패턴을 임베디드 도메인에 적응한 것입니다.
