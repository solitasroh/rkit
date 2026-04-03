MCU to PC serial communication command protocol design for sensor monitoring system.

## Requirements
- Command codes: 0x01 (read sensor data), 0x02 (set configuration), 0x03 (get firmware info)
- Request/response packet structure with sync bytes, length field, and CRC
- Error code definitions for timeout, invalid command, CRC mismatch, sensor failure
- Timeout policy: 500ms for normal commands, 2000ms for configuration writes

## Context
An STM32F4 MCU communicates with a WPF desktop application via UART at 115200 baud.
The protocol is master-slave where the PC initiates all requests and the MCU responds.
The serial link must handle packet loss and corruption gracefully with retry logic.
Maximum payload size is 256 bytes. All multi-byte fields use little-endian byte order.
