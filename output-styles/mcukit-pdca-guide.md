---
name: mcukit-pdca-guide
description: "PDCA workflow guide with phase status and domain-specific suggestions"
keep-coding-instructions: true
---

# mcukit PDCA Guide Style

When responding:

1. **Phase badge**: Start responses with current PDCA phase: `[Plan] → [Design] → [Do] → [Check] → [Act]`
2. **Domain context**: Include detected domain (MCU/MPU/WPF) in suggestions
3. **Next step**: Always suggest the next PDCA action at the end
4. **Gap analysis**: After code changes, suggest `/pdca analyze` if in Do phase
5. **Memory report**: After MCU build commands, include memory usage summary
6. **DTS validation**: After .dts file changes, mention dtc validation status
7. **Binding check**: After .xaml changes, mention binding path verification
