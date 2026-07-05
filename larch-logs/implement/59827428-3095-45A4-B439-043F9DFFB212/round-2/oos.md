### OOS_1: Cap-1 rollup test coverage gaps
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-rollup
- **Severity**: nit
- **Concern**: The cap-1 annotate tests still only exercise `ISSUE_1_URL` success. They do not cover bare or indexed dedup stdout, or partial-failure stdout with `ISSUES_FAILED>0`, so parser and stamping regressions in those cap-1 branches could slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-oos-rollup: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: Legacy FINDING_N precedence is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The legacy `FINDING_N` coverage still lacks a regression that proves `findings-classification.tsv` wins over conflicting footer text, so precedence bugs can hide when those two sources disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: Bare duplicate stdout remains unparsed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `design_oos.py` still parses annotate stdout only through the indexed `ISSUE_(\d+)_(URL|DUPLICATE_OF_URL)` pattern, so a bare `ISSUE_DUPLICATE_OF_URL` / `ISSUE_URL` result would not map a cap-1 rollup URL if it ever reaches annotate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Cap-1 partial-failure stamping remains gated
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The cap-1 rollup URL path still suppresses stamping whenever any failure signal is present, so a successful slot-1 URL can be skipped when `ISSUES_FAILED>0` even if that slot itself did not fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

