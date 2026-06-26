### FINDING_1: All-security dropped-OOS regression test is optional
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The all-security-only pre-vote drop scenario is guarded only by an optional ("if needed") pytest, even though it covers the primary leak path. If every dropped OOS block is security-tagged and a missed empty write to `oos-dropped-before-vote.md` leaves prior-round public audit bytes in `review_tmpdir`, `_flush_round_log` can still allowlist and commit that stale public file, so security fixes may ship without catching the exact regression this issue describes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Make the all-security dropped-OOS pytest mandatory (not "if needed"): assert dropped_count counts security blocks, oos-dropped-before-vote.md is empty, and oos-dropped-security-local.md holds the renumbered security block

### FINDING_2: Non-atomic dropped-OOS audit writes can publish stale public content on partial failure
- **Reviewer(s)**: Codex-dyn-Security Oos Boundary
- **Severity**: blocking
- **Concern**: The plan splits audit streams but does not make the two writes atomic or clean up the public file on write failure. A failure after `oos-dropped-before-vote.md` is written can leave public security-adjacent content on disk. `python/review_pipeline.py:2262-2264` still routes gate failures through the panel-failed path, which flushes the round log, and `python/run_logs.py:2999-3009` still allowlists `oos-dropped-before-vote.md`, so a partial failure can still publish stale public content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Security Oos Boundary: Stage both audit writes to temp files and rename them only after both succeed, or truncate/delete `oos-dropped-before-vote.md` before re-raising so the fail-closed path cannot flush partial public content.
