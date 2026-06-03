### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: ci-wait.sh defaults missing CONFLICTED to false
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `scripts/ci-wait.sh:216-221`, a missing `CONFLICTED` line defaults to false. Partial upgrade (old `ci-status` without `CONFLICTED`) with pass+behind>0 and a `DIRTY` PR can loop merge then `main_advanced` until caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No dedicated CLEAN mergeStateStatus test in test-ci-status.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ci-status.sh:70-88` has no dedicated `CLEAN` `mergeStateStatus` / `CONFLICTED=false` test case per the plan test list. Regression in `CLEAN` classification could slip through because only default-stub pending cases assert `CONFLICTED=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated CONFLICTED classification without bash/Python parity test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `CONFLICTED` classification is duplicated across `scripts/ci-status.sh:201-206` and `python/ci_monitor.py:110-120` with no cross-language parity test. A new `mergeStateStatus` value handled differently in bash vs Python can cause merge/rebase loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicate BEHIND merge test mocks across Python test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/test_merge.py` and `python/test_merge_bash_parity.py` duplicate BEHIND merge test mocks. Fixing stub behavior requires two edits and risks skew.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Monitor driver fixtures omit mergeStateStatus default
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Monitor driver fixtures in `python/test_ci_monitor.py:1469-1525` omit `mergeStateStatus`, defaulting to conflicted=true. Future pass+behind tests on those fixtures would expect merge but get rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: BEHIND recovery tests use pending CI only, not passing CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: G4/G6/Q2 `BEHIND` recovery cases in `scripts/test-merge-pr.sh` use pending CI only, while `test-merge-pr.md` documents green CI → `admin_merged`. Post-`UNKNOWN` `BEHIND` recovery with passing CI could regress to `ci_not_ready` or `main_advanced` without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

