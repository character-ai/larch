## Proposed Design Outline

### Goals
- Stop unbounded $TMPDIR top-level growth from the report-tokens `mkdtemp` sites via cleanup when the owning process is done with them.
- Make the existing age-based `cleanup run` sweep run automatically every session start, removing the "operator must remember /larch:cleanup" dependency.
- Add regression coverage proving report-tokens runs leave no new top-level $TMPDIR entries behind.

### Non-goals
- Do not synchronously clean the `_plan_quality_commands.py` mkstemp fallback; it is a cross-process `VALIDATE_LOG_FILE` hand-off read after this process exits (Round 1 Decision 2). Periodic sweep only.
- Do not alter the macOS auto-open-plot UX; cleanup must not race it (Round 1 Decision 1).
- Do not change where `sweep-design-logs.sh`'s scratch log or the no-session quiet-log land; both already carry the `larch-` prefix the existing reaper's glob matches.
- Do not search for leak sites beyond the issue's 5 named ones; treat the 2026-07-01 audit as the closed set.

### Approach sketch
- Wrap the two report-tokens `mkdtemp` call sites (`report_tokens_cli.py:66`, `report_tokens_render.py:219`) so the temp root is removed when the owning process is done with it, except skip synchronous removal when a plot was just auto-opened on macOS; the periodic sweep is the backstop for that case.
- Add a new SessionStart hook script mirroring `scripts/sweep-design-logs.sh`'s exact pattern (detached background subprocess, always exit 0, non-blocking) that launches `python3 python/cli.py cleanup run`, registered as a new `hooks/hooks.json` SessionStart entry.
- Add regression tests asserting no new top-level $TMPDIR entries survive a report-tokens run, covering both the CLI and render fallback paths.

### Surfaces in scope
- `python/larch/report/report_tokens_cli.py`
- `python/larch/report/report_tokens_render.py`
- `hooks/hooks.json` + a new SessionStart hook script under `scripts/` (with sibling `.md` doc)
- `python/tests/report/test_report_tokens_cli.py` and `test_report_tokens_render.py`

### Open questions
- None.
