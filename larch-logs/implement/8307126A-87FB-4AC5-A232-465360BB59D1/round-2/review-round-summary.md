# Review Round 2

- Mode: `diff`
- 8 accepted, 7 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Cursor stdin test does not assert fd0 inheritance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Cursor stdin control coverage only checks metadata and would not fail if Cursor were accidentally launched with fd 0 redirected to `/dev/null`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Wait helper usage-error branch lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `_wait_rc!=0` branch in `dispatch-code-voters.sh` is not tested, so invalid wait helper usage or configuration errors could lose the expected `larch_err` diagnostic contract.
- **Suggested revisions (informational for voters; coder decides)**:
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


