### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Align PID-capture window documentation with lint behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `BASH_AUTHORING.md` describes the PID-capture placement more strictly than the linter enforces. Authors may believe a third non-blank line capture is invalid even though lint accepts it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Document or harden test-only kill-by-PID-file pattern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The fake monitor test harness kills a process using an unvalidated PID read from a paired PID file. Although harness-only, it resembles an unsafe pattern unless explicitly scoped or validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_6: Monitor failure branch may leave writer running
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The documented monitor-failure branch uses non-blocking wait without signaling the writer when `monitor_rc=2`. A monitor argv failure can leave `ship-pr.sh` running and race later invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Make wrapper exit authoritative over stale status file reads
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 8+ routing can read a stale successful `LARCH_STATUS_FILE` value before the writer’s final exit. If the wrapper later exits nonzero, bail or conflict routing may be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

