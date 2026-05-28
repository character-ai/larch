### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: render-plan-review-prompt rejects not-yet-created allowlisted tmpdirs before shared validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` gates allowlist validation behind `! -d`, so valid allowlisted session paths that do not exist yet receive a generic directory error instead of the shared allowlist diagnostic used by peer scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: design-pause-save reports missing tmpdir before allowlist violation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-save.sh` checks `-d` before `larch_design_tmpdir_validate`, so a non-existent disallowed path reports `tmpdir-missing` instead of `tmpdir-invalid`, obscuring the configuration error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Missing contract-level negative harnesses for tmpdir validator wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI only covers the shared tmpdir validation library, not contract-preserving negative paths in individual consumers. Future edits could break rc/KV/stdout mappings for allowlist failures without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: finalize-plan uses the same status for allowlist failure and missing directory
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/finalize-plan.sh` maps allowlist rejection to `FINALIZE_PLAN_STATUS=missing-design-tmpdir`, the same token used for missing directories, making operator telemetry and tests ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Harnesses lack allowlist failure coverage for plan review and waterfall paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-plan-review-loop.sh` and `test-revise-plan-with-waterfall.sh` use `mktemp` under `TMPDIR` only, so new allowlist failure behavior is not exercised in those harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

