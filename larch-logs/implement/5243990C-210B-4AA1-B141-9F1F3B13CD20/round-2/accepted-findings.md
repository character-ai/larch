### FINDING_1: Step 18b failure logs are empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `append_failure_best_effort` creates failure log paths but does not redirect failing helper stdout/stderr into them, so execution issues can point to empty logs after `token-report.sh` or `write-final-report.sh` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_10: Missing empty/comment-only state-file harness cases for clear/seed paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The stall-recovery harness lacks dedicated blank/comment-only `ship-pr-state.sh` cases for `clear-stall` and `seed-terminal-state`, so regressions around those edge cases could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Step 18b harness misses session-env and plugin-root fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-step-18b-final-report.sh` stubs helper behavior without exercising production `session-env.sh` rehydration or `plugin-root.env` fallback, so regressions in load-bearing env wiring may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_13: MV-failure tests do not assert disk state remains unchanged
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `clear-stall` / `seed-terminal-state` mv-failure harness cases check emitted KVs but not that on-disk `STALL_TRACKING` and file contents remain unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: E1 KV-before-exit testing only covers mv failures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not cover temp-read or destination-read assertion failures, so helpers might abort without the promised `CLEARED=false` / `SEEDED=false` KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_29: Step 18b command substitution hides emitted KVs from tool stdout
- **Reviewer(s)**: dyn-teardown-boundary-output.txt
- **Severity**: important
- **Concern**: The Step 18 Bash fence captures `step-18b-final-report.sh` output in `_step18b_out` and parses it internally but does not re-print it, so the LLM orchestrator may not see `EMIT_BODY` / `WFR_RC` even though NEVER #20 depends on them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-boundary-output.txt: Address the concern above.


### FINDING_31: Unused `token_rc` variable in Step 18b
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never read or emitted, adding reviewer noise and possible future confusion about whether a KV exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


### FINDING_34: Step 18b contract doc contradicts rooted-path requirement
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.md` says helper paths must be rooted under `$IMPLEMENT_TMPDIR`, but its emit-decision section still shows cwd-relative `summary-final.md`, `.step18-prebody`, and `cmp` examples, risking reintroduction of the rooted-path bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_4: `validate_ship_pr_state` rejects key-empty state files and changes classify behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: Adding a `saw_key` / empty-file rejection to `validate_ship_pr_state` makes existing blank or comment-only `ship-pr-state.sh` files cause `classify` and other existing callers to exit 3 instead of falling back to session-env behavior as before.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt: Address the concern above.


### FINDING_8: `seed-terminal-state` mishandles empty-but-present state files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A zero-byte or comment-only existing `ship-pr-state.sh` is treated as malformed instead of absent/fresh, blocking durable terminal stall seeding and `[STALLED]` rename behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


