# Design: eval-full-coverage

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 벤치마크 31% 통과율, 기존 도메인 eval 12개가 placeholder 수준, bkit 공통 웹 스킬이 mcukit과 무관하게 config에 포함 |
| **Solution** | Clean Architecture: config 재구성 + runner.js criteria 확장 + 기존 12개 업그레이드 + 신규 10개 작성 |
| **Function UX Effect** | 벤치마크 31개 스킬 전체 통과(100%), 스킬별 정밀 criteria로 도메인 특화 품질 검증 |
| **Core Value** | MCU/MPU/Desktop 도메인에 집중된 자동 품질 검증 체계, Qt 확장 대비 구조 |

## 1. 설계 선택: Option B — Clean Architecture

### 1.1 핵심 결정사항

| 항목 | 결정 |
|------|------|
| 아키텍처 | 스킬별 고유 criteria + 도메인 키워드 확장 |
| runner.js | evaluateAgainstCriteria에 5개 criteria 카테고리 추가 |
| config.json | bkit 공통 10개 제거 + 도메인 12개 추가 = 31개 |
| 기존 eval | 12개 placeholder → substantive content 업그레이드 |
| 신규 eval | 10개 작성 (workflow 2 + capability 8) |
| Desktop 범위 | WPF + WinUI3 (C# 기반), Electron/Tauri 제외 |
| 확장성 | Qt/QML 도메인 추가 시 config + eval 3파일만 추가 |

### 1.2 기존 placeholder 이슈

| 스킬 | prompt | expected | 통과 여부 |
|------|--------|----------|----------|
| stm32-hal | 1줄 ~70자 | 1줄 ~68자 | ❌ placeholder |
| freertos | 1줄 ~48자 | 1줄 ~52자 | ❌ placeholder |
| wpf-mvvm | 1줄 ~48자 | 1줄 ~52자 | ❌ placeholder |
| 기타 8개 | 1줄 | 1줄 | ❌ placeholder |

**통과 조건** (evaluateAgainstCriteria):
- prompt: >1줄 AND ≥50자
- expected: >1줄 AND ≥50자 (placeholder 탈락)
- expected: ≥100자 AND ≥5줄 (generic criteria 통과)

## 2. runner.js criteria 매칭 확장

### 2.1 현재 키워드 카테고리 (5개)

| 카테고리 | 매칭 키워드 | 검증 대상 | 검증 방법 |
|----------|-----------|----------|----------|
| trigger | `trigger`, `keyword` | prompt | prompt에 trigger/keyword/intent 포함 |
| process | `process`, `step` | expected | expected에 1./Step/## 포함 |
| output | `output`, `produce` | expected | expected에 Expected/Output/Result/``` 포함 |
| pattern | `pattern`, `follow` | expected | expected에 pattern/format/structure/template 포함 |
| generic | (위 키워드 없음) | expected | expected ≥100자 AND ≥5줄 |

### 2.2 신규 추가 키워드 카테고리 (5개)

| 카테고리 | 매칭 키워드 | 검증 대상 | 검증 방법 |
|----------|-----------|----------|----------|
| **code** | `code`, `implement` | expected | expected에 ``` / function / void / class / def / const 포함 |
| **safety** | `safety`, `security`, `vulnerability` | expected | expected에 MISRA/OWASP/CVE/validation/sanitize/security 포함 |
| **architecture** | `architecture`, `design`, `layer` | expected | expected에 layer/module/component/interface/diagram/architecture 포함 |
| **api** | `api`, `endpoint`, `protocol` | expected | expected에 GET/POST/request/response/serial/packet 포함 |
| **config** | `config`, `setup`, `initialize` | expected | expected에 config/setup/.yaml/.json/CMake/Makefile 포함 |

### 2.3 runner.js 수정 코드

`evaluateAgainstCriteria()` 함수의 기존 pattern 카테고리 else-if 블록 뒤, generic else 블록 앞에 5개 블록 추가:

```javascript
} else if (criterionLower.includes('code') || criterionLower.includes('implement')) {
  const hasCode = expected.includes('```') || expected.includes('function') ||
                  expected.includes('void') || expected.includes('class') ||
                  expected.includes('def') || expected.includes('const');
  if (hasCode) { matchedCriteria.push(criterion); }
  else { failedCriteria.push(criterion); }

} else if (criterionLower.includes('safety') || criterionLower.includes('security') || criterionLower.includes('vulnerability')) {
  const hasSafety = expected.includes('MISRA') || expected.includes('OWASP') ||
                    expected.includes('CVE') || expected.includes('validation') ||
                    expected.includes('sanitize') || expected.includes('security');
  if (hasSafety) { matchedCriteria.push(criterion); }
  else { failedCriteria.push(criterion); }

} else if (criterionLower.includes('architecture') || criterionLower.includes('design') || criterionLower.includes('layer')) {
  const hasArch = expected.includes('layer') || expected.includes('module') ||
                  expected.includes('component') || expected.includes('interface') ||
                  expected.includes('diagram') || expected.includes('architecture');
  if (hasArch) { matchedCriteria.push(criterion); }
  else { failedCriteria.push(criterion); }

} else if (criterionLower.includes('api') || criterionLower.includes('endpoint') || criterionLower.includes('protocol')) {
  const hasApi = expected.includes('GET') || expected.includes('POST') ||
                 expected.includes('request') || expected.includes('response') ||
                 expected.includes('serial') || expected.includes('packet');
  if (hasApi) { matchedCriteria.push(criterion); }
  else { failedCriteria.push(criterion); }

} else if (criterionLower.includes('config') || criterionLower.includes('setup') || criterionLower.includes('initialize')) {
  const hasConfig = expected.includes('config') || expected.includes('setup') ||
                    expected.includes('.yaml') || expected.includes('.json') ||
                    expected.includes('CMake') || expected.includes('Makefile');
  if (hasConfig) { matchedCriteria.push(criterion); }
  else { failedCriteria.push(criterion); }
}
```

## 3. config.json 재구성

### 3.1 변경 후 전체 구조

```json
{
  "version": "2.0.0",
  "defaultTimeout": 60000,
  "maxRetries": 2,
  "benchmarkModel": "claude-sonnet-4-6",
  "parityThreshold": 0.85,
  "classifications": {
    "workflow": { "evalType": "process_compliance", "parityTest": false },
    "capability": { "evalType": "output_quality", "parityTest": true },
    "hybrid": { "evalType": "both", "parityTest": true }
  },
  "skills": {
    "workflow": [
      "mcukit-rules", "mcukit-templates", "pdca", "development-pipeline",
      "phase-2-convention", "phase-8-review", "zero-script-qa", "code-review",
      "pm-discovery", "cc-version-analysis", "misra-c"
    ],
    "capability": [
      "phase-1-schema", "phase-3-mockup", "phase-4-api",
      "phase-5-design-system", "phase-6-ui-integration",
      "phase-7-seo-security", "phase-9-deployment", "desktop-app",
      "stm32-hal", "freertos", "nxp-mcuxpresso",
      "imx-bsp", "kernel-driver", "yocto-build",
      "wpf-mvvm", "xaml-design",
      "cmake-embedded", "communication", "serial-bridge"
    ],
    "hybrid": ["plan-plus"]
  }
}
```

**변경 내역:**
- workflow: +1 (`misra-c`) → 11개
- capability: -10 (bkit 공통) +11 (도메인) → 19개
- hybrid: 변경 없음 → 1개
- **총 31개**

## 4. 스킬별 eval 설계

### 4.1 Workflow eval 신규 (2개)

#### zero-script-qa

```yaml
name: "zero-script-qa"
classification: "workflow"
version: "2.0.0"
evals:
  - name: "trigger-accuracy"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must trigger correctly on QA/testing keywords"
      - "Must follow defined log analysis process steps"
      - "Must produce structured test report output"
    timeout: 60000
  - name: "docker-log-analysis"
    prompt: "prompt-2.md"
    expected: "expected-2.md"
    criteria:
      - "Must follow log collection process steps"
      - "Must produce issue detection output from logs"
    timeout: 60000
