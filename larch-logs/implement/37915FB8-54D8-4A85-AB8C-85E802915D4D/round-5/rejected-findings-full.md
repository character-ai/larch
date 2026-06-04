### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Truncation banner is not modeled as a protected report section
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `SectionPriority.BANNER` is unused, and the actual truncation notice is not a `ReportSection`, so the trim contract and tests do not protect the posted notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Scan uses raw repo env var string instead of config constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `report_tokens_scan.py` references the raw `LARCH_REPORT_TOKENS_REPO` string, so future config renames can miss this call site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `LARCH_REPORT_TOKENS_LIMIT=0` scans everything
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A limit of `0` is treated as unlimited, contrary to an operator’s likely expectation of zero scanned directories or an explicit error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Trim priority drops suggestions before trend tables
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Under size pressure, cost-reduction suggestions are removed while per-day trend tables remain, which conflicts with the planned trim ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Quiet wrapper lacks gh repo resolution failure coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The quiet wrapper harness does not cover gh repo resolution failure behavior, leaving quiet-mode stderr and friendly failure messaging under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: JSON log reads are unbounded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Unbounded `read_text` on log JSON files can exhaust memory, especially with huge files or symlinks to huge files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicate `_as_mapping` helper can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_as_mapping` is duplicated across scan and cost modules, creating maintenance drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: Stdout report can differ from trimmed filed issue
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Automation may read full stdout and assume it matches the GitHub issue, while the filed issue body may have been trimmed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: Repo slug failure does not fail fast when issue posting is enabled
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: If gh repo resolution fails, the CLI still prices/renders/prints the report before exiting non-zero at the issue-posting gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Inconsistent boolean env flag parsing can drift or mis-handle `NO_OPEN`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-plot-boundary-output.txt
- **Severity**: latent
- **Concern**: Boolean env parsing is duplicated/inconsistent; specifically `LARCH_REPORT_TOKENS_NO_OPEN=0` suppresses auto-open because it is checked as a raw non-empty string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-plot-boundary-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_41

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_41: Python report-token bail exits may break callers expecting old exit codes
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: Operational failures now propagate as exit code `4`, while the old bash entrypoint used different wrapper-side failure codes such as `1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicate date parsing helper can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Date parsing helpers are duplicated between render and plot code, risking silent divergence in date/axis semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `SectionPriority.CACHE` name is ambiguous
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `CACHE` names the rates section and may be confused with NDJSON cache paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Render layer depends on pricing/cost module rollups
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Rendering imports token aggregation from the cost layer, coupling display rendering to pricing argv construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Test fake runner dataclasses are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple identical fake runner dataclasses across tests make runner contract changes require repeated edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

