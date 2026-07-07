### FINDING_2: Fresh issue paths can inherit stale REPO
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-resume-env
- **Severity**: major
- **Concern**: When a fresh issue invocation starts with no `REPO`, unconditional route-state gap-fill can copy an old repo before `resolve_repo()` runs, so `gh issue view`, `design route`, and refreshed `source-env.sh` can target the wrong remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restrict gap-fill to resume@ paths or never gap-fill REPO when ISSUE_NUMBER came from argv; always resolve_repo when REPO is route-state-sourced.
  - From cursor-specialist-edge-cases: Limit gap-fill to resume paths or re-resolve REPO when argv supplies a new ISSUE_NUMBER.
  - From codex-specialist-edge-cases: Limit route-state recovery to confirmed resume@... flows, or gate it behind an explicit resume marker so fresh routes keep using argv, parsed env, and resolve_repo().
  - From dyn-dyn-resume-env: On fresh issue entry, resolve REPO from the live git remote and never gap-fill REPO from route-state unless the invocation is resume-shaped;


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Route-state writes are not fail-closed
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: A failed route-state write can leave stale values behind, and resume refresh can still trust those values and rewrite `source-env.sh` from the wrong issue or repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Check the write result and abort before refresh on failure, or validate the freshly written file, and add a failure-mode test.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Route-state persistence failure leaves stale sidecars
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-resume-env
- **Severity**: minor
- **Concern**: Route-state persistence failure is ignored, so a stale sidecar can survive and mislead later readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Check the write return value and abort Step 0b on persistence failure.
  - From cursor-specialist-testing: Fail closed when route-state write fails and avoid merging from a sidecar known to be stale.
  - From dyn-dyn-resume-env: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Whitespace-only issue values are accepted too late
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-resume-env
- **Severity**: minor
- **Concern**: Whitespace-only issue strings can survive until pause-load or resume handling because the route driver does not reject them early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Strip and reject non-digit issue values immediately after gap-fill.
  - From cursor-specialist-testing: Strip and reject non-digit issue strings at the route driver entry guard.
  - From dyn-dyn-resume-env: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Malformed recovery should fail closed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Recovery parse errors other than `OSError` are not fail-closed, so partially malformed sidecar content can produce incomplete recovery without a clear abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Treat unreadable or empty recovery as hard failure on resume paths.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Resume fail-closed tests are still missing
- **Reviewer(s)**: dyn-dyn-resume-env
- **Severity**: minor
- **Concern**: Resume fail-closed paths still lack targeted tests, so coverage stays centered on the happy rehydration path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-resume-env: Address the concern above.
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

