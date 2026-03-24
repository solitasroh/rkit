---
name: guard
classification: capability
classification-reason: Safety mode orchestration independent of model advancement
deprecation-risk: none
description: |
  Combined safety mode that orchestrates freeze + destructive detection + automation cap.
  When active: freezes domain preset, caps automation at L2, enhances Bash scrutiny.

  Triggers: guard, safety mode, careful mode, 가드, 안전 모드, 조심,
  ガードモード, 安全モード, 慎重, 守卫模式, 安全模式, 谨慎,
  modo guardia, modo seguro, mode garde, mode sécurisé,
  Schutzmodus, Sicherheitsmodus, modalità guardia, modalità sicura

  Do NOT use for: individual file freeze (use /freeze),
  automation level control (use /control), PDCA phase management.
argument-hint: "[on|off|status] [domain]"
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
task-template: "[Guard] {action}"
---

# Guard Skill

> Combined safety mode: freeze preset + automation L2 cap + enhanced Bash scrutiny.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| (none) | Show guard mode status | `/guard` |
| `on [domain]` | Activate guard mode | `/guard on mcu` |
| `off` | Deactivate guard mode | `/guard off` |
| `status` | Show guard mode status | `/guard status` |

## How It Works

Guard mode is a single toggle that activates three safety mechanisms simultaneously:

1. **Freeze Preset** — Auto-applies domain freeze preset (MCU/MPU/WPF)
2. **Automation Cap** — Caps automation level at L2 (Semi-Auto), blocking L3/L4
3. **Enhanced Bash Scrutiny** — Domain-specific destructive operation detection (G-009~G-011)

## Actions

### on [domain]

1. If no domain specified, auto-detect from project files or use AskUserQuestion:
   - "Which domain preset to apply?" Options: mcu, mpu, wpf
2. Save current automation level for later restore
3. Apply domain freeze preset via `freeze-manager.freezePreset(domain)`
4. Cap automation at L2 via `guard-mode.activate(domain, currentLevel)`
5. Confirm activation with summary:
   - Frozen file count
   - Previous automation level → capped level
   - Domain-specific rules active (G-009/G-010/G-011)

### off

1. Verify guard mode is active
2. Unfreeze all guard-applied patterns via `freeze-manager.unfreezeAll()`
3. Restore previous automation level via `guard-mode.deactivate()`
4. Confirm deactivation with summary:
   - Unfrozen file count
   - Restored automation level

### status

1. Read guard mode state from `.mcukit/state/guard-mode.json`
2. Read freeze status from freeze-manager
3. Display formatted status

**Output Format**:
```
--- Guard Mode Status ----------------------------
Active        : Yes
Domain        : mcu
Activated At  : 2026-03-25T10:30:00Z
Reason        : Guard mode activated for mcu domain
---------------------------------------------------
Freeze Status:
  Frozen patterns: 6 (preset: mcu)
  *.ld, startup_*.s, *.ioc, system_*.c, ...

Automation Cap:
  Current: L2 (capped from L3)
  Previous level will restore on /guard off

Domain Rules:
  [ON] G-009: MCU Flash programmer detection
  [ON] G-010: Kernel/device dangerous operation
  [ON] G-011: Certificate/signing operation
---------------------------------------------------
```

## Domain-Specific Rules

### MCU Domain (G-009)
Detects MCU flash programming tools:
- `openocd`, `st-flash`, `STM32_Programmer_CLI`, `JLinkExe`, `pyocd`

### MPU Domain (G-010)
Detects kernel/device dangerous operations:
- `dd if=...of=/dev/`, `insmod`, `rmmod`, `mknod`, `devmem`, `echo > /proc/`

### WPF Domain (G-011)
Detects certificate/signing operations:
- `signtool`, `certutil -add|-delete|-import`, `sn.exe`

## Integration

### /control status
Guard mode status is shown in `/control status` output:
```
Guard Mode: Active (mcu, L2 cap)
```

### /freeze
Guard mode auto-applies domain freeze preset. Manual `/freeze` commands work independently.

### pre-write.js Hook
Frozen files are checked before every Write/Edit operation (via freeze-manager).

### unified-bash-pre.js Hook
Guard mode enables enhanced Bash scrutiny with domain-specific rules (G-009~G-011).

### PDCA Do Phase
Auto-suggested when entering Do phase on MCU/MPU/WPF projects:
"Consider activating guard mode with `/guard on` before implementation."

## State

| File | Purpose |
|------|---------|
| `.mcukit/state/guard-mode.json` | Guard mode state (active, domain, previousLevel) |
| `.mcukit/state/freeze-list.json` | Frozen file patterns (managed by freeze-manager) |

## Module Dependencies

| Module | Function | Usage |
|--------|----------|-------|
| `lib/control/guard-mode.js` | `activate()`, `deactivate()`, `getStatus()` | Guard mode orchestration |
| `lib/control/freeze-manager.js` | `freezePreset()`, `unfreezeAll()` | File protection |
| `lib/control/automation-controller.js` | `getCurrentLevel()`, `setLevel()` | Automation level control |
| `lib/control/destructive-detector.js` | G-009~G-011 rules | Domain-specific detection |

## Usage Examples

```bash
# Activate guard mode for MCU project
/guard on mcu

# Check guard status
/guard status

# Deactivate and restore previous settings
/guard off

# Activate for MPU (kernel/driver) project
/guard on mpu

# Activate for WPF project
/guard on wpf
```
