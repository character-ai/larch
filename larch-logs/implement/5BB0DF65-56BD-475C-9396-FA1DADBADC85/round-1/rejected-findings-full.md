### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: plan-voter subprocess spend is misattributed as review provenance
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `claude-plan-voter` / voter retry timing kinds fall through to review-style raw provenance, so plan-voter subprocess spend is counted in `claude_sub` but labeled as review spend.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: subprocess launcher deletes or fails to preserve the raw Claude JSON envelope
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After successful spawned Claude reviewer/scout runs, the ledger has `claude_sub` counts but the original `${OUTPUT}.json` envelope is removed, preventing audit of usage against the source envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: CI launcher deletes or fails to preserve the raw Claude JSON envelope
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: CI-fixer runs can record `claude_sub` usage while deleting the raw `.usage` source envelope, preventing operators from cross-checking ledger totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: terse token report uses raw `claude_sub` instead of display label
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The terse report path still emits raw `claude_sub` labeling rather than the locked display label `Claude (subprocess)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: ledger-vendor collision regression is reported missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: One reviewer reported that there is no regression fixture proving a ledger vendor named `claude` cannot overwrite transcript-derived `claude` totals in report JSON merge semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

