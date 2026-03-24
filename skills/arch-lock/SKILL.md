---
name: arch-lock
classification: capability
classification-reason: Architecture boundary enforcement independent of model advancement
deprecation-risk: none
description: |
  Lock architecture decisions from Design documents to prevent scope creep during Do phase.
  Auto-generates Mermaid diagrams for MCU memory maps, MPU software stacks, WPF MVVM structures.

  Triggers: arch-lock, architecture lock, lock design, 아키텍처 락, 설계 잠금,
  アーキテクチャロック, 設計ロック, 架构锁定, 设计锁定,
  bloqueo de arquitectura, verrouillage d'architecture,
  Architektursperre, blocco dell'architettura

  Do NOT use for: file-level freeze (use /freeze), automation control (use /control).
argument-hint: "[lock|unlock|status|diagram] [feature]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
imports:
  - arch-lock.template.md
next-skill: null
pdca-phase: design
task-template: "[Arch-Lock] {action}"
---

# Arch-Lock Skill

> Lock architecture decisions from Design documents. Prevents scope creep during Do phase.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| (none) | Show arch-lock status | `/arch-lock` |
| `lock {feature}` | Lock architecture from Design doc | `/arch-lock lock uart-dma` |
| `unlock {id}` | Unlock specific decision | `/arch-lock unlock AD-001` |
| `unlock all` | Unlock all decisions | `/arch-lock unlock all` |
| `status` | Show locked decisions | `/arch-lock status` |
| `diagram {feature}` | Generate architecture diagram | `/arch-lock diagram uart-dma` |

## How It Works

1. Reads the Design document (`docs/02-design/features/{feature}.design.md`)
2. Extracts architecture decisions (layers, interfaces, memory, patterns, dependencies)
3. Locks decisions in `.mcukit/state/arch-lock.json`
4. Generates Mermaid diagrams based on domain
5. Pre-write hook checks modifications against locked boundaries

## Actions

### lock {feature}

1. Read Design document for the feature
2. Auto-detect domain (MCU/MPU/WPF) from project context
3. Extract architecture decisions from Design document sections:
   - Software layer structure
   - Interface definitions
   - Memory/resource allocation
   - Design patterns chosen
   - Dependency directions
4. Present extracted decisions for confirmation via AskUserQuestion
5. Lock decisions in state file
6. Generate domain-specific Mermaid diagram
7. Write lock document to `docs/02-design/features/{feature}.arch-lock.md`

### unlock

- `unlock {id}`: Remove specific decision by ID (e.g., `AD-001`)
- `unlock all`: Remove all locked decisions, disable arch-lock

### status

Display all locked decisions with categories and affected paths.

```
--- Architecture Lock Status ----------------------
Active    : Yes
Feature   : uart-dma
Domain    : mcu
Decisions : 4 locked

| ID     | Category  | Title                      |
|--------|-----------|----------------------------|
| AD-001 | layer     | Software Layer Structure   |
| AD-002 | memory    | Memory Map                 |
| AD-003 | interface | Interrupt Priority Map     |
| AD-004 | interface | Peripheral Allocation      |
---------------------------------------------------
```

### diagram {feature}

Generate domain-specific Mermaid architecture diagram.

**MCU Diagrams**:
- Memory Map (Flash/RAM sections)
- Peripheral allocation table
- Interrupt priority map
- Software layer diagram (Application → Driver → HAL)

**MPU Diagrams**:
- Software stack (Kernel → Driver → Library → App)
- DT node tree structure
- IPC/interface structure (ioctl/sysfs/socket)

**WPF Diagrams**:
- MVVM structure (View ↔ ViewModel ↔ Model)
- DI container graph
- Navigation map

## Domain Templates

### MCU
| Decision | Description |
|----------|-------------|
| Software Layer Structure | Application → Driver → HAL. No direct register access from app. |
| Memory Map | Flash/RAM allocation per linker script |
| Interrupt Priority Map | ISR priorities locked |
| Peripheral Allocation | Peripheral-to-function mapping |

### MPU (Kernel/Driver/App)
| Decision | Description |
|----------|-------------|
| Software Stack | Kernel → Driver → Library → App. Clear user/kernel boundary. |
| Driver Interface | ioctl/sysfs/netlink per driver |
| DT Node Structure | Device Tree hierarchy and bindings |
| IPC Architecture | Inter-process communication method |

### WPF
| Decision | Description |
|----------|-------------|
| MVVM Structure | View → ViewModel → Model. ViewModel must not reference View. |
| DI Container | Service registration and lifetimes |
| Navigation Pattern | Page/Window navigation strategy |
| Communication Architecture | Serial/network layer isolation |

## Integration

### pre-write.js Hook
When arch-lock is active, Write/Edit operations to affected paths show a warning:
```
Architecture decision AD-001 (Software Layer Structure) applies to this file.
Ensure changes comply with locked architecture. Use /arch-lock unlock AD-001 to modify.
```

### /guard mode
Guard mode activates arch-lock boundary enforcement alongside freeze and L2 cap.

### PDCA Design Phase
Auto-suggested after Design document creation:
"Consider locking architecture decisions with `/arch-lock lock {feature}`."

## State

| File | Purpose |
|------|---------|
| `.mcukit/state/arch-lock.json` | Locked decisions state |
| `docs/02-design/features/{feature}.arch-lock.md` | Lock document with diagrams |

## Usage Examples

```bash
# Lock architecture after design
/arch-lock lock uart-dma

# Check what's locked
/arch-lock status

# Generate diagram
/arch-lock diagram uart-dma

# Unlock specific decision
/arch-lock unlock AD-002

# Unlock everything
/arch-lock unlock all
```