```

- **prompt-1.md**: MCU UART 통신 펌웨어의 Docker 로그 기반 QA 테스트 시나리오. 테스트 대상, 검증 항목, Docker 환경 정보 포함.
- **expected-1.md**: Step 1 로그 수집 → Step 2 패턴 매칭 → Step 3 이슈 탐지 → Step 4 리포트 생성 프로세스 (5+ 스텝, structured output)

#### cc-version-analysis

```yaml
name: "cc-version-analysis"
classification: "workflow"
version: "2.0.0"
evals:
  - name: "trigger-accuracy"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must trigger correctly on version/upgrade keywords"
      - "Must follow defined analysis process steps"
      - "Must produce impact report output"
    timeout: 60000
```

- **prompt-1.md**: CC v2.1.79 업그레이드 시 mcukit 영향 분석 요청. 현재 버전, 업그레이드 대상, 관심 영역 포함.
- **expected-1.md**: Step 1 버전 조사 → Step 2 변경 분석 → Step 3 아키텍처 영향 → Step 4 리포트 생성

### 4.2 Workflow eval 업그레이드 (1개)

#### misra-c (workflow 이동 + 내용 확장)

```yaml
name: "misra-c"
classification: "workflow"
version: "2.0.0"
evals:
  - name: "trigger-accuracy"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must trigger correctly on MISRA/safety keywords"
      - "Must follow defined code analysis process steps"
      - "Must produce violation report with safety classification output"
    timeout: 60000
