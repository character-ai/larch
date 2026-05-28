# Review Round 1

- Mode: `diff`
- 5 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: unresolved vars are suppressed in scoped pin checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: In `--changed-files` mode, unresolved `$VAR` targets can be skipped without `UNRESOLVED_VAR`, contradicting the documented contract and letting typoed or misconfigured pin assertions pass local `relevant-checks`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: relevant-checks does not test pin verifier failure propagation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The relevant-checks fixture covers pin verifier success but not verifier exit `1`, so a regression that drops `PINS_EXIT` propagation could allow pin defects to pass before `agent-lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: scoped verifier ignores changed pin-bearing test scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Scoped verification keys only on resolved target document paths, so commits that change only `scripts/test-*.sh` pin text can skip local pin checks until CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: relevant-checks does not assert pin phase accounting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Fixture 3f does not assert that the pin verifier increments `PHASES_RUN`, so phase accounting could regress without the existing fixture failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: read-only verifier assertion is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required `git diff --quiet` before/after assertion is absent, so CI would not catch a verifier regression that writes to the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


