### FINDING_1: Per-step completion sentinels are not written at step boundaries
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.completed/step-*` sentinels are documented only in a shared/reference Bash fence instead of being written at each step’s terminal success boundary. A live `/design` run therefore cannot persist accurate pause/resume progress, and `design-pause-save.sh` may record the wrong next step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_5: Repeat pause publish may fail on existing log branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Pause publish does not reliably reuse or base the worktree on an existing remote `larch-log-design` branch for the same `RUN_ID`. A second pause can fail despite the remote branch existing, and current tests do not cover the force-with-lease reuse path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: `.pause-requested` prelude is inert
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `.pause-requested` prelude appears throughout `skills/design/SKILL.md`, but no in-repo writer creates that sentinel after the synchronous `/larch:pause` behavior. The defensive pause path is dead noise unless a writer is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Named block writer allowlist conflicts with extensible marker contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `named-block-write.sh` rejects regex-valid marker names outside `plan|design-pause`, so future markers require code changes despite the documented extensible regex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_10: Pause-state redaction lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The planned pause-state redaction case is not asserted. Sensitive values could be written into issue marker payloads without a test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Plan-block wrapper path is not directly tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A low-risk wrapper argv regression in `plan-block-write.sh` would not be caught because the case skips the wrapper and exercises the underlying behavior directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Missing agent-lint harness exclusions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: New `test-design-pause-resume` paths lack peer harness exclusion comments in `agent-lint.toml`, which may cause future lint noise if global suppressions change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Final summary block lacks pause-check prelude
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The final summary Bash block lacks the pause-check prelude, making late `.pause-requested` deferral inconsistent with the Step 1c onward rule if that defensive path is intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_17: [OUT_OF_SCOPE] Admin-only squash merge limits publish success path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Environments without admin merge always use the recovery branch path for publish success. Reviewer marked this as pre-existing operator context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: README command catalog uses `/pause` instead of `/larch:pause`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `README.md` lists `/pause` while plan acceptance wording refers to `/larch:pause`, creating a minor catalog mismatch unless aliasing is documented there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
