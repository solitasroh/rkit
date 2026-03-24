---
name: freeze
classification: capability
classification-reason: File protection capability independent of model advancement
deprecation-risk: none
description: |
  Freeze critical files to prevent accidental modification during development.
  Protects linker scripts, Device Tree, kernel headers, project configs, and more.
  Domain-specific presets for MCU, MPU (Kernel/Driver/App), and WPF.

  Triggers: freeze, unfreeze, protect, lock files, 동결, 보호, 파일 잠금,
  凍結, ファイル保護, 冻结, 文件保护, congelar, proteger, geler, protéger,
  einfrieren, schützen, congelare, proteggere

  Do NOT use for: architecture-level locking (use /arch-lock),
  automation level control (use /control), PDCA phase management.
argument-hint: "[freeze|unfreeze|list|preset] [patterns...]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
imports: []
next-skill: null
pdca-phase: do
task-template: "[Freeze] {action}"
---

# Freeze Skill

> Protect critical files from accidental modification during PDCA Do phase.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| (none) | Show freeze status (same as `list`) | `/freeze` |
| `freeze <patterns...>` | Freeze specific file patterns | `/freeze *.ld startup_*.s` |
| `unfreeze <patterns...>` | Unfreeze specific patterns | `/freeze unfreeze *.ld` |
| `unfreeze all` | Unfreeze all patterns | `/freeze unfreeze all` |
| `list` | List all frozen patterns | `/freeze list` |
| `preset <domain>` | Apply domain preset (mcu/mpu/wpf) | `/freeze preset mcu` |
| `preset list` | Show available presets | `/freeze preset list` |

## How It Works

1. Frozen file patterns are stored in `.mcukit/state/freeze-list.json`
2. The `pre-write.js` hook checks every Write/Edit operation against frozen patterns
3. If a file matches a frozen pattern, the operation is **blocked** with explanation
4. Freeze state persists across sessions until explicitly unfrozen

## Domain Presets

### MCU Preset (`/freeze preset mcu`)

| Pattern | Reason |
|---------|--------|
| `*.ld` | Linker scripts — wrong modification causes boot failure |
| `startup_*.s` | Startup assembly — vector table and init sequence |
| `*.ioc` | CubeMX project — regeneration overwrites manual changes |
| `system_*.c` | System init — clock and peripheral base config |
| `stm32*_hal_conf.h` | HAL config — module enable/disable flags |
| `**/Core/Startup/**` | Core startup directory |

### MPU Preset (`/freeze preset mpu`)

| Pattern | Reason |
|---------|--------|
| `*.dts`, `*.dtsi` | Device Tree — affects all drivers and peripherals |
| `**/Kconfig` | Kernel config — build-wide impact |
| `**/Makefile.kernel` | Kernel Makefile — build system |
| `include/linux/*.h` | Kernel public headers — ABI contract |
| `include/dt-bindings/**` | DT bindings — driver-DT interface contract |

### WPF Preset (`/freeze preset wpf`)

| Pattern | Reason |
|---------|--------|
| `App.xaml`, `App.xaml.cs` | Application entry point |
| `*.csproj` | Project configuration — build target, dependencies |
| `AssemblyInfo.cs` | Assembly metadata — versioning |
| `app.manifest` | Application manifest — permissions, DPI |
| `**/Properties/launchSettings.json` | Debug/launch configuration |

## Actions

### freeze

1. Parse patterns from arguments
2. If no patterns provided, use AskUserQuestion to ask:
   - "Which files do you want to freeze?" with options: domain preset, custom patterns
3. Add patterns to freeze list with timestamp and reason
4. Confirm frozen count

### unfreeze

1. If `unfreeze all`: clear entire freeze list with confirmation
2. If specific patterns: remove matching entries
3. Show remaining frozen count

### list

1. Read freeze list from state file
2. Display table: pattern, reason, frozen date, frozen by
3. Show total count and active presets

### preset

1. If `preset list`: show all available presets with patterns
2. If `preset <domain>`: apply domain preset
3. Show what was added vs already frozen

## Integration

### pre-write.js Hook
The freeze check runs in `scripts/pre-write.js` before any Write/Edit operation:
```
if (isFrozen(filePath)) {
  outputBlock(`File "${filePath}" is frozen (${reason}). Use /freeze unfreeze to modify.`);
}
```

### /control status
Freeze status is shown in `/control status` output:
```
🔒 Freeze: Active (6 patterns, preset: mcu)
```

### /guard mode
When `/guard on` is activated, it auto-applies the detected domain preset.

### PDCA Do Phase
Auto-suggested when entering Do phase on MCU/MPU/WPF projects:
"Consider freezing critical files with `/freeze preset <domain>` before implementation."

## Output Example

```
🔒 Freeze Status
─────────────────────────────
Frozen patterns: 6
Active presets: mcu

| # | Pattern            | Reason                    | Frozen     |
|---|--------------------|---------------------------|------------|
| 1 | *.ld               | MCU critical: linker...   | 2026-03-25 |
| 2 | startup_*.s        | MCU critical: linker...   | 2026-03-25 |
| 3 | *.ioc              | MCU critical: linker...   | 2026-03-25 |
| 4 | system_*.c         | MCU critical: linker...   | 2026-03-25 |
| 5 | stm32*_hal_conf.h  | MCU critical: linker...   | 2026-03-25 |
| 6 | **/Core/Startup/** | MCU critical: linker...   | 2026-03-25 |
─────────────────────────────
```
