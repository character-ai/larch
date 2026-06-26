### FINDING_1: Verdict wrapper gate/render ownership contradicts pre-render stats contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan requires degradation and gate fields on `GroundTruthStats` before the sole `_render_ground_truth_report` call and forbids mutating them after calibration returns finished text, but the verdict wrapper section still directs evaluating and assigning `gate_result` / `gate_reason` after `ground_truth_voter_calibration` returns. Today calibration renders internally before return, so an implementer following the wrapper bullet can print a report missing PASS/FAIL and `gate_reason`, then set gate fields or exit code afterward, desyncing stdout, stderr `ERROR=`, and `stats.gate_result`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin one contract: compute incentive, degradation, corpus, and final `stats.gate_result` / `stats.gate_reason` inside `ground_truth_voter_calibration` immediately before its single `_render_ground_truth_report` call; limit the wrapper to argv defaults, calling calibration, printing returned text, and returning non-zero from `stats.gate_result` only. Delete wrapper wording about assigning gate fields before render after calibration returns.
  - From Cursor-Innovation: Pin one owner: compute corpus, degradation, incentive, and final `stats.gate_result` / `stats.gate_reason` inside calibration immediately before the single render; limit the wrapper to printing returned text and returning non-zero from `stats.gate_result`.
  - From Cursor-Pragmatic: Pin one path only: compute incentive/degradation/corpus gate on `stats` inside `ground_truth_voter_calibration` immediately before its sole `_render_ground_truth_report` call, and limit the wrapper to printing returned text plus reading `stats.gate_result` for exit code; or move render entirely to the wrapper and remove the internal render. Delete the post-return gate-assignment branch.
  - From Cursor-Requirements: Pin verdict mode so corpus, degradation, and #5461 incentive gates are computed inside `ground_truth_voter_calibration` immediately before its single render (or defer all rendering to the wrapper after gates are set). Restrict the wrapper to printing returned text and returning `0`/`1` from `stats.gate_result`; delete the post-return gate-evaluation step.


### FINDING_2: #5461 shipped check ignores bulk-loaded issues already available to coordinators
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `_ground_truth_calibration_incentive_shipped` only consults `filed_issue_details` or a live `gh issue view`. Coordinators on both live and offline paths already bulk-load issues (including `stateReason` and `closedByPullRequestsReferences`), and offline `analyze --json` can contain #5461, but neither path is consulted. #5461 is not a filed-OOS log target, so replay or live runs with a healthy bulk dump can still force `calibration_incentive_check_unavailable` or `calibration_incentive_not_shipped` when `gh` is down or targeted fetch is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `_ground_truth_calibration_incentive_shipped` to accept the coordinator `issues` sequence, look up `GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER` there first (same closed / not `NOT_PLANNED` / closing-PR rules), then fall back to `filed_issue_details` and `gh issue view`. Pass `issues` from both verdict coordinators; add a regression test where bulk JSON proves shipped state without `gh`.
  - From Cursor-Innovation: Extend the helper to accept the loaded `issues` list (or `_merged_issue_index`) and resolve #5461 there before `filed_issue_details` / `gh`; add an offline verdict test with #5461 present only in the bulk JSON dump.
  - From Cursor-Pragmatic: Pass the coordinator `issues` sequence into the incentive helper and resolve #5461 via `_merged_issue_index(issues, filed_issue_details)` before any dedicated fetch; keep `gh issue view` only as fallback when the merged record is absent.
  - From Cursor-Requirements: Extend `_ground_truth_calibration_incentive_shipped` to accept the loaded `issues` sequence (or a prebuilt merged index) and resolve #5461 from that data before `gh`. Keep the conservative `NOT_PLANNED` / missing-closing-PR rules; add a regression test for offline verdict GO when #5461 is present only in the bulk JSON.


### FINDING_3: Verdict scan-counter OR rule can reintroduce global totals
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan's verdict scan-counter rule still offers an OR that permits incrementing counters globally and recomputing later. That recompute branch matches today's failure mode: filtered `qualifying_runs` paired with legacy global `files_seen` / `scanned_rows` still appearing in the report, reintroducing inflated totals from ineligible pre-since `run_dir` values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove the recompute alternative. Require verdict discovery to evaluate `run_dir` eligibility before any `files_seen`, `scanned_rows`, `eligible_rows`, or related counter increments, and assert in tests that ineligible pre-since dirs contribute zero scan counters.


### FINDING_7: #5461 shipped check uses wrong gh JSON field closingIssuesReferences
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The incentive gate fetch asks for `closingIssuesReferences`, which does not match the issue shape this codebase already uses (`closedByPullRequestsReferences` in `_fetch_filed_oos_issue_details`, `fetch_main`, and `classify_oos_issue_fate`). A live `gh issue view --json closingIssuesReferences` call can fail or return empty refs, forcing `calibration_incentive_check_unavailable` and a false NO-GO even when #5461 is closed with a merging PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use `closedByPullRequestsReferences` (same as existing fetch paths) for both `gh issue view` and in-memory issue records; reuse the same non-empty-refs predicate already used at python/analyze_issues.py:746-747.
  - From Codex-Innovation: Request `closedByPullRequestsReferences` here, or reuse the already-fetched issue payload field used by the rest of the analyzer.
  - From Cursor-Pragmatic: Use `closedByPullRequestsReferences` in the `gh issue view` fields list and shipped predicate; reuse the existing NOT_PLANNED / PR-ref logic from `classify_oos_issue_fate` / `_has_not_planned_signal`.


