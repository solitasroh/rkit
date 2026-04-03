STM32F407 UART DMA circular buffer receive driver with HAL callback pattern.

## Requirements
- 1024-byte circular receive buffer
- Use HAL_UARTEx_ReceiveToIdle_DMA for idle line detection
- Implement HAL_UARTEx_RxEventCallback for data processing
- Overflow protection when consumer is slower than producer
- FreeRTOS queue integration to pass received frames to processing task

## Context
The target is an STM32F407VG running at 168 MHz with FreeRTOS.
UART2 is connected to an external sensor module sending variable-length packets
at 115200 baud. Packets arrive every 10-50ms and range from 8 to 256 bytes.
The system must not lose any data even under peak load conditions.
