### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Shared driver phase sentinel allowlist is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Driver phase sentinel basenames are duplicated across `design-log-publish.sh`, `design-driver.sh`, and tests. A future ACTION can re-break pause publish if the publisher allowlist is not updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Restore install failure can leave dirty tmpdir for retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A failed `cp -R` install can leave partial files in `DESIGN_TMPDIR`; because the marker remains for retry, a later load into the same tmpdir can merge fresh snapshot files with orphaned partial content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Ship state write validation omits persisted identity fields
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: `_validate_ship_state_value` does not validate fields like `REPO`, `ISSUE_NUMBER`, `RUN_ID`, and `PHASE` before persisting them, relying on later read-side checks instead of fail-closed write hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Gh-skipped local merge quorum can be satisfied only by state file values
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: Resume logic can treat `local_merged` as true using only persisted `PR_CLOSED` and `MERGE_RESULT`, allowing corrupt or tampered state to advance post-merge finalization without non-state-file corroboration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Ship state rewrites can drop `CONFLICT_FILES`
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state` preserves some disk fields but drops previously persisted `CONFLICT_FILES` unless passed again, weakening conflict handoff metadata across routine rewrites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Restore path lacks destination containment check
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` checks relative path segments but does not verify the computed `dest` remains under `$restore_tmp` before writing blobs and copying into `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Pause/resume harness git stub is monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `test-design-pause-resume.sh` has grown a large inline git stub and many scenario blocks, making contract changes hard to isolate and reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Git stub does not model commit-object extraction
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The git stub serves `ls-tree` and `show` from a mutable filesystem tree rather than a pinned commit object, so stub-backed tests can pass despite production ref/blob mismatches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Export-ignore regression test lacks archive negative control
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: The real-git export-ignore reproduction proves `ls-tree`/`show` succeeds but does not assert the old `git archive | tar` path fails or omits files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `.completed` enumeration pattern is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.completed` staging uses process-substitution enumeration while sibling loops use mktemp capture, increasing audit complexity for `set -e` safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Combined body-drift plus marker-delete-failed loader warning is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: There is no combined loader test for simultaneous `body-drift` and `marker-delete-failed`, so a regression dropping one WARN line could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Dual WARN stdout contract may be lossy for consumers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Separate `WARN=` lines for combined body drift and marker delete failure may cause single-WARN parsers to miss one condition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

