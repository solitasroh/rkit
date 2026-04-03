STM32 flash programming and i.MX6 SD card image deployment procedure.

## Requirements
- STM32 flash via ST-Link using OpenOCD and st-flash CLI tools
- i.MX6 SD card image deployment with partition layout and U-Boot configuration
- Pre-deployment release checklist (build verification, version tagging, checksum)
- Post-flash validation procedure (connection test, version readback, functional check)
- Rollback plan for both MCU and MPU targets

## Context
The deployment covers two targets in a single product:
1. STM32F4 MCU: firmware binary (.bin) flashed via ST-Link v2 debugger
2. i.MX6ULL MPU: Linux image (kernel + rootfs) deployed to SD card
Both targets must be version-tagged and verified before shipping.
The deployment is performed by a production engineer using CLI tools on an Ubuntu workstation.
Rollback must be possible within 5 minutes if post-flash validation fails.
