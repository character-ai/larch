## Goal
Implement issue #5540: [IMPLEMENTING] [BUG] (URGENT) Remove redundant post-apply full test suite runs from Step 5 review-round _step5_post_round_gates.

## Implementation Plan
## Summary

After every accepted finding is applied in a Step 5 review round, `_step5_post_round_gates` in `python/review_and_fix.py` calls `_run_relevant_checks_captured`, which runs the full `make py-lint py-test` suite (site `step5-review-fixes`). This is redundant: the dedicated check steps (Step 3 after implementation, Step 6 after review commits) already cover this. Running the full test suite after every individual coder apply adds roughly 12 minutes of unlabeled wall time per accepted finding per round, directly causing the massive blank gaps seen in the review-round Gantt charts. These post-apply checks must be removed; only pre-commit hook checks should fire naturally when the review round makes a commit.

## Original report

Stop running tests and linters after applying review-round changes. After each coder apply in `_step5_post_round_gates` (`python/review_and_fix.py`), the code calls `_run_relevant_checks_captured` which runs the full `make py-lint py-test` suite. This is wrong: tests and linters are run at a later dedicated stage (Step 3 and Step 6). Only pre-commit hooks should fire naturally when the review round commits. The post-apply check run is a redundant full test suite invocation per accepted finding that adds ~12 minutes of silent unlabeled work per finding per round.

## Reproduction scenario

Run `/implement` on any Python-heavy target that generates accepted findings in Step 5 review rounds. Inspect the per-round Gantt chart in the final summary. Observe multi-hour round windows with large unlabeled gaps between each `cursor/apply` bar. Each gap is one `make py-lint py-test` run (`~12–15 minutes`) triggered by `_run_relevant_checks_captured` at `python/review_and_fix.py:1836`.

Confirmed in run `AB90FD92-70C9-4D91-AC26-9D69349E2C0C` (issue #5464):
- Round 1 window: 7257s (2h 1m); review core: ~652s; visible `cursor/apply` bars: ~2686s; unlabeled gap: ~3919s.
- 4 accepted findings × ~1 post-apply check run = ~4 full test suite runs hidden in gaps per round.

## Expected behavior

`_step5_post_round_gates` does not run `make py-lint py-test` after each coder apply. The only test/lint runs during the review-apply loop come from pre-commit hooks when the loop makes a commit. Dedicated check passes run at Step 3 (after implementation) and Step 6 (after review fixes), which are the correct check points.

## Observed behavior

`_step5_post_round_gates` (`python/review_and_fix.py:1827`) runs `_run_relevant_checks_captured` (line 1836) immediately after every `fix-applied` round result. On check failure it also runs the lint-fix loop with up to `lint_max` additional `_run_relevant_checks_captured` rechecks (lines 1871, 1883, 1902). All of these runs execute the full `make py-lint py-test` suite via `checks.run_relevant_checks(site="step5-review-fixes", ...)`. None record a timing entry, so they appear as blank gaps in the Gantt chart (see companion bug #5539).

## Root cause analysis

`_step5_post_round_gates` was written to verify that coder-applied fixes do not break tests before the round advances. However, this per-apply check is architecturally wrong for two reasons:

1. **Redundancy with Step 6**: Step 6 runs `checks.run_relevant_checks(site="step6")` after all review commits are done, covering the same surface. A failure here will be caught there.
2. **Cumulative cost**: with N accepted findings per round, there are N sequential full test-suite runs inside the round, each taking ~12 minutes. For 4 accepted findings per round across 3 rounds, that is up to 12 full test-suite runs (potentially ~2.4h of test time) beyond what Step 3 and Step 6 already provide.

The pre-commit hook fires naturally on commit and covers lint enforcement without a separate explicit `run_relevant_checks` call.

## Evidence

- `python/review_and_fix.py:1836`: `checks = _run_relevant_checks_captured(implement_tmpdir)` — first call in `_step5_post_round_gates` after every `fix-applied` result.
- `python/review_and_fix.py:1871,1883,1902`: three additional `_run_relevant_checks_captured` rechecks inside the lint-fix while loop.
- `python/review_and_fix.py:3016`: `_step5_post_round_gates` called on every `result.status == "fix-applied"` in the main review loop.
- `python/review_and_fix.py:1783–1789`: `_run_relevant_checks_captured` calls `checks.run_relevant_checks(proc, site="step5-review-fixes", ...)` — full suite.
- `python/checks.py:91,101`: `site.startswith("step5")` handling confirms `step5-review-fixes` runs the full check surface.
- `python/timing.py` `TIMING_TASK_KINDS_ALLOWED`: no entry for post-apply checks → these runs produce zero Gantt rows (confirmed by companion bug #5539).
- Empirical: `make py-test` on the repo takes ~23s for `test_analyze_issues.py` alone; the full suite takes considerably longer. The Step 6 pass observed at 719s (12 min) in run `AB90FD92-70C9-4D91-AC26-9D69349E2C0C` confirms the per-run cost.
- `Makefile:100`: `py-test` target runs the full Python test suite via `python3 -m pytest python/`.
- Step 3 (`skills/implement/scripts/run-step-checks.sh --site step3`) and Step 6 (`python/cli.py implement checks-commit-route --checks-site step6`) both already run the full relevant-checks suite.

## Affected files

- `python/review_and_fix.py` — `_step5_post_round_gates` (lines ~1827–1909): remove `_run_relevant_checks_captured` call and the entire lint-fix retry loop that follows it. Remove `_run_relevant_checks_captured` helper itself if it has no other callers after this change.
- `python/test_review_and_fix.py` — update any tests that assert `_step5_post_round_gates` calls checks, or assert `lint-fix-main-agent-required` stall behavior that is no longer reachable without the check call.
- `python/checks.py` — no change required, but `run_lint_fix` may also become unreachable from Step 5; audit callers.

## Suggested fix(es)

1. In `_step5_post_round_gates`, remove the `_run_relevant_checks_captured(implement_tmpdir)` call at line 1836 and the entire lint-fix while loop (lines ~1842–1909). Return `(None, None, True)` unconditionally when `result.status == "fix-applied"` (advance to the next round).
2. If `_run_relevant_checks_captured` has no remaining callers, delete it.
3. The existing Step 3 and Step 6 check passes remain unchanged and continue to catch test/lint failures introduced by review fixes.
4. Update `python/test_review_and_fix.py` to remove or rework assertions that depend on post-apply check behavior (`lint-fix-main-agent-required`, `lint-fix-failed`, `lint-fix-attempt-cap` stall paths that flow from `_step5_post_round_gates`).
5. Verify that `make py-test` and `make lint` still pass after the removal.

## Open questions

- Are there any cases where the post-apply checks in `_step5_post_round_gates` caught a failure that Step 6 would NOT have caught? If so, those cases need to be documented and a targeted check (not full suite) may be warranted.
- Does removing the lint-fix loop from `_step5_post_round_gates` leave `run_lint_fix` in `python/checks.py` entirely unused from Step 5, or is it still called from elsewhere in the review-and-fix loop?
- The companion bug (#5539) adds Gantt labels for these check runs; if that fix is applied before this one, the labeled bars will appear and confirm the cost before removal. Consider sequencing this fix after #5539.

## Test plan
(no test plan section in plan-file)
