### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Self-declared trailers downgrade diff gating without repo verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `mechanical_churn` and `diff_added` trailers can downgrade or replace diff hard gating without verification against actual repo churn. A plan or issue body can end with `mechanical_churn: true` and low `diff_added` while `diff_lines` stays above legacy thresholds; Step 2b.5 and `plan-review-loop` may proceed without Split/Cancel for very large stated churn. Trailers should be documented as unverified assertions; do not rely on this gate alone for safety limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Missing script-md sibling / shebang inconsistency for shared trailer library
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `lib-plan-optional-trailers.sh` is sourced-only but carries a shebang while peer libs (e.g. `lib-findings-classification.sh`) do not, and there is no `lib-plan-optional-trailers.md` co-located stub per the repo `script-md-siblings` contract. Contributors editing trailer grammar may miss documented invariants and downstream callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Dead code `snapshot_optional_trailer_values`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `snapshot_optional_trailer_values` in `lib-plan-optional-trailers.sh` is unused. Future edits may assume trailer values are snapshotted for validation when only keys are checked today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Redundant subshell churn parsing awk four-line output
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check-plan-size.sh` uses four `sed` calls to parse one awk multi-line result on every Step 2b.5 invocation instead of a single `read`/`mapfile` pass over the four-line block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

