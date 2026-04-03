MCU-to-WPF serial communication bridge with packet framing and error detection.

## Requirements
- Packet framing with STX (0x02) / ETX (0x03) delimiters
- CRC16-CCITT validation for data integrity
- Command/response protocol with command ID and sequence number
- Retransmission on timeout (500ms, max 3 retries)
- Both MCU-side (C) and WPF-side (C#) implementation

## Context
An STM32F407 MCU sends sensor data to a WPF desktop application over UART
at 115200 baud, 8N1. The protocol supports bidirectional communication:
- MCU sends periodic sensor data reports (temperature, humidity, status)
- WPF sends configuration commands (sampling rate, threshold settings)
- Each packet has a sequence number for matching request to response
- Lost or corrupted packets must be detected and retransmitted
