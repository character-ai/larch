### OOS_1: [OUT_OF_SCOPE] CI-fix end-to-end regression missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-runlog-refresh
- **Severity**: important
- **Concern**: The CI-fix path still only proves callback wiring and invalidation ordering. It does not exercise a real tmpdir run-log state, a durable warning append, a successful push, and a committed `execution-issues.ndjson` warning, so a flush/commit regression could still ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-runlog-refresh: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Post-rebase invalidation still lacks a warning-triggered flush
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-runlog-refresh
- **Severity**: latent
- **Concern**: The rebase paths still invalidate guidelines only after `rebase_and_push` completes, so a warning appended on that seam can miss the push that just finished and rely on a later flush or teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-runlog-refresh: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Fallback invalidate path ignores the boolean return
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The fallback path can append a warning without ever flushing it, so an `execution-issues.md` note may remain uncommitted after the post-monitor invalidate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

