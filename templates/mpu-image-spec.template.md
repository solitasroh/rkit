# {feature} Image Specification

## 1. Target
| Item | Value |
|------|-------|
| SoC | {soc} |
| Build System | {yocto/buildroot} |
| MACHINE | {machine} |
| Base Image | {base_image} |

## 2. Image Composition
| Component | Size | Format |
|-----------|:----:|--------|
| Rootfs | {size} MB | ext4 / squashfs |
| Kernel | {size} KB | zImage |
| DTB | {size} KB | {board}.dtb |
| U-Boot | {size} KB | u-boot.imx |

## 3. Installed Packages
| Package | Version | Size | Purpose |
|---------|---------|:----:|---------|
| {pkg} | {ver} | {size} | {purpose} |

## 4. Size Limits
| Item | Limit | Current |
|------|:-----:|:-------:|
| Rootfs | {max} MB | {current} MB |
| Kernel | {max} KB | {current} KB |
| Boot Time | {max} s | {current} s |