```

### 4.3 Capability eval 신규 (8개)

#### phase-1-schema (MCU 데이터 구조)

```yaml
name: "phase-1-schema"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce register map and protocol data structure design output"
      - "Must follow schema definition process steps"
      - "No common endianness or alignment pitfalls"
    timeout: 60000
```

- **prompt**: STM32 센서 레지스터 맵(I2C 주소, 비트필드) + UART 프레임 프로토콜(헤더, 페이로드, CRC) 스키마 정의
- **expected**: 레지스터 비트필드 정의 → 프로토콜 프레임 구조 → 엔디언 처리 → 검증 체크리스트

#### phase-3-mockup (Desktop 모니터링 UI)

```yaml
name: "phase-3-mockup"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce UI layout design with component structure output"
      - "Must follow MVVM pattern for Desktop mockup design steps"
    timeout: 60000
```

- **prompt**: MCU 센서 데이터(온도/습도/압력) 실시간 모니터링 WPF 대시보드 목업. 게이지, 차트, 상태 LED 컴포넌트 포함.
- **expected**: 레이아웃 구조 → XAML 컴포넌트 배치 → ViewModel 바인딩 → 디자인 토큰/스타일

#### phase-4-api (시리얼 통신 프로토콜)

```yaml
name: "phase-4-api"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce serial protocol command/response endpoint definitions"
      - "Must follow protocol design process steps"
      - "No common serial communication pitfalls"
    timeout: 60000
```

- **prompt**: MCU↔PC 시리얼 통신 명령 프로토콜 설계. 명령 코드, 요청/응답 패킷 구조, 에러 코드, 타임아웃 정책.
- **expected**: 패킷 포맷 → 명령 코드 테이블 → request/response 시퀀스 → 에러 핸들링

#### phase-5-design-system (Desktop 컴포넌트)

```yaml
name: "phase-5-design-system"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce XAML component design with style/template output"
      - "Must follow design system architecture layer definition steps"
    timeout: 60000
