### FINDING_1: Cursor stdin test does not assert fd0 inheritance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Cursor stdin control coverage only checks metadata and would not fail if Cursor were accidentally launched with fd 0 redirected to `/dev/null`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Delayed `.done` production launcher race is not covered
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The dispatch voter tests do not exercise the production `launch-review.sh` delayed `.done` promotion path required by the plan; current coverage uses a stub waterfall or unrelated exit-143 hook path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Claude/Voter 1 delayed `.done` test proves non-wait behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Voter 1 delayed `.done` test validates immediate synthetic `.done` backfill instead of proving the dispatcher waits for launcher-owned completion, so it does not catch regressions in Voter 1 barrier inclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Delayed voter fixture does not reproduce txt-before-done ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The delayed voter fixture writes `.txt` and `.done` together after sleeping, so it does not reproduce the original failure mode where output is visible while completion is still missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Voter 1 synthetic `.done` backfill can bypass the wait barrier
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `dispatch-code-voters.sh` writes Voter 1 `.done` before the wait list is built, allowing the barrier to treat Voter 1 as complete before launcher-owned output completion is stable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Wait barrier ignores non-zero DONE exit codes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `dispatch-code-voters.sh` logs wait results but still classifies voters from non-empty `.txt` files, so a voter that exits non-zero while leaving parseable output can be tallied as valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Sentinel timeouts can degrade quorum even when voters finish shortly after
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Sentinel wait timeouts are non-blocking; slow `.done` creation can mark external voters failed and force degraded quorum or main-agent-vote-required even if votes complete shortly after the timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: `VOTER_2_STATUS=skipped` branch is unreachable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `dispatch-code-voters.sh` checks for `VOTER_2_STATUS=skipped` but never assigns that value, so future skipped wiring could be misclassified as failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Parse-rate retry lacks a second completion barrier
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parse-rate retry happens after the initial wait; if retries later become asynchronous, replacement voter output could reintroduce tally-before-complete behavior for retry paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Wait helper usage-error branch lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `_wait_rc!=0` branch in `dispatch-code-voters.sh` is not tested, so invalid wait helper usage or configuration errors could lose the expected `larch_err` diagnostic contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Production comments use stale panel finding IDs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Production comments in `dispatch-code-voters.sh` reference `FINDING_*` panel IDs that can become misleading after review rounds close.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: Progress stderr contract is under-documented and under-audited
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` progress and timeout messages now go to stderr, but documentation and caller coverage may not fully describe or protect that stdout/stderr split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Cursor control documentation overstates stdin coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-external-agent.md` describes Cursor control as verifying non-Codex stdin behavior even though current coverage only checks metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Dispatch voter coverage labels do not match plan finding IDs
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-dispatch-code-voters.md` mis-maps plan `FINDING_3` and `FINDING_4`, reducing traceability from panel findings to tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Empty failure sidecars remain ambiguous
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `launch-review.sh` writes sidecar ok markers only for success; failed runs with empty stderr can leave a 0-byte sidecar that is hard to distinguish from a successful no-stderr run by sidecar inspection alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Plan voter path lacks `.done` barrier
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-voters.sh` has no equivalent voter `.done` barrier, leaving the same tally-before-complete class possible in the plan-review path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Branch bundles unrelated script/test changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch combines unrelated `#3007` script/test changes with the `#2973` voter fix, making review and revert isolation harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Waterfall launcher also backfills missing `.done`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `dispatch-with-waterfall.sh` has a pre-existing missing-`.done` backfill pattern that may share the premature-sentinel failure class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Test hook env leakage can leave arbitrary source enabled
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `LARCH_ALLOW_TEST_HOOKS` plus `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` source hook can execute attacker-controlled code if those env vars leak into voter launch paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Degraded quorum on sentinel timeout is an availability tradeoff
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The wait intentionally proceeds after sentinel timeout, allowing tally with fewer judges; this is an availability/correctness tradeoff rather than a direct security flaw.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Breadcrumb monitor can exit before review-and-fix finishes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` can still let the orchestrator misread Step 5 completion and trigger redundant follow-up work while `review-and-fix` continues in the background.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Lint-fix Codex path may misalign stall detection with events stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The lint-fix Codex path no longer uses `--capture-stdout` on `run-external-agent`, so wrapper stall detection may warn about an empty `codex.log` while events are written elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
