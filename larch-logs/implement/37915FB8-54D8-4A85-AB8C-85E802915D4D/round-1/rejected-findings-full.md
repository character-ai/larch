### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: Design SIMPLE/HARD render split lacks golden coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Render tests do not assert separate SIMPLE and HARD per-workflow trend sections for design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_31: Empty-record analysis skips requested issue posting
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: When scan finds zero parseable runs, the CLI returns success after printing “No parseable token reports found” and does not create an issue even if issue posting was requested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: Repo/post failures changed exit code from 1 to 4
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: latent
- **Concern**: Repo-resolution and issue-posting failures now return `EXIT_BAIL` 4 instead of the prior operator-error exit 1, which can break callers that classify failures by code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: Plot child does not validate the version/skill/series contract
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `plot-cost-over-time.py` accepts malformed or drifted plot input without enforcing `version`, allowed `skill`, required labels, or expected series cardinality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_35: Plot child silently skips malformed series/points
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Invalid `series` or `points` entries are skipped with `continue`, letting partially invalid payloads exit 0 and appear equivalent to valid “no data” runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Workflow resolution omits bash fallback chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `report_tokens_scan.py` inlines workflow resolution and may miss workflow locations handled by the bash helper fallback chain, skewing classification for design SIMPLE/HARD plots and tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_41

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_41: Quiet harness git shim hardcodes `/usr/bin/git`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: latent
- **Concern**: The quiet harness falls back to `/usr/bin/git`, reducing portability once the harness is added to CI or local matrices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate helper functions are spread across report-tokens modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_as_mapping` / `_date` style helpers are duplicated across scan, cost, render, and plot modules, increasing maintenance risk for JSON-shape changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The banner priority enum value is not represented as a `ReportSection`, making trim/banner immutability harder to reason about or test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

