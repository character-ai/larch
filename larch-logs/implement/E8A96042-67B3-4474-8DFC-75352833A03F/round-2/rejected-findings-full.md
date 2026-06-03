### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Missing absent pins for removed `_ib_*` helpers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: Structural tests do not forbid reintroducing `_ib_handle_bootstrap_exit2` or `_ib_kv_scan` helper definitions/calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Step 0 prose can be read as multiple bootstrap invocations
- **Reviewer(s)**: dyn-prompt-orchestration-output.txt
- **Severity**: latent
- **Concern**: Multiple imperative references to running `implement-bootstrap-invoke.sh --mode initial` can lead a literal agent to invoke bootstrap outside the single Step 0 owner block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestration-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Wrapper internal names still use stale `_ib_*` prefix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Wrapper-local helpers still use `_ib_*` names after SKILL-side helpers were removed, which can confuse future maintainers and searches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

