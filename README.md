# mcukit — AI Native Embedded Development Kit

> **PDCA methodology + Domain-specific AI agents for MCU/MPU/WPF development**

mcukit is a Claude Code plugin that provides structured development workflows for embedded and desktop projects. It auto-detects your project domain and activates domain-specific Skills, Agents, and Quality Gates.

## Supported Domains

| Domain | Platforms | Key Features |
|--------|-----------|-------------|
| **MCU** | STM32, NXP Kinetis K | .map memory analysis, .ioc pin/clock validation, MISRA C |
| **MPU** | i.MX6, i.MX6ULL, i.MX28 | Device Tree validation, Yocto/Buildroot analysis |
| **WPF** | C#/XAML/.NET 8 | XAML binding verification, MVVM pattern validation |

## Installation

### Option 1: Plugin Marketplace (Recommended)

```bash
# 1. Register mcukit as a marketplace
/plugin marketplace add solitasroh/mcukit

# 2. Install the plugin
/plugin install mcukit@solitasroh-mcukit
```

### Option 2: Manual Clone + Symlink

```bash
# 1. Clone the repository
git clone https://github.com/solitasroh/mcukit.git ~/.claude/plugins/mcukit

# 2. Symlink skills and agents
ln -s ~/.claude/plugins/mcukit/skills ~/.claude/skills
ln -s ~/.claude/plugins/mcukit/agents ~/.claude/agents
```

### Option 3: Project-local (Submodule)

```bash
# 1. Add to your embedded project as a submodule
cd my-stm32-project
git submodule add https://github.com/solitasroh/mcukit.git .mcukit

# 2. Symlink into .claude/
mkdir -p .claude
ln -s ../.mcukit/skills .claude/skills
ln -s ../.mcukit/agents .claude/agents
cp .mcukit/CLAUDE.md ./CLAUDE.md
```

## Quick Start

```bash
# 1. Open your MCU/MPU/WPF project in Claude Code
cd my-stm32-project
claude

# 2. mcukit auto-detects domain (MCU/MPU/WPF)
# 3. Start PDCA workflow
/pdca plan my-feature
/pdca design my-feature
/pdca do my-feature
/pdca analyze my-feature
/pdca report my-feature
```

## Plugin Contents

| Component | Count | Description |
|-----------|:-----:|-------------|
| **Skills** | 44 | Domain knowledge, PDCA workflow, 9-phase pipeline, utilities |
| **Agents** | 39 | AI specialists (fw-architect, linux-bsp-expert, wpf-architect, CTO, PM team...) |
| **Hook Events** | 18 | Lifecycle automation (build, validation, PDCA, team, session...) |
| **Output Styles** | 4 | Response formatting (learning, pdca-guide, embedded, pdca-embedded) |
| **Templates** | 38 | PDCA documents, domain specs, pipeline phases, shared patterns |
| **MCP Servers** | 2 | PDCA status & metrics, code quality & gap analysis |
| **Refs** | 5 | Code pattern references (HAL, SDK, DTS, Yocto, MVVM) |
| **Integration Tests** | 76 | All passing |

## Key Features

### MCU Domain
- **Auto Memory Report**: `make` builds trigger automatic Flash/RAM dashboard
- **Pin Conflict Detection**: CubeMX .ioc pin assignment validation
- **Clock Tree Verification**: PLL/SYSCLK/APB frequency calculation and limit check
- **MISRA C Guide**: Required/Advisory rule reference with cppcheck integration

### MPU Domain
- **DTS Validation**: Automatic `dtc` syntax check on .dts/.dtsi file save
- **Yocto Analysis**: local.conf/bblayers.conf parsing, image size tracking
- **Cross-Compiler Detection**: i.MX28 soft float auto-selection (ARMv5TEJ)

### WPF Domain
- **XAML Binding Check**: Path extraction with [ObservableProperty] Source Generator support
- **MVVM Validation**: Pattern compliance scoring (no View references in ViewModel)
- **Serial Bridge**: MCU UART ↔ WPF SerialPort parameter consistency check

## Requirements

- Claude Code v2.1.78 or later
- Node.js 18+ (for hook scripts)

## License

MIT

## Based On

Core PDCA engine ported from [bkit-claude-code](https://github.com/popup-studio-ai/bkit-claude-code) (Apache 2.0) by POPUP STUDIO.
