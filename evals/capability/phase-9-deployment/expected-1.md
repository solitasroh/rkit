## Step 1: Pre-Deployment Build Verification

1. Verify build artifacts exist and match expected version tag
2. Compute SHA-256 checksum of firmware binary and Linux image
3. Compare checksums against release manifest
4. Verify Flash/RAM usage is within budget (Flash < 85%, RAM < 75%)
5. Tag the release in git with version number

```bash
# MCU build verification
arm-none-eabi-size build/firmware.elf
sha256sum build/firmware.bin > release/firmware.sha256

# MPU image verification
ls -la build/images/core-image-minimal-imx6ull.sdcard
sha256sum build/images/core-image-minimal-imx6ull.sdcard > release/image.sha256
```

Release config checklist:
- [ ] Version string matches git tag
- [ ] Debug symbols stripped from release binary
- [ ] Optimization level set to -O2 (not -O0 debug)
- [ ] Serial console disabled in production image

## Step 2: STM32 Flash Programming

**Option A: OpenOCD setup and flash**
```bash
# OpenOCD config for ST-Link v2
openocd -f interface/stlink-v2.cfg \
        -f target/stm32f4x.cfg \
        -c "program build/firmware.bin verify reset exit 0x08000000"
```

**Option B: st-flash utility**
```bash
# Flash binary to address 0x08000000
st-flash write build/firmware.bin 0x08000000

# Verify flash contents
st-flash read readback.bin 0x08000000 $(stat -c%s build/firmware.bin)
diff build/firmware.bin readback.bin && echo "Flash verified OK"
```

Configuration notes:
- ST-Link v2 must be connected before running flash commands
- Target MCU must be powered and reset line connected
- OpenOCD config file specifies clock speed and flash driver setup

## Step 3: Post-Flash Validation (MCU)

1. Reset the MCU after flashing completes
2. Open serial terminal to verify boot message and version string
3. Send firmware info command (0x03) and verify response matches expected version
4. Run basic sensor read test to confirm peripheral initialization
5. Record validation result in deployment log

```bash
# Serial config for validation
minicom -D /dev/ttyUSB0 -b 115200

# Expected boot output:
# [BOOT] Firmware v2.1.0 (2026-04-03)
# [INIT] Sensor OK, Serial OK
```

## Step 4: i.MX6 SD Card Image Deployment

1. Identify the SD card device (verify correct device to prevent data loss)
2. Write the complete SD card image using dd with progress monitoring
3. Sync and verify the written image

```bash
# Identify SD card device - VERIFY THIS IS CORRECT
lsblk

# Write image to SD card (setup for i.MX6ULL)
sudo dd if=build/images/core-image-minimal-imx6ull.sdcard \
        of=/dev/sdX bs=4M conv=fsync status=progress

# Verify written image
sudo dd if=/dev/sdX bs=4M count=$(stat -c%s build/images/core-image-minimal-imx6ull.sdcard | awk '{print int($1/4194304)+1}') | sha256sum
```

SD card partition config layout:
```
/dev/sdX1  - FAT32  - U-Boot, kernel (zImage), DTB
/dev/sdX2  - ext4   - Root filesystem
```

## Step 5: Post-Deployment Validation (MPU)

1. Insert SD card into i.MX6ULL board and power on
2. Monitor U-Boot console for successful kernel load
3. Verify Linux boots to login prompt within 30 seconds
4. Check kernel version and device tree name match release config
5. Run basic connectivity test (Ethernet ping, I2C sensor detect)

```bash
# On target board via serial console
uname -a
cat /etc/version
i2cdetect -y 0
```

## Step 6: Rollback Plan

**MCU Rollback (< 2 minutes):**
1. Keep previous firmware binary in release/previous/ directory
2. Flash previous version using same OpenOCD/st-flash setup commands
3. Verify rollback with version readback

**MPU Rollback (< 5 minutes):**
1. Keep previous SD card image in release/previous/ directory
2. Re-write SD card with previous image using dd
3. Boot and verify previous version

```bash
# MCU rollback
st-flash write release/previous/firmware.bin 0x08000000

# MPU rollback
sudo dd if=release/previous/core-image-minimal-imx6ull.sdcard \
        of=/dev/sdX bs=4M conv=fsync status=progress
```

## Summary

- Pre-deployment verification ensures build artifacts match release config
- STM32 flash via OpenOCD or st-flash with address 0x08000000
- i.MX6 SD card deployment with dd and partition setup verification
- Post-flash validation confirms firmware version and basic functionality
- Rollback plan enables recovery within 5 minutes for both targets
