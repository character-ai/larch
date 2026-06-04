### FINDING_1: [OUT_OF_SCOPE] `_posting_body` applies redaction more than once
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-posting-output.txt
- **Severity**: important
- **Concern**: Issue posting applies `redact.redact()` more than once, so trim sizing and body posting no longer follow the documented single-redaction-pass contract; redundant passes are harmless only if redaction remains perfectly idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-issue-posting-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] Ship-pr Phase 7 paths were not reviewed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Ship-pr Phase 7 driver changes appear in the branch diff but were outside the report-tokens-focused correctness pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] `LARCH_REPORT_TOKENS_LIMIT` counts directories, not parsed records
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-semantics-output.txt
- **Severity**: latent
- **Concern**: The limit can stop after lexicographically early junk directories and skip later valid runs; reviewers marked this as pre-existing or plan-out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Plot dates and per-day table dates use different fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-pricing-pipeline-output.txt, dyn-scan-semantics-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plots use `closed_at` while per-day tables use `started_at`, so the same run can land on different dates; reviewers marked this as a preserved legacy quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-pricing-pipeline-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Bad manifest/token-report scan fixtures are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-scan-semantics-output.txt
- **Severity**: important
- **Concern**: Plan-listed malformed manifest and token-report fixtures are missing or incomplete, especially invalid syntax, `null`, non-object, and empty-object cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Ship-pr parity target increases harness shard load
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-merge-parity` bundled in the same branch may affect shard timing, but reviewers marked this as unrelated ship-pr work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_36: [OUT_OF_SCOPE] Mixed bucket/blended argv behavior matches the plan
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that per-vendor mixed bucket/blended argv behavior is correct and improves on the removed bash all-or-blended gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] Cost env forwarding matches the documented contract
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that forwarding `LARCH_RATE_*` and legacy aliases into `token-cost.sh` matches the documented contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] Design summaries include unknown workflow runs that trend/plot series omit
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: latent
- **Concern**: Design-mode summary totals can include `unknown` workflow runs while SIMPLE/HARD trend tables and plots omit them; reviewer marked this as a pre-existing plan quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: The trim contract documents a banner priority, but no rendered `ReportSection` uses `SectionPriority.BANNER`; banner text is assembled outside the section list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-issue-posting-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] Issue/plot stdout lines drift from cache-trailer contract
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: Successful issue-post output and plot status lines append stdout after the analysis/cache trailer, mixing operational metadata with the analysis artifact; reviewer also noted adjacent pre-existing plot stdout drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] Plot `open` result is unchecked
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `report_tokens_plot.py` invokes `open` through the runner without checking the result; reviewer marked this as a minor operational gap outside matplotlib isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_45: [OUT_OF_SCOPE] CI wiring for pytest and harness shards looks consistent
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that pytest requirements and shard placement for new harness targets appear consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] `py-lint` scope excludes skill script by design
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that `make py-lint` intentionally scans only `python/`, with plot script static coverage relying on py_compile tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_47: [OUT_OF_SCOPE] Merge parity test runs redundantly
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: `test_merge_bash_parity.py` runs through both shard 5 and `make py-test`; reviewer marked this as redundant but harmless.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] Exit code constants alias value 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `EXIT_BAIL` and `EXIT_STALLED` share value `4`; reviewer marked this as pre-existing config aliasing unrelated to report-tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_9: [OUT_OF_SCOPE] Test fake-runner boilerplate is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Per-file fake runner dataclasses duplicate test boilerplate, but this is a pre-existing test pattern outside the report-tokens plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

