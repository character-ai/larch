### FINDING_1: Duplicate validate_repo implementations can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `validate_repo` is duplicated across multiple scripts. Future grammar or security-rule changes could be applied to only some copies, causing inconsistent repo acceptance across publish, pause, and post-plan paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Pause save accepts repo values that pause load rejects
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` uses weaker repo validation than `scripts/design-pause-load.sh`, so a pause can appear to succeed but fail on resume when the persisted repo is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: publish-skipped can still synthesize a run-log path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-final-summary.sh` excludes `failed-publish` from `RUN_LOGS_PATH` synthesis but not `publish-skipped`. With `OUTCOME=publish-skipped` and a real session/run id, the driver can pass a concrete run-log path to `render-run-summary.sh`, bypassing the downstream `N/A` guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_4: Clarify publish fail-closed handling is prompt-orchestrated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Clarify-only publish handling relies on prompt-side orchestration rather than the scripted `design-publish.sh` normalizer. Future orchestrator drift could again trust contradictory `PUBLISH_OK=true` output from a non-zero publish exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: publish-skipped note text is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.sh` duplicates the publish-skipped note in primary and fallback render paths, creating a small maintenance/desync risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Structural assertion labels are reused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` reuses assertion labels such as `(27)` and `(28)` for unrelated pins, making CI failures harder to triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: publish-skipped step-5c sentinel behavior is ambiguous
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 5c may be marked complete when publish is skipped because `SESSION_ID` is empty, causing resume to skip the publish tail. The contract should clarify whether skipped publish is intentionally terminal or whether retry should be possible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_10: design-publish exports metadata from contradictory failed publish output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-publish.sh` can retain parsed PR/recovery metadata after a non-zero publish exit whose stdout contradicted the exit status with `PUBLISH_OK=true`, causing failed-publish notes to cite untrusted PR or branch data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] write-design-current-env uses weaker REPO validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `scripts/write-design-current-env.sh` validates `REPO` with a looser regex than stricter repo validators elsewhere. A future or direct caller could persist a repo value later rejected or mishandled by stricter paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-repo-routing-output.txt: Address the concern above.

### FINDING_12: Failed-publish step-5c withholding lacks executable pause/resume coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The contract that failed publish should not write `.completed/step-5c` is only structurally pinned, not covered by an executable pause/resume harness. A regression could advance resume past Step 5c and prevent retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Auto-resolved REPO is not revalidated
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-routing-output.txt, dyn-shell-parsing-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` validates explicit `--repo` values but does not re-run the strict validator after resolving `REPO` through `resolve-repo.sh` or `gh repo view`, leaving inconsistent fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-repo-routing-output.txt, dyn-shell-parsing-output.txt: Address the concern above.

### FINDING_14: design-postplan-emit builds --repo exec arguments defensively weakly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/design-postplan-emit.sh` uses unquoted parameter expansion for `--repo`. Current validation mitigates this, but an argv array or explicit conditional exec would be safer if validation is ever bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] design-publish omits --repo when writing the plan block
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` resolves and forwards `REPO` to several helpers but not to `plan-block-write.sh`. Non-default repo runs can write the plan block to a different repository than the rest of the publish flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-repo-routing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] pause-state is written before publish outcome is known
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-save.sh` writes `pause-state.txt` before confirming publish success or validated recovery, so failed publish without recovery can leave a stray local pause-state file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Final-summary outcome enum omits publish-skipped
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: nit
- **Concern**: The Step 0b final-summary block documents `failed-publish` but not `publish-skipped`; current runtime paths may not hit this, but the enum is drifting from the broader outcome surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] postplan helper repo routing relies on prior source-env persistence
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: Some `design-postplan-emit.sh` invocations omit explicit `--repo` and rely on resolving from `source-env.sh`, coupling postplan behavior to successful earlier init-runparams persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_19: Clarify route does not persist or forward REPO consistently
- **Reviewer(s)**: dyn-repo-routing-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify handling can run GitHub helpers before resolving `REPO`, does not persist `REPO` on clarify-only routes, and omits explicit `--repo` forwarding on several clarify helpers. Non-default repo clarify runs can target the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-routing-output.txt: Address the concern above.

