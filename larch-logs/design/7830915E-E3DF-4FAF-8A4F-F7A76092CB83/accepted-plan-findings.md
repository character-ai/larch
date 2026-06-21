### FINDING_1: run_main cannot pass filed_issue_details into fate scoring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The live `/analyze-issues` `run_main` path is supposed to fetch per-issue GitHub view data and render fate-adjusted OOS scoring, but `filed_issue_details` is an in-memory dict that cannot cross the `main(analyze_args)` argv-only boundary. `run_main` today only forwards analyze flags into `main()`, so enriched comment/fate data never reaches `fate_adjusted_oos_scoring`; live runs may skip wiring entirely, omit combined-away docking despite extra `gh` calls, or require duplicate fetch logic outside `main()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extract a shared render helper (e.g. build_report/load_issues + fate_adjusted_oos_scoring + section assembly) called by both main() and run_main; have run_main load the dump, scan logs, fetch filed_issue_details, then call the helper with that dict; keep offline analyze --json on the helper with filed_issue_details={} and no network
  - From Cursor-Innovation: Extract one shared report builder used by main() and run_main(), or pass filed_issue_details via an explicit argv sidecar (for example --filed-issue-details-file) that main() reads before fate_adjusted_oos_scoring
  - From Cursor-Pragmatic: Add an explicit handoff: e.g. run_main writes a sidecar JSON map and forwards --filed-issue-details-json PATH (and --log-root) through analyze_args; main() loads issues from --json, loads the sidecar when present, and passes filed_issue_details into fate_adjusted_oos_scoring before printing the new section


### FINDING_2: Cap-rollup same-source fallback may select wrong members when candidate count exceeds N
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: When a cap-rollup cites N combined OOS blocks but more than N same-source unfiled blocks exist in the logs, the planned source-key fallback orders unfiled blocks and takes up to N without an exactly-N guard. Production rollups can leave many same-source `oos-accepted` blocks (for example 8 blocks for a rollup of 3), so heuristic expansion can credit/dock the wrong reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require unambiguous membership before expansion: use explicit stable-id citations or rollup excerpt mapping first; for same-source fallback only expand when the unfiled candidate count equals N, otherwise emit ambiguous_rollup_expansion; add a fixture with N=3 and 8 candidates that must not expand
  - From Cursor-Innovation: When inferred same-source unfiled candidates exceed parsed rollup N, emit ambiguous_rollup_expansion instead of taking the first N by artifact_relpath/heading order


### FINDING_3: Cap-rollup expansion does not bridge main-agent aggregate stable ids to review-path markdown
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Committed ndjson often uses `oos-accepted-main-agent:OOS_1` while member blocks live under `round-*/oos-accepted-review.md`. Strict source-key matching from the aggregate stable id skips those blocks, so rollup docking under-attributes or misses member rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse oos_filer._issue_covers_stable_id (or the planned widened _stable_ids_cover) when resolving rollup members, not only stem equality; add a regression fixture with main-agent aggregate stable id and review-path markdown blocks


### FINDING_4: Plan omits wiring fate-adjusted section into main() stdout join
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `main()` can keep printing only the seven legacy sections; without an explicit append, fate-adjusted totals never appear in `analyze --json` or `run_main` output even if scoring logic exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Explicitly append fate_adjusted_oos_scoring output after reviewer_effectiveness in main()'s join list, with try/except degrade per plan failure-mode note


### FINDING_5: fetch_main lacks mandated retry when expanded gh JSON fields are unsupported
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Adding `stateReason` and `url` to the bulk `gh issue list --json` field list is documented only under failure modes, not in the `fetch_main` change list. On older `gh` builds the entire list call can fail, aborting `run_main` before any report rather than degrading fate classification only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mandate in the fetch_main update: try the expanded --json field list once; on non-zero exit retry with the current field set (number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences) and record degraded stateReason/url availability for classify_oos_issue_fate


