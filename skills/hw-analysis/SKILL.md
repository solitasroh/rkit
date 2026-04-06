---
name: hw-analysis
classification: capability
deprecation-risk: low
domain: mpu
platforms: [stm32mp]
description: |
  하드웨어 회로도/데이터시트 분석 → DTS/defconfig/드라이버 매핑 스킬.
  Mermaid 다이어그램을 적극 활용하여 하드웨어 블록과 핀 매핑을 시각화한다.
  Triggers: 회로도 분석, 핀맵, DTS 생성, schematic, datasheet, hw analysis
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
imports:
  - ${PLUGIN_ROOT}/skills/mermaid/SKILL.md
pdca-phase: do
---
# Hardware Analysis

회로도 PDF + SoC 데이터시트를 분석하여 Yocto BSP 산출물(DTS, defconfig, 드라이버 bbappend)을 생성한다.

## 전제 조건

### .env 확인 (공통)

스킬 실행 전 프로젝트 루트의 `.env` 파일을 확인한다:

1. `.env` 파일이 있으면 → 정상 진행 (값을 읽어서 사용)
2. `.env` 파일이 없으면:
   - devkit plugin 디렉토리의 `templates/env.template` 파일을 찾는다
   - `env.template`이 있으면 → 프로젝트 루트에 `.env.example`과 `.env`로 복사
   - 사용자에게 안내: "`.env` 파일이 생성되었습니다. 필요한 값을 채워주세요."
   - `env.template`이 없으면 → "devkit plugin이 설치되지 않은 것 같습니다." 안내
3. `.env`에서 이 스킬에 필요한 변수를 읽는다 (빈 값이면 사용자에게 질문)

- `docs/hardware/` 에 회로도 PDF와 SoC 데이터시트가 있어야 한다
- yocto-setup 스킬로 환경이 구성되어 있어야 한다
- `.env` 파일에 Yocto 환경변수가 설정되어 있어야 한다

## 입력 파일 규칙

```
docs/hardware/
  schematic/          ← 보드 회로도 PDF
    {board-name}.pdf
  datasheet/          ← SoC/IC 데이터시트 PDF
    {soc-name}.pdf
    {ic-name}.pdf     ← 외부 IC (PMIC, codec, sensor 등)
  pinmap/             ← (산출물) 핀맵 분석 결과
    {board-name}-pinmap.md
  README.md           ← 문서 버전, 보드 리비전 정보
```

## 연계 스킬

- `yocto-bsp` — DTS overlay 생성, defconfig fragment, 소스 fork
- `yocto-recipe` — bbappend 생성, 외부 드라이버 recipe

## 절차

실행 시 메뉴를 표시한다:

```
Hardware Analysis:

1. 전체 분석        — 회로도 + 데이터시트 → 핀맵 → DTS → defconfig → 드라이버
2. 회로도 분석      — 회로도에서 SoC 핀 연결, 외부 IC, 전원 트리 추출
3. 핀맵 생성        — SoC 핀 기능별 매핑 테이블 생성
4. DTS 생성/수정    — 핀맵 기반 device tree 생성
5. defconfig 생성   — 필요 드라이버/서브시스템 활성화 cfg fragment
6. 드라이버 매핑    — 외부 IC별 커널 드라이버 식별 + bbappend 생성
7. 차이 분석        — 레퍼런스 보드 vs 커스텀 보드 HW 차이점
```


### 메뉴 2: 회로도 분석

**목표**: 회로도 PDF에서 SoC 연결 정보를 추출한다.

**Step 1: 회로도 PDF 읽기**

```
docs/hardware/schematic/{board-name}.pdf 를 Read 도구로 읽는다.
대형 PDF는 섹션별로 나누어 읽는다 (pages 파라미터 사용).
```

**Step 2: 페이지별 분석**

회로도는 보통 다음 구조로 구성된다:

| 페이지 유형 | 추출 대상 |
|-------------|-----------|
| 블록 다이어그램 | 전체 구조, 버스 연결 |
| SoC 핀아웃 | GPIO/AF 매핑, 핀 번호 |
| 전원 | PMIC, LDO, 전원 시퀀스 |
| DDR | 메모리 타입, 용량, 버스폭 |
| eMMC/SD | 인터페이스, 버스폭, 전압 |
| USB | USB2/3, OTG, VBUS 제어 |
| Ethernet | PHY 모델, RMII/RGMII, MDIO |
| Display | DSI/LVDS/HDMI, 해상도, 백라이트 |
| Audio | Codec, I2S/TDM, 앰프 |
| Camera | CSI, I2C 주소 |
| Debug | UART, JTAG/SWD |
| Wireless | WiFi/BT 모듈, SDIO/UART |
| Sensor | I2C/SPI 센서, 인터럽트 핀 |
| Connector | 확장 커넥터 핀아웃 |

