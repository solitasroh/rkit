## Step 1: Recipe Header and Source Configuration

Define metadata and source location in the recipe file:

```bitbake
SUMMARY = "Sensor data collection daemon"
DESCRIPTION = "Daemon that reads I2C/GPIO sensors and logs data"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=abcdef1234567890abcdef1234567890"

SRC_URI = "git://git.example.com/sensor-daemon.git;branch=main;protocol=https \
           file://sensor-daemon.service \
          "
SRCREV = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
S = "${WORKDIR}/git"
```

## Step 2: Dependencies Setup

```bitbake
DEPENDS = "libgpiod libi2c cmake-native"
RDEPENDS:${PN} = "libgpiod libi2c"
```

## Step 3: CMake Compile Configuration

```bitbake
inherit cmake systemd

EXTRA_OECMAKE = "-DCMAKE_BUILD_TYPE=Release"

do_compile() {
    cmake_do_compile
}
```

## Step 4: Install to Target

```bitbake
do_install() {
    cmake_do_install

    # Install systemd service unit
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/sensor-daemon.service \
        ${D}${systemd_system_unitdir}/sensor-daemon.service
}
```

## Step 5: Systemd Service Integration

The service file (sensor-daemon.service):

```ini
[Unit]
Description=Sensor Data Collection Daemon
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/sensor-daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Recipe config for systemd auto-enable:

```bitbake
SYSTEMD_SERVICE:${PN} = "sensor-daemon.service"
SYSTEMD_AUTO_ENABLE = "enable"
```

## Build and Verification

Expected Result after `bitbake sensor-daemon`:
- Binary installed at `/usr/bin/sensor-daemon`
- Service file at `/lib/systemd/system/sensor-daemon.service`
- Service enabled by default on first boot

Makefile-style build is also possible by replacing `inherit cmake` with
manual do_compile/do_install, but CMake integration is preferred for
proper cross-compilation config handling.
