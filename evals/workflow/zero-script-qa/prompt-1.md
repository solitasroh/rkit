# Zero Script QA: STM32 UART Communication Firmware Testing

My intent is to trigger a Zero Script QA session for our STM32 UART communication module.
The keyword for this test cycle is "uart-bridge-validation".

## Test Target
- STM32F407 UART TX/RX communication over a USB-to-serial bridge
- Firmware handles bidirectional data transfer at 115200 baud, 8N1
- TX sends structured JSON packets, RX validates CRC-16 checksums

## Docker Environment
- `docker-compose.yml` with services: `serial-bridge`, `log-collector`, `test-runner`
- Serial bridge container exposes `/dev/ttyUSB0` mapped to the STM32 board
- Log collector aggregates all structured JSON logs to stdout

## Expected Log Patterns
- TX success: `{"event":"tx_complete","bytes":64,"crc":"0xABCD"}`
- RX success: `{"event":"rx_complete","bytes":64,"crc_valid":true}`
- Error case: `{"event":"rx_error","type":"timeout","elapsed_ms":500}`

Please run the full Zero Script QA process using Docker log analysis to verify this UART module.
