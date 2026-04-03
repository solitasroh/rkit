STM32 I2C sensor register map and UART frame protocol schema definition for a temperature/humidity sensor.

## Requirements
- I2C sensor register map: device address, register addresses, bitfield definitions for temperature and humidity readings
- UART communication frame protocol: header (sync byte, message ID), payload (sensor data), CRC-16 checksum
- Support for both big-endian and little-endian representations
- Data validation rules for sensor value ranges

## Context
The target MCU is an STM32F4 communicating with an SHT30 temperature/humidity sensor via I2C.
Sensor data is then forwarded to a PC application via UART at 115200 baud.
Temperature range is -40 to 125 degrees Celsius, humidity range is 0 to 100% RH.
The protocol must handle multi-byte values with clear endianness specification.
