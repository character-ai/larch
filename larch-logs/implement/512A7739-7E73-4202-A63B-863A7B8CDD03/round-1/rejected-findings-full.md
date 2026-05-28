### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Explicit coder-unavailable tests miss quiet breadcrumb suppression assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Explicit coder-unavailable coverage does not assert coder breadcrumb suppression when `LARCH_QUIET_BREADCRUMBS=1`. A breadcrumb regression on bail could pass if other paths preserve the expected count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Cursor-first implicit routing widens default filesystem trust
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Reversing omitted-coder dispatch to Cursor-first means hosts with both tools now run Cursor with broader trust by default instead of Codex’s sandboxed default. The change needs to be documented as an explicit product decision, with operator guidance or warning if desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Session Setup subsection exceeds planned size budget
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Session Setup subsection is roughly 102-103 lines, exceeding the stated ~80 line target and slightly missing the acceptance budget. This makes Step 0 harder to scan and the budget is not structurally enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Coder harness labels and matrix drift from plan numbering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Coder tests use `B5-coder-*` labels instead of the planned `B11-B17` range, and the sibling markdown omits some cases. This weakens traceability between issue, plan, and harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: phase_coder_select re-reads unused tool presence keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `phase_coder_select` re-reads `CODEX_PRESENT` / `CURSOR_PRESENT` even though only `*_BINARY_FOUND` is needed for explicit-unavailable warnings, adding noise and diverging from reuse of phase-infra globals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

