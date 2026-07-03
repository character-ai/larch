## Decision 1: OOS_1 fix depth (flush-timing guarantee)
- **Question**: A safe OOS_1 fix requires careful push/flush ordering in the CI-fix and merge loop (a naive "flush immediately" adds a new git push mid-loop, which can retrigger CI on a fresh HEAD, the same failure class as past incidents #5217 and #5186). Should the design fix both OOS_1 and OOS_5 properly, do a best-effort OOS_1 fix only, or file OOS_1 separately and fix only OOS_5 now?
- **Resolution**: Fix both properly. Solve OOS_1 with correct push/flush ordering even if it touches the CI-fix/merge loop, and fix OOS_5 (swallowed append).
- **Source**: default (AskUserQuestion timed out after 60s with no response; proceeded with the recommended option, per this skill's documented timeout-default safety policy since /design gates only publish plan text).

## Decision 2: Hard constraint — no direct push to main, no branch resurrection
- **Question**: What existing invariants must the OOS_1 fix preserve?
- **Resolution**: The fix must never commit or push directly to `main`, and must never push to a PR branch after merge (GitHub may have auto-deleted it; pushing would resurrect it). `python/larch/state/finalize.py::_teardown_log_flush` already guards on `not post_merge_sentinel.exists()` and `branch not in {main, master}` before committing; this guard must remain intact.
- **Source**: codebase (`python/larch/state/finalize.py` lines 623-680; confirmed by existing project convention that larch never pushes directly to main).

## Decision 3: Hard constraint — no new CI-retriggering push
- **Question**: What must the OOS_1 fix avoid regressing?
- **Resolution**: Any new push introduced to guarantee flush timing must not reintroduce the failure classes from #5217 (redundant head-moving push on a fresh run) or #5186 (perpetual no-ci-checks-observed loop on resume). Mechanism is left to plan drafting/review, not fixed here.
- **Source**: codebase (`python/larch/implement/ci_monitor.py` ~1440-1514, `python/larch/implement/ship.py` ~723, `python/larch/implement/ship_merge.py::_post_ensure_flush_and_push` docstring citing #5217/#5186).

## Decision 4: OOS_5 scope
- **Question**: Should the "don't swallow warning-append failures silently" fix cover only `_log_guidelines_ship_warning`, or broader suppress(Exception) patterns in the same file?
- **Resolution**: Narrow scope: only `ship_guidelines.py::_log_guidelines_ship_warning`'s `suppress(Exception)` around `run_logs.append_execution_issue`, matching the issue's literal description. Other suppress patterns in `ship_guidelines.py` / `architectural_guidelines.py` are out of scope.
- **Source**: codebase (issue #6061 body: "warning-append failures are hidden behind suppress(Exception)" refers specifically to this one call site).

## Decision 5: Test coverage requirement
- **Question**: What must be tested to consider this fixed?
- **Resolution**: A regression test must simulate the exact race: a CI-fix round invalidates the guideline note (writing a warning to execution-issues.md), then a clean merge follows with no other retry/stall. The warning must appear in the committed `execution-issues.ndjson` batch afterward. A second test must confirm an append failure in `_log_guidelines_ship_warning` is no longer fully silent (e.g. surfaces via stderr, a Tool Failures entry, or a return value the caller checks).
- **Source**: codebase (mandatory Testing strategy section) and issue #6061 suggested fix.

Record: 5 decisions resolved (1 via AskUserQuestion timeout-default, 4 via direct codebase exploration).
