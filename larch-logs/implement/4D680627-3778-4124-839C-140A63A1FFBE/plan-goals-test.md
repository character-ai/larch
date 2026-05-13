## Goal
Add an explicit anti-polling rule in `skills/implement/SKILL.md` Step 2, co-located with the `step2-implement.sh` dispatch block, to prevent orchestrators from polling the sidecar log and printing intermediate output while waiting for the external implementer.

## Implementation Plan

### File to modify
`skills/implement/SKILL.md`

### Approach
In section **"2.1 — First dispatch invocation"** of Step 2, after the closing triple-backtick of the bash block (the block ending with `--workflow "$implement_workflow"`), insert a new bold rule paragraph:

```
**Do NOT poll or print sidecar output while dispatching.** Invoke `step2-implement.sh` as a foreground-blocking Bash call (no `run_in_background: true`). While the external implementer runs, do NOT read the sidecar log and do NOT print intermediate output to the user — polling floods the terminal with non-actionable messages. The dispatcher blocks; parse its stdout as KV after it exits.
```

This is a pure prose insertion — no code changes, no script changes.

### Edge cases
- The insertion point is unambiguous: it's the blank line between the closing ``` of the bash block and the `$PLAN_FILE is the path...` paragraph at line ~932.
- The `run_in_background: true` code span must not have leading/trailing spaces (MD038).

### Testing strategy
Run `/relevant-checks` after the edit (pre-commit + agent-lint). The edit is prose-only, so there's no runtime behavior to test.