```

- **prompt**: MCU 제어용 WPF/WinUI3 컴포넌트 라이브러리 설계. RadialGauge, LineChart, StatusLed, CommandButton.
- **expected**: 디자인 토큰 → ResourceDictionary 구조 → 컴포넌트 인터페이스 → 테마 layer 분리

#### phase-6-ui-integration (Desktop-MCU 연동)

```yaml
name: "phase-6-ui-integration"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce ViewModel-SerialPort integration code implementation"
      - "Must follow MVVM data binding process steps"
    timeout: 60000
```

- **prompt**: WPF ViewModel에서 SerialPort 데이터 수신 → ObservableProperty 바인딩 → UI 자동 업데이트. 스레드 마샬링, 디스커넥트 핸들링 포함.
- **expected**: SerialPort 래퍼 → ViewModel 바인딩 → Dispatcher.Invoke → 에러/재연결 처리

#### phase-7-seo-security (임베디드 보안)

```yaml
name: "phase-7-seo-security"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must follow OTA security review process steps"
      - "Must check for firmware update security vulnerabilities"
    timeout: 60000
```

- **prompt**: MCU 펌웨어 OTA 업데이트 보안 검증. 서명 검증(ECDSA), 암호화 전송, 롤백 보호, 버전 체크.
- **expected**: 서명 검증 프로세스 → 암호화 채널 → 롤백 메커니즘 → 취약점 체크리스트

#### phase-9-deployment (펌웨어/이미지 배포)

```yaml
name: "phase-9-deployment"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must follow firmware deployment process steps"
      - "Must produce flash/image deployment configuration output"
    timeout: 60000
```

- **prompt**: STM32 플래시 프로그래밍(ST-Link, OpenOCD) + i.MX6 SD카드 이미지 배포. 릴리스 체크리스트, 검증 절차 포함.
- **expected**: 빌드 → 바이너리 검증 → 플래싱 명령 → 배포 후 검증 → 롤백 절차

#### desktop-app (C# 데스크탑 앱)

```yaml
name: "desktop-app"
classification: "capability"
version: "2.0.0"
evals:
  - name: "basic-usage"
    prompt: "prompt-1.md"
    expected: "expected-1.md"
    criteria:
      - "Must produce WPF/WinUI3 project setup configuration output"
      - "Must follow MVVM architecture design steps"
      - "No common C# desktop app pitfalls"
    timeout: 60000
