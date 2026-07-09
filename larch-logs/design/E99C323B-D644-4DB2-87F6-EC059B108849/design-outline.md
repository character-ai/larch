## Proposed Design Outline

### Goals
- Anchor the flush-integrity requirement in `ARCHITECTURAL_INVARIANTS.md` as `I-Flush-1`.
- Add a post-flush completeness check: a missing required artifact without a matching execution-issue entry fails the flush with a distinct exit code.
- Prove all three paths with regression tests.

### Non-goals
- Backfilling historical committed run logs.
- Changing the artifact schema or adding new artifact types.
- Modifying readers (`/analyze-bugs`, `/audit-runs`, `/report-tokens`).

### Approach sketch
- Append the `## Run-log integrity` section to `ARCHITECTURAL_INVARIANTS.md` verbatim (work item 1).
- Identify the required artifact set per run kind using existing manifest/ledger machinery in `run_log_manifest.py` or `run_log_flush.py`.
- Add a pre-commit check gate: iterate required artifacts; for each missing one, verify a matching category-keyed execution-issue entry exists; fail loudly with a new exit code if not.
- Keep optional artifacts fail-soft; the check is additive for schema evolution.
- Extend `python/tests/report/test_run_log_flush.py` with four scenarios.

### Surfaces in scope
- `ARCHITECTURAL_INVARIANTS.md`
- `python/larch/report/run_log_flush.py`
- `python/larch/report/run_log_manifest.py` (possibly, for artifact enumeration)
- `python/tests/report/test_run_log_flush.py`

### Open questions
- Exact hook seam: pre-commit validator inside `flush_logs_pre` vs. a dedicated function in `run_log_manifest.py`. /design resolves after reading both files.
