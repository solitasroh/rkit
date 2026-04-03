Custom Yocto recipe for an application daemon with systemd integration.

## Requirements
- SRC_URI fetching source from a git repository
- do_compile using CMake build system
- do_install placing binary to /usr/bin
- systemd service unit file for automatic startup
- Proper LICENSE and LIC_FILES_CHKSUM fields

## Context
The application is a sensor data collection daemon written in C.
It uses CMake as its build system and depends on libgpiod and libi2c.
The target image is based on core-image-minimal with systemd as init system.
The git repository is hosted at git://git.example.com/sensor-daemon.git
on branch main with a known SRCREV.
