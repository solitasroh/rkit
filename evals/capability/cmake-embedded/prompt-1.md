CMake embedded build system for ARM Cortex-M4 (STM32F407).

## Requirements
- arm-none-eabi toolchain file for cross-compilation
- Linker script integration for STM32F407VG (512KB Flash, 192KB SRAM)
- Startup assembly file inclusion (startup_stm32f407xx.s)
- Debug and Release build configurations with appropriate optimization
- Post-build commands for .bin/.hex generation and size reporting

## Context
Building a bare-metal firmware project for STM32F407VG Discovery board.
The project has HAL sources in Drivers/STM32F4xx_HAL_Driver/,
CMSIS headers in Drivers/CMSIS/, application code in Src/, and headers in Inc/.
The linker script is STM32F407VGTx_FLASH.ld in the project root.
Need to support both Debug (-Og) and Release (-Os) builds with
different preprocessor definitions.
