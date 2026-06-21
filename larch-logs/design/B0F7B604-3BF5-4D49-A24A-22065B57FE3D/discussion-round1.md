## Decision 1: Confirmed root cause
- **Question**: Why is the typed `p`/`progress` zero-turn report no longer working in both `/implement` and `/design`?
- **Resolution**: `report_main` in `python/progress_report.py` calls `logging_util.quiet_init(argv0="cli.py")`, which does `os.dup2(log_fd, 1)` — redirecting stdout (FD 1) into a quiet log file. The subsequent `print(report)` writes into that log, so `hook-progress-report.sh`'s `report=$(... progress report ...)` capture is empty. With an empty report the hook emits no `{decision:"block"}`, so `p`/`progress` falls through to a normal LLM turn. Verified empirically: `LARCH_QUIET_DISABLE=1` → report on stdout; default → 0 stdout bytes, report found in the quiet log. Single root cause explains both the `/implement` and `/design` symptoms.
- **Source**: codebase

## Decision 2: Fix breadth — audit sibling commands
- **Question**: Should the fix be minimal (`report_main` only) or also audit sibling `cli.py` commands for the same pattern?
- **Resolution**: Also audit. In-scope inline fix is `report_main`. Audit method: among `cli.py`-dispatched `*_main` functions that call `quiet_init`, find any that emit their **primary deliverable to plain stdout** (`print`/`sys.stdout.write`) rather than the FD-3 `emit`/`contract_stream` contract stream — those are the ones broken when a consumer captures raw stdout. Fix-vs-OOS rule: fix inline any that are the same unambiguous captured-stdout-deliverable bug (identical trivial pattern); OOS-file any where correct behavior is ambiguous or a fix would alter a deliberate quiet contract. Expectation: `report_main` is the primary/only offender (the FD-3 contract is well-established; ~35 modules call `quiet_init` and the rest emit via FD 3).
- **Source**: user (breadth) + codebase (boundary)

## Decision 3: Acceptance — automated regression test
- **Question**: What defines "done"?
- **Resolution**: An automated regression test that exercises `report_main` (or the `cli.py progress report` subprocess) under a quiet-enabled environment and asserts the report text reaches **stdout** (not the quiet log). This is the exact coverage gap that let the regression land — `test_progress_report.py` currently has zero `report_main`/stdout/quiet coverage. No live-QA acceptance gate required.
- **Source**: user

## Decision 4: Hard constraints / non-goals
- **Resolution**: Preserve the hook's fail-open contract (no blocking ordinary prompts; no network; no file writes). Preserve the `{decision:"block",reason:...}` hook output contract — the hook is not the regression. Do NOT redesign the progress engine or introduce a literal "status file"; the existing dynamic render (ship-pr state, design plan-review detail, generic step) IS the feature. Keep `report_main` writing its deliverable to plain stdout (it never needed the FD-3 contract). Out of scope: the separate, already-addressed stale-pointer selection bug (#4024 / wrong-tmpdir family). `SECURITY.md` needs no change — behavior is restored, not changed (the documented hook surface is unchanged). Honor `script-md-siblings`: update `progress_report` test coverage and any sibling `.md` only as the change requires.
- **Source**: codebase / user
