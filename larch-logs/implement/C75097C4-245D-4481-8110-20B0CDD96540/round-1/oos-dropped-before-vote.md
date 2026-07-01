### OOS_1: [OUT_OF_SCOPE] Unknown/unparseable exit retryable by design in classifier
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Unknown/unparseable exit is intentionally retryable per plan; same-cause-repeat caps bound blast radius. Omitting `--exit-code` on positive failures retries by design, not accidental omission in classifier logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Narrow to negative-only if operators prefer fail-closed behavior over retry on missing data.

### OOS_2: [OUT_OF_SCOPE] checks-leg-timeout remains terminal contract-failure at step 3/6
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `checks-leg-timeout` still hits blanket step 3/6 contract-failure; plan scoped only `checks-child-failed` SIGTERM. Internal `_run_leg_with_timeout` at step 3 remains terminal with `RESUME_HINT=none`. Runs killed by the internal checks leg deadline still get contract-failure / no retry at step 3/6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Handle checks-leg-timeout separately if that failure mode should also retry.
  - From cursor-specialist-testing: Out of plan scope; separate issue if leg-timeout retries are desired.

### OOS_3: [OUT_OF_SCOPE] _DIRECT_BAIL_CLASSIFICATIONS dict refactor widens review surface
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_DIRECT_BAIL_CLASSIFICATIONS` dict refactor is behavior-neutral scope beyond the plan. No runtime impact; slightly widens review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Inline or defer refactor unless needed for the SIGTERM guard.

### OOS_4: [OUT_OF_SCOPE] Omitting --exit-code on checks-child-failed may retry positive failures by plan design
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `stall-recovery` item 3 does not normatively require passing composite `EXIT_CODE` to classify. Omitting `--exit-code` with `checks-child-failed` can classify unknown exit as retryable per plan, but positive `EXIT_CODE=1` failures may also retry if orchestrator omits the flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document --exit-code forwarding in item 3 or bind EXIT_CODE before Step 18a classify (future scope).

### OOS_5: [OUT_OF_SCOPE] Generic profile never emits retry hint for checks-child-sigterm
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Generic profile never emits a retry hint for `checks-child-sigterm`. Generic terminal-state classification stays `RESUME_HINT=none` even for transient-infra sigterm pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend generic path only if generic-profile retries are required later.

### OOS_6: [OUT_OF_SCOPE] _seed_durable_stall_state does not persist EXIT_CODE to disk
- **Reviewer(s)**: dyn-dyn-stall-recovery
- **Severity**: latent
- **Concern**: `_seed_durable_stall_state()` still writes only `STALL_TRACKING`, `STALL_STEP`, and `BAIL_REASON`, so disk state alone cannot supply the exit code this branch now depends on. That predates the diff; this change amplifies the need to forward `EXIT_CODE` prompt-side rather than persisting it in the commit-route seeder.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none; reviewer provided no concrete fix direction beyond the concern)

