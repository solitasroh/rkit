MCU firmware OTA update security review for an STM32-based IoT device.

## Requirements
- ECDSA signature verification of firmware images before flashing
- Encrypted transport channel for firmware download (TLS 1.3 or AES-256-GCM)
- Rollback protection using monotonic version counter in OTP fuse
- Version downgrade prevention with anti-rollback counter
- Secure boot chain from ROM bootloader to application firmware

## Context
The target device is an STM32H7 with dual-bank flash, enabling background firmware download.
Firmware images are distributed from a cloud server to devices in the field via MQTT/TLS.
The device stores a signing public key in read-only flash. Private key is held by the build server.
Threat model includes: man-in-the-middle attacks, firmware tampering, replay attacks with old versions,
and physical access to JTAG/SWD debug ports.
