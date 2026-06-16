### [Plan Review] FINDING_2

### FINDING_2: Harness baseline timing can be fetched twice or via divergent code paths
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a harness pre-write fetch gate but does not retire the existing inline baseline loop (`run_list_successful` plus per-run `_collect_log_rows`). Under `--kind harness` or `all`, the script may fetch and parse the same CI logs twice, or the old loop and the new gate may diverge on skip-on-failed-log semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After `ci_timing_fetch` lands, route every harness baseline read through `harness_ci_timing.fetch_timing_rows` and keep `_collect_log_rows` only for per-run verification logs (or one shared helper used by both)


