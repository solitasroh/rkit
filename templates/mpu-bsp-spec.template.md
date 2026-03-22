# {feature} BSP Specification

## 1. Target SoC
| Item | Value |
|------|-------|
| SoC | {soc_name} |
| Core | {core_type} |
| DDR | {ddr_size} |
| Boot Media | {boot_media} |

## 2. Device Tree Files
| File | Purpose |
|------|---------|
| {soc}.dtsi | SoC-level definitions |
| {board}.dts | Board-level customization |

## 3. Kernel Configuration
| CONFIG | Value | Purpose |
|--------|:-----:|---------|
| {config} | {y/m/n} | {purpose} |

## 4. Boot Sequence
1. Boot ROM → {bootloader}
2. {bootloader} → Kernel (zImage + DTB)
3. Kernel → rootfs mount
4. init → services

## 5. Build System
| Item | Value |
|------|-------|
| Build | {yocto/buildroot} |
| MACHINE | {machine_name} |
| Image | {image_name} |
