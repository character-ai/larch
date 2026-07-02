### OOS_1: [OUT_OF_SCOPE] Step 8 warning drops can miss committed run logs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Step 8+ guideline-drop warnings are still only written to the temp execution-issues log, so the committed run logs can miss the drop notice and its diagnostic reason when pinning fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Ship-level test coverage still misses failure and drift cases
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The new ship test proves the happy path, but it still does not cover empty fingerprints, write failures, or the moving-repo structural cases called out in the review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Closeout still re-materializes live diffs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The closeout and stall path still uses the older pin, refresh, retry flow with repeated live-diff computations, so concurrent drift can still drop guideline notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] note_fingerprint_stale can still fall back to live diff
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: When the snapshot check fails, note_fingerprint_stale can still materialize live diff, leaving a narrow post-pin race that can reintroduce the stale-note path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Warning append failures are swallowed
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Warning append failures are still hidden behind suppress(Exception), so diagnostic warnings can disappear independently of the flush timing issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] materialize_implementation_diff can see inconsistent repo state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: materialize_implementation_diff still runs git merge-base and git diff as separate subprocesses, so a moving HEAD or origin/main can expose inconsistent repo state between the two calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Core helper tests still lack direct unit coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There are still no direct unit tests for pin_note_from_staged_for_current_head or _pin_note_from_live_diff, so regressions there are only indirectly exercised through the ship harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

