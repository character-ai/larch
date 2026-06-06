### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Round-cap inert-source test does not cover CLI-shaped positional args
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The inert-source test does not source `lib-implement-round-cap.sh` with `--count-prior-degraded`-shaped arguments, so a guard bug that exits only for CLI-shaped args while sourced would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a source test using --count-prior-degraded-shaped args and assert no usage/exit occurs and the function remains callable.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Helper CLI failure-output conventions diverge from the shared quiet contract
- **Reviewer(s)**: dyn-quiet-contract-output.txt
- **Severity**: latent
- **Concern**: The branch introduces or exposes inconsistent CLI contracts: `append-execution-issue.sh` adds a `USAGE=` quiet-envelope key, while `lib-implement-round-cap.sh` emits raw stderr usage and bare stdout integers. The shared `lib-quiet.md` authority does not document optional failure envelope keys, leaving callers without one reusable parsing model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-contract-output.txt: Document in `scripts/lib-quiet.md` when optional `USAGE=` is permitted on quiet helpers, and either align round-cap CLI errors with `emit_kv` or explicitly classify it as a “numeric probe” exception with a shared naming table for failure keys.
  - From dyn-quiet-contract-output.txt: Add a short “optional failure envelope keys” subsection to `lib-quiet.md` (`FAILED`, `ERROR`, optional `USAGE`) and cross-link from `append-execution-issue.md`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Bootstrap self-derive test hides stderr diagnostics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The new derive test discards stderr, so failures surface only as return-code or stdout mismatches without the wrapper’s actual error context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Capture stderr to artifact file and print on failure.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `append-execution-issue.sh` fail-usage tests miss remaining branches
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness checks only some `fail_usage` paths, so unsupported-category or mutual-exclusive-entry regressions could drop `USAGE=` without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add table-driven cases for remaining exit-1 fail_usage paths


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

