## Goal
Implement issue #4493: [IMPLEMENTING] rebalance: verify shard balance on real CI job wall-clock, not timing sums.

## Implementation Plan
`/rebalance-test-harnesses` (`.claude/skills/rebalance-test-harnesses/scripts/rebalance.py`) verifies the post-rebalance balance using the **sum** of per-target `LARCH_HARNESS_TIMING` medians per shard (`median_shard_totals(verify_rows)` in step 9) and applies `--balance-threshold` (default 15s) to that sum-spread. It never reads **real CI job wall-clock** (the Actions jobs API `started_at`/`completed_at` per `test-harnesses (N)` job).

Confirmed by grep: `rebalance.py` has zero `jobs`/`started_at`/`completed_at`/`duration` references; `gh.py` GETs `/jobs` only for failed-job names (`failed_jobs_read`), never durations.

## Why this is wrong

The sum of self-reported test timings is not what operators see in CI. Real job wall-clock = sum + roughly-constant per-job overhead (checkout, setup-python, deps, make) of ~12-15s. The operator-facing goal ("every shard under N seconds of wall-clock") is invisible to the script, and the verdict can be flatly wrong.

**Concrete example, PR #4492** (the rebalance after the timing-blind-spot fix #4491):

- Script verdict: `⚠ Shard balance FAILED (spread 20.6s > 15.0s)` on the sum metric.
- Real job wall-clock (jobs API, median of the 3 verification runs): worst shard 54s, fastest 37s, **0 shards over 60s** — the real outcome is a success.

The script reported FAILURE while the actual goal was met. Before #4491 the sum metric was even blind to untimed targets: a shard summed to ~24s but ran 133s.

## Proposed change

1. Add a `gh.py` helper `job_durations(runner, run_id, *, repo) -> dict[int, float]` that GETs `/repos/{repo}/actions/runs/{run_id}/jobs` (paginated) and returns `{shard: completed_at - started_at}` for `test-harnesses (N)` jobs. Reuse the jobs-API plumbing in `failed_jobs_read`.
2. In step 9, compute median per-shard wall-clock across the verification runs from the jobs API; report BEFORE/AFTER and key the pass/fail verdict on that metric (show the sum metric alongside if useful).
3. Express the threshold in operator terms: a `--max-shard-wall-clock` budget (pass/fail on the slowest shard's real wall-clock) and/or a real-wall-clock spread threshold. Keep the sum-based estimate as the pre-pack feasibility heuristic (no jobs-API data exists pre-merge); the post-merge verification should use real wall-clock.

## Acceptance

- `rebalance.py` step 9 reports real per-shard job wall-clock (jobs API) for the verification runs.
- The pass/fail verdict reflects the real-wall-clock goal, not (only) the `LARCH_HARNESS_TIMING` sum.
- `gh.py` gains a tested `job_durations` helper (`test_gh.py`).
- `rebalance.md` and `SKILL.md` updated.

## Test plan
(no test plan section in plan-file)
