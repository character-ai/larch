### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `check-plan-size.sh --plan-file` can read an arbitrary local path into metrics tooling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Optional `--plan-file` reads an arbitrary path with `awk`/`grep`; misuse could pull sensitive local files into the KV metrics path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Semantic soft estimate can re-offer soft UI across Gate B replans without harness coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A semantic soft estimate can remain true across plan rewrites so Split/Continue prompts may repeat after a single Continue, with no stated harness coverage for that loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: YES/EXONERATE voter framing duplicated across three prose locations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Long YES/EXONERATE voter framing is maintained in `scripts/dispatch-plan-voters.sh` and in `skills/design/references/plan-review.md` and `plan-review-quick.md`, so future edits risk updating only one copy and leaving voters and quick-mode guidance inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_3: Step 2b.5 KV capture depends on quiet-session / stdout contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Step 2b.5 KV capture uses command substitution on stdout in a way that assumes `LARCH_QUIET_DISABLE=1` (or equivalent) so `emit_kv` contract lines are not diverted from captured stdout; a quiet orchestrator that omits the export can mis-parse triggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `SEMANTIC_SOFT_ESTIMATE` naming misreads as a line-count estimate
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The identifier suggests a numeric estimate rather than boolean sprawl semantics, so readers may skip the real branching condition; footer copy may need alignment if renamed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Split-path prose ties tmpdir preservation to `PLAN_WRITE_OK` inaccurately
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Prose implies `PLAN_WRITE_OK` gates tmpdir preservation when preservation is actually due to exiting before Step 6 cleanup / finalize, which can mislead debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

