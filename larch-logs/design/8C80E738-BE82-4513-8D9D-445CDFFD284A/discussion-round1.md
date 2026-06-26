## Decision 1: Instrumentation coverage breadth
- **Question**: Where should the post-apply timing instrumentation live, and how broad should coverage be (targeted Step 5 vs source-level checks.py vs comprehensive zero-gap)?
- **Resolution**: Source-level. Instrument `run_relevant_checks` and `run_lint_fix` in `python/checks.py` directly via an optional ledger handle, so every real caller (Step 5 review rounds, Step 6 CI, future callers) emits Gantt vendor-task bars automatically. Chosen for robustness and future coverage over the minimal targeted fix.
- **Source**: user

### Decision 1 follow-up: do (1) Targeted AND (2) Source-level together?
- **Question**: Operator asked whether combining the targeted Step 5 wrap (1) with source-level (2) adds value.
- **Resolution**: No. In Step 5 the only path to checks/lint is `_run_relevant_checks_captured` -> `run_relevant_checks` and `_run_lint_fix_loop` -> `run_lint_fix`. Source-level (2) already brackets those functions, emitting one bar per Step 5 call. Adding (1) would bracket the same calls one frame higher, producing two overlapping bars for the same interval (double-counting; inflates `vendor_task_averages`; clutters the Gantt). (2) alone closes the Step 5 gap and extends coverage to other callers. Proceed with (2) only.
- **Source**: codebase + operator (conditional "do both only if there is a point")

### Decision 1 detail: lint-fix internal coder time
- **Resolution**: `run_lint_fix` may invoke an external coder to apply lint fixes. The source-level bar brackets the whole `run_lint_fix` invocation so the internal coder time stays inside the bar and does not reappear as a fresh unlabeled gap.
- **Source**: codebase

## Decision 2: Gantt label granularity (task-kind naming)
- **Question**: Generic task-kind (e.g. `claude-post-apply-checks`) or per-round/per-attempt encoded (e.g. `claude-post-apply-checks-r1-a1`)?
- **Resolution**: Generic task-kinds. Each `v1 vendor` ledger row already renders as its own Gantt bar with its own start/end (`python/progress_report.py:1302-1326`), so generic kinds yield one bar per call. Per-attempt encoding is unnecessary and would (a) fall outside `TIMING_TASK_KINDS_ALLOWED` (warning noise) and (b) fragment `vendor_task_averages` into 1-sample buckets. Bar labels derive from the output basename, so output files are named to yield `claude/...` labels.
- **Source**: codebase

## Hard constraints (preserved, not user-gated)
- New task-kinds MUST be added to `TIMING_TASK_KINDS_ALLOWED` in `python/timing.py` in the same change (`.claude/rules/timing-task-kind-allowlist.md`).
- Timing-record failures must stay non-fatal to the checks/lint flow; instrumentation wraps record calls so a ledger error never aborts a check or lint run.
- The ledger handle must be optional and backward-compatible: existing `run_relevant_checks` / `run_lint_fix` callers and tests are unaffected when no ledger is supplied.
- `python/cli.py review-and-fix step5` behavior changes require a same-PR `python/test_review_and_fix.py` update (`.claude/rules/launcher-argv-test-coverage.md`).

## Non-goals
- No redesign of the Gantt renderer or timing-ledger format.
- No change to round-window computation; post-apply work already falls inside the recorded round window.
