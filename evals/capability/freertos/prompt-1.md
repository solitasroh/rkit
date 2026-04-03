FreeRTOS sensor read task + communication task connected by Queue on STM32F407.

## Requirements
- Sensor task: reads I2C temperature sensor every 100ms, sends data via Queue
- Communication task: receives from Queue, formats and sends over UART
- Priority design: sensor task higher priority than communication task
- Stack sizing: appropriate for each task's memory needs
- Deadlock prevention: timeout on all blocking calls
- Watchdog integration: both tasks must kick IWDG within their loops

## Context
Running on STM32F407 with 192KB SRAM. The application has 4 other tasks
already consuming ~40KB. Available heap for these two new tasks is ~20KB.
The I2C read takes up to 5ms, and UART transmission can block for up to 50ms.
