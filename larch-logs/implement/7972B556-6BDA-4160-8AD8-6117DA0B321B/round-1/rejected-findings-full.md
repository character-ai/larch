### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Step 0b sync pins do not cover recovery control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness and edit-in-sync doc pin the jq filter text, but not the surrounding guard branches, jq-unavailable path, or jq failure handling. SKILL.md Step 0b recovery behavior can drift while current substring/filter checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Broad `no auto-apply` absent needle can false-positive on accurate prose
- **Reviewer(s)**: dyn-absent-phrase-scope-output.txt
- **Severity**: latent
- **Concern**: The bare fixed-string `no auto-apply` absent check can fail CI on accurate non-stale documentation that happens to use that phrase outside the legacy Gate B contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-absent-phrase-scope-output.txt: Replace the short needle with a longer stale-only literal (e.g. a full legacy contract sentence from #3009-era docs) or add a second, context-aware check that only fails when `no auto-apply` appears in Gate B normative sections, not in loop-internals prose.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Jq merge failure path is not asserted for non-mutation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A jq merge failure aborts the harness, while production is expected to log and preserve `run-params.json`; corrupt JSON or failed merge behavior can regress without a checksum/non-mutation assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Whitespace-only manual Gate B values get a different rejection path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `--manual-gate-b " "` bypasses the empty-value check and fails later as an invalid enum, so callers matching the new “requires a value” stderr may mishandle whitespace-only argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

