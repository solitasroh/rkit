---
name: board-debug
classification: capability
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  타겟 보드 디버깅 스킬. SSH 원격 테스트, 시리얼 로그 수집/분석, 디버그 리포트 생성.
  Triggers: 보드 디버깅, 보드 테스트, board debug, boot check, 부팅 확인
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: check
---
# Board Debug

타겟 보드의 부팅 및 기능을 디버깅/검증하고 리포트를 생성한다.

## 전제 조건: 환경변수

### .env 확인 (공통)

스킬 실행 전 프로젝트 루트의 `.env` 파일을 확인한다:

1. `.env` 파일이 있으면 → 정상 진행 (값을 읽어서 사용)
2. `.env` 파일이 없으면:
   - devkit plugin 디렉토리의 `templates/env.template` 파일을 찾는다
   - `env.template`이 있으면 → 프로젝트 루트에 `.env.example`과 `.env`로 복사
   - 사용자에게 안내: "`.env` 파일이 생성되었습니다. 필요한 값을 채워주세요."
   - `env.template`이 없으면 → "devkit plugin이 설치되지 않은 것 같습니다." 안내
3. `.env`에서 이 스킬에 필요한 변수를 읽는다 (빈 값이면 사용자에게 질문)

`.env`에 타겟 보드 접속 정보를 설정한다:

```bash
### 타겟 보드 SSH
BOARD_SSH_HOST=192.168.1.100    # 보드 IP
BOARD_SSH_PORT=22
BOARD_SSH_USER=root
BOARD_SSH_PASSWORD=             # 비어있으면 BOARD_SSH_KEY 사용
BOARD_SSH_KEY=~/.ssh/id_rsa     # 기본 키 경로 (다른 키로 변경 가능)

### 시리얼 디버그 서비스 (serial-debug)
SERIAL_DEBUG_HOST=10.10.23.100  # serial-debug 서비스 호스트
SERIAL_DEBUG_API_PORT=8090      # REST API + Web UI 포트
SERIAL_DEBUG_TCP_PORT=9000      # TCP raw proxy 시작 포트
```

### SSH 인증 우선순위

1. `BOARD_SSH_PASSWORD`가 설정되어 있으면 → 비밀번호 인증
2. 비어있으면 → `BOARD_SSH_KEY` 경로의 SSH 키 인증 (기본 `~/.ssh/id_rsa`)

```bash
# 비밀번호 인증
sshpass -p "${BOARD_SSH_PASSWORD}" ssh -o StrictHostKeyChecking=no \
  -p ${BOARD_SSH_PORT} ${BOARD_SSH_USER}@${BOARD_SSH_HOST} "uname -r"

# 키 인증 (비밀번호 미설정 시)
ssh -i ${BOARD_SSH_KEY} -o StrictHostKeyChecking=no \
  -p ${BOARD_SSH_PORT} ${BOARD_SSH_USER}@${BOARD_SSH_HOST} "uname -r"
```

> STM32MP OpenSTLinux 기본 이미지는 dropbear SSH + debug-tweaks로
> root 비밀번호 없이 접속 가능. 이 경우 비밀번호/키 모두 불필요.

## 시리얼 디버그 서비스 (serial-debug)

별도 호스트에서 실행되는 serial-debug 서비스가 시리얼 포트를 관리한다.
이 스킬은 REST API로 로그를 가져오고, 필요시 명령을 전송한다.

- **REST API / Web UI**: `http://${SERIAL_DEBUG_HOST}:${SERIAL_DEBUG_API_PORT}/`
- **TCP raw proxy**: `${SERIAL_DEBUG_HOST}:${SERIAL_DEBUG_TCP_PORT}` (장치별 9000, 9001, ...)

### REST API 사용법

```bash
SERIAL_API="http://${SERIAL_DEBUG_HOST}:${SERIAL_DEBUG_API_PORT}"

# 장치 목록 조회
curl -s ${SERIAL_API}/api/devices | python3 -m json.tool

# 특정 장치 로그 가져오기 (최근 200줄)
curl -s ${SERIAL_API}/api/devices/{name}/log?lines=200

# 명령 전송 + 응답 대기
curl -s -X POST ${SERIAL_API}/api/devices/{name}/send \
  -H "Content-Type: application/json" \
  -d '{"command": "uname -r\n", "wait_ms": 2000}'

# 로그 파일 목록
curl -s ${SERIAL_API}/api/devices/{name}/logs

# 로그 파일 다운로드
curl -s ${SERIAL_API}/api/logs/{filename} -o boot_log.txt
```

