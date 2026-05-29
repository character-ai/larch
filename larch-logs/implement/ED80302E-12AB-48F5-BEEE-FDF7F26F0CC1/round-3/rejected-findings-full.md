### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Planned `emit_breadcrumb` grep acceptance is not enforced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan’s acceptance check for zero `.sh` `emit_breadcrumb` callsites is not pinned in CI or Makefile lint, so a reintroduced callsite could ship until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Family-B live diagnostics bypass prior monitor redaction path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Migrated Family-B progress now uses `larch_err`/FD4 while `breadcrumb-monitor` redaction only applied to `larch:bc` stream records, so live operator transcript diagnostics may no longer receive the same per-line filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Collect-agent retry diagnostics now expose artifact basenames live
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/collect-agent-results.sh` moved retry breadcrumbs to `larch_err`/FD4, making namespace retry artifact basenames visible in the operator transcript where they previously stayed in the quiet breadcrumb channel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Published quiet-log forensics omit migrated `larch_err` progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-larch-log.sh` quiet-log-only publication cannot stage progress emitted via `larch_err`, so committed breadcrumb forensics may lack ship-pr/ci-wait progress that no longer enters quiet logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Branch mixes Stage 2 breadcrumb work with unrelated Gate B/version/run-log changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch appears to combine Stage 2 breadcrumb migration with #2667 Gate B documentation, version/changelog updates, and run-log flushes, making PR review, traceability, and bisecting less clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Rebase checkpoint probe exports dead quiet breadcrumb env
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-rebase-checkpoint-probe.sh` still exports inert `LARCH_QUIET_BREADCRUMBS=1`, which can mislead maintainers about how breadcrumb assertions are surfaced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Review-and-fix tests rely on inert quiet breadcrumb env plus outer stderr capture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` sets inert `LARCH_QUIET_BREADCRUMBS=1`; the tests actually depend on outer `2>&1` capture before quiet init, making future failures confusing if capture changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

