### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: OOS checkpoint carve-outs may miss Python state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Python runs may lack `ship-pr-state.sh`, so forked/repo-unavailable OOS checkpoint skips can fail unless helpers also read session/finalize state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: CI goto-rebase ignores rebase result
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The CI loop does not check `RebaseResult`, so failed or incomplete rebases can appear successful and spin until caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Session tmpdir allowlist logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` and `python/finalize.py` duplicate tmpdir root/session validation, so future edits can make ship accept paths that finalize refuses or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_35: Python teardown omits live bash Step 18 substeps
- **Reviewer(s)**: dyn-finalize-parity-output.txt
- **Severity**: important
- **Concern**: Planned Python teardown omits execution-issue safety net, manifest recovery, optional teardown log commit, background-process kill, and bash cleanup-tmpdir behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-finalize-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `run_ship` is too monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The large inline orchestrator in `python/ship.py` makes phase ordering and state-write regressions harder to review and maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Dead merge race-gate stub remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_version_race_gate` remains as a dead stub with linter suppressions, confusing the merge-path behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Legacy exit constants can confuse Outcome routing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Legacy `EXIT_BAIL` / `EXIT_STALL` constants coexist with the newer `OUTCOME_EXIT_MAP`, risking future semantic inversion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `flush_logs_post` mutates manifest inconsistently
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `flush_logs_post` duplicates `pr_number` across manifest fields and bypasses `update_manifest`, risking disagreement among manifest consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

