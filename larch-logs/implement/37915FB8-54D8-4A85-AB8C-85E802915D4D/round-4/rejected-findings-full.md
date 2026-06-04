### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: `token-cost.sh` stderr is forwarded without redaction/noise control
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Child stderr from `token-cost.sh` is forwarded directly, which can leak sensitive-adjacent diagnostics and flood output even on successful runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: CLI prints full analysis before issue-post failure is known
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The CLI emits a complete report to stdout before optional GitHub issue posting, so scripts or operators may treat captured stdout as success even if the later post fails and the process exits non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Quiet-mode harness does not cover post-restore Python failures
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: latent
- **Concern**: The quiet-mode test covers happy path and pre-Python validation errors, but not failures after stdout/stderr restoration, leaving the main Python diagnostic regression only partially guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_24: Design workflow fallback does not match bash fail-closed HARD behavior
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: important
- **Concern**: `_workflow_from` returns `unknown` for missing/invalid design classification instead of defaulting to `HARD` like the old bash helper, so older/partial design runs can be dropped from design trends and plots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: Plot subprocess smoke test bypasses production isolation contract
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: The optional real-subprocess plot smoke test runs the child directly without `MPLCONFIGDIR` isolation and does not assert returned PNG paths survive after subprocess exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Plot producer/consumer JSON contract lacks shared fixtures
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Producer and consumer tests use separate inline plot payloads, so `_series()` and `_validate_series()` can drift while both test suites still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Token bucket schema logic is duplicated between scan and cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Per-vendor bucket key lists and token aggregation are duplicated across scan and cost modules, creating drift risk where one path accepts data the other prices incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Workflow grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Skill/workflow grouping is copy-pasted in render and plot paths, so future workflow behavior changes can diverge between tables and charts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicate env flag helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `env_flag_enabled` helpers are duplicated in CLI and plot code, risking inconsistent truthy-value handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `SectionPriority.BANNER` exists but no banner section uses it; trim notices are inline strings, so the enum implies a contract the render pipeline does not implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

