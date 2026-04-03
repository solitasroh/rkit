i.MX6ULL custom board BSP - UART4 + I2C2 sensor Device Tree configuration.

## Requirements
- UART4 node with pinctrl for TX/RX on specific pads
- I2C2 node with BME280 environmental sensor at address 0x76
- Proper pinctrl group definitions with mux and pad settings
- Clock assignment for both peripherals
- Interrupt specifier configuration
- Status enabled for both nodes

## Context
Custom carrier board based on i.MX6ULL EVK. The board connects a BME280
temperature/humidity/pressure sensor on I2C2 (SDA=GPIO1_IO01, SCL=GPIO1_IO00)
and a GPS module on UART4 (TX=UART4_TX_DATA, RX=UART4_RX_DATA).
Base DTS is imx6ull-14x14-evk.dts from NXP BSP. We need a board-level
overlay or include for the custom peripherals.