**Step 3: 분석 결과 문서화**

`docs/hardware/pinmap/{board-name}-schematic-analysis.md` 에 저장:

```markdown
# Schematic Analysis: {board-name}

## Board Info
- Board: {이름}
- Revision: {리비전}
- SoC: {SoC 모델}

## Block Diagram Summary
(블록 다이어그램 기반 전체 연결 요약)

## SoC Peripherals Used

| Peripheral | Interface | External IC | Connection | Notes |
|------------|-----------|-------------|------------|-------|
| SDMMC1 | 8-bit | eMMC | direct | boot device |
| SDMMC2 | 4-bit | SD card | direct | removable |
| I2C1 | I2C | PMIC (STPMIC25) | addr 0x33 | |
| USART2 | UART | Debug console | ST-Link | 115200 |
| ETH1 | RGMII | RTL8211F | MDIO addr 0 | |
| ... | ... | ... | ... | ... |

## Power Tree
(PMIC 출력 → 각 레일 → 소비자)

## External ICs

| IC | Part Number | Interface | I2C Addr | IRQ Pin | Driver |
|----|-------------|-----------|----------|---------|--------|
| PMIC | STPMIC25 | I2C1 | 0x33 | PA0 | stpmic1 |
| ETH PHY | RTL8211F | RGMII+MDIO | 0 | PC3 | r8169 |
| ... | ... | ... | ... | ... | ... |
```


### 메뉴 4: DTS 생성/수정

**목표**: 핀맵을 기반으로 device tree source를 생성한다.

**Step 1: 레퍼런스 DTS 확인**

```bash
# STM32MP21 레퍼런스 DTS
find $YOCTO_WORK_DIR/sources/ -name "stm32mp215f-dk*.dts*" -type f
find $YOCTO_WORK_DIR/sources/ -name "stm32mp21*.dtsi" -type f
```

레퍼런스 DTS를 Read 도구로 읽고 구조를 파악한다.

**Step 2: 차이점 식별**

메뉴 7(차이 분석) 결과 또는 핀맵을 기반으로 레퍼런스 대비 변경이 필요한 노드를 식별:

| 변경 유형 | 예시 |
|-----------|------|
| pinctrl 변경 | 핀 AF 변경, 풀업/다운 설정 |
| 노드 활성화 | `status = "okay"` |
| 노드 비활성화 | `status = "disabled"` |
| 속성 변경 | clock-frequency, reg 주소 |
| 노드 추가 | 새 외부 IC (센서, codec 등) |
| 노드 삭제 | 미사용 peripheral |

**Step 3: DTS overlay 또는 수정 방식 결정**

```
DTS 수정 방식:

a. DTS overlay (.dtso) — 레퍼런스 DTS 유지 + 차이만 overlay (권장)
b. 새 DTS 파일 — 레퍼런스 복사 후 수정 (대규모 변경 시)
c. 기존 DTS 직접 수정 — 소스 fork 필요
```

**Step 4a: DTS overlay 생성**

`sources/meta-{PROJECT_NAME}/recipes-kernel/linux/files/{board-name}-overlay.dtso`:

```dts
/dts-v1/;
/plugin/;

/* Custom board overlay for {board-name} */

&i2c1 {
    status = "okay";
    clock-frequency = <400000>;

    pmic@33 {
        compatible = "st,stpmic1";
        reg = <0x33>;
        interrupts-extended = <&exti 0 IRQ_TYPE_LEVEL_LOW>;
        /* ... */
    };
};

&sdmmc1 {
    status = "okay";
    /* eMMC configuration */
    bus-width = <8>;
    non-removable;
    /* ... */
};
```

> DTS 작성 시 **반드시 데이터시트의 레지스터 주소, 인터럽트 번호, 클럭 정보를 참조**한다.
> 추측으로 작성하지 않는다.

**Step 4b: 새 DTS 파일 생성**

레퍼런스 DTS를 복사하여 새 파일 생성. yocto-bsp 스킬의 DTS 수정 절차를 따른다.

**Step 5: 산출물 기록**

`docs/hardware/pinmap/{board-name}-dts-changes.md`:

```markdown
# DTS Changes: {board-name}

## Base DTS
- Reference: stm32mp215f-dk.dts
- Method: overlay / new file / fork

## Changes

| Node | Change | Property | Value | Reason |
|------|--------|----------|-------|--------|
| &i2c1 | enable | status | "okay" | PMIC connected |
| &sdmmc1 | modify | bus-width | <8> | eMMC 8-bit |
| &usart2 | enable | status | "okay" | Debug console |
| ... | ... | ... | ... | ... |
```


