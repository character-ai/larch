# Review Round 3

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Bulk issues row blocks filed_issue_details override for #5461 capstone gate
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `_ground_truth_calibration_incentive_shipped()` resolves #5461 via `_incentive_issue_from_sources()`, which scans the bulk `issues` list and returns the first matching row immediately. It never consults `_merged_issue_index(issues, filed_issue_details)`, so a stale or partial bulk row showing #5461 as open wins over fresher `filed_issue_details` that already prove closed with non-empty `closedByPullRequestsReferences`. A live run can therefore fail the capstone gate when bulk data is stale even though targeted fetch details are authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: resolve #5461 from `_merged_issue_index(issues, filed_issue_details)` first, then evaluate state, `stateReason`, and `closedByPullRequestsReferences` on the merged record before falling back to `gh`.


### FINDING_2: Ambiguous rollup OOS rows dedupe across run_dir_key
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Ambiguous rollup OOS rows still dedupe on `(run_id, bucket, issue_number/issue_url)` when `identity` is absent, and `_ambiguous_rollup_expansion_row()` at `python/analyze_issues.py:1076` emits no `identity` at all. That means `design/run-1` and `implement/run-1` ambiguous rollup evidence can collapse into one `seen_items` entry in `fate_adjusted_oos_scoring`, undercounting the bucket and reviewer totals in the normal report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: give ambiguous rollup rows a root-relative `identity` that includes `run_dir_key`, or change the explicit-bucket fallback in `fate_adjusted_oos_scoring()` to key on `run_dir_key` before `run_id`.


