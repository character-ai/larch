### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Display titles are duplicated and coupled to internal section keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Reader-facing section titles are duplicated between render output and `_TITLE_BY_SECTION`, while `ReportSection.title` appears to hold internal slugs; header renames can leave stale trim notices or internal keys in output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: Full analysis stdout is not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The CLI prints full markdown to stdout without applying the same redaction used for issue bodies, so sensitive phase names or paths can leak to CI/operator transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Implement/design grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Render tables and plot series duplicate skill-specific aggregation/filtering, so implement/design behavior can diverge after a one-sided edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: Truncation notice overemphasizes `--no-issue`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The truncation banner tells issue readers to rerun with `--no-issue` even though the normal invocation already printed the full analysis to stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_40: Issue-post failure can look like a successful analysis artifact
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: The CLI prints the full analysis and cache trailer before posting; if posting fails, callers that grep stdout but ignore exit status may treat the run as fully successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: Plot subprocess has no timeout
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: The matplotlib child runs via `runner.run(...)` without a timeout, so a hung or pathological plot run can block `/report-tokens`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicate `_as_mapping` helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scan` and `cost` define duplicate mapping coercion helpers, creating drift risk for edge-case JSON typing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate date helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Render and plot duplicate date parsing helpers, so date behavior changes require synchronized edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Env boolean parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: CLI and plot env-boolean parsing duplicates existing `run_context._env_bool` semantics and could disagree on enabled values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