```

- **prompt**: MCU 시리얼 모니터링 데스크탑 앱 프로젝트 구조 설계. WPF(.NET 8) 기반, WinUI3 마이그레이션 고려. CommunityToolkit.Mvvm, DI 컨테이너, 시리얼 포트 서비스.
- **expected**: .csproj 설정 → MVVM 폴더 구조 → DI 컨테이너 setup → SerialPort 서비스 인터페이스 → WinUI3 호환 가이드

### 4.4 기존 도메인 eval 업그레이드 (11개)

모든 eval을 멀티라인 substantive content로 확장 + 스킬별 고유 criteria 적용.

#### MCU 도메인 (3개)

| 스킬 | 신규 criteria | prompt 확장 방향 |
|------|-------------|-----------------|
| stm32-hal | "Must produce HAL API code implementation", "Must follow DMA/interrupt process steps", "No common STM32 safety pitfalls" | UART DMA 수신 요구사항 상세화 (버퍼 크기, FreeRTOS 연동, 에러 핸들링) |
| freertos | "Must produce task/queue code implementation", "Must follow RTOS design process steps", "No common stack overflow pitfalls" | 태스크 간 통신 요구사항 상세화 (우선순위, 스택 사이징, 데드락 방지) |
| nxp-mcuxpresso | "Must produce fsl_* API code implementation", "Must follow SDK initialization setup steps" | SDK 드라이버 초기화 요구사항 (clock config, pin mux, CMSIS 패턴) |

#### MPU 도메인 (3개)

| 스킬 | 신규 criteria | prompt 확장 방향 |
|------|-------------|-----------------|
| imx-bsp | "Must produce Device Tree configuration output", "Must follow BSP porting process steps" | DTS 노드 작성 (pinctrl, 클럭, 인터럽트, compatible 매칭) |
| kernel-driver | "Must produce kernel module code implementation", "Must follow driver probe/remove process steps" | platform_driver 구현 (probe, sysfs, ioctl 인터페이스) |
| yocto-build | "Must produce recipe/layer configuration output", "Must follow Yocto build setup process" | 커스텀 레시피 작성 (SRC_URI, do_compile, do_install, 의존성) |

#### Desktop 도메인 (2개)

| 스킬 | 신규 criteria | prompt 확장 방향 |
|------|-------------|-----------------|
| wpf-mvvm | "Must produce ViewModel code implementation", "Must follow MVVM pattern design steps", "No common WPF binding pitfalls" | CommunityToolkit.Mvvm ViewModel (ObservableProperty, RelayCommand, DI) |
| xaml-design | "Must produce XAML style/template output", "Must follow ResourceDictionary design pattern steps" | DataTemplate + Style + Converter 조합 (센서 데이터 시각화 컴포넌트) |

#### Cross 도메인 (3개)

| 스킬 | 신규 criteria | prompt 확장 방향 |
|------|-------------|-----------------|
| cmake-embedded | "Must produce CMakeLists.txt configuration output", "Must follow cross-compile setup process steps" | arm-none-eabi 툴체인 파일 + 링커 스크립트 연동 |
| communication | "Must produce communication driver code implementation", "Must follow DMA/interrupt protocol process steps" | UART/SPI/I2C 멀티 프로토콜 드라이버 (DMA 전송, 인터럽트 수신) |
| serial-bridge | "Must produce serial protocol bridge code implementation", "Must follow MCU-Desktop bridge design process steps" | MCU↔WPF 시리얼 통신 브릿지 (패킷 프레이밍, CRC, 재전송) |

## 5. 파일 변경 목록

### 5.1 수정 파일 (2개)

| 파일 | 변경 내용 |
|------|----------|
| `evals/runner.js` | evaluateAgainstCriteria에 5개 criteria 카테고리 추가 (§2.3) |
| `evals/config.json` | bkit 10개 제거, 도메인 12개 추가, 총 31개 (§3.1) |

### 5.2 업그레이드 파일 (36개 = 12 스킬 × 3 파일)

| 디렉토리 | 도메인 | 파일 |
|----------|--------|------|
| `evals/capability/stm32-hal/` | MCU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/freertos/` | MCU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/nxp-mcuxpresso/` | MCU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/imx-bsp/` | MPU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/kernel-driver/` | MPU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/yocto-build/` | MPU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/wpf-mvvm/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/xaml-design/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/cmake-embedded/` | Cross | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/communication/` | Cross | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/serial-bridge/` | Cross | eval.yaml, prompt-1.md, expected-1.md |
| `evals/workflow/misra-c/` | Safety | eval.yaml, prompt-1.md, expected-1.md |

### 5.3 신규 파일 (32개)

**Workflow 신규 (2 스킬 × 3 파일 + 멀티eval 2 파일 = 8개):**

| 디렉토리 | 파일 |
|----------|------|
| `evals/workflow/zero-script-qa/` | eval.yaml, prompt-1.md, expected-1.md, prompt-2.md, expected-2.md |
| `evals/workflow/cc-version-analysis/` | eval.yaml, prompt-1.md, expected-1.md |

**Capability 신규 (8 스킬 × 3 파일 = 24개):**

| 디렉토리 | 도메인 | 파일 |
|----------|--------|------|
| `evals/capability/phase-1-schema/` | MCU | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-3-mockup/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-4-api/` | Cross | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-5-design-system/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-6-ui-integration/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-7-seo-security/` | Security | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/phase-9-deployment/` | Cross | eval.yaml, prompt-1.md, expected-1.md |
| `evals/capability/desktop-app/` | Desktop | eval.yaml, prompt-1.md, expected-1.md |

### 5.4 총 변경 규모

