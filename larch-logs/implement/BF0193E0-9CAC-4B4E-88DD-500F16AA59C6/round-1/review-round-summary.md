# Review Round 1

- Mode: `diff`
- 7 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Tier-A dedup does not forward validated mutation context
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: `dedup_tier_a_report` authorizes the operation in Python but invokes `file-failure-report-cross-repo.sh` without `--mutation-context`. Authorized live Tier-A dedup therefore fails at the helper’s secondary authorization gate, preventing deduplication and duplicate comments and causing fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-auth-boundary: Thread `--mutation-context` through every helper invocation from authorized Python callers, and make the shell checker call the same trusted-root validation as Python before any `gh` use.


### FINDING_2: Design terminal filing does not forward validated mutation context
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: After reporter authorization succeeds, `file_issue_after_dedup` invokes the cross-repo helper without `--mutation-context`. Authorized `/design` no-match filing therefore fails at the helper authorization gate and falls back locally instead of filing the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-auth-boundary: Thread `--mutation-context` through every helper invocation from authorized Python callers, and make the shell checker call the same trusted-root validation as Python before any `gh` use.


### FINDING_3: Tier-B filing lacks reporter-level authorization and mutation context
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `_emit_chat_print_filing_status` can reach the cross-repo helper without a Python-side live-mutation authorization check or forwarded mutation context. Live Tier-B stall reports therefore fail closed at the helper and fall back to local output instead of filing or commenting upstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_4: Dry-run performs GitHub and body-file work before returning
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: `issue create-one --dry-run` resolves repositories and validates labels through `gh`, and may read the body file, before returning the preview. This violates the zero-`gh`, authorization-free offline dry-run contract and can prevent previews when live repository or body-file data is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-auth-boundary: Return the dry-run envelope immediately after title redaction and body read, before `_resolve_repo()`, `_valid_labels()`, tempfile creation, or any `gh` subprocess; treat supplied repo/labels as offline preview inputs only.


### FINDING_5: Session authorization does not consistently enforce trusted roots and run identity
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: Session-backed authorization can trust arbitrary context files under broad temporary roots and accepts missing or unvalidated run identity at callers. A crafted or stale context file containing `LARCH_LIVE_MUTATION_OK=true` can authorize a mutation for the wrong session or run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Require a concrete trusted session root plus a present matching run ID whenever a run identity is expected.
  - From codex-specialist-edge-cases: Require a validated larch session root and a nonempty matching run ID at every session-backed caller.
  - From dyn-dyn-auth-boundary: Pass the active run id into every session-backed auth check and fail closed on mismatch; only trusted bootstrap/Step-0 writers may set or refresh `LARCH_LIVE_MUTATION_OK=true`.


### FINDING_9: Missing refusal-harness coverage for invalid mutation contexts
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The shell-helper test harness lacks plan-required cases for missing, invalid, and test-denied mutation contexts. Unauthorized paths or missing `--mutation-context` regressions could therefore pass CI without proving refusal or zero `gh` activity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Missing end-to-end design authorization and reconciliation tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Design terminal authorization and salvage-reconciliation behavior are largely untested end to end, while existing tests still monkeypatch the reconciliation seam. Unauthorized and authorized reporter/reconcile paths could regress without exercising the real helper boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
