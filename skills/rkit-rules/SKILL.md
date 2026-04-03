---
name: rkit-rules
classification: workflow
classification-reason: "Core development rules for embedded/desktop PDCA workflow"
deprecation-risk: none
description: |
  Core rules for rkit plugin. PDCA methodology, domain detection,
  agent auto-triggering, and embedded code quality standards.

  Triggers: rkit, PDCA, develop, implement, feature, driver, firmware,
  개발, 기능, 드라이버, 펌웨어, 커널, WPF, MVVM
user-invocable: false
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
imports:
  - ${PLUGIN_ROOT}/refs/code-quality/common.md
---

# rkit Core Rules

## 1. PDCA Methodology (Always Apply)

- New feature → Check/create Plan/Design documents first
- After implementation → Suggest Gap analysis (`/pdca analyze`)
- Gap Analysis < 90% → Auto-improvement with pdca-iterator
- Gap Analysis >= 90% → Completion report (`/pdca report`)

## 2. Domain-Aware Development

rkit automatically detects the project domain and applies domain-specific rules:

### MCU (STM32, NXP Kinetis K)
- Follow MISRA C:2012 coding standards
- Check memory budget (Flash/RAM) after every build
- Use HAL/LL API patterns from refs/
- Verify pin assignments before peripheral initialization

### MPU (i.MX6, i.MX6ULL, i.MX28)
- Validate Device Tree changes with dtc
- Check Yocto build image sizes
- i.MX28 uses soft float toolchain (arm-linux-gnueabi-gcc)
- i.MX6/6ULL uses hard float (arm-linux-gnueabihf-gcc)

### WPF (C#/.NET)
- Follow MVVM pattern (CommunityToolkit.Mvvm recommended)
- No x:Bind (UWP only) - use {Binding} syntax
- Check XAML binding paths against ViewModel properties
- .NET 8: Use `Microsoft.NET.Sdk` with `<UseWPF>true</UseWPF>`

## 3. Code Structure Quality (All Domains)

AI-generated code introduces 1.7x more structural issues — these rules prevent that.
Apply these rules whenever generating code, regardless of domain.

### Core Principles
1. **Single Responsibility**: Each function/class/module has one reason to change
2. **Open/Closed**: 3+ branches on same axis → Strategy/polymorphism, not more elif
3. **Depend on Abstractions**: Inject dependencies via constructor, never instantiate internally
4. **Reuse Before Write**: Check existing codebase first, do not reimplement utilities
5. **Refactor First, Then Add**: If existing code can't absorb addition cleanly — refactor first

### Sizing Limits
| Metric | Limit | Action |
|--------|-------|--------|
| Function body | 40 lines | Extract helpers |
| Parameters | 3 | Parameter object |
| Nesting depth | 3 levels | Early return / guard clauses |
| Class public methods | 7 | Split responsibilities |
| File length | 300 lines | Split by cohesion |

### Self-Check (before completing any code task)
1. Does each unit have a single, nameable responsibility?
2. Could I add a new variant without editing existing code?
3. Are dependencies injected, not instantiated internally?
4. Did I reuse existing project code, or write from scratch?
5. Is every function under 40 lines and under 3 params?

### Language-Specific Rules (MANDATORY)

<HARD-RULE>
Before writing or designing any code, you MUST use the Read tool to load the matching
language reference. Apply the patterns, modern idioms, and reference repo styles from that document.
This is not optional — skipping this produces structurally poor code.
</HARD-RULE>

| File Extension | Read This Reference | Key Patterns |
|----------------|-------------------|--------------|
| `.c`, `.cpp`, `.h`, `.hpp` | `refs/code-quality/cpp.md` | RAII, ownership semantics, concepts, Modern C++17/20 |
| `.cs` | `refs/code-quality/csharp.md` | Clean Architecture layers, ErrorOr, Modern C# 12 |
| `.ts`, `.tsx`, `.js` | `refs/code-quality/typescript.md` | Result pattern, feature-based modules, Modern TS 5.x |
| `.py` | `refs/code-quality/python.md` | Protocol, frozen dataclass, async TaskGroup, Modern 3.12 |

Each reference contains:
- Bad/Good code pairs (follow the Good patterns)
- Modern language idioms (use these, not legacy patterns)
- Reference repositories (study these for code style)
- Anti-patterns (avoid these explicitly)

## 4. Domain Code Quality Standards

- MCU: Zero MISRA Required violations, advisory max 10
- MPU: Device Tree must compile with dtc
- WPF: Zero build warnings, zero binding errors
- All: Convention compliance >= 90%

## 5. Safety Rules

- Never auto-execute flash erase commands
- Never auto-execute dd to block devices
- Always confirm destructive operations with user
