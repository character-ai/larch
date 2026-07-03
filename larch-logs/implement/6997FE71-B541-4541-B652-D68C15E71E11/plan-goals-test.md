## Goal
Implement issue #6128: [IMPLEMENTING] [OOS] Tally-error doc still claims restore-without-restore.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Arch
**Phase**: design
**Vote tally**: N/A

## Description

`plan-review.md` says a Step 3 tally-error "restores cumulative accepted artifacts," but no restore helper exists anywhere in the codebase — the `.prev.md` sidecars are delete-only (used during manual Gate A/C re-entry cleanup), never written or read as a snapshot-then-restore mechanism. The actual tally-error behavior only fail-closes by not clearing cumulative files; it does not implement restore. Affected: `skills/design/references/plan-review.md:65` ("Tally failures" bullet under "Single-pass review").

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
