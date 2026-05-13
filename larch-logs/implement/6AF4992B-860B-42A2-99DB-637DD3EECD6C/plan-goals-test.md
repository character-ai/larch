## Goal
Add `--no-logs-commit` flag to `/implement` and `/fix-issue` that skips the `larch-log.sh commit` git commits while still generating log files in the temp directory.

## Goal
Add `--no-logs-commit` flag to `/implement` and `/fix-issue` that skips the `larch-log.sh commit` git commits while still generating log files in the temp directory.

## Implementation Plan

### Files to modify

1. `skills/implement/SKILL.md` — three changes:
   a. **Flags section** (after `--no-admin-fallback`): add `--no-logs-commit` flag entry setting `no_logs_commit=true`.
   b. **Step 7a "Pre-bump log flush"** (the `larch-log.sh commit` line at the end): wrap with `if [ "$no_logs_commit" != "true" ]` guard so the write calls still run but the commit is skipped when the flag is set.
   c. **Step 18 transcript commit block**: wrap the inner `larch-log.sh commit` call with the same guard.

2. `skills/implement/references/rebase-rebump-subprocedure.md` — one change:
   - **step 1b log-flush commit** (the `larch-log.sh commit` call): add a prose condition that the commit is skipped when `no_logs_commit=true`.

3. `skills/fix-issue/SKILL.md` — two changes:
   a. **Flags section** (after `--no-admin-fallback`): add `--no-logs-commit` flag entry.
   b. **Step 5a `/implement` invocation**: add `[--no-logs-commit if no_logs_commit]` to the forwarded flags.

### Approach

The issue specifies: skip only the `larch-log.sh commit` step (which flushes from temp to git tree), not the `larch-log.sh write` steps (which create the log files in the temp directory). This means:
- In the pre-bump log flush: keep the four `larch-log.sh write` calls, skip only the final `larch-log.sh commit` call
- In step 1b of rebase-rebump: keep the write calls, skip the commit call
- In Step 18: skip the `larch-log.sh commit` inside the transcript block

### Edge cases
- The flag is independent of all other flags (like `--no-admin-fallback`, `--auto`, etc.)
- The `larch-log.sh write` calls must still run so logs are available in tmpdir for analysis
- For `/fix-issue`, this is a pure pass-through — no logic change in fix-issue itself

### Verification
Run `/relevant-checks` after changes (pre-commit + agent-lint on modified files).
