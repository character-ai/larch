### FINDING_1: Voter 2 skipped status can be overwritten as failed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The post-wait `VOTER_2_PATH` size check can overwrite an intentional `VOTER_2_STATUS=skipped` with `failed`, which would corrupt quorum and paths-file behavior if skipped voter-2 wiring is added or reached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Launcher-hook race regression test is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The dispatcher tests use stub-waterfall coverage but do not exercise the production `launch-review.sh` hook path with `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE`, so the inner `.done` promotion and final `.done` rename race could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Claude delayed-.done dispatcher race is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Voter 1 Claude delayed `.done` race is not covered at the dispatcher boundary, so the #2973-style tally-before-ready failure could recur without a failing regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Cursor stdin control test does not assert fd0 inheritance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Cursor control case only checks tool metadata, so an accidental non-Codex `< /dev/null` redirect could pass CI while breaking expected stdin inheritance for Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Timeout handling path is present but untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The wait-barrier timeout branch and `TIMEOUT` stdout parsing/logging path are not exercised, so timeout logging or degraded failed-status behavior could break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Delayed-barrier test relies on wall-clock timing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The delayed-barrier regression test uses elapsed wall-clock duration as proof that dispatch waited, which can flake under load or pass without proving sentinel ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Wait barrier may accept early .done without validating final output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The wait barrier keys on `.done` existence without also validating sentinel exit code and canonical non-empty output before treating a voter as launched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Timeout parsing duplicates collect-agent-results behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `dispatch-code-voters.sh` duplicates the timeout parsing pattern from `collect-agent-results.sh`, creating drift risk if wait-for-reviewers stdout changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: run-external-agent launch branches are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_launch_capture_stdout_only` has duplicated codex and non-codex branches, so future spawn-flag edits need to update near-identical lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Step 5b follow-up issue is not evidenced
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan acceptance step for filing an out-of-scope breadcrumb-monitor cascade follow-up is not evidenced, so the deferred monitor bug may ship without tracking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Test sibling doc omits planned coverage cross-references
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-dispatch-code-voters.md` does not list the relevant plan cases and cross-references, creating documentation drift from the test inventory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Voter 1 wait sentinel inclusion is confusing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Voter 1 is included in `wait_sentinels` despite being launched synchronously, which may imply it still has the same async race as later voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Branch bundles unrelated work
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch includes unrelated script, test, log, or version-bump changes alongside the voter-failure fix, widening review scope and obscuring the regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Red-on-main evidence for tests is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: There is no evidence that the new tests fail on pre-fix SHAs, so they may not prove the intended bugs are caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Test hook remains arbitrary same-user code execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_ALLOW_TEST_HOOKS=1` with a writable `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` still allows arbitrary code at the end of Cursor review launches within the same-user or poisoned-shell trust boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Sentinel timeout can pressure vote integrity
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If a same-user actor can delay `.done` creation beyond `LARCH_VOTER_WAIT_TIMEOUT`, dispatch continues with degraded quorum and main-agent adjudication, creating availability or vote-integrity pressure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Raw events JSONL exclusion should be preserved
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The documented allowlist behavior that keeps raw `*.events.jsonl` out of committed `larch-logs/` is a positive security control that future allowlist edits should preserve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Negotiation Codex path may still inherit prompt stdin
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Direct Codex execution in `run-negotiation-round.sh` does not use the `run-external-agent` stdin redirect contract, so background negotiation Codex can still encounter parent-exit stdin EOF.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Skipped voter status is referenced but not assigned
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `VOTER_2_STATUS=skipped` is referenced defensively but not currently assigned, leaving docs and implementation semantics misaligned until skipped wiring exists or the references are removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
