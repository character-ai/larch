### FINDING_2: Harness pin at `scripts/test-design-structure.sh:90` omits anti-halt and Gate C clauses
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The line ~90 `contains` pin for passive-summary non-blocking mode does not assert `do **not** halt the turn on the printed table` or Gate C single-decision-point prose from `approval-gates.md`. An edit could drop the anti-halt sentence while keeping the AskUserQuestion-removal substring; CI would still pass but orchestrators might halt on the multi-round table—the failure mode this feature targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add contains pins for do **not** halt the turn on the printed table and Gate C (Step 4b) is the single decision point
  - From cursor-specialist-testing-output.txt: Extend the line ~90 contains assertion (or add a second pin) to include do **not** halt the turn on the printed table and optionally Gate C (Step 4b) is the single decision point.
  - From cursor-specialist-edge-cases-output.txt: Add a contains assertion for do **not** halt the turn on the printed table.


