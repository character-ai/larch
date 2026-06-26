## Acceptance

- `python/timing.py` `TIMING_TASK_KINDS_ALLOWED` includes `claude-relevant-checks` and `claude-lint-fix`.
- `checks.run_relevant_checks` records one `claude-relevant-checks` vendor-task row per invocation through the injected `Runner`, with `--vendor claude` and `--output` basename `claude-relevant-checks.txt`.
- `checks.run_lint_fix` records one `claude-lint-fix` vendor-task row per non-Claude invocation and skips the outer record when `outcome.coder_tool == "claude"` (the Claude lint-fix launcher already emits that row).
- Both public wrappers record in `finally` on exception paths (exit code `1`, status `complete`) and re-raise; timing-record failures are suppressed and never abort a check or lint run.
- `python/review_and_fix.py` defers `record_round_timing` for `fix-applied` rounds into a `try`/`finally` after `_step5_post_round_gates`, so post-apply vendor rows fall inside the round Gantt window. The deferred call also fires on `gate_continue=True` rounds and on post-gate exceptions, before any `continue`.
- No call-site timing wrappers are added in `_step5_post_round_gates`; source-level `checks.py` instrumentation is the sole producer of post-apply vendor rows (no double-counting).
- After a simulated `fix-applied` round, the timing ledger contains at least one `claude-relevant-checks` row, rendered as a labeled Gantt bar (`claude/relevant-checks`); the per-round Gantt window has no unlabeled gap for these two functions.
- `python/test_checks.py`, `python/test_timing.py`, and `python/test_review_and_fix.py` cover the helper routing, exception paths, Claude duplicate guard, allow-list, and deferred round timing. `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 265
