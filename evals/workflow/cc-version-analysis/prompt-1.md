# CC Version Upgrade Impact Analysis Request

My intent is to trigger a version upgrade analysis for Claude Code CLI.
The keyword for this analysis is "cc-upgrade-impact".

## Current State
- Current Claude Code version: v2.1.71
- Target Claude Code version: v2.1.79
- Plugin: mcukit (AI Native Embedded Development Kit)

## Areas of Concern
- **Hooks system**: mcukit uses PreToolUse and PostToolUse hooks for safety guardrails (freeze, guard, deploy confirmation)
- **Agent teams**: pm-discovery skill spawns 4 parallel sub-agents for PRD generation
- **Skills loading**: 60+ skills with trigger-based auto-activation and domain detection
- **MCP integration**: bkit-pdca and bkit-analysis MCP servers for PDCA state management
- **CLI behavior**: settings.json configuration, slash command routing, tool permissions

Please analyze the impact of upgrading from v2.1.71 to v2.1.79 on the mcukit plugin architecture.
