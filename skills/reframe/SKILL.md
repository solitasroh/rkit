---
name: reframe
classification: workflow
classification-reason: Structured methodology for problem validation before PDCA planning
deprecation-risk: none
description: |
  Embedded Challenge Protocol — 5-phase 21-question systematic problem validation
  before PDCA planning. Combines 6 validated frameworks: Wedell-Wedellsborg reframing,
  Garry Tan demand reality, Gary Klein pre-mortem, David Bland assumption mapping,
  Toyota Five Whys, McKinsey MECE.

  Triggers: reframe, challenge, office hours, problem validation, 리프레이밍, 문제 검증,
  リフレーミング, 問題検証, 问题验证, reencuadre, recadrage, Neuformulierung, riformulazione

  Do NOT use for: implementation tasks, code review, PDCA phase execution.
  Use this BEFORE /pdca plan for complex features.
argument-hint: "[feature] [--mode full|standard|quick]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
imports:
  - reframe.template.md
next-skill: pdca plan
pdca-phase: null
task-template: "[Reframe] {feature}"
---

# Reframe Skill — Embedded Challenge Protocol

> 5-phase 21-question problem validation. Run BEFORE `/pdca plan` for complex features.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `{feature}` | Feature name to reframe | `/reframe uart-dma` |
| `{feature} --mode full` | Full mode: all 21 questions | `/reframe uart-dma --mode full` |
| `{feature} --mode standard` | Standard mode: Q1-Q15 (default) | `/reframe uart-dma --mode standard` |
| `{feature} --mode quick` | Quick mode: 7 core questions | `/reframe uart-dma --mode quick` |

## Mode Selection

| Mode | Questions | When to Use |
|------|-----------|-------------|
| **Full** (21) | Q1-Q21 | New features, architecture changes, high-risk work |
| **Standard** (15) | Q1-Q15 | Medium-scale tasks, code quality covered in review |
| **Quick** (7) | Q1,Q3,Q5,Q7,Q11,Q13,Q18 | Bug fixes, small improvements |

## Methodology

Six validated frameworks integrated into 5 phases:

| Framework | Source | Phase |
|-----------|--------|-------|
| Problem Reframing | Wedell-Wedellsborg (HBR 2017) | Phase 1 |
| Demand Reality + Narrowest Wedge | Garry Tan (gstack /office-hours) | Phase 1, 3 |
| Pre-Mortem | Gary Klein (HBR 2007) | Phase 2 |
| Assumption Mapping | David Bland (Strategyzer) | Phase 2 |
| Five Whys | Toyota Production System | Phase 3 |
| MECE Decomposition | McKinsey | Phase 3 |

## Execution Flow

### Step 1: Mode Selection

If `--mode` not specified, use AskUserQuestion:
> "Which reframe mode? Feature complexity determines depth."
> - Full (21 questions) — new features, architecture changes
> - Standard (15 questions) — medium tasks (default)
> - Quick (7 questions) — bug fixes, small improvements

### Step 2: Domain Detection

Auto-detect project domain (MCU/MPU/WPF) from project files.
Domain determines reframing guides, MECE checklists, and assumption examples.

### Step 3: Interactive Questions

Execute questions sequentially using AskUserQuestion for each.
Provide domain-specific hints and examples with each question.

#### Phase 1: Problem Validation (Q1-Q4)

Questions probe problem definition, demand reality, status quo cost, and alternative framing.

**Q4 Domain-Specific Reframing Guide**:

| Instead of asking... | Reframe to... |
|---------------------|---------------|
| MCU: "How to make this ISR faster?" | "Should this work be in the ISR at all, or deferred?" |
| MCU: "How to fit in Flash?" | "What are we storing that's actually unnecessary?" |
| MPU: "How to add ioctl?" | "Is sysfs/configfs sufficient? Why is ioctl really needed?" |
| MPU: "Why does probe fail?" | "Does DT compatible string match? Are dependencies (clk, gpio, regulator) ready?" |
| WPF: "How to make WPF UI responsive?" | "Should this processing be in ViewModel or a background service?" |
| WPF: "Why is DataGrid slow?" | "Is virtualization enabled? Are 10,000 rows really needed?" |

#### Phase 2: Assumption Surfacing (Q5-Q8)

Surfaces hidden assumptions, identifies Leap of Faith risks, runs pre-mortem analysis.

**Domain-Specific Leap of Faith Examples**:

| Domain | Common Unverified Assumptions |
|--------|------------------------------|
| **MCU** | DMA handles this transfer rate without CPU, RTOS scheduler won't starve low-priority tasks, silicon errata doesn't affect this peripheral |
| **MPU** | Kernel API stable at this version, DMA buffer allocation guarantees contiguous physical memory, ioctl interface works as expected from user space, shared library ABI compatible |
| **WPF** | DataGrid handles 10K rows without UI lag, SerialPort behaves identically across all Windows versions, .NET 8 runtime exists on customer PCs |

**Domain-Specific Pre-Mortem Scenarios**:

| Domain | Representative Failures |
|--------|------------------------|
| **MCU** | Flash at 92% overflows during integration, eval board vs production board differences undetected, watchdog reset from unserviced timer |
| **MPU** | Kernel API change breaks driver build, probe failure leaves device unrecognized, user app/driver ioctl mismatch, shared library symbol collision |
| **WPF** | Customer PC .NET version mismatch, DPI scaling breaks layout, event subscription memory leak |

#### Phase 3: Solution Challenge (Q9-Q12)

