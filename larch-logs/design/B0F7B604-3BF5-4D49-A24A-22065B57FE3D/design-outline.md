## Proposed Design Outline

### Goals
- Restore the zero-turn `p`/`progress` report so the hook's stdout capture is non-empty again (fixes `/implement` and `/design` together).
- Add the missing regression coverage so the stdout path cannot silently regress.
- Audit sibling `cli.py` commands for the same "quiet_init swallows a stdout deliverable" pattern; fix-inline or OOS-file.

### Non-goals
- No redesign of the progress engine and no literal "status file" — restore the existing dynamic render.
- No change to the hook's `{decision:"block"}` output contract or its fail-open behavior.
- No change to the unrelated stale-pointer selection logic; no `SECURITY.md` behavior change.

### Approach sketch
- Stop `report_main` (`python/progress_report.py`) from routing its deliverable through `quiet_init`; it uses plain `print`, so `print(report)` then reaches real stdout.
- Add a regression test in `python/test_progress_report.py` that runs `report_main`/`cli.py progress report` under a quiet-enabled env and asserts the report lands on stdout, not the quiet log.
- Audit `cli.py`-dispatched `*_main` functions that call `quiet_init` AND print a primary deliverable to plain stdout; apply Decision 2's fix-vs-OOS rule.

### Surfaces in scope
- `python/progress_report.py` (`report_main`)
- `python/test_progress_report.py` (new regression test)
- Read-only audit across `python/*.py` `*_main` `quiet_init` callers (inline edits only for a true same-bug sibling)
- `python/progress_report.md` sibling contract, if a behavior note changes

### Open questions
- None. (Whether any sibling is a same-bug inline fix vs OOS is resolved during the audit per Decision 2.)