### FINDING_20: design-pause-load does not validate caller-supplied --repo
- **Reviewer(s)**: dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-load.sh` validates marker/restored repo values but not argv `--repo` before building `gh` arguments. Direct or future callers that bypass `design-route.sh` validation can pass malformed repo values to `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-routing-output.txt: Address the concern above.

### FINDING_21: render-run-summary documentation is split on publish-skipped
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-run-summary.md` lists `publish-skipped` in a later normative table but omits it from primary Usage/Output sections, creating a contract mismatch for downstream docs or tooling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] failed-plan-write can still show a run-log pointer
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior in `render-final-summary.sh` can synthesize a `larch-logs/design/<RUN_ID>/` pointer for `failed-plan-write` even though publish never completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Primary and fallback publish notes differ in placement
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: For `publish-skipped` and `failed-publish`, primary and degraded fallback render paths both include the note, but place it in different positions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_24: postplan pause aborts on invalid persisted REPO instead of returning pause-save envelope
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: important
- **Concern**: `_postplan_pause_checkpoint` validates repo before writing `POSTPLAN_EMIT_STATUS=paused` and before execing `design-pause-save.sh`. A malformed persisted repo exits as a postplan configuration error instead of delegating to pause-save’s structured `PAUSE_OK=false` / `ERROR=invalid-repo` response.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_25: pause-save logs only stderr for contradictory publish envelopes
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: When pause-save normalizes non-zero publish output that claimed `PUBLISH_OK=true`, it logs only stderr. If the misleading envelope was on stdout and stderr was empty, diagnostics omit the evidence that caused normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Missing publish envelope ignores possible recovery branch
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: Pre-existing pause-save behavior returns `ERROR=publish-failed` when publish exits non-zero without a `PUBLISH_OK` line and does not inspect `RECOVERY_BRANCH`; reviewers note this is theoretical because current publisher emits the expected envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Recovery path logs Tool Failure even when pause is resumable
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: Pre-existing failed-publish recovery appends a Tool Failures entry even when valid recovery yields `PAUSE_OK=true`, which can make logs look harder-failed than the actual resumable state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Local recovery branch shape lacks test coverage
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: Existing pause/resume tests cover remote recovery branch shape but not the local `larch-log-design-recovery-<RUN_ID>` branch shape for non-zero publish with `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.

### FINDING_29: pause-save sources source-env.sh before validation
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` sources `$DESIGN_TMPDIR/source-env.sh` before adopting and validating argv `REPO`. If a session tmpdir is tampered with, arbitrary shell in `source-env.sh` can execute before repo grammar checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.

### FINDING_30: pause-save can write unsanitized publish metadata into pause-state
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `scripts/design-pause-save.sh` parses publish stdout with simple `awk -F=` and writes `RECOVERY_BRANCH` into `pause-state.txt` without newline/CR or branch-slug validation, allowing corrupted or hostile publish output to inject extra state lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.

### FINDING_31: Failed-publish PR and recovery metadata are not allowlisted before summaries
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` and `render-final-summary.sh` propagate `PR_URL` and `RECOVERY_BRANCH` from publish stdout into operator-facing summaries without URL scheme, GitHub pull URL, or branch-slug validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Custom publish implementation trust boundary remains broad
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DESIGN_LOG_PUBLISH` can substitute the publish implementation. That pre-existing trust boundary limits how much contradictory-envelope handling can protect against hostile custom publisher stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Branch hardening is directionally sound
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that the branch’s new validation, argv precedence, awk-only repo resolution, and repo forwarding are directionally sound; remaining issues are mostly inconsistent hardening rather than missing validation at the new entry points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.
