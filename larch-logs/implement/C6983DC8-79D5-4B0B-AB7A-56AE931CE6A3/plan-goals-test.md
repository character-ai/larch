## Goal
Document SCOUT_STATUS=validation-failed in dispatch-panel.md and scout-dynamic-archetypes.md

## Implementation Plan

### Goal
Add `validation-failed` to the documented SCOUT_STATUS enum in:
1. `skills/review/scripts/dispatch-panel.md`
2. `scripts/scout-dynamic-archetypes.md`

`docs/run-logs.md` has no SCOUT_STATUS references — no change needed.

### Changes

**File 1: `skills/review/scripts/dispatch-panel.md`**

In the dynamic-archetypes paragraph (the long sentence block), after the existing sentence about `SCOUT_STATUS=missing-diff-file`, add a sentence explaining `validation-failed`:

> When `scout-dynamic-archetypes.sh` itself exits non-zero (subprocess crash, signal, or a `validation_jq_error` that bubbled past the script's own non-fatal guard), the dispatcher writes an empty manifest and emits `SCOUT_STATUS=validation-failed`. This is distinct from `SCOUT_STATUS=parse-failed`, which occurs when the scout script exits 0 but the produced manifest fails downstream validation by `scout_manifest_is_valid`.

**File 2: `scripts/scout-dynamic-archetypes.md`**

In the "Stdout is KEY=value:" line, after the `optional SCOUT_FAIL_REASON on SCOUT_STATUS=parse-failed` phrase, add a note that `validation-failed` is a dispatcher-emitted status (not emitted by the scout script itself): add a sentence explaining it after the stdout line or extend the existing note about `dispatch-panel.sh` wrapper-level `SCOUT_FAIL_REASON` values to mention that `dispatch-panel.sh` also emits `SCOUT_STATUS=validation-failed` when the scout script exits non-zero.

Also update the "Edit in sync" note at the bottom (line 28) to mention `validation-failed` as a status in scope when changing "statuses".


## Test plan
- Run `/relevant-checks` (markdownlint, pre-commit) after edits
- grep both files for `validation-failed` to confirm presence
