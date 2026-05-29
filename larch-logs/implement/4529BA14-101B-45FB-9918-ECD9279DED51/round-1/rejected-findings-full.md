### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: explicit empty reviewer flag can be overwritten by recovery
- **Reviewer(s)**: dyn-recovery-semantics-output.txt
- **Severity**: latent
- **Concern**: Recovery checks whether the variable value is empty rather than whether the corresponding flag was omitted. Because `validate_bool` accepts empty values, an explicit `--codex-present ""` can be repopulated from the prior file, contradicting the documented contract that explicit flags override recovered values. The source says documented `/design` callers do not hit this, making it manual/custom-caller reachable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-recovery-semantics-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Case 14 test lacks strict unset detection and symmetric coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Case 14 in `skills/design/scripts/test-write-design-current-env.sh` omits `set -u`, unlike Case 13, so missing exports might not fail the harness. One reviewer also notes missing symmetric cursor-only partial mirror coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_4: missing test for no-prior-output refresh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No harness case covers recovery when `--output` does not yet exist. First-write no-flag refresh behavior is therefore not pinned, making regressions in the missing-file guard harder to catch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: no-flag recovery preserves mismatched alias pairs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: During no-flag refresh, prior mismatched `PRESENT` and `AVAILABLE` values can be preserved independently because partial CLI mirroring does not run. The source suggests either documenting byte-preserving recovery or adding post-recovery pair sync when neither side was explicitly set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

