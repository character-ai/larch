# Review Round 2

- Mode: `diff`
- 2 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_2: proposer-map-failed validation-exhausted path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Proposer-map-failed coverage hits only the post-aggregate call site; the validation-exhausted call site at `review_pipeline.py:2184-2191` is untested despite the plan requiring both. A regression that breaks row assembly on the exhausted-path early return can ship with green tests while review-and-fix parsers see wrong stdout on that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a _review_core_body test with aggregate_exhausted stub plus failing _write_proposer_sidecar_and_neutralize; assert scout prefix, THRESHOLD_REASON=proposer-map-failed, no classification/VOTER rows, rc 2.


### FINDING_3: ship resume merged path missing phase=postmerge write test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The resume merged path lacks a test that `run_ship` writes `phase=postmerge` before `_ship_postmerge_phase` as required by the plan. Removing the caller-owned pre-helper state write during helper extraction would not fail current tests; resume metadata could be wrong before postmerge runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Spy on _write_ship_state in a merged-resume run_ship test and assert phase=postmerge is written before postmerge helper invocation.


