Linux platform_driver for custom SPI sensor on i.MX6ULL.

## Requirements
- Implement probe and remove functions for device lifecycle
- Create sysfs attribute interface for reading sensor value from userspace
- Module init/exit registration
- Device Tree compatible string matching
- Proper error handling with devm_* managed resources

## Context
The sensor is a custom SPI device connected to ECSPI1 on i.MX6ULL.
It has a simple register-based interface: write register address,
read 2 bytes of data. The driver should expose the last read value
via a sysfs attribute at /sys/bus/spi/devices/.../sensor_value.
Kernel version is 5.15 (Yocto Kirkstone).
