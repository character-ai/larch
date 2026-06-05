### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `ls-remote` calls lack `--` separator
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Branch names are passed to `git ls-remote` without `--`, so branch refs beginning with `-` could be interpreted as options.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `finalize_postmerge_logs` alias can drift from actual post-flush path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `finalize_postmerge_logs` is a thin alias while merge/ship callers can bypass or mock lower-level helpers, so future ordering or recovery logic added to the named boundary may not affect actual postmerge flushing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `stage_and_push` is a multi-concern god function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `stage_and_push` combines rebase deferral, OID resolution, verification, pending-state handling, and push behavior, making bash boundary parity and isolated failure testing harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Teardown log flush conflates recovery failure with commit warning
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `_teardown_log_flush()` mutates or returns `recovery_ok=False` for best-effort larch-log commit failure, causing Python to drop stalled-run recovery metadata that bash still writes after commit warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