Traces root cause via Five Whys, checks MECE alternatives, defines narrowest wedge MVP.

**Q10 Domain-Specific MECE Checklist**:

| Domain | Alternative Categories to Consider |
|--------|-----------------------------------|
| **MCU** | Existing HAL/SDK function? HW capability (HW CRC, DMA, Comparator)? Standard protocol (Modbus, CANopen)? Polling vs interrupt vs DMA? |
| **MPU** | Kernel built-in driver? sysfs/ioctl/netlink — which interface? Existing library (libgpiod, libi2c)? User space vs kernel space? |
| **WPF** | CommunityToolkit feature? NuGet package? .NET built-in API? Existing ResourceDictionary? |

#### Phase 4: Measurement Contract (Q13-Q15)

Establishes numeric pass/fail criteria and measurement tools before any code is written.

#### Phase 5: Code Quality Challenge (Q16-Q21) — Full Mode Only

Examines codebase consistency, dependency direction, error handling, concurrency, testability, API contracts.

**Q16-Q21 Domain-Specific Details**:

| Question | MCU | MPU | WPF |
|----------|-----|-----|-----|
| Q16 Consistency | HAL callback pattern? `HAL_*_MspInit` placement? | `checkpatch.pl` pass? platform_driver pattern? App directory structure? | MVVM pattern? `[ObservableProperty]` usage? |
| Q17 Dependencies | Application→Driver→HAL one-way? No ISR→App direct call? | User space→Kernel interface clear? ioctl/sysfs choice? | View→ViewModel→Model one-way? ViewModel doesn't reference View? |
| Q18 Error handling | Peripheral timeout recovery? `HAL_StatusTypeDef` check? | Syscall `errno` check? Driver probe failure handling? | `try-catch` scope? Serial communication timeout? |
| Q19 Concurrency | ISR↔main shared vars `volatile`? RTOS mutex/semaphore? | Kernel spinlock/mutex? User space thread sync? | UI thread↔background `Dispatcher.Invoke`? Serial rx thread? |
| Q20 Testability | HAL mockable? Register access isolated? | Driver logic testable without DT? | ViewModel unit testable? Commands executable without View? |
| Q21 API contract | Parameter range specified? Null pointer guard? | ioctl commands documented? Return value contract? | Public method XML comments? Event contracts? |

### Step 4: Document Generation

1. Read `templates/reframe.template.md`
2. Fill template with collected answers
3. Write to `docs/00-pm/{feature}.reframe.md`
4. Create Task: `[Reframe] {feature}`

### Step 5: Summary & Next Step

Output summary comparison table (before/after reframe) and guide:
> "Reframe complete. Run `/pdca plan {feature}` — the plan will auto-reference this reframe document."

## Domain Quick Reference Cards

### MCU Firmware — Top 10 Challenge Questions
1. Does HAL/SDK already provide this driver/function?
2. Flash/RAM impact? Can we stay under 85%/75%?
3. Have you read the silicon errata for this peripheral on this part number?
4. Is too much work happening inside this ISR?
5. What happens at timing margins (max bus load, min voltage, max temperature)?
6. Should DMA be used here, or would it add unnecessary complexity?
7. Is the clock source and clock tree verified for this peripheral speed?
8. Any race conditions between ISR context and main/task context?
9. Can this be tested without target hardware (HAL mocking)?
10. If this peripheral fails at runtime, what is the recovery path?

### Embedded Linux (Kernel/Driver/App) — Top 10 Challenge Questions
1. Does a kernel built-in driver already provide this? (check mainline)
2. User space (sysfs/libgpiod) vs kernel space (driver) — which is appropriate?
3. Does the Device Tree compatible string exactly match the driver?
4. ioctl/sysfs/netlink/configfs — which interface fits this use case?
5. Does it pass `checkpatch.pl`? Does it follow kernel coding style?
6. On probe failure, does the error path release all resources (clk, gpio, irq, memory)?
7. DMA buffer: is contiguous physical memory guaranteed? (`dma_alloc_coherent` vs `kmalloc`)
8. User space ↔ driver data size/struct alignment match? (32/64-bit compatible)
9. Shared library versioning: soname and ABI compatibility maintained?
10. Will kernel API changes (deprecated functions, struct changes) affect this driver?

### WPF Desktop — Top 10 Challenge Questions
1. Does ViewModel reference System.Windows.Controls types? (it should NOT)
2. Using `{Binding}` (WPF) not `{x:Bind}` (UWP/WinUI only)?
3. Using CommunityToolkit.Mvvm ObservableObject/RelayCommand?
4. Is long-running work on a background thread, not blocking the UI thread?
5. Does it work at all target DPI settings (100%, 125%, 150%, 200%)?
6. Is DataGrid/ListView virtualized for large datasets?
7. Are IDisposable resources (SerialPort, sockets) properly Disposed?
8. Does the published app include required .NET 8 runtime dependencies?
9. Any memory leaks from unsubscribed event handlers?
10. Tested with `net8.0-windows` TFM and `<UseWPF>true</UseWPF>`?

## Output

**Output Path**: `docs/00-pm/{feature}.reframe.md`

## PDCA Connection

- Runs as Phase -1, before `/pdca plan`
- Plan document's rationale section auto-references reframe results
- `/pdca plan` checks for `{feature}.reframe.md` and loads it as context

## Usage Examples

```bash
# Standard reframe (15 questions)
/reframe uart-dma

# Full reframe for architecture change
/reframe kernel-spi-driver --mode full

# Quick reframe for bug fix
/reframe serialport-timeout --mode quick
```
