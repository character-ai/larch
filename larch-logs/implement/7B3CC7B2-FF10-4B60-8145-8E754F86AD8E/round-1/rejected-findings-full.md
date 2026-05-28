### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Severity precedence cross-reference points to a non-matching heading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A cross-reference names a `Severity precedence rule` heading that does not exist verbatim in `approval-gates.md`, making the intended rubric hard to find.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Structure tests under-pin severity fallback rubric text
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The #2667 structure test pins only part of the approval-gates severity fallback rubric. It does not cover whole-set Concern-text fallback language or invalid-severity fallback prose, so future edits could remove important Gate B documentation while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Loop-emitted Severity lines make Concern-text fallback effectively unreachable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `emit_finding` always writes a structured Severity line and defaults missing TSV severity to `nit`, so normal loop output uses H/M/L structured buckets rather than Concern-text C/H/M/L fallback. Operators may expect Concern-text classification for empty reviewer TSV severity, but that path generally requires a missing or invalid Severity line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Gate B prompt text acceptance criteria lack structure-test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The two Gate B AskUserQuestion question-text formats are acceptance criteria but are not pinned by the new structure tests. A future edit could remove or swap the structured H/M/L and Concern-text C/H/M/L prompt strings without failing the #2667 checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Env-var documentation parity is not protected across docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Env-var contracts are duplicated in `flags.md` and `configuration-and-permissions.md` without cross-doc structure pins, and docs-only `relevant-checks` may not run `test-design-structure`. A follow-up could change fail-closed exit-2 prose in one file but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

