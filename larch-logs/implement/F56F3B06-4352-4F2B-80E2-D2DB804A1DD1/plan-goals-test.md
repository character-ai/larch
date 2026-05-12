## Goal
Suppress stdout from the two `tracking-issue-summary.sh upsert-summary` calls in `run_postmerge_phase` in `scripts/ship-pr.sh` so their `COMMENT_ID=`, `COMMENT_URL=`, `UPDATED=...` KV lines no longer appear in the `/implement` transcript.

## Implementation Plan

### File to modify
- `scripts/ship-pr.sh` — `run_postmerge_phase` function (around line 643–655 in current code)

### Approach
Change `2>/dev/null || true` to `>/dev/null 2>&1 || true` on both `tracking-issue-summary.sh upsert-summary` calls. This suppresses stdout (the KV output lines) in addition to the already-suppressed stderr.

### Files
- `scripts/ship-pr.sh`: two one-line changes in `run_postmerge_phase`

### Edge cases
- No behavioral change: ship-pr.sh reads nothing from these calls' stdout (it uses `|| true` to discard any exit code)
- `scripts/ship-pr.sh.md` is the sibling doc; no behavior change so no doc update needed

### Test plan
- Run `/relevant-checks` after the change
- Verify the change looks correct in `git diff`
