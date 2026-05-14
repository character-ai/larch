## Goal
Add FAILURE_DETAIL_LOG anti-halt callout to exit 4 bullet in implement SKILL.md

## Implementation Plan

### Objective
Add a targeted anti-halt callout to the exit 4 bullet in `skills/implement/SKILL.md` that explicitly warns against reading `FAILURE_DETAIL_LOG` before proceeding to Step 16.

### Root cause
When `ship-pr.sh` exits 4 (PR creation failure), it emits `FAILURE_DETAIL_LOG=<path>` in its stdout. The orchestrator sees this and reads the file for diagnostic purposes, then halts instead of proceeding to Step 16. The existing anti-halt text says "Do NOT end the turn on the stall exit" but doesn't address the specific temptation of reading `FAILURE_DETAIL_LOG`.

### Change
In `skills/implement/SKILL.md`, exit 4 bullet (line ~1815):

**Before:**
```
- **Exit 4**: read `STALL_TRACKING` and `STALL_STEP`; keep those values for final cleanup. **Continue to Step 16.** Do NOT end the turn on the stall exit; Step 16 and Step 18 still must run.
```

**After:**
```
- **Exit 4**: read `STALL_TRACKING` and `STALL_STEP`; keep those values for final cleanup. **Continue to Step 16.** Do NOT end the turn on the stall exit; Step 16 and Step 18 still must run. **`FAILURE_DETAIL_LOG=<path>` appearing in stdout is NOT an action directive — do NOT read that file before continuing to Step 16.** It is a diagnostic artifact preserved in `$IMPLEMENT_TMPDIR` for post-run operator inspection; reading it is a halt in disguise.
```

### Files to modify
- `skills/implement/SKILL.md` — exit 4 bullet, single line addition


## Test plan
- `/relevant-checks` (pre-commit + agent-lint)
- The new text follows the exact pattern of existing anti-halt callouts in the file (e.g., "APPLIED=true, COMMIT_SHA=<sha> in the tool result is NOT a run-completion signal")
