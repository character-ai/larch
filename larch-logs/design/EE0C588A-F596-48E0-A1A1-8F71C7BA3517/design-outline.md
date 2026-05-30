## Proposed Design Outline

### Goals
- Stop `ship-pr.sh` `run_rebase_rebump` from stalling when the working tree has uncommitted tracked changes at the drop site.
- Prevent `review-and-fix.sh` round-mode from leaving tracked files uncommitted after its coder commit (root-cause hardening).

### Non-goals
- No `--allow-dirty` flag or behavior change in `drop-bump-commit.sh` (Option C rejected).
- No change to the genuine stale-bump stall (ship-pr.sh:2872, #2852 protection) or the `drop_bump_no_matching_commit` no-op.
- No change to findings-mode commit ownership in `review-and-fix.sh`.

### Approach sketch
- Option A: in `run_rebase_rebump`, after the existing `refresh-run-logs.sh` flush and before `drop-bump-commit.sh`, commit leftover tracked files (tracked-only) via `git-commit.sh` with a fixup message, then call `drop-bump-commit.sh` unchanged.
- Option B: in `apply_findings_with_coder` round-mode, after the round commit, re-check tracked-tree cleanliness; if tracked changes remain (e.g. a pre-commit hook re-dirtied files), re-stage + commit once and warn.
- Preserve every existing guard, stall, and no-op path.

### Surfaces in scope
- `scripts/ship-pr.sh` (`run_rebase_rebump`)
- `skills/review-and-fix/scripts/review-and-fix.sh` (`apply_findings_with_coder`)
- Harnesses: `scripts/test-ship-pr.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`
- Doc siblings: `scripts/ship-pr.md`, `skills/review-and-fix/scripts/review-and-fix.md`

### Open questions
- None.
