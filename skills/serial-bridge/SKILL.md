---
name: serial-bridge
classification: capability
deprecation-risk: none
domain: wpf
platforms: [wpf, stm32, nxp-k]
description: |
  MCU↔WPF 시리얼 통신 브릿지 가이드. UART/SerialPort 설정 일관성, 프로토콜 설계.
  Triggers: serial, UART, SerialPort, 시리얼, 통신 브릿지, MCU WPF 연동
user-invocable: true
allowed-tools: [Read, Write, Edit, Glob, Grep]
pdca-phase: do
---

# MCU↔WPF Serial Bridge Guide

## MCU Side (STM32 HAL)
```c
huart1.Init.BaudRate = 115200;
huart1.Init.WordLength = UART_WORDLENGTH_8B;
huart1.Init.StopBits = UART_STOPBITS_1;
huart1.Init.Parity = UART_PARITY_NONE;
huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
```

## WPF Side (System.IO.Ports)
```csharp
// NuGet: System.IO.Ports (required in .NET 8, built-in in .NET Framework)
var port = new SerialPort("COM3", 115200, Parity.None, 8, StopBits.One);
port.DataReceived += (s, e) => {
    var data = port.ReadExisting();
    Dispatcher.Invoke(() => ReceivedText += data);
};
port.Open();
```

## Parameter Matching Checklist
| Parameter | MCU Value | WPF Value | Must Match |
|-----------|----------|-----------|:----------:|
| Baud Rate | 115200 | 115200 | Yes |
| Data Bits | WORDLENGTH_8B | 8 | Yes |
| Parity | PARITY_NONE | Parity.None | Yes |
| Stop Bits | STOPBITS_1 | StopBits.One | Yes |
| Flow Control | HWCONTROL_NONE | Handshake.None | Yes |

## Protocol Design Tips
- Define frame structure: [START][LENGTH][DATA...][CRC][END]
- Use CRC-8 or CRC-16 for error detection
- Implement timeout on both sides
- MCU: Use DMA circular receive for continuous data
- WPF: Use DataReceived event, marshal to UI thread with Dispatcher.Invoke
