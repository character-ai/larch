### OOS_1: `checks-leg-timeout` at Step 3/6 still hits blanket `step-contract`
- **Description**: `checks-leg-timeout` at Step 3/6 still hits blanket `step-contract`. Scenario: Internal `_run_leg_with_timeout` timeout emits `FAILURE_REASON=checks-leg-timeout`, not `checks-child-failed`; the plan only intercepts `checks-child-failed`. Large suites that hit the internal deadline get no retry path
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:126-127
- **Phase**: design



### OOS_2: Internal checks-leg-timeout still hits step-contract after this plan
- **Description**: Internal checks-leg-timeout still hits step-contract after this plan. Scenario: When `_run_leg_with_timeout` fires (`_CHECKS_DEADLINE_MS` = 3h), the composite emits `FAILURE_REASON=checks-leg-timeout`, not `checks-child-failed`. The planned guard keys only on `checks-child-failed`, so that path still returns `contract-failure` / `RESUME_HINT=none` at step 3/6. Long runs that die on the internal leg timer remain terminal.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:186-190
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Threading raw EXIT_CODE through the generic terminal-state path is dead code under current validation.
- **Description**: [OUT_OF_SCOPE] Threading raw EXIT_CODE through the generic terminal-state path is dead code under current validation.. Scenario: The generic terminal-state validator still rejects negative EXIT_CODE values, so this branch cannot affect the SIGTERM case this PR is trying to fix.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/state/_classify.py:276-283; python/larch/state/_validate.py:77-80
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] The raw-exit plumbing for `_classify_generic_from_terminal_state()` does not affect this `/implement` stall fix, because generic terminal-state validation still rejects negative `EXIT_CODE` values before classification.
- **Description**: [OUT_OF_SCOPE] The raw-exit plumbing for `_classify_generic_from_terminal_state()` does not affect this `/implement` stall fix, because generic terminal-state validation still rejects negative `EXIT_CODE` values before classification.. Scenario: Feature still ships correctly without the generic `/design` seam, so this adds extra surface and test work without changing Step 18a behavior.
- **Reviewer**: Codex-dyn-Stall Classifier
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/_classify.py:274-315; python/larch/state/_validate.py:77-82
- **Phase**: design



