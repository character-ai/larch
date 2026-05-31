### FINDING_6: plan-review-loop.sh collector/FIFO change outside extract scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` collector stderr FIFO / early-return changes are outside the stated Step 3 driver extract-only scope, expanding PR blast radius and coupling unrelated collector behavior to the driver refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Revert here or split to a dedicated PR with its own harness justification
  - From cursor-specialist-plan-fidelity-output.txt: Split the collector change to its own PR or update the plan/acceptance to document and test it explicitly.



### FINDING_8: Harness gaps for collector hard-fail / FIFO cleanup path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-fifo-rc-propagation-output.txt
- **Severity**: latent
- **Concern**: New collector stderr/FIFO and `collect_rc` early-return paths lack failure-path tests (non-zero collect exit, fifo removal, `LOOP_STATUS` / round-summary propagation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub collect exit 2; assert loop rc and skipped downstream steps.
  - From dyn-fifo-rc-propagation-output.txt: Add a case with a stub collector that `exit 1` before emitting records; assert `LOOP_STATUS=panel-failed`, absence of the fifo file, and (if preserving new semantics) that `run-step3-review` / round-count behavior matches the documented contract.



