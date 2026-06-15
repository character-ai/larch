## Plan

Fix five latent ship/rebase/research/timing/progress robustness gaps with surgical Python and markdown edits. Add focused regressions for MAIN_ADVANCED rebase routing, rebase token sidecar fallback, research warning exit codes, timing CI task-kind parity, and live progress Gantt filtering.

### Files to modify/create

#### UPDATED: python/ship.py

Fix the MAIN_ADVANCED post-merge loop.

- In the merge-result branch, handle config.MERGE_RESULT_MAIN_ADVANCED differently from config.MERGE_RESULT_CI_NOT_READY.
- When merge returns MAIN_ADVANCED, route directly through the same rebase path used for monitor.goto_rebase: write phase="rebase" state, run the pre-rebase log flush, call rebase.rebase_and_push(...) with existing arguments, preserve PrePushConflictHandoff handling, increment rebase_count, increment iteration, write phase="ci-initial", continue.
- Leave CI_NOT_READY behavior unchanged, except keep the existing review-required probe.

#### UPDATED: python/test_ship.py

Add a regression for the MAIN_ADVANCED branch: stub monitor to return action="merge"/goto_rebase=False, stub merge to return MAIN_ADVANCED, assert rebase_and_push is called once and ship does not retry merge without rebasing.

#### UPDATED: python/rebase.py

Add token sidecar fallback parity for conflict-fix launchers.

- Before launching codex or cursor, pre-clear Path(f"{output}.token-record") with missing_ok=True.
- Pass allow_output_fallback=True to agents.ingest_launcher_token_sidecar(...) for codex and cursor. Keep Claude unchanged.

#### UPDATED: python/test_rebase.py

Extend conflict-launch token sidecar coverage: assert allow_output_fallback=True for cursor/codex, add pre-clear freshness test, and a case that omits TOKEN_RECORD= from stdout and proves fallback ingestion via the output sidecar.

#### UPDATED: skills/research/references/research-phase.md

Fix the Bash exit-code capture snippet: replace both `if ! command; then _rc=$? ...` blocks with explicit rc capture: `set +e; command; rc=$?; set -e`.

#### UPDATED: python/timing.py

Add codex-ci, cursor-ci, claude-ci to TIMING_TASK_KINDS_ALLOWED (plus a dedicated TIMING_CI_TASK_KINDS_ALLOWED constant that unions in). Keep legacy *-ci-fix names.

#### UPDATED: python/test_timing.py

Pin that record_vendor_task(...) accepts codex-ci, cursor-ci, claude-ci without an "unknown task-kind" warning.

#### UPDATED: python/progress_report.py

Filter live inflight Gantt rows: add a helper that excludes CI/probe rows from _progress_vendor_rows by task kind (kinds in TIMING_CI_TASK_KINDS_ALLOWED, patterns *-ci, *-ci-fix, *-ci-test) and output basename (ci.out, *-ci.out, ci-fix-*.out, claude.out, codex.out, cursor.out).

#### UPDATED: python/test_progress_report.py

Add filtering regressions: mixed-row _progress_vendor_rows test and an inflight Step 5 test that CI-only rows produce no Gantt.

### Edge cases

- MAIN_ADVANCED can arise from merge-state lag, admin failure, version advancement, or post-force-push recovery. All should force one rebase pass before another merge attempt.
- CI_NOT_READY must still wait/continue as before.
- Rebase sidecar fallback must not ingest stale ${output}.token-record from a previous attempt (pre-clear addresses this).
- Research ingestion warnings must report the real failing command rc, not 0.
- Progress filtering should exclude CI/probe rows by both task kind and output basename.

### Failure modes

- If pre-rebase flush skips for a non-allowed reason after MAIN_ADVANCED, return the same STALLED shape as the existing goto_rebase path.
- If conflict-fix sidecar pre-clear fails due to permissions, let the exception fail closed before launch.
- If timing import from progress_report.py causes a cycle, keep the helper local and add a parity assertion.

### Testing strategy

```
python3 -m pytest python/test_ship.py -k 'main_advanced or rebase'
python3 -m pytest python/test_rebase.py -k 'conflict_launch_fn'
python3 -m pytest python/test_timing.py python/test_progress_report.py
make py-lint && make py-test && make lint
```

## Acceptance

- ship.py MAIN_ADVANCED path triggers rebase.rebase_and_push before looping back to CI monitor.
- rebase.py conflict-fixer pre-clears the token-record sidecar and passes allow_output_fallback=True for codex/cursor.
- research-phase.md sidecar snippet captures real command exit codes.
- TIMING_TASK_KINDS_ALLOWED includes codex-ci, cursor-ci, claude-ci; no warnings for live CI launcher kinds.
- _progress_vendor_rows in _render_inflight_gantt excludes CI/probe rows matching the committed report filter.
- All new tests pass; make py-lint, make py-test, and make lint pass.

diff_lines: 245
