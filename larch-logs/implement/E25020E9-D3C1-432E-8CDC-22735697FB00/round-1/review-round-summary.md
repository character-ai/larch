# Review Round 1

- Mode: `diff`
- 11 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Per-step completion sentinels are not written at step boundaries
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.completed/step-*` sentinels are documented only in a shared/reference Bash fence instead of being written at each step’s terminal success boundary. A live `/design` run therefore cannot persist accurate pause/resume progress, and `design-pause-save.sh` may record the wrong next step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Pause-state redaction lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The planned pause-state redaction case is not asserted. Sensitive values could be written into issue marker payloads without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Pause marker is not bound to issue identity
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The pause marker does not bind the `RUN_ID` snapshot to the issue number or repo. An edited issue body could point at another run’s design log, causing restore of the wrong state and skipped gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_15: Marker deletion failure leaves ambiguous restored state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` deletes the marker after successful restore. If deletion fails, the tmpdir is already restored but the marker remains, creating an ambiguous retry state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Empty pause publish can create unusable marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` can report `PUBLISH_OK=true` with a pause marker when porcelain is empty. Resume may then fail because no snapshot artifact exists on the default branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: README command catalog uses `/pause` instead of `/larch:pause`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `README.md` lists `/pause` while plan acceptance wording refers to `/larch:pause`, creating a minor catalog mismatch unless aliasing is documented there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Registry walk incorrectly skips Step 0c
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` skips all step ids matching `0*`, which excludes `0c` even though it is present in the registry. A pause during Step 0c can record `STEP=1c`, causing resume to skip scan work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Planned pause/resume harness cases are missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-pause-resume.sh` does not implement several planned cases, including multi-cycle idempotency, multi-sentinel registry order/staging, and `ISSUE_NUMBER` refresh. Repeat pause/resume and env-refresh regressions may ship without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Structure test only greps sentinel text globally
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `assert_step_completion_sentinels` passes when sentinel writes appear anywhere in `SKILL.md`, including a reference block. CI can pass even when production step sections do not write sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Missing absent-delete coverage for named block writer
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The pause/resume harness lacks coverage for `named-block-write --delete` on an absent marker. Delete-on-absent `MODE=absent-noop` semantics could regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Pause commit subject assertion checks source instead of runtime commit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-log-publish.sh` verifies the pause commit subject by grepping script source rather than inspecting `git log`, so runtime commit messages could drift while the test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


