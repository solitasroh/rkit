# Yocto Recipe Patterns Reference

## Basic Recipe (.bb)
```
SUMMARY = "My custom application"
DESCRIPTION = "A simple application for i.MX6"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=abc123..."

SRC_URI = "git://github.com/user/repo.git;branch=main;protocol=https"
SRCREV = "abc123def456..."
S = "${WORKDIR}/git"

inherit cmake
# or: inherit autotools
# or: do_compile() { ${CC} ${CFLAGS} ${LDFLAGS} -o myapp ${S}/main.c }

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/myapp ${D}${bindir}/
}
```

## Recipe Append (.bbappend)
```
# linux-imx_%.bbappend - Add custom DTS
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://my-board.dts"
do_configure:append() {
    cp ${WORKDIR}/my-board.dts ${S}/arch/arm/boot/dts/
}
```

## Layer Structure
```
meta-mylayer/
├── conf/
│   └── layer.conf
├── recipes-bsp/
│   └── u-boot/
│       └── u-boot-imx_%.bbappend
├── recipes-kernel/
│   └── linux/
│       ├── linux-imx_%.bbappend
│       └── files/my-board.dts
└── recipes-app/
    └── myapp/
        ├── myapp_1.0.bb
        └── files/myapp.c
```

## Common Variables
```
IMAGE_INSTALL:append = " myapp mylib"
MACHINE_FEATURES += "wifi bluetooth"
DISTRO_FEATURES:append = " systemd"
PREFERRED_PROVIDER_virtual/kernel = "linux-imx"
```

## NXP Layer Notes
- meta-freescale: Open-source community BSP
- meta-imx: NXP official (includes proprietary GPU/VPU)
- Both needed for full i.MX6 multimedia support
