## Goal
Implement issue #4459: [IMPLEMENTING] [OOS] Deduplicate the ~25 multi-target pytest harness targets that re-run their full file.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Main agent
**Phase**: implement
**Vote tally**: N/A; follow-up from #4453

## Description

Follow-up to #4453 (per-target CI harness speedups). A `pytest --co` sweep across every `test-harnesses` Makefile target found ~25 source files run by 2+ harness targets that do NOT form a partition: most run the FULL file under several distinct target names, re-paying the whole file's runtime each time. Highest-impact offenders: `python/test_agents.py` (142-test file run in full by ~11 targets, e.g. test-parse-codex-usage / test-launch-codex-exec / test-launch-cursor-ci / test-launch-claude-ci / test-launch-codex-ci / test-run-external-agent-args / test-degraded-tools-gate / test-launch-claude-subprocess / test-launch-claude-review / test-agent-model-args / test-run-external-agent), `python/test_run_logs.py` (76 tests x 8 full-file targets), `python/test_tokens.py` (40 x 7), `python/test_redact.py` (40 x 4), `python/test_release.py` (30 x 4), `python/test_report_tokens_cost.py` (33 x 4), `python/test_implement_dispatch.py` (55 x 5), `python/test_timing.py` (28 x 4), `python/test_plan_review_panel.py` (7 x 3); plus several `-k`-sliced files with uncovered or overlapping tests (test_plan_quality.py, test_plan_review.py, test_review_and_fix.py, test_pr_body.py, test_bootstrap.py, test_admission.py, test_file_oos.py, test_stall_recovery.py, test_execution_issues.py). This is a much larger CI-time win than the research-target dedup in #4453 (roughly ~10x by re-paid full-file runtime). Suggested fix: for each file either slice its targets into disjoint `-k`/node-id selections (the #4453 A1/A2 pattern), or where targets are genuinely identical full-file runs, retire duplicates to one canonical target and update `scripts/test-harness-shards-coverage.sh` shard membership (the #4453 A3 pattern); then add each de-duplicated file to the `ENFORCED` allow-list in `scripts/lint-harness-pytest-partition.py` (the #4453 A4 guard) to lock it in. Measure with a `pytest --co` sweep per target; the guard accepts a Makefile-path argument for dry runs. Likely warrants several scoped PRs given the file count. #4453 intentionally scoped its A4 guard to only the 3 files it sliced because a global strict-partition guard would fail on all ~25 today.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
