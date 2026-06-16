### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pytest_ci_timing.py:139-148
- **Concern**: Baseline packing uses compute_medians on all parsed rows without latest-attempt dedup. Scenario: When a baseline CI run retried a python-tests matrix job, parse_log keeps call rows from every duration section (attempt 0 and 1+). compute_medians pools those seconds per nodeid while shard_totals_per_run dedupes to the latest attempt only. LPT packing can overweight or duplicate retried work and emit a shard-assignments.json that fails Python verification or needs another manual run
- **Proposed resolution**: Filter rows to the latest attempt per (run_id, shard) — reuse _split_pytest_shard_attempts — before compute_medians in the Python rebalance path; document the same rule in rebalance.md and cover it in test_pytest_ci_timing.py

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/rebalance-tests/scripts/rebalance.py:416-439
- **Concern**: Plan adds a harness pre-write fetch gate but never retires today’s inline baseline loop (`run_list_successful` plus per-run `_collect_log_rows`). Scenario: `--kind harness` or `all` can fetch and parse the same CI logs twice, or the old loop and the new gate can diverge on skip-on-failed-log semantics
- **Proposed resolution**: After `ci_timing_fetch` lands, route every harness baseline read through `harness_ci_timing.fetch_timing_rows` and keep `_collect_log_rows` only for per-run verification logs (or one shared helper used by both)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pytest_ci_timing.py:139-147
- **Concern**: Baseline nodeid medians used for LPT packing do not dedupe retried matrix attempts. Scenario: `compute_medians` aggregates every `call` row, but `shard_totals_per_run` / verification keep only the latest `attempt` per `(run_id, shard)`. A retried `python-tests` job can emit two duration sections; both attempts feed packing weights while verification ignores the first, producing assignments optimized on stale/double-counted timings and defeating the rebalance goal on the exact retry path the plan calls out in Edge cases.
- **Proposed resolution**: Filter rows to latest `attempt` per `(run_id, shard)` before `compute_medians` (or teach `compute_medians` to do so). Add a unit test that two duration banners in one shard yield one median per nodeid for packing.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/rebalance-tests/scripts/rebalance.py:104-111
- **Concern**: Post-PR verification-run triggering is not bound to Python-selected kinds. Scenario: Under `--kind python` (or a Python-only leg of `--kind all`), an implementer can gate `workflow_dispatch` / `_trigger_and_wait` on the harness leg only; Python verification then reads stale or empty logs and fail-closes (or passes on the wrong data) even though baseline packing succeeded
- **Proposed resolution**: In the Verification section and `rebalance.md`, state explicitly that after PR creation any selected leg that runs post-PR verification (harness, python, or both) shares one `n_verify_runs` workflow_dispatch loop before leg-specific collection; Python fail-closed checks run only after those runs complete

