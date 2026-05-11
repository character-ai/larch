---
name: test-issue
description: "Use when testing an issue workflow end-to-end."
allowed-tools: Bash
---

# Test Issue Skill

This skill runs a simple test command.

## Flags

- `--run-id <ID>`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).
<execute_bash>
  <command>
    "${CLAUDE_PLUGIN_ROOT}/skills/test-issue/scripts/test-issue.sh"
  </command>
</execute_bash>
