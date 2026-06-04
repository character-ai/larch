### FINDING_10: design-publish exports metadata from contradictory failed publish output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-publish.sh` can retain parsed PR/recovery metadata after a non-zero publish exit whose stdout contradicted the exit status with `PUBLISH_OK=true`, causing failed-publish notes to cite untrusted PR or branch data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Clarify route does not persist or forward REPO consistently
- **Reviewer(s)**: dyn-repo-routing-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify handling can run GitHub helpers before resolving `REPO`, does not persist `REPO` on clarify-only routes, and omits explicit `--repo` forwarding on several clarify helpers. Non-default repo clarify runs can target the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-routing-output.txt: Address the concern above.


### FINDING_2: Pause save accepts repo values that pause load rejects
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` uses weaker repo validation than `scripts/design-pause-load.sh`, so a pause can appear to succeed but fail on resume when the persisted repo is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_29: pause-save sources source-env.sh before validation
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` sources `$DESIGN_TMPDIR/source-env.sh` before adopting and validating argv `REPO`. If a session tmpdir is tampered with, arbitrary shell in `source-env.sh` can execute before repo grammar checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.


### FINDING_3: publish-skipped can still synthesize a run-log path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-final-summary.sh` excludes `failed-publish` from `RUN_LOGS_PATH` synthesis but not `publish-skipped`. With `OUTCOME=publish-skipped` and a real session/run id, the driver can pass a concrete run-log path to `render-run-summary.sh`, bypassing the downstream `N/A` guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_31: Failed-publish PR and recovery metadata are not allowlisted before summaries
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` and `render-final-summary.sh` propagate `PR_URL` and `RECOVERY_BRANCH` from publish stdout into operator-facing summaries without URL scheme, GitHub pull URL, or branch-slug validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.


### FINDING_6: Structural assertion labels are reused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` reuses assertion labels such as `(27)` and `(28)` for unrelated pins, making CI failures harder to triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: pause-save trusts recovery metadata from contradictory publish output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `scripts/design-pause-save.sh`, a non-zero publish exit with stdout claiming `PUBLISH_OK=true` is normalized to failure but can still retain `RECOVERY_BRANCH`, allowing `PAUSE_OK=true` and a resumable marker based on untrusted contradictory stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Clarify failed-publish summaries lose DESIGN_LOG recovery metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: Clarify Step 0b sets `DESIGN_LOG_*` after failed publish, but the final-summary Bash block does not export or persist those values before invoking `render-final-summary.sh`. Failed-publish summaries can omit recovery PR/branch bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt: Address the concern above.


