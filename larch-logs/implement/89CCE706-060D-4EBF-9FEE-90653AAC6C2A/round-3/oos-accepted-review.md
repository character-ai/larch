### FINDING_12: [OUT_OF_SCOPE] Description-mode text is embedded raw in reviewer prompts
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: Operator-supplied `DESCRIPTION_TEXT` can be interpolated into external reviewer prompt preambles without the same escaping/redaction used for other untrusted prompt data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] `log_dropped_slots` uses implement-centric site label
- **Reviewer(s)**: dyn-waterfall-output.txt
- **Severity**: nit
- **Concern**: Dropped static slots are logged with `--site "5"`, which can mislabel standalone `/review` drops as Step 5 issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Launched-slot padding path appears unused in production
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: nit
- **Concern**: Since review-core passes launched slots equal to intended slots, threshold script documentation about lower launched counts for vendor-unhealthy cases may not match production behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_20: [OUT_OF_SCOPE] Threshold failure can suppress coverage diagnostics
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: nit
- **Concern**: When aggregate threshold fails first, the coverage gate may not run, so operators may not see missing-archetype diagnostics on heavily degraded panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] Dynamic scout notes remain an untrusted prompt surface
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: Dynamic reviewer scout rationale/prompt bodies are embedded in prompt context without the newer redaction path, leaving a separate unchanged untrusted-data surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_29: [OUT_OF_SCOPE] Agent headers still claim template derivation
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: Some hand-maintained reviewer agent headers still say they are derived from the shared template, which can confuse contributors now that fold edits are intended directly in those files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_3: [OUT_OF_SCOPE] Dynamic Codex log inclusion contract conflicts with implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-output.txt
- **Severity**: important
- **Concern**: `dyn-*-codex-output.txt` and related artifacts are excluded from committed run logs despite acceptance/product text expecting dynamic Codex transcripts to remain available for forensics and run-log mining. The current allow/deny patterns may also treat phased and unphased dynamic Codex outputs inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] Dead static focus-area arms remain in tally code
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy `static_focus_area` branches for removed folded specialists remain in `tally-code-votes.sh`, creating minor maintenance confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


