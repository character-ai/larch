### FINDING_1: Baseline pytest packing does not dedupe retried matrix attempts before `compute_medians`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Baseline LPT packing uses `compute_medians` on all parsed `call` rows without latest-attempt dedup per `(run_id, shard)`. When a baseline CI run retries a `python-tests` matrix job, `parse_log` can retain duration sections from every attempt while `shard_totals_per_run` / verification keep only the latest attempt. Packing can overweight or double-count retried work, producing a `shard-assignments.json` optimized on stale timings, failing Python verification, or requiring another manual rebalance run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Filter rows to the latest attempt per (run_id, shard) — reuse _split_pytest_shard_attempts — before compute_medians in the Python rebalance path; document the same rule in rebalance.md and cover it in test_pytest_ci_timing.py
  - From Cursor-Pragmatic: Filter rows to latest `attempt` per `(run_id, shard)` before `compute_medians` (or teach `compute_medians` to do so). Add a unit test that two duration banners in one shard yield one median per nodeid for packing.

### FINDING_2: Harness baseline timing can be fetched twice or via divergent code paths
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a harness pre-write fetch gate but does not retire the existing inline baseline loop (`run_list_successful` plus per-run `_collect_log_rows`). Under `--kind harness` or `all`, the script may fetch and parse the same CI logs twice, or the old loop and the new gate may diverge on skip-on-failed-log semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After `ci_timing_fetch` lands, route every harness baseline read through `harness_ci_timing.fetch_timing_rows` and keep `_collect_log_rows` only for per-run verification logs (or one shared helper used by both)

### FINDING_3: Post-PR verification workflow dispatch is not bound to Python-selected kinds
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Post-PR verification-run triggering is not tied to Python-selected kinds. Under `--kind python` (or the Python leg of `--kind all`), an implementer could gate `workflow_dispatch` / `_trigger_and_wait` on the harness leg only. Python verification would then read stale or empty logs and fail-closed (or pass on wrong data) even though baseline packing succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the Verification section and `rebalance.md`, state explicitly that after PR creation any selected leg that runs post-PR verification (harness, python, or both) shares one `n_verify_runs` workflow_dispatch loop before leg-specific collection; Python fail-closed checks run only after those runs complete
