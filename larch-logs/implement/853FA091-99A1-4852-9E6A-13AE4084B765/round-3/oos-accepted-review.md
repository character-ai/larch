### FINDING_12: [OUT_OF_SCOPE] report-tokens v2 workflow_path path lacks direct test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` lacks a direct fixture for v2 design runs using `workflow_path`, so token report output may regress independently of timing-report behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] v1 run-params tier labels can differ across readers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: For v1 run-params, timing can label workflow via `workflow_path` while the classification reader defaults to HARD, causing inconsistent labels between timing reports and final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] Legacy Quick heuristic mislabels report-token workflows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The legacy Quick mode tally heuristic in `skills/report-tokens/scripts/run-analysis.sh` can force historical or malformed runs to `SIMPLE`, producing misleading token reports after Quick mode removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


