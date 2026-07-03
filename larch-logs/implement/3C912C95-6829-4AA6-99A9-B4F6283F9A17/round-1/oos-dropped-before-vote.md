### OOS_1: [OUT_OF_SCOPE] duplicate review_log_root assignment in scout block
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The scout bash block reassigns `review_log_root` even though it was already hoisted earlier, which makes the scout block look like the canonical definition site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove the duplicate review_log_root assignment from the scout-only block per the plan

### OOS_2: [OUT_OF_SCOPE] missing CI pin for the Step 4 guard contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-review-runlog
- **Severity**: nit
- **Concern**: Step 4 structure tests still lack a static pin for the hoisted `review_log_root` and slug-valid RUN_ID guard wording, so prompt-side regressions can slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add optional pins for hoisted review_log_root and slug-valid RUN_ID guard wording when tightening review structure tests
  - From cursor-specialist-edge-cases: Add pins for review_log_root assignment RUN_ID slug predicate and review_run_id_valid gating when desired
  - From cursor-specialist-testing: Optionally extend pin (18) when tightening review Step 4 contracts
  - From dyn-dyn-review-runlog: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] clarify publish still uses the 5c warning label
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Clarify publish omits `--reason`, so warnings still label 5c instead of clarify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Out of scope this round per plan; future work could pass --reason clarify or a dedicated label

### OOS_4: [OUT_OF_SCOPE] capture-transcript still needs slug and log-root checks
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-review-runlog
- **Severity**: nit
- **Concern**: `capture-transcript` still builds paths from `Path(args.log_root)` and `args.run_id` directly, so the Python boundary does not enforce slug validity or the commit-style log-root resolution fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add validate_run_id_slug at capture-transcript entry; pre-existing gap not introduced here
  - From cursor-specialist-testing: Teach capture-transcript to resolve log-root like commit in a separate change
  - From dyn-dyn-review-runlog: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] publish CLI integration test still lacks the warning-step-label pin
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The design publish CLI integration path has no argv pin for `--warning-step-label 5c`, so the default final publish path is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend the fake-cli call-log assertion in that test to pin --warning-step-label and 5c for the default final publish path

### OOS_6: [OUT_OF_SCOPE] offline Step 4 harness is still missing
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-review-runlog
- **Severity**: nit
- **Concern**: No dedicated offline harness covers the standalone Step 4 capture argv, nested-review skip, or `SESSION_UUID` mismatch, so the prompt-only guard wiring remains unmechanized in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept as deferred follow-up or add a thin harness in a later issue
  - From dyn-dyn-review-runlog: Address the concern above.

