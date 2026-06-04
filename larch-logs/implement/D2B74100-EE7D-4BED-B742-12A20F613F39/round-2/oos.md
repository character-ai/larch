### FINDING_11: [OUT_OF_SCOPE] write-design-current-env uses weaker REPO validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `scripts/write-design-current-env.sh` validates `REPO` with a looser regex than stricter repo validators elsewhere. A future or direct caller could persist a repo value later rejected or mishandled by stricter paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-repo-routing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Auto-resolved REPO is not revalidated
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-routing-output.txt, dyn-shell-parsing-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` validates explicit `--repo` values but does not re-run the strict validator after resolving `REPO` through `resolve-repo.sh` or `gh repo view`, leaving inconsistent fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-repo-routing-output.txt, dyn-shell-parsing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] design-publish omits --repo when writing the plan block
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-routing-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` resolves and forwards `REPO` to several helpers but not to `plan-block-write.sh`. Non-default repo runs can write the plan block to a different repository than the rest of the publish flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-repo-routing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] pause-state is written before publish outcome is known
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-save.sh` writes `pause-state.txt` before confirming publish success or validated recovery, so failed publish without recovery can leave a stray local pause-state file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] Final-summary outcome enum omits publish-skipped
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: nit
- **Concern**: The Step 0b final-summary block documents `failed-publish` but not `publish-skipped`; current runtime paths may not hit this, but the enum is drifting from the broader outcome surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] postplan helper repo routing relies on prior source-env persistence
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: Some `design-postplan-emit.sh` invocations omit explicit `--repo` and rely on resolving from `source-env.sh`, coupling postplan behavior to successful earlier init-runparams persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] failed-plan-write can still show a run-log pointer
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: Pre-existing behavior in `render-final-summary.sh` can synthesize a `larch-logs/design/<RUN_ID>/` pointer for `failed-plan-write` even though publish never completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Primary and fallback publish notes differ in placement
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: For `publish-skipped` and `failed-publish`, primary and degraded fallback render paths both include the note, but place it in different positions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] Missing publish envelope ignores possible recovery branch
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: latent
- **Concern**: Pre-existing pause-save behavior returns `ERROR=publish-failed` when publish exits non-zero without a `PUBLISH_OK` line and does not inspect `RECOVERY_BRANCH`; reviewers note this is theoretical because current publisher emits the expected envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Recovery path logs Tool Failure even when pause is resumable
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: Pre-existing failed-publish recovery appends a Tool Failures entry even when valid recovery yields `PAUSE_OK=true`, which can make logs look harder-failed than the actual resumable state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] Local recovery branch shape lacks test coverage
- **Reviewer(s)**: dyn-pause-recovery-output.txt
- **Severity**: nit
- **Concern**: Existing pause/resume tests cover remote recovery branch shape but not the local `larch-log-design-recovery-<RUN_ID>` branch shape for non-zero publish with `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-recovery-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_32: [OUT_OF_SCOPE] Custom publish implementation trust boundary remains broad
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DESIGN_LOG_PUBLISH` can substitute the publish implementation. That pre-existing trust boundary limits how much contradictory-envelope handling can protect against hostile custom publisher stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] Branch hardening is directionally sound
- **Reviewer(s)**: dyn-shell-parsing-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that the branch’s new validation, argv precedence, awk-only repo resolution, and repo forwarding are directionally sound; remaining issues are mostly inconsistent hardening rather than missing validation at the new entry points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parsing-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

