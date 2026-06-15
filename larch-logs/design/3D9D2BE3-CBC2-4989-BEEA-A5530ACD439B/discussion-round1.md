## Decision 1: MAIN_ADVANCED rebase routing
- **Question**: Should MAIN_ADVANCED route to the same rebase path as `monitor.goto_rebase`, or does it need different handling?
- **Resolution**: Route through the same rebase path (write phase="rebase", pre_rebase flush, rebase_and_push, PrePushConflictHandoff handling, increment rebase_count, continue). MAIN_ADVANCED always means main has advanced past the PR branch at merge time — rebase is the only valid next action.
- **Source**: codebase (python/ship.py lines 1583-1651)

## Decision 2: rebase.py allow_output_fallback scope
- **Question**: Should allow_output_fallback=True apply to both codex and cursor conflict-fix launchers, or only one?
- **Resolution**: Both codex and cursor; Claude does not use the sidecar fallback. Pre-clear must happen before each launch.
- **Source**: codebase (python/rebase.py lines 203-212, python/agents.py ingest_launcher_token_sidecar)

## Decision 3: research-phase.md exit-code fix pattern
- **Question**: Which pattern to use for safe exit-code capture in strict-mode bash?
- **Resolution**: `rc=0; command || rc=$?` (the `||` form is idiomatic and works under set -euo pipefail). The `if ! cmd; then rc=$?` pattern always captures 0 because `!` inverts the condition before `then` executes.
- **Source**: codebase (BASH_AUTHORING.md, research-phase.md lines 194-205)

## Decision 4: TIMING_CI_TASK_KINDS_ALLOWED placement
- **Question**: Should TIMING_CI_TASK_KINDS_ALLOWED be exported from timing.py or kept private in progress_report.py?
- **Resolution**: Keep the CI task kind set local to progress_report.py as a module-private constant — avoids a new import dependency between modules that were previously independent, and the set is only needed for Gantt filtering.
- **Source**: codebase (python/progress_report.py imports nothing from python/timing.py)

## Decision 5: progress_report.py CI filter implementation
- **Question**: Add a parameter to _progress_vendor_rows or filter in _render_inflight_gantt after the call?
- **Resolution**: Add skip_ci: bool = False parameter to _progress_vendor_rows with a private _is_ci_gantt_row(kind, output) helper that mirrors the AWK skip_gantt_row logic in render-review-phase-detail.sh. Default=False preserves backward compat for tests and any future callers that want unfiltered rows. _render_inflight_gantt passes skip_ci=True.
- **Source**: codebase (render-review-phase-detail.sh lines 395-412, progress_report.py line 580)

4 decisions resolved.
