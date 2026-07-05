---
name: block-issue
description: "Use when expressing a native GitHub blocked-by relationship between two issues. Takes the blocked issue number and the blocking issue number as arguments."
argument-hint: "<ISSUE_A> <ISSUE_B> [--repo owner/name]"
allowed-tools: Bash
---

# block-issue

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Express a native GitHub blocking relationship: issue ISSUE_A is blocked by issue ISSUE_B.

## Arguments

Positional: `ISSUE_A ISSUE_B` — plain issue numbers (≥1). Optional: `--repo owner/name` (auto-detected from `gh repo view` when omitted). Optional: `--run-id <ID>`; shared flag details are in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-id-flag.md`. Example: `/block-issue 1842 1827` marks #1842 as blocked by #1827.

<!-- step:1 — Add blocked-by relationship -->

Strip `--run-id <ID>` from `$ARGUMENTS` before invoking the script (the script does not accept this flag). Script contract: `${CLAUDE_PLUGIN_ROOT}/python/issue_block.py`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" block-issue add-blocked-by $ARGUMENTS
```

Parse `SUCCESS` and the confirmation line from stdout without `eval`/`source`. Verify the relationship was established before reporting:

- **`SUCCESS=true`**: Print the confirmation line (e.g., `✓ #1842 is now blocked by #1827`).
- Non-zero exit: Surface the `ERROR=` message from stderr and stop.
