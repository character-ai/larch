### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: `_resume_plan` is too dense and mixes routing stages
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_resume_plan` is a large mixed-responsibility function covering validation, GitHub routing, gh-skipped routing, and precedence decisions, making future routing changes regression-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Terminal state writes collapse non-OK phases to generic stalled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_write_terminal_state` loses specific stall-step granularity by collapsing non-OK phases to `stalled`, which may confuse resume routing or diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: `_materialize_manifest_oos` can clobber persisted counters
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: `_materialize_manifest_oos()` writes ship state without threading counter kwargs, so an OOS materialization write can reset counters to zero mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `_write_ship_state` drops `CONFLICT_FILES` on routine rewrites
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Routine full-file ship-state rewrites preserve some handoff fields but not `CONFLICT_FILES`, so conflict metadata can be lost after a pre-push handoff marker is bypassed or cleared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: State-hydrated durable flags can force gh-skipped routing
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: Durable flags read from state can disable GitHub ground-truth checks and route through gh-skipped local-state classification without caller/context agreement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Iteration-cap stall handling is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The CI loop has repeated iteration-cap stall blocks, increasing the chance that future cap-order fixes update only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Boolean state parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_state_bool_text` duplicates boolean parsing already present in `run_logs`, risking divergent handling of persisted flags over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1

