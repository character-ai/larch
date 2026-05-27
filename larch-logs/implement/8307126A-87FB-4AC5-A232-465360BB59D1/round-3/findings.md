### FINDING_1: Missing real launcher delayed-.done regression
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Delayed `.done` race coverage relies on stub or alternate fixtures instead of a real `launch-review` hook path, so production Codex `.inner.done` to `.done` promotion could regress while current tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Production comments lack issue references
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Production comments reference panel `FINDING_*` IDs instead of durable issue references, making the rationale hard to trace later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Empty-sidecar marker logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Codex and Cursor branches duplicate empty-sidecar marker blocks, creating drift risk if one guard or message changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Wait/TIMEOUT parsing is duplicated across callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `wait-for-reviewers` and `TIMEOUT` parsing logic is duplicated with different failure policies, risking inconsistent updates when the wait contract changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Voter 1 backfill can mask missing or timed-out sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-wait synthetic Voter 1 `.done` backfill can make a slot look healthy when the launcher sentinel is missing or timed out but output is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] run-external-agent stderr progress contract is undocumented
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Progress diagnostics moved to stderr without a matching `run-external-agent.md` contract update, so future callers may mis-handle stdout/stderr expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Branch mixes unrelated concerns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch appears to mix the #2973 voter fix with unrelated telemetry, parser, validation, and log changes, making review, bisect, and revert harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] skipped voter status is documented but not produced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `VOTER_2_STATUS=skipped` is documented or handled, but the waterfall path does not produce it, leaving dead or untested conditional behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Parse-rate retries backfill .done outside the new barrier
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Parse-rate retry relaunches still backfill `${retry_output}.done` immediately after synchronous relaunch instead of using the new voter wait-barrier pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Direct Codex call sites bypass stdin guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Some scripts invoke `codex exec` directly rather than through `run-external-agent.sh`, so they do not inherit the new `< /dev/null` spawn-layer guard if later backgrounded without prompt-file redirection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Cursor stdin regression test is insufficient
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cursor stdin coverage only checks that stdout does not mention `/dev/null`, not that the wrapper temp-file stdin is actually inherited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Delayed-sentinel tests rely on wall-clock seconds
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Wall-clock second thresholds in delayed-sentinel tests can flake on loaded CI or give false confidence when dispatch returns within the same second.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Missing Step 5 integration test for voter barrier
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no `review-and-fix` Step 5 integration test proving the voter `.done` barrier prevents premature tally behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: test-harnesses-3 may exceed shard budget
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The happy section of `test-dispatch-code-voters` gained many sub-cases and may push `test-harnesses-3` beyond CI shard timing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: test-launch-review coverage list is malformed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-review.md` has malformed coverage bullets after sidecar-marker entries, making tested behaviors harder to read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Initial launches inherit gated test-hook environment
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Initial voter/reviewer launches via `dispatch-with-waterfall.sh` may inherit `LARCH_ALLOW_TEST_HOOKS` and `LARCH_TEST_TRAP_*` from the parent environment, unlike retry relaunches that strip them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Negotiation events JSONL may persist sensitive content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Negotiation Codex `--json` streams can contain prompts and tool output on disk beside response files until session tmpdir cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Test harness uses awk plus eval
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` extracts a function body with `awk` and `eval`; it is test-only but still avoidable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Voter 2/3 status ignores .done exit codes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-barrier Voter 2/3 status checks use only non-empty `.txt` output, so non-zero launcher exits with non-empty output can still appear launched until later parse-rate handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] breadcrumb-monitor early exit remains unresolved
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` can still let the orchestrator misread Step 5 status while `review-and-fix` continues in the background.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: test-dispatch-code-voters coverage bullets are too compressed
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-dispatch-code-voters.md` merges three planned #2973 coverage cases into one paragraph, making acceptance criteria harder to verify item by item.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
