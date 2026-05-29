### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: Update run-log docs for quiet-log-only sourcing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `docs/run-logs.md` still describes live NDJSON stream files under session `breadcrumbs/`, but Stage 2 diagnostics now come from session-root quiet logs with operator-visible stderr via `larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Clarify interim breadcrumb monitor role
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Family-B background+monitor pairing remains mandatory by lint, but after callsite migration the monitor no longer receives `larch:bc` records and mostly waits for the sentinel. This creates an idle mandatory stack with little live-progress value until Piece 3 removes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Add quiet-active integration coverage for larch_err mirroring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Major Family-B harnesses run with `LARCH_QUIET_DISABLE=1`, so they do not exercise quiet-active `larch_err` mirroring into `larch-quiet-*.log` files that publication commits. A quiet-mode mirroring regression could pass those tests while real `/implement` run logs miss operator diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: Add inherited invalid breadcrumb FD coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The planned `emit_breadcrumb` assertion update is comment-only, so there is no behavioral test pin for stale `LARCH_QUIET_BREADCRUMB_FD`. An invalid inherited FD could regress into early `larch_err` failure without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Quiet-log publication broadens committed stderr capture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Quiet-log-only publication can stage full session quiet logs plus `larch_err`-mirrored lines, not capped ndjson breadcrumb records. This may commit broader stderr captures than the old 1KiB breadcrumb stream and increases reliance on redaction discipline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Warn or error on invalid breadcrumb source hint
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If `LARCH_BREADCRUMB_SOURCE_DIR` points outside allowed session tmpdirs, publication returns success without breadcrumbs. A misconfiguration can make commits appear successful while omitting expected breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

