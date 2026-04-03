# Expected: CC Version Upgrade Impact Analysis Process

## Step 1: Version Research
1. Fetch the Claude Code changelog entries between v2.1.71 and v2.1.79
2. Identify release notes and documented breaking changes for each intermediate version
3. Catalog new features, deprecations, and behavioral changes
4. Flag any changes to hooks API, agent spawning, or skill loading mechanisms

## Step 2: Change Classification
1. Categorize each change by impact area: hooks, agents, skills, CLI, MCP, permissions
2. Assign severity levels: breaking (requires code change), notable (behavioral shift), minor (cosmetic)
3. Cross-reference with mcukit's hook definitions in settings.json
4. Identify changes that affect tool permission model or sandbox behavior

## Step 3: Architecture Impact Analysis
1. Map each CC change to specific mcukit components that may be affected
2. Evaluate hooks system compatibility: PreToolUse/PostToolUse contract stability
3. Assess agent team spawning: verify sub-agent parallel execution still works
4. Check skill loading: trigger matching, SKILL.md parsing, slash command routing
5. Review MCP server integration: bkit-pdca and bkit-analysis connection handling

## Step 4: Compatibility Testing
1. Verify mcukit skill auto-detection works correctly on the new CC version
2. Test freeze/guard/deploy safety hooks fire as expected
3. Confirm pm-discovery agent team completes without timeout or orphan agents
4. Validate PDCA workflow end-to-end: plan -> design -> do -> analyze -> report
5. Check domain detection (MCU/MPU/WPF) triggers appropriate skill sets

## Step 5: Impact Report Generation
1. Output a comprehensive impact report with risk assessment matrix
2. Result classification: safe to upgrade / upgrade with caution / block upgrade
3. List all required mcukit code changes before upgrading (if any)
4. Document ENH (enhancement) opportunities enabled by new CC features
5. Expected Output format: markdown report with summary table, detailed findings, and action items
