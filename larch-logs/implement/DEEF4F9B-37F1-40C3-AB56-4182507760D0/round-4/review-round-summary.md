# Review Round 4

- Mode: `diff`
- 4 accepted, 7 rejected (6 exonerated)

## Accepted Findings

### FINDING_12: Corrupt SIMPLE sessions can bypass repair or launch regular sketch work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-workflow-state-output.txt
- **Severity**: important
- **Concern**: SIMPLE routing is inconsistent when classification says SIMPLE but sentinel/marker package checks fail: prose can route directly to Step 2b or fall through to regular sketch launch before the Step 2a.5 repair block runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-workflow-state-output.txt: Address the concern above.


### FINDING_14: Step 2a.5 SIMPLE repair can clobber non-sentinel synthesis artifacts
- **Reviewer(s)**: dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: If `run-params.json` is corrupt or restored as SIMPLE for a session that already has real sketch synthesis, the Step 2a.5 repair branch can overwrite non-empty, non-sentinel artifacts before detecting the mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-compat-output.txt: Address the concern above.


### FINDING_3: Pause/resume tests miss the marker-only Step 2a.5 repair path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: Existing legacy SIMPLE pause fixtures exercise full artifact repair, but not the branch where valid SIMPLE artifacts and `step-2a` exist while only `step-2a.5` is missing; one reviewer also calls out the missing HARD negative case for the same sentinel layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-resume-compat-output.txt: Address the concern above.


### FINDING_8: Step 3b→Step 4 routing guard has coverage gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-guards-output.txt
- **Severity**: latent
- **Concern**: The structure guard can miss direct Step 3b→Step 4 prose because it does not catch Unicode-arrow forms and does not scan the Step 3.6 slice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-guards-output.txt: Address the concern above.


