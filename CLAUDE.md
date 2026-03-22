# mcukit - AI Native Embedded Development Kit

## Overview
mcukit is a Claude Code plugin for MCU/MPU/WPF development with PDCA methodology.
It auto-detects your project domain and provides domain-specific AI assistance.

## Supported Domains

| Domain | Platforms | Detection |
|--------|-----------|-----------|
| **MCU** | STM32, NXP Kinetis K | `.ioc`, `.ld`, `startup_*.s`, `stm32*.h`, `fsl_*.h` |
| **MPU** | i.MX6, i.MX6ULL, i.MX28 | `.dts`, `.dtsi`, `bblayers.conf`, `*.bb` |
| **WPF** | C#/XAML/.NET 8 | `.csproj` with `<UseWPF>true</UseWPF>` |

## Quick Start

```bash
# Check PDCA status
/pdca status

# Start a new feature
/pdca plan my-feature

# Design → Implement → Verify
/pdca design my-feature
/pdca do my-feature
/pdca analyze my-feature

# Generate report
/pdca report my-feature
```

## Key Commands

| Command | Action |
|---------|--------|
| `/pdca plan {feature}` | Create Plan document |
| `/pdca design {feature}` | Create Design document |
| `/pdca do {feature}` | Implementation guide |
| `/pdca analyze {feature}` | Gap analysis (Check) |
| `/pdca iterate {feature}` | Auto-fix (Act) |
| `/pdca report {feature}` | Completion report |
| `/pdca status` | Show current status |

## Coding Conventions

### MCU (C/Embedded)
- Follow MISRA C:2012 Required rules (zero violations)
- Use HAL/SDK API patterns from skills
- Check memory budget after every build (Flash < 85%, RAM < 75%)

### MPU (Embedded Linux)
- Validate Device Tree with `dtc` before commit
- i.MX28: Use `arm-linux-gnueabi-gcc` (soft float, NO hard float)
- Distinguish `meta-freescale` (open source) from `meta-imx` (NXP official)

### WPF (C#/XAML)
- Use CommunityToolkit.Mvvm (ObservableObject, [ObservableProperty], [RelayCommand])
- NO `{x:Bind}` (UWP/WinUI only, not WPF)
- ViewModel must NOT reference System.Windows.Controls
- .NET 8: `Microsoft.NET.Sdk` + `<UseWPF>true</UseWPF>` + `net8.0-windows`

## Safety Rules
- Flash erase commands require manual confirmation
- `dd if=` to block devices is blocked by default
- Destructive git operations (force push, hard reset) are denied

## Build Commands

### MCU
```bash
mkdir -p build && cd build && cmake .. && cmake --build . -j$(nproc)
```

### MPU (Yocto)
```bash
source oe-init-build-env build
bitbake core-image-minimal
```

### WPF
```bash
dotnet build
dotnet publish -c Release
```
