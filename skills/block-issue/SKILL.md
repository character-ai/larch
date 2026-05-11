---
name: block-issue
description: "use when you need to express the fact that issue A is blocked by issue B. The skill should take issue numbers A and B as arguments and use the above GitHub native blocking relationship API you just discovered and used."
argument-hint: "<ISSUE_A> <ISSUE_B>"
allowed-tools: Bash
---

# block-issue

Express a native GitHub blocking relationship: issue ISSUE_A is blocked by issue ISSUE_B.

## Arguments

Positional: `ISSUE_A ISSUE_B` — plain issue numbers. Example: `/block-issue 1842 1827` marks #1842 as blocked by #1827.

## Step 1 — Add blocked-by relationship

```bash
${CLAUDE_PLUGIN_ROOT}/skills/block-issue/scripts/add-blocked-by.sh <ISSUE_A> <ISSUE_B>
```

Parse `SUCCESS=true` and the confirmation line from stdout. On non-zero exit, surface the `ERROR=` message and stop.