### 메뉴 6: 드라이버 매핑

**목표**: 외부 IC별 커널 드라이버를 식별하고 bbappend를 준비한다.

**Step 1: 외부 IC 목록 확인**

메뉴 2(회로도 분석)에서 추출한 외부 IC 목록을 사용한다.

**Step 2: 드라이버 식별**

각 IC에 대해:

1. **커널 내장 드라이버**: `compatible` 문자열로 커널 소스 검색
   ```bash
   grep -r "\"realtek,rtl8211f\"" $YOCTO_WORK_DIR/sources/*/linux-*/drivers/
   ```

2. **외부 드라이버**: 벤더 제공 또는 커뮤니티 드라이버
   - 벤더 SDK에 포함된 드라이버
   - GitHub/GitLab의 out-of-tree 드라이버

3. **드라이버 없음**: 신규 개발 필요

**Step 3: 드라이버 매핑 테이블**

`docs/hardware/pinmap/{board-name}-driver-map.md`:

```markdown
# Driver Map: {board-name}

## Driver Summary

| IC | Part | Interface | Kernel Driver | Config Symbol | Status |
|----|------|-----------|---------------|---------------|--------|
| PMIC | STPMIC25 | I2C | stpmic1 | CONFIG_MFD_STPMIC1 | in-tree |
| ETH PHY | RTL8211F | MDIO | realtek | CONFIG_REALTEK_PHY | in-tree |
| WiFi | CYW43455 | SDIO | brcmfmac | CONFIG_BRCMFMAC | in-tree + FW |
| Audio | WM8960 | I2S+I2C | wm8960 | CONFIG_SND_SOC_WM8960 | in-tree |
| Sensor | BME280 | I2C | bme280 | CONFIG_BME280 | in-tree |
| Touch | FT5x06 | I2C | edt-ft5x06 | CONFIG_TOUCHSCREEN_EDT_FT5X06 | in-tree |
| Display | ILI9881C | DSI | panel-ilitek | CONFIG_DRM_PANEL_ILITEK_ILI9881C | in-tree |
| Custom IC | XYZ | SPI | (none) | - | need dev |

## Firmware Requirements

| Driver | Firmware File | Package |
|--------|--------------|---------|
| brcmfmac | brcmfmac43455-sdio.bin | linux-firmware |
| ... | ... | ... |

## Out-of-tree Drivers

외부 드라이버가 필요한 경우, yocto-recipe 스킬로 recipe를 생성한다:

| IC | Source | License | Notes |
|----|--------|---------|-------|
| Custom IC | https://... | GPLv2 | vendor SDK |
```

**Step 4: 필요 시 bbappend/recipe 생성**

- in-tree 드라이버: defconfig fragment로 활성화 (메뉴 5)
- firmware 필요: linux-firmware bbappend 또는 custom firmware recipe
- out-of-tree: yocto-recipe 스킬로 kernel module recipe 생성


## 산출물 요약

전체 분석(메뉴 1) 완료 시 생성되는 파일:

```
docs/hardware/
  pinmap/
    {board-name}-schematic-analysis.md    ← 회로도 분석 결과
    {board-name}-pinmap.md                ← SoC 핀맵 테이블
    {board-name}-dts-changes.md           ← DTS 변경 목록
    {board-name}-driver-map.md            ← 드라이버 매핑
    {board-name}-hw-diff.md               ← 레퍼런스 대비 차이

sources/meta-{PROJECT_NAME}/
  recipes-kernel/linux/files/
    {board-name}-overlay.dtso             ← DTS overlay (필요 시)
    {board-name}.cfg                      ← defconfig fragment
  recipes-kernel/linux/
    linux-stm32mp_%.bbappend              ← kernel bbappend
```

## 주의사항

- PDF에서 핀 번호/AF 값을 읽을 때 OCR 오류가 있을 수 있다. **반드시 데이터시트와 교차 검증**한다.
- DTS `reg` 주소, 인터럽트 번호는 **데이터시트 원문 확인** 없이 추측하지 않는다.
- SoC의 pinctrl은 벤더마다 DTS 표현이 다르다:
  - ST: `&pinctrl { ... pin-function = <STM32_PINMUX(...)>; }`
  - NXP: `&iomuxc { ... fsl,pins = <MX8MM_IOMUXC_...>; }`
- 외부 IC의 `compatible` 문자열은 커널 소스의 `of_device_id` 테이블에서 정확히 확인한다.
- DTS overlay는 커널 5.x+ 에서만 지원. 이전 버전은 새 DTS 파일을 생성해야 한다.
- 회로도가 여러 리비전일 경우 `docs/hardware/README.md`에 사용 중인 리비전을 기록한다.
