### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:221-229
- **Concern**: Verdict wrapper text assigns gate fields after calibration returns while calibration still owns `_render_ground_truth_report`. Scenario: Today `ground_truth_voter_calibration` renders internally and returns finished text. The wrapper step that evaluates `gate_result` / `gate_reason` "after calibration returns" cannot run before that render, so an implementer can set degradation or gate fields too late and desync the printed verdict corpus block from exit code and stderr `ERROR=` (the failure mode prior rounds flagged for degradation).
- **Proposed resolution**: Pin one contract: compute incentive, degradation, corpus, and final `stats.gate_result` / `stats.gate_reason` inside `ground_truth_voter_calibration` immediately before its single `_render_ground_truth_report` call; limit the wrapper to argv defaults, calling calibration, printing returned text, and returning non-zero from `stats.gate_result` only. Delete wrapper wording about assigning gate fields before render after calibration returns.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:153-163
- **Concern**: `#5461` shipped gate ignores the bulk-loaded `issues` sequence coordinators already fetch. Scenario: `_ground_truth_calibration_incentive_shipped` only consults `filed_issue_details` or a live `gh issue view`. Live `run_main` bulk-fetches issues (including `stateReason` and `closedByPullRequestsReferences`), and offline `analyze --json` can already contain issue `5461`, but neither path is consulted. A replay or live run with a healthy bulk dump can still force `calibration_incentive_check_unavailable` or `calibration_incentive_not_shipped` when `gh` is down or #5461 was never a filed-OOS target.
- **Proposed resolution**: Extend `_ground_truth_calibration_incentive_shipped` to accept the coordinator `issues` sequence, look up `GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER` there first (same closed / not `NOT_PLANNED` / closing-PR rules), then fall back to `filed_issue_details` and `gh issue view`. Pass `issues` from both verdict coordinators; add a regression test where bulk JSON proves shipped state without `gh`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:135-137
- **Concern**: Verdict scan-counter rule still offers an OR that can reintroduce global totals. Scenario: FINDING_8 was accepted to stop counting ineligible `run_dir` values, but the plan allows either skipping ineligible dirs before incrementing counters or incrementing globally and recomputing later. The recompute branch matches today's failure mode: filtered `qualifying_runs` with legacy global `files_seen` / `scanned_rows` still in the report.
- **Proposed resolution**: Remove the recompute alternative. Require verdict discovery to evaluate `run_dir` eligibility before any `files_seen`, `scanned_rows`, `eligible_rows`, or related counter increments, and assert in tests that ineligible pre-since dirs contribute zero scan counters.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:12-22
- **Concern**: Committed verdict artifact target is referenced but never scheduled. Scenario: The plan says to record human judgment in docs/ground-truth-verdict.md, but that file is absent and not listed for creation or update, so the capstone cannot land the promised committed verdict artifact.
- **Proposed resolution**: Add docs/ground-truth-verdict.md to Files to modify/create, or name another concrete committed artifact path and include it.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:1579-1601
- **Concern**: GroundTruthStats adds fields without constructor defaults. Scenario: ground_truth_voter_calibration() still calls GroundTruthStats(), and the new set, bool, int, and optional fields need defaults or default_factory; otherwise the dataclass cannot be instantiated and verdict scanning fails immediately.
- **Proposed resolution**: Give every new stats field a default and use field(default_factory=set) for qualifying_run_dirs.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:1623-1636,2131-2160
- **Concern**: GroundTruthEvidence.run_dir_key is not wired through all constructors. Scenario: The plan only mentions populating run_dir_key for accepted finding evidence. _ground_truth_issue_evidence() still constructs issue-backed evidence, so verdict runs will hit a missing-argument path or carry incomplete evidence metadata.
- **Proposed resolution**: Either default run_dir_key to "" or update _ground_truth_issue_evidence() and every other GroundTruthEvidence constructor to pass it.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:157
- **Concern**: #5461 shipped check pins wrong gh JSON field `closingIssuesReferences`. Scenario: The repo already uses `closedByPullRequestsReferences` in `_fetch_filed_oos_issue_details`, `fetch_main`, and `classify_oos_issue_fate`. A live `gh issue view --json closingIssuesReferences` call can fail or return empty refs, forcing `calibration_incentive_check_unavailable` and a false NO-GO even when #5461 is closed with a merging PR.
- **Proposed resolution**: Use `closedByPullRequestsReferences` (same as existing fetch paths) for both `gh issue view` and in-memory issue records; reuse the same non-empty-refs predicate already used at python/analyze_issues.py:746-747.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:155-163
- **Concern**: Offline verdict path cannot prove #5461 from the bulk issue dump already loaded (FINDING_11 still open). Scenario: `_ground_truth_calibration_incentive_shipped` only consults `filed_issue_details` or live `gh`. Offline `analyze_main` with `--json` can contain #5461 as CLOSED with `closedByPullRequestsReferences`, but verdict mode still NO-GOs because incentive lookup ignores the `issues` sequence passed to calibration.
- **Proposed resolution**: Extend the helper to accept the loaded `issues` list (or `_merged_issue_index`) and resolve #5461 there before `filed_issue_details` / `gh`; add an offline verdict test with #5461 present only in the bulk JSON dump.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/analyze_issues.py:221-226
- **Concern**: Verdict wrapper still describes post-calibration gate assignment that conflicts with the pre-render contract. Scenario: Round-4 FINDING_1 is only half-fixed: lines 16 and 171 require degradation and gate fields on `stats` before `_render_ground_truth_report`, but the wrapper bullets say to evaluate `gate_result` after calibration returns. `ground_truth_voter_calibration` renders before return today, so a wrapper-only gate leaves PASS/FAIL and `gate_reason` out of the printed report while exit code disagrees.
- **Proposed resolution**: Pin one owner: compute corpus, degradation, incentive, and final `stats.gate_result` / `stats.gate_reason` inside calibration immediately before the single render; limit the wrapper to printing returned text and returning non-zero from `stats.gate_result`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:125
- **Concern**: Diagnostic row-cache key still allows verdict-only tuple members when `--ground-truth-verdict` is unset (FINDING_5 still open). Scenario: The plan always keys `_GROUND_TRUTH_ROW_CACHE` with `(log_root, since_date, min_larch_version, verdict_mode, min_runs)` while stray filter flags are no-ops in normal mode. If coordinators forward argv into the key when `verdict_mode=False`, one process caches the same unfiltered scan under multiple keys and can reuse a verdict-filtered entry whose `stats.min_runs` / gate fields do not match a later diagnostic call.
- **Proposed resolution**: Build cache keys from normalized stats only: diagnostic mode uses a fixed `(log_root, False)` (or equivalent sentinels); include `since_date`, `min_larch_version`, and `min_runs` only when `verdict_mode` is true.



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: README.md:291-298
- **Concern**: [SCOPE-REDUCTION] Firm README.md and docs/skills.md updates are outside binding issue surfaces. Scenario: Binding scope lists only `python/analyze_issues.py`, `.claude/skills/analyze-issues/SKILL.md`, and `docs/point-competition.md`. Duplicate verdict-flag synopsis in README and docs/skills.md adds maintenance without changing verdict correctness or the committed artifact path (prior FINDING_14 rejection still applies).
- **Proposed resolution**: Drop `### UPDATED: README.md` and `### UPDATED: docs/skills.md` from the firm plan; keep operator-facing verdict docs in the skill and `docs/point-competition.md` only.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:12-24
- **Concern**: Committed verdict artifact is referenced but never scheduled for creation. Scenario: The plan can print and gate on a verdict, but the required persistent record in `docs/ground-truth-verdict.md` never lands, so the capstone acceptance artifact stays missing.
- **Proposed resolution**: Add `docs/ground-truth-verdict.md` to Files to modify/create and define the committed verdict entry to write.



### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:155-159
- **Concern**: Incentive gate fetch asks for `closingIssuesReferences`, which does not match the issue shape this code already uses. Scenario: The shipped-check helper will miss the closing PR reference and keep #5461 stuck at NO-GO even when the issue is actually closed by a PR.
- **Proposed resolution**: Request `closedByPullRequestsReferences` here, or reuse the already-fetched issue payload field used by the rest of the analyzer.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:155-159
- **Concern**: #5461 shipped check names wrong gh JSON field `closingIssuesReferences`. Scenario: The repo and `_fetch_filed_oos_issue_details` already use `closedByPullRequestsReferences` (see `analyze_issues.py:1314`, `classify_oos_issue_fate` at `:746-748`). Implementing the plan literally queries a non-existent field, so the incentive gate can never see a closing PR and always returns `calibration_incentive_not_shipped` / `calibration_incentive_check_unavailable` even when #5461 is closed with a merged PR.
- **Proposed resolution**: Use `closedByPullRequestsReferences` in the `gh issue view` fields list and shipped predicate; reuse the existing NOT_PLANNED / PR-ref logic from `classify_oos_issue_fate` / `_has_not_planned_signal`.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:16-17,221-225
- **Concern**: [ALREADY_ADDRESSED] Gate/render ownership still contradicts post-return wrapper text (FINDING_1 incomplete). Scenario: Line 16 forbids mutating degradation or gate fields after calibration returns finished text, but the wrapper bullets still say to evaluate and assign `gate_result` / `gate_reason` after calibration returns and before the single render. Today `ground_truth_voter_calibration` renders internally (`:2617-2624`). An implementer can set gate fields only after text is already rendered, desyncing PASS/FAIL lines from exit code and reintroducing targeted-fetch omission in the corpus block.
- **Proposed resolution**: Pin one path only: compute incentive/degradation/corpus gate on `stats` inside `ground_truth_voter_calibration` immediately before its sole `_render_ground_truth_report` call, and limit the wrapper to printing returned text plus reading `stats.gate_result` for exit code; or move render entirely to the wrapper and remove the internal render. Delete the post-return gate-assignment branch.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:155-160,2740-2756
- **Concern**: #5461 incentive gate omits bulk-loaded `issues` already available to coordinators. Scenario: The plan loads bulk issues on both live and offline paths (`run_main` issue dump; offline `--json`) but `_ground_truth_calibration_incentive_shipped` only checks `filed_issue_details` plus optional `gh issue view`. #5461 is not a filed-OOS log target, so offline replay and any run where targeted `gh` fails can NO-GO with `calibration_incentive_check_unavailable` even when the loaded issue dump already shows #5461 CLOSED with `closedByPullRequestsReferences`.
- **Proposed resolution**: Pass the coordinator `issues` sequence into the incentive helper and resolve #5461 via `_merged_issue_index(issues, filed_issue_details)` before any dedicated fetch; keep `gh issue view` only as fallback when the merged record is absent.



### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:197-199
- **Concern**: [SCOPE-REDUCTION] Keep the severity slice verdict-only; adding it to normal diagnostic reports is extra surface area the capstone feature does not need.. Scenario: Normal /analyze-issues output changes even when --ground-truth-verdict is off, so the plan adds churn and new test burden without restoring a broken path.
- **Proposed resolution**: Gate the severity slice behind verdict mode, and leave the existing diagnostic report unchanged.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:2487-2625
- **Concern**: Verdict wrapper gate evaluation contradicts the pre-render stats contract. Scenario: The plan requires degradation and gate fields on `GroundTruthStats` before the sole `_render_ground_truth_report` call and forbids mutating them after calibration returns finished text (plan lines 16-17). It also tells the verdict wrapper to evaluate `gate_result` / `gate_reason` after `ground_truth_voter_calibration` returns (plan lines 221-225), while today's calibration always renders internally before return. An implementer can follow the wrapper bullet, print a report missing PASS/FAIL and `gate_reason`, then mutate stats or exit from wrapper locals so stdout, stderr `ERROR=`, and `stats.gate_result` disagree.
- **Proposed resolution**: Pin verdict mode so corpus, degradation, and #5461 incentive gates are computed inside `ground_truth_voter_calibration` immediately before its single render (or defer all rendering to the wrapper after gates are set). Restrict the wrapper to printing returned text and returning `0`/`1` from `stats.gate_result`; delete the post-return gate-evaluation step.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:1398-1409
- **Concern**: #5461 shipped check ignores the offline bulk issue dump the coordinator already loaded. Scenario: `_ground_truth_calibration_incentive_shipped` is specified to read only `filed_issue_details` or live `gh issue view 5461` (plan lines 155-160). Offline `main()` already loads a bulk `--json` issue list and builds `_merged_issue_index`, but #5461 is not a filed-OOS target, so it will not appear in `filed_issue_details`. A replayed offline verdict run with a dump that already proves #5461 closed-with-PR can still fail `calibration_incentive_check_unavailable` and block a GO artifact even when log-root evidence and corpus gates pass.
- **Proposed resolution**: Extend `_ground_truth_calibration_incentive_shipped` to accept the loaded `issues` sequence (or a prebuilt merged index) and resolve #5461 from that data before `gh`. Keep the conservative `NOT_PLANNED` / missing-closing-PR rules; add a regression test for offline verdict GO when #5461 is present only in the bulk JSON. ## Findings ### 1. [correctness] Verdict wrapper gate evaluation contradicts the pre-render stats contract (`python/analyze_issues.py:2487-2625`) The plan’s top-level render contract (lines 16-17) requires all degradation and gate fields on `GroundTruthStats` before the single `_render_ground_truth_report` call and forbids post-return mutation once calibration returns finished text. The wrapper section (lines 221-225) still says to evaluate `gate_result` after calibration returns. Today `ground_truth_voter_calibration` always renders at line 2617 before return, so following the wrapper bullet produces a report without PASS/FAIL, then mutates stats or exit code afterward. **Suggested revision:** Compute corpus, degradation, and incentive gates inside calibration immediately before its one render (or have calibration return unrendered stats and let the wrapper render once). Limit the wrapper to printing text and returning exit code from `stats.gate_result`. ### 2. [correctness] #5461 shipped check ignores offline bulk issue dump (`python/analyze_issues.py:1398-1409`) Prior round FINDING_11 remains open. The incentive gate helper only consults `filed_issue_details` or live `gh`, not the bulk `issues` list offline `main()` already loads via `_merged_issue_index`. #5461 is not a filed-OOS issue, so offline replay runs cannot prove incentive-era shipped from the JSON they already have. **Suggested revision:** Resolve #5461 from the merged bulk issue index before falling back to `gh`; add an offline-only test where #5461 appears in `--json` but not in filed-issue details.



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/ground-truth-verdict.md
- **Concern**: Committed verdict artifact is referenced but not added to Files to modify/create.. Scenario: Plan can ship the code path without any committed verdict report to review or gate token allocation against.
- **Proposed resolution**: Add `### NEW: docs/ground-truth-verdict.md` to Files to modify/create and seed it with the first verdict report or summary.



### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_analyze_issues.py:235-260
- **Concern**: Verdict-mode offline entry path lacks regression coverage for the empty-issue early return bypass and stderr gate error.. Scenario: main()/analyze_main() can still short-circuit on empty issues or fail to surface `ERROR=` when verdict mode is on, leaving the new branch unverifiable.
- **Proposed resolution**: Add a verdict-mode test that uses an empty JSON dump plus populated log-root evidence, asserts the verdict report renders, exit is non-zero on gate failure, and stderr carries `ERROR=`.



