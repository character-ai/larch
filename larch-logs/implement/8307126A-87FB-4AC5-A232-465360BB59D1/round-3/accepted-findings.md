### FINDING_1: Missing real launcher delayed-.done regression
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Delayed `.done` race coverage relies on stub or alternate fixtures instead of a real `launch-review` hook path, so production Codex `.inner.done` to `.done` promotion could regress while current tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Cursor stdin regression test is insufficient
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cursor stdin coverage only checks that stdout does not mention `/dev/null`, not that the wrapper temp-file stdin is actually inherited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: test-launch-review coverage list is malformed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-review.md` has malformed coverage bullets after sidecar-marker entries, making tested behaviors harder to read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Voter 2/3 status ignores .done exit codes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-barrier Voter 2/3 status checks use only non-empty `.txt` output, so non-zero launcher exits with non-empty output can still appear launched until later parse-rate handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Voter 1 backfill can mask missing or timed-out sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-wait synthetic Voter 1 `.done` backfill can make a slot look healthy when the launcher sentinel is missing or timed out but output is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


