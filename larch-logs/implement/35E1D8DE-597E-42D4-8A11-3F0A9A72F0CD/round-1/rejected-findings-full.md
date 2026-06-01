### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `decide` parity table missing merge-past-cap rows
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Parametrize table lacks merge-past-cap rows for `rebase_count` and `fix_attempts`. Wrong ordering of safety limits could bail on pass+up-to-date when only rebase/fix caps exceeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Parametrize pass/behind=0 with rebase_count=20 and fix_attempts=10 expecting merge.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: In-progress deferral test lacks per-outer log refresh assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Existing in_progress deferral test does not assert per-outer log refresh call count. Stale logs across outers might not be caught if `evaluate_failure` reuses one `collect_failed_logs` result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert gh run view --log-failed call count equals outer attempts.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Duplicate redact unit test overlaps `collect_failed_logs` redaction test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Duplicate redact unit test adds maintenance noise only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Remove or merge duplicate test.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

