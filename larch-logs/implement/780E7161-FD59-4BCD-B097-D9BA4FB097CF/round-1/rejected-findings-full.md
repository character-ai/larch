### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated read_lines_kv / KV parsing in write-final-report.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `read_lines_kv` and nested `case` integer checks at `skills/implement/scripts/write-final-report.sh:111-147` duplicate existing `read_kv` style, making consistent KV parsing harder to maintain across `write-final-report.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate parsing/validation into a small shared helper.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated gh PR /files TSV shim across test harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `gh` PR files shim at `scripts/test-compute-pr-line-counts.sh:35-52` is duplicated in `skills/implement/scripts/test-write-final-report.sh`, risking fixture drift if one harness updates TSV rows and the other does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared test fixture for gh and /files TSV output.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: compute-pr-line-counts discards gh stderr on API failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/compute-pr-line-counts.sh:50`, `gh` stderr is discarded on API failure. Operators see only `Lines (PR diff): N/A` with no hint whether failure was auth, network, or bad repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider surfacing REASON detail to stderr or logging a warning without aborting the report.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Missing or non-executable compute-pr-line-counts.sh fails silently to N/A
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/implement/scripts/write-final-report.sh:118-126`, a missing or non-executable `compute-pr-line-counts.sh` degrades to N/A without an execution-issues warning, which can mask a broken plugin install or chmod regression as “no data PR.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Append a Warnings entry when helper invocation fails and PR_NUMBER is nonzero.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

