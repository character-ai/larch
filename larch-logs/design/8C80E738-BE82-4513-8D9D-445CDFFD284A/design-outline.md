## Proposed Design Outline

### Goals
- Every `run_relevant_checks` and `run_lint_fix` run in a review round renders as a labeled Gantt bar with accurate start/end.
- Coverage is source-level: all callers (Step 5 review rounds, Step 6 CI, future) emit bars automatically.
- No unlabeled blank gaps remain in the per-round Gantt for these two functions.

### Non-goals
- No redesign of the Gantt renderer, timing-ledger format, or round-window logic.
- No call-site wrapping in `_step5_post_round_gates` (would double-count against the source-level bars).
- No per-attempt task-kind encoding; each call is already its own bar.

### Approach sketch
- Instrument `run_relevant_checks` and `run_lint_fix` in `python/checks.py`: capture start/end around the real run and record one `timing record-vendor-task` (vendor `claude`) per invocation.
- Resolve the ledger from the existing `tmpdir`/env by reusing the `_mark_step_ledger` subprocess pattern; no new threaded ledger param, no caller edits.
- Wrap each record call in failure-suppression so a ledger error never aborts a check or lint run.
- Add new generic task-kinds to `TIMING_TASK_KINDS_ALLOWED` in `python/timing.py`; pick the record `--output` basename so bars label as `claude/...`.

### Surfaces in scope
- `python/checks.py` — `run_relevant_checks`, `run_lint_fix` instrumentation.
- `python/timing.py` — `TIMING_TASK_KINDS_ALLOWED` new task-kinds.
- `python/test_checks.py`, `python/test_review_and_fix.py`, `python/test_timing.py` — regression coverage.

### Open questions
- Task-kind + output basename for clean labels: `claude-relevant-checks` / `claude-lint-fix` vs the issue's `claude-post-apply-checks` / `claude-lint-fix-attempt`.
- Lint-fix vendor label: always `claude`, or reflect the actual coder (`coder_tool`) that applied fixes.