### TCP raw 접속 (양방향 시리얼)

장치 목록 API에서 `tcp_port`를 확인하여 직접 접속 가능:

```bash
# raw 접속 (에코 제거 권장)
stty -echo; nc ${SERIAL_DEBUG_HOST} ${SERIAL_DEBUG_TCP_PORT}; stty echo

# socat
socat -,rawer tcp:${SERIAL_DEBUG_HOST}:${SERIAL_DEBUG_TCP_PORT}
```

### Web UI

`http://${SERIAL_DEBUG_HOST}:${SERIAL_DEBUG_API_PORT}/` 에서 장치별 탭으로 실시간 모니터링 가능.

## 접근 방식

| 방식 | 용도 | 사용 시점 |
|------|------|----------|
| **A. SSH 원격 테스트** | 기능 검증 | Linux 부팅 후, 네트워크 연결됨 |
| **B. serial-debug API** | 부팅 로그, U-Boot | 부팅 실패, U-Boot 디버깅, 전체 로그 |
| **C. 로그 파일 분석** | 오프라인 분석 | 시리얼 로그 파일을 전달받은 경우 |

## 절차

실행 시 메뉴를 표시한다:

```
Board Debug:

1. SSH 원격 테스트     — 네트워크로 보드 접속하여 체크리스트 실행
2. 시리얼 로그 수집    — serial-debug API로 부팅 로그 가져오기
3. 부팅 로그 분석      — 로그 파일/API에서 에러 패턴 검출
4. 개별 테스트         — 항목 선택하여 SSH로 실행
5. 생산 QC             — 최소 체크리스트 (SSH)
```


### 메뉴 1: SSH 원격 테스트 (추천)

보드가 네트워크에 연결되고 SSH 접근 가능한 상태에서 체크리스트를 자동 실행한다.

#### 체크리스트

| # | 항목 | 명령 | 판정 기준 | 필수 |
|---|------|------|-----------|------|
| 1 | Kernel 버전 | `uname -r` | 예상 버전과 일치 | O |
| 2 | Boot 로그 에러 | `dmesg \| grep -i -E "error\|fail\|panic"` | critical 에러 없음 | O |
| 3 | rootfs 마운트 | `mount \| grep "on / "` | ext4, rw | O |
| 4 | 디스크 용량 | `df -h /` | 정상 크기 | O |
| 5 | eMMC/SD 파티션 | `lsblk` | 예상 파티션 구조 | O |
| 6 | 네트워크 인터페이스 | `ip addr show` | eth0/end0 존재 | O |
| 7 | IP 획득 | `ip addr show \| grep "inet "` | IP 할당됨 | O |
| 8 | 드라이버 로드 | `lsmod` | 주요 모듈 로드 확인 | O |
| 9 | USB 장치 | `lsusb` | USB 컨트롤러 인식 | - |
| 10 | WiFi 스캔 | `iw dev wlan0 scan \| grep SSID` | AP 목록 (WiFi 있는 경우) | - |
| 11 | BT 스캔 | `hciconfig` | BT 인터페이스 (BT 있는 경우) | - |
| 12 | 오디오 장치 | `aplay -l` | 사운드카드 인식 | - |
| 13 | 디스플레이 | `cat /sys/class/drm/card*/status` | connected | - |
| 14 | Qt 라이브러리 | `ls /usr/share/qt6/` | Qt 존재 | - |
| 15 | systemd 서비스 | `systemctl --failed` | failed 서비스 없음 | O |
| 16 | 시간 | `timedatectl` | RTC 또는 NTP 동기 | - |
| 17 | 온도 센서 | `cat /sys/class/thermal/thermal_zone*/temp` | 정상 범위 | - |
| 18 | CPU 정보 | `cat /proc/cpuinfo` | 예상 코어 수/모델 | O |

