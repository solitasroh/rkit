---
name: ship
classification: workflow
classification-reason: Delivery workflow depends on external tooling (glab CLI)
deprecation-risk: low
description: |
  Create GitLab Merge Requests from PDCA Report using glab CLI.
  Domain-specific MR templates for MCU, MPU (Kernel/Driver/App), and WPF.

  Triggers: ship, merge request, MR, deliver, 배포, MR 생성,
  マージリクエスト, 合并请求, solicitud de fusión, demande de fusion,
  Merge-Anfrage, richiesta di unione

  Do NOT use for: GitHub PRs (use gh directly), deployment (use /phase-9-deployment).
argument-hint: "[mr|release|tag] [feature]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
imports:
  - ship-mr.template.md
next-skill: null
pdca-phase: null
task-template: "[Ship] {action}"
---

# Ship Skill

> Create GitLab Merge Requests from PDCA completion. Uses `glab` CLI.

## Prerequisites

- `glab` CLI installed and authenticated (`glab auth login`)
- Git remote configured for GitLab
- PDCA Report completed (recommended, not required)

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `mr {feature}` | Create MR from feature branch | `/ship mr uart-dma` |
| `mr` | Create MR from current branch | `/ship mr` |
| `release {version}` | Create release (tag + MR + changelog) | `/ship release v1.2.0` |
| `tag {version}` | Create annotated tag | `/ship tag v1.2.0` |

## Actions

### mr {feature}

**Workflow**:

1. **Pre-flight checks**:
   - Verify `glab` is available (`glab --version`)
   - Check git status (warn on uncommitted changes)
   - Read PDCA report if available (`docs/04-report/{feature}.report.md`)

2. **Branch management**:
   - If not on feature branch: `git checkout -b feature/{feature}`
   - Stage and commit changes with PDCA-based commit message
   - Push branch: `git push -u origin feature/{feature}`

3. **MR creation**:
   - Detect domain (MCU/MPU/WPF) for template selection
   - Fill MR template from `templates/ship-mr.template.md`
   - Include PDCA report summary (match rate, iterations)
   - Add domain-specific impact section
   - Create MR: `glab mr create --title --description --target-branch main`

4. **Post-creation**:
   - Display MR URL: `glab mr view --web`
   - Create Task: `[Ship] MR for {feature}`
   - Write audit log: `mr_created`

**Domain-Specific MR Sections**:

| Domain | Additional Sections |
|--------|-------------------|
| **MCU** | Flash/RAM delta, peripheral changes, interrupt changes, MISRA compliance |
| **MPU** | Kernel ABI impact, driver interface changes (ioctl/sysfs), DT binding changes, library API/ABI compatibility |
| **WPF** | NuGet package changes, XAML binding impact, .NET target compatibility |

**MR Title Format**: `[{domain}] {feature}: {summary from PDCA report}`

**Example**:
```
[MCU] uart-dma: Implement DMA-based UART driver with circular buffer

## Summary
DMA-based UART receive/transmit with double-buffering for high-throughput serial communication.

## Changes
- src/driver/uart_dma.c (new)
- src/driver/uart_dma.h (new)
- src/hal/dma_config.c (modified)

## PDCA Report
- Match Rate: 95%
- Iterations: 2
- Report: docs/04-report/uart-dma.report.md

## MCU Impact
- Flash: +2.1KB (78% → 79%)
- RAM: +512B (62% → 63%)
- Peripheral changes: DMA1 Channel 4/5 allocated for UART1
- Interrupt changes: DMA1_Ch4_IRQHandler, DMA1_Ch5_IRQHandler added
- MISRA compliance: 0 Required violations
```

### release {version}

Combines tag creation + MR + changelog generation into a single release workflow.

1. **Pre-flight**: Verify all active PDCA features are completed (matchRate >= 90%)
2. **Changelog**: Collect PDCA reports since last tag, generate `CHANGELOG.md` entry
3. **Version bump**: Update version in `package.json` / `plugin.json` if applicable
4. **Tag**: Create annotated tag: `git tag -a {version} -m "{changelog summary}"`
5. **Push**: Push tag and branch: `git push origin {version} && git push`
6. **GitLab release**: `glab release create {version} --notes "{changelog}"`
7. **Post-release**: Write audit log: `release_created`

### tag {version}

1. Validate semver format
2. Generate tag message from recent PDCA reports
3. Create annotated tag: `git tag -a {version} -m "{message}"`
4. Push tag: `git push origin {version}`
5. Display tag info

## glab Commands Used

| Command | Purpose |
|---------|---------|
| `glab auth status` | Verify authentication |
| `glab mr create` | Create merge request |
| `glab mr view` | View MR details |
| `glab mr list` | List open MRs |

## Integration

### PDCA Report
Auto-reads PDCA report for MR description. Match rate and iteration count included.

### /code-review
Suggest running `/code-review` before `/ship mr` if not done.

### /security-review
Include security review status in MR checklist if available.

## Usage Examples

```bash
# Create MR for a completed feature
/ship mr uart-dma

# Create MR from current branch
/ship mr

# Tag a release
/ship tag v1.2.0
```
