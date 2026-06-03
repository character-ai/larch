### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: --timeout argv forwarding untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Timeout forwarding to `assess-plan-round.sh` could break without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: One test passing --timeout and asserting stub argv


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: LARCH_*_SH overrides allow arbitrary script execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_SNAPSHOT_PLAN_ROUND_SH` / `LARCH_ASSESS_PLAN_ROUND_SH` let the orchestrator shell substitute scripts; malicious exports before `/design` could exec attacker-controlled code with design tmpdir access.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document harness-only use; optionally require child paths under PLUGIN_ROOT.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: WARN= lines replay verbatim to LLM chat
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `WARN=` lines from a writable result env replay verbatim into orchestrator context without bounds; crafted WARN in env could inject instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Normalize/truncate WARN replay or only trust WARN from same-run stdout.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: stderr merged into assess/snapshot capture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Merging stderr into assess/snapshot capture can pollute KV parsing; spurious `ASSESSOR_STATUS=` on stderr could mis-set routing variables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Capture stdout only or parse contract stream separately.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate KV/json helpers vs design-postplan-emit
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `json_scalar_or_sed` and `parse_kv_from_output` duplicate `design-postplan-emit.sh`; future edits may update one driver and not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move helpers to lib-phase-driver.sh and source from both drivers.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Non-HARD runs always spawn assessor driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Non-HARD runs print the skip breadcrumb then always invoke `design-plan-quality-assessor.sh`, adding an extra subprocess on every SIMPLE design run even when unified KV write is not required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional early skip without driver invoke if unified KV write is not required.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: WORSE gate may use non-numeric EFFECTIVE_ASSESSORS in bash test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: WORSE gate prose implies numeric comparison; corrupt `EFFECTIVE_ASSESSORS=unknown` in env could break if copied into bash `[[ -ge 1 ]]` or mis-route the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use orchestrator judgment only or add explicit numeric guard before AskUserQuestion.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

