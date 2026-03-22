---
name: kernel-driver
classification: capability
deprecation-risk: low
domain: mpu
description: |
  리눅스 커널 모듈/드라이버 개발 가이드. platform_driver, DT 바인딩, sysfs, ioctl.
  Triggers: kernel module, driver, platform_driver, sysfs, ioctl, 커널 모듈, カーネル
user-invocable: true
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
pdca-phase: do
---

# Linux Kernel Driver Guide

## Module Skeleton
```c
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/io.h>

struct mydrv_data { void __iomem *base; int irq; };

static int mydrv_probe(struct platform_device *pdev) {
    struct mydrv_data *priv;
    struct resource *res;
    priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    priv->base = devm_ioremap_resource(&pdev->dev, res);
    priv->irq = platform_get_irq(pdev, 0);
    platform_set_drvdata(pdev, priv);
    return 0;
}
```

## DT Binding
```dts
mydevice@21e8000 {
    compatible = "vendor,mydevice";
    reg = <0x021e8000 0x4000>;
    interrupts = <GIC_SPI 27 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6QDL_CLK_UART_IPG>;
    status = "okay";
};
```

## Makefile (out-of-tree)
```makefile
obj-m := mydrv.o
KDIR ?= /lib/modules/$(shell uname -r)/build
all: $(MAKE) -C $(KDIR) M=$(PWD) modules
clean: $(MAKE) -C $(KDIR) M=$(PWD) clean
```

## Key APIs
- `devm_*` managed resources (auto-cleanup on remove)
- `platform_get_resource()` for MMIO regions
- `devm_request_irq()` for interrupt handlers
- `sysfs_create_group()` for user-space interface
