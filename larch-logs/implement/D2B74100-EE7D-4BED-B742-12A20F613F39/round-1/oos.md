### FINDING_13: [OUT_OF_SCOPE] Auto-resolved design-publish repo is not revalidated
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` validates argv `--repo`, but auto-resolved `REPO` from `gh`/`resolve-repo.sh` is used downstream without a second validation pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-binding-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Pause-save sources executable source-env before validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` sources `$DESIGN_TMPDIR/source-env.sh` before validating extracted fields, so a same-UID writer can execute shell and still provide syntactically valid repo/session values afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-binding-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Publish-skipped Step 5c completion can prevent resume retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-flow-output.txt
- **Severity**: latent
- **Concern**: Step 5c is marked complete when `SESSION_ID` is empty because that is treated as “publish did not fail,” so a publish-skipped run may not self-heal on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] Clarify and Gate C use different no-log-flush terminal outcomes
- **Reviewer(s)**: dyn-publish-flow-output.txt
- **Severity**: nit
- **Concern**: Clarify exits with `cancelled-clarify` when publish is skipped, while Gate C uses `publish-skipped`; this may confuse operators even if intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Positive coverage/implementation observation
- **Reviewer(s)**: dyn-publish-flow-output.txt, dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Reviewers observed that the main publish-flow implementation and harness coverage generally align with acceptance criteria for Gate C, fail-closed envelopes, skipped publish, and run-log suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-flow-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Plan block write omits explicit repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` invokes `plan-block-write.sh` without `--repo`, so plan writes can target the hub default while publish/rename paths use an explicit repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] write-design-current-env repo validation is weaker
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: nit
- **Concern**: `write-design-current-env.sh` uses regex-only repo validation that is slightly weaker than newer duplicated helpers, though the reviewer did not identify a functional bypass introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Primary and degraded fallback note ordering differs
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Recovery/skipped-publish note ordering still differs between primary and degraded fallback summaries; this predates the branch and is covered by separate assertions rather than byte parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Pause-save and pause-load repo validation mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Pause-save’s new repo validation is looser than pause-load’s `--*` rejection, leaving inconsistent pause-family validation for edge-case repo strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

