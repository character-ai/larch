### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Pause publish loses recovery branch on log-branch worktree conflict
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `design-log-publish.sh` can fail with no `RECOVERY_BRANCH` when the log branch is checked out in another worktree, even if an existing remote branch could be reported for recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Marker deletion before route creates crash window
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After a successful load, the marker is deleted before the orchestrator routes to the restored step. A crash in that window removes the issue-body resume pointer, making later `/design` unable to resume from the issue alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Divergent repo resolution helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `named-block-write.sh` and pause helpers carry separate `resolve_repo` implementations, risking inconsistent repo fallback behavior between plan block writes and pause save/load.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: plan.txt validation is step-gated despite documented mandatory restore artifact
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` does not always require `plan.txt` for restored snapshots. Early or Step 2b resumes can report `LOAD_OK=true` without `plan.txt`, conflicting with the plan/harness expectation that missing restored artifacts fail or requiring explicit documentation of step-gated reconstruction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