#### 실행 방법

```bash
# SSH 접속 (인증 방식 자동 선택)
if [ -n "${BOARD_SSH_PASSWORD}" ]; then
  SSH_CMD="sshpass -p ${BOARD_SSH_PASSWORD} ssh -o StrictHostKeyChecking=no -p ${BOARD_SSH_PORT} ${BOARD_SSH_USER}@${BOARD_SSH_HOST}"
else
  SSH_CMD="ssh -i ${BOARD_SSH_KEY} -o StrictHostKeyChecking=no -p ${BOARD_SSH_PORT} ${BOARD_SSH_USER}@${BOARD_SSH_HOST}"
fi

# 전체 체크리스트 일괄 실행
${SSH_CMD} bash << 'TESTEOF'
echo "=== Kernel ==="
uname -r
echo "=== Boot Errors ==="
dmesg | grep -i -c -E "error|fail|panic" || echo "0"
echo "=== Rootfs ==="
mount | grep "on / "
echo "=== Disk ==="
df -h /
echo "=== Partitions ==="
lsblk
echo "=== Network ==="
ip addr show
echo "=== Modules ==="
lsmod | head -20
echo "=== systemd ==="
systemctl --failed
echo "=== CPU ==="
cat /proc/cpuinfo | grep -E "processor|model|Hardware"
echo "=== Temperature ==="
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null || echo "N/A"
TESTEOF
```

#### 판정

- **PASS**: 필수(O) 항목 모두 통과
- **WARN**: 비필수 항목 실패 (WiFi, BT, Audio 등 — 보드 구성에 따라)
- **FAIL**: 필수 항목 1개 이상 실패


### 메뉴 3: 부팅 로그 분석

시리얼 로그(API에서 수집, 파일 전달, 또는 붙여넣기)를 분석한다.
`tools/log_analyze.py`를 사용하거나, AI가 직접 Read 도구로 읽고 분석한다.

#### 로그 입력 방법

| 방법 | 명령 |
|------|------|
| 파일 분석 | `python tools/log_analyze.py boot_log.txt` |
| stdin 리다이렉트 | `python tools/log_analyze.py < boot_log.txt` |
| 파이프 | `cat boot_log.txt \| python tools/log_analyze.py` |
| 붙여넣기 (대화형) | `python tools/log_analyze.py --paste` |
| 마크다운 출력 (리포트용) | `python tools/log_analyze.py boot_log.txt --markdown` |
| API에서 직접 | `curl -s ${SERIAL_API}/api/devices/{name}/log?lines=500 \| python tools/log_analyze.py` |

#### 분석 패턴

| 패턴 | 심각도 | 설명 |
| ---- | ------ | ---- |
| `Kernel panic` | CRITICAL | 커널 패닉 |
| `Unable to mount root` | CRITICAL | rootfs 마운트 실패 |
| `Oops`, `BUG:` | CRITICAL | 커널 oops/BUG |
| `probe failed` | HIGH | 드라이버 프로빙 실패 |
| `Error` | HIGH | 드라이버/서브시스템 에러 |
| `failed` | MEDIUM | 서비스/작업 실패 |
| `timeout` | MEDIUM | 하드웨어 응답 없음 |
| `WARNING` | LOW | 커널 경고 |

분석 결과를 정리하여 리포트에 포함한다.

> 부팅 로그 분석은 시리얼 연결 없이도 가능하므로,
> 로그 파일, 붙여넣기, 파이프 등 어떤 방식으로든 분석할 수 있다.


### 메뉴 5: 생산 QC

생산 라인에서 최소한으로 확인할 항목만 SSH로 실행한다:

| # | 항목 | 명령 | 시간 |
|---|------|------|------|
| 1 | SSH 접속 | `ssh root@{IP} "echo ok"` | ~1초 |
| 2 | Kernel 버전 | `uname -r` | 즉시 |
| 3 | eMMC 파티션 | `lsblk \| grep mmcblk` | 즉시 |
| 4 | 네트워크 | `ip link show` | 즉시 |
| 5 | systemd 상태 | `systemctl is-system-running` | 즉시 |

총 QC 시간: **~5초** (보드 부팅 완료 후)

