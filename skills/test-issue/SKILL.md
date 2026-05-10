---
name: test-issue
description: "Use when testing an issue workflow end-to-end."
allowed-tools: Bash
---

# Test Issue Skill

This skill runs a simple test command.
<execute_bash>
  <command>
    "${CLAUDE_PLUGIN_ROOT}/skills/test-issue/scripts/test-issue.sh"
  </command>
</execute_bash>
