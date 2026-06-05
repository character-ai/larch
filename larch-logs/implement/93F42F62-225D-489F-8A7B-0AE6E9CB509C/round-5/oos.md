### FINDING_12: [OUT_OF_SCOPE] Run-log flush commit is intentional artifact
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The `larch-logs` flush commit is surfaced as an intentional run-log artifact and not a pause/resume plan violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] Ship iteration cap guard is unreachable dead code
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: nit
- **Concern**: A post-monitor `iteration > SHIP_MERGE_LOOP_MAX_ITERATIONS` guard appears unreachable because the same check already occurs before monitoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] SECURITY symlink wording may be stale
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` is reported as still claiming the loader rejects extracted symlinks, while the new restore path writes blob bytes and does not materialize git symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] SECURITY symlink doc change is characterized as non-regression
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: nit
- **Concern**: The pause/resume symlink behavior is described as a documentation-alignment point rather than a symlink-extraction regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Collaborator-editable pause markers remain residual risk
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: latent
- **Concern**: Collaborator-editable `larch:design-pause` markers can still redirect resume to another snapshot for the same issue; WI3 does not change that documented residual risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] Unknown resume fields are silently cleared
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: nit
- **Concern**: Unknown `RESUME_PHASE` and `CALLER_KIND` values read from disk are silently cleared on write, which is conservative but may mask corrupt state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Body-drift marker lifecycle docs may mislead
- **Reviewer(s)**: dyn-route-contract-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.md` body-drift wording predates delete-on-success behavior and may mislead operators about whether successful loads clear the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-route-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] Simultaneous WARN propagation through route is unverified
- **Reviewer(s)**: dyn-route-contract-output.txt
- **Severity**: nit
- **Concern**: End-to-end propagation of simultaneous `WARN=body-drift` and `WARN=marker-delete-failed` through `design-route.sh` is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-route-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Corrupt resume counter tests diverge from bash behavior
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: Python tests codify silent coercion of corrupt resume counters without comparing behavior against bash `ship-pr.sh` arithmetic on similar state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] Ship resume tests rely on monkeypatches instead of gh fixtures
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: New ship resume tests use heavy monkeypatching rather than parsed `gh` CLI JSON fixtures, so real CLI serde drift would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Unrelated Python ship changes are bundled with pause/resume fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes large `python/ship.py`/run-log changes unrelated to the stated pause/resume plan, increasing review, bisect, and revert complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Marker-delete failure hides stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear_pause_marker` reports `WARN=marker-delete-failed` without surfacing actionable delete failure details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