| 구분 | 파일 수 |
|------|---------|
| 수정 (runner.js, config.json) | 2 |
| 업그레이드 (기존 eval 12 스킬) | 36 |
| 신규 생성 (10 스킬 + 1 멀티eval) | 32 |
| **합계** | **70 파일** |

### 5.5 도메인별 커버리지

| 도메인 | 스킬 수 | 업그레이드 | 신규 |
|--------|---------|-----------|------|
| MCU | 4 | stm32-hal, freertos, nxp-mcuxpresso | phase-1-schema |
| MPU | 3 | imx-bsp, kernel-driver, yocto-build | — |
| Desktop | 5 | wpf-mvvm, xaml-design | phase-3-mockup, phase-5-design-system, phase-6-ui-integration, desktop-app |
| Cross | 4 | cmake-embedded, communication, serial-bridge | phase-4-api, phase-9-deployment |
| Safety/Security | 2 | misra-c | phase-7-seo-security |
| Workflow | 11 | misra-c | zero-script-qa, cc-version-analysis |
| Hybrid | 1 | — | — |

## 6. 구현 순서

| 순서 | 작업 | 의존성 | 파일 수 |
|------|------|--------|---------|
| **Step 1** | runner.js criteria 확장 | 없음 | 1 |
| **Step 2** | config.json 재구성 | 없음 | 1 |
| **Step 3** | 기존 도메인 eval 12개 업그레이드 | Step 1 | 36 |
| **Step 4** | Workflow eval 2개 신규 작성 | Step 1 | 8 |
| **Step 5** | Capability eval 8개 신규 작성 | Step 1 | 24 |
| **Step 6** | 벤치마크 실행 및 전체 검증 | Step 2~5 | 0 |

Step 1, 2는 병렬 실행 가능. Step 3, 4, 5도 독립적이므로 병렬 가능.

## 7. 성공 기준

| 항목 | 기준 |
|------|------|
| 벤치마크 통과율 | 31/31 = 100% |
| Workflow 통과 | 11/11 |
| Capability 통과 | 19/19 |
| Hybrid 통과 | 1/1 |
| prompt 품질 | 모든 파일 >1줄, ≥50자, 도메인 시나리오 포함 |
| expected 품질 | 모든 파일 >1줄, ≥100자, ≥5줄, structured steps |
| criteria 정합성 | 모든 criteria가 runner.js 10개 키워드 카테고리에 매칭 |
| 도메인 적용 | 모든 eval이 MCU/MPU/Desktop 시나리오 반영 |

## 8. 위험 요소 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| runner.js 수정으로 기존 통과 eval 깨짐 | 높음 | Step 1 완료 후 기존 벤치마크 재실행하여 회귀 확인 |
| criteria 키워드 충돌 (여러 카테고리 동시 매칭) | 중간 | if-else 순서에서 구체적 키워드가 먼저 매칭되도록 배치 |
| bkit 공통 eval 디렉토리 잔존 | 낮음 | config에서 제거하면 벤치마크에 미포함, 파일 삭제 불필요 |

## 9. 확장성 설계

### 9.1 Qt 도메인 추가 시 절차

1. `evals/capability/qt-widgets/` 디렉토리 생성 (eval.yaml + prompt + expected)
2. `evals/config.json`의 capability 배열에 `"qt-widgets"` 추가
3. 벤치마크 자동 포함 (runner.js 변경 불필요)

### 9.2 새 도메인 추가 체크리스트

```
□ eval.yaml 작성 (name, classification, criteria)
□ prompt-1.md 작성 (≥50자, 멀티라인, 도메인 시나리오)
□ expected-1.md 작성 (≥100자, ≥5줄, structured steps)
□ criteria 키워드가 runner.js 10개 카테고리에 매칭되는지 확인
□ config.json에 스킬명 추가
□ node evals/runner.js --skill {name} 으로 개별 검증
□ node evals/runner.js --benchmark 로 전체 회귀 확인
```
