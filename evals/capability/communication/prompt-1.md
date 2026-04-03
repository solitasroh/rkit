Multi-protocol communication driver (UART + SPI + I2C) with DMA transfer
and interrupt-based receive on STM32F407.

## Requirements
- UART DMA transmit with interrupt completion callback
- SPI DMA full-duplex transfer for high-speed sensor data
- I2C interrupt-based receive for low-speed sensor polling
- Abstraction layer (common interface) for protocol switching at runtime
- Error handling and retry logic for each protocol

## Context
The firmware communicates with three external devices:
1. GPS module via UART2 at 9600 baud (variable-length NMEA sentences)
2. High-speed ADC via SPI1 at 10 MHz (fixed 16-bit samples, continuous)
3. Environmental sensor (BME280) via I2C1 at 400 kHz (register read/write)

A unified communication interface allows the application layer to
read data from any peripheral without knowing the underlying protocol.
All transfers should use DMA where available to minimize CPU load.
