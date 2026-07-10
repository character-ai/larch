# Review Round 1

- Mode: `diff`
- 2 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_9: Bootstrap routing tests do not cover the complete difficulty matrix
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: minor
- **Concern**: Bootstrap tests do not cover Moderate Cursor-unavailable fallback, Trivial and Hard routing, invalid or missing difficulty fallback, or explicit coder behavior, leaving routing regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Add focused bootstrap and dispatch tests for each omitted scenario, including selected vendor and resolved model assertions.


### FINDING_13: Direct Step 2 dispatch does not resolve omitted difficulty from persisted state
- **Reviewer(s)**: dyn-dyn-routing-parity
- **Severity**: minor
- **Concern**: `step2_dispatch_main` does not call `resolve_step2_effective_difficulty(tmpdir)` when `--difficulty` is omitted, unlike the run-dispatch wrapper. Direct callers can therefore launch Moderate Cursor work with the Composer default and attribute the wrong model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-routing-parity: After tmpdir validation in `step2_dispatch_main`, backfill `args.difficulty` from `resolve_step2_effective_difficulty(tmpdir)` when empty, matching the run-dispatch wrapper, before `_dispatch_state()` and launcher argv assembly.
