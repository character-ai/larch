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

### FINDING_4: Committed verdict artifact referenced but never scheduled for creation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan references recording human judgment in `docs/ground-truth-verdict.md` as the capstone acceptance artifact, but that file is absent and not listed under Files to modify/create. The code path can gate and print a verdict without landing the promised committed report, leaving the capstone artifact missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add docs/ground-truth-verdict.md to Files to modify/create, or name another concrete committed artifact path and include it.
  - From Codex-Innovation: Add `docs/ground-truth-verdict.md` to Files to modify/create and define the committed verdict entry to write.
  - From Codex-Requirements: Add `### NEW: docs/ground-truth-verdict.md` to Files to modify/create and seed it with the first verdict report or summary.

### FINDING_5: GroundTruthStats new fields lack constructor defaults
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: `GroundTruthStats` adds set, bool, int, and optional fields without constructor defaults. `ground_truth_voter_calibration()` still calls `GroundTruthStats()` with no arguments, so the dataclass cannot be instantiated and verdict scanning fails immediately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Give every new stats field a default and use field(default_factory=set) for qualifying_run_dirs.

### FINDING_6: GroundTruthEvidence.run_dir_key not wired through all constructors
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The plan only mentions populating `run_dir_key` for accepted finding evidence, but `_ground_truth_issue_evidence()` and other constructors still build issue-backed evidence without it. Verdict runs will hit a missing-argument path or carry incomplete evidence metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either default run_dir_key to "" or update _ground_truth_issue_evidence() and every other GroundTruthEvidence constructor to pass it.

### FINDING_7: #5461 shipped check uses wrong gh JSON field closingIssuesReferences
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The incentive gate fetch asks for `closingIssuesReferences`, which does not match the issue shape this codebase already uses (`closedByPullRequestsReferences` in `_fetch_filed_oos_issue_details`, `fetch_main`, and `classify_oos_issue_fate`). A live `gh issue view --json closingIssuesReferences` call can fail or return empty refs, forcing `calibration_incentive_check_unavailable` and a false NO-GO even when #5461 is closed with a merging PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use `closedByPullRequestsReferences` (same as existing fetch paths) for both `gh issue view` and in-memory issue records; reuse the same non-empty-refs predicate already used at python/analyze_issues.py:746-747.
  - From Codex-Innovation: Request `closedByPullRequestsReferences` here, or reuse the already-fetched issue payload field used by the rest of the analyzer.
  - From Cursor-Pragmatic: Use `closedByPullRequestsReferences` in the `gh issue view` fields list and shipped predicate; reuse the existing NOT_PLANNED / PR-ref logic from `classify_oos_issue_fate` / `_has_not_planned_signal`.

### FINDING_8: Diagnostic row-cache key includes verdict-only tuple members when verdict_mode unset
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan keys `_GROUND_TRUTH_ROW_CACHE` with `(log_root, since_date, min_larch_version, verdict_mode, min_runs)` even when `--ground-truth-verdict` is unset. If coordinators forward argv into the key when `verdict_mode=False`, one process can cache the same unfiltered scan under multiple keys and reuse a verdict-filtered entry whose `stats.min_runs` / gate fields do not match a later diagnostic call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build cache keys from normalized stats only: diagnostic mode uses a fixed `(log_root, False)` (or equivalent sentinels); include `since_date`, `min_larch_version`, and `min_runs` only when `verdict_mode` is true.

### FINDING_9: Verdict-mode offline entry path lacks regression coverage for empty-issue bypass and stderr gate error
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `main()` / `analyze_main()` can still short-circuit on empty issues or fail to surface `ERROR=` when verdict mode is on, leaving the new branch unverifiable without dedicated regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a verdict-mode test that uses an empty JSON dump plus populated log-root evidence, asserts the verdict report renders, exit is non-zero on gate failure, and stderr carries `ERROR=`.
```

**Merge notes**

| Source IDs subsumed | Merged into |
|---|---|
| FINDING_1, 9, 15, 18 (+ embedded Requirements narrative #1) | FINDING_1 |
| FINDING_2, 8, 16, 19 (+ embedded Requirements narrative #2) | FINDING_2 |
| FINDING_4, 12, 20 | FINDING_4 |
| FINDING_7, 13, 14 | FINDING_7 |

FINDING_2 and FINDING_7 are related (#5461 incentive gate) but kept separate: one is missing bulk-issue lookup, the other is the wrong JSON field name. No `[OUT_OF_SCOPE]` tags in the input. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token (non-empty merge).

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: README.md:291-298
- **Concern**: [SCOPE-REDUCTION] Firm README.md and docs/skills.md updates are outside binding issue surfaces. Scenario: Binding scope lists only `python/analyze_issues.py`, `.claude/skills/analyze-issues/SKILL.md`, and `docs/point-competition.md`. Duplicate verdict-flag synopsis in README and docs/skills.md adds maintenance without changing verdict correctness or the committed artifact path (prior FINDING_14 rejection still applies).
- **Proposed resolution**: Drop `### UPDATED: README.md` and `### UPDATED: docs/skills.md` from the firm plan; keep operator-facing verdict docs in the skill and `docs/point-competition.md` only.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:197-199
- **Concern**: [SCOPE-REDUCTION] Keep the severity slice verdict-only; adding it to normal diagnostic reports is extra surface area the capstone feature does not need.. Scenario: Normal /analyze-issues output changes even when --ground-truth-verdict is off, so the plan adds churn and new test burden without restoring a broken path.
- **Proposed resolution**: Gate the severity slice behind verdict mode, and leave the existing diagnostic report unchanged.
