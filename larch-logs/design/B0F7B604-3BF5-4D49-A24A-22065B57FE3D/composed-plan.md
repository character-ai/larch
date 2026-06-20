## Plan

Restore the zero-turn `p`/`progress` report. Root cause: `report_main` in `python/progress_report.py` calls `logging_util.quiet_init(argv0="cli.py")`, which redirects stdout (FD 1) into the lib-quiet log file. The later `print(report)` writes into that log, so `scripts/hook-progress-report.sh`'s `report=$(... progress report ...)` capture is empty, the hook emits no `{decision:"block"}`, and `p`/`progress` falls through to a normal turn. Verified: `LARCH_QUIET_DISABLE=1` prints the report to stdout; the default run leaves stdout empty and the report in the quiet log. One root cause explains both the `/implement` and `/design` symptoms.

### UPDATED: python/progress_report.py

Remove the `logging_util.quiet_init(argv0="cli.py")` call from `report_main`.

- `progress report` is a hook-captured stdout contract. Do not route its primary report through lib-quiet.
- Leave plain `print(report)` as the deliverable so it reaches real stdout.
- Keep the existing fail-open `try/except` behavior.
- Do not change `_report`, the dynamic renderers, session pointer selection, or hook JSON behavior.

### UPDATED: python/test_progress_report.py

Add a regression test that runs the real CLI as a subprocess under a quiet-enabled env and asserts the report reaches stdout. This is the coverage gap that let the regression land: there is no current `report_main`/stdout/quiet coverage.

- Build a live fixture: temporary `HOME`, repo cwd, implement (or design) tmpdir, `current-implement-env-<pid>.sh`, and a `timing-ledger.tsv` step mark.
- Run `[sys.executable, str(Path(__file__).with_name("cli.py")), "progress", "report", "--cwd", str(cwd)]`.
- Build the child env from `os.environ.copy()`, then `env.pop(config.ENV_LARCH_QUIET_DISABLE, None)`; set `LARCH_QUIET_ACTIVE=1`, a foreign `LARCH_QUIET_PID`, and `LARCH_QUIET_LOG_FILE` to a temp path. Scrubbing `LARCH_QUIET_DISABLE` is required, else `quiet_init` is a no-op and the test passes even when broken.
- Assert: exit code 0; stdout contains the report text; the quiet log is absent or lacks the report.

### Sibling audit (read-only; no extra inline files expected)

Audit `cli.py`-dispatched `*_main` functions that call `quiet_init` AND emit their primary deliverable via plain `print`/`sys.stdout.write` rather than the FD-3 `emit`/`contract_stream` contract stream. Those are the ones broken when a consumer captures raw stdout. Fix inline only an unambiguous same-bug captured-stdout deliverable; record ambiguous cases as out-of-scope follow-ups. Expected result: only `python/progress_report.py` changes inline. About 35 modules call `quiet_init`; the rest emit deliverables via FD 3 by design and are not affected.

## Acceptance

- `cli.py progress report --cwd <repo>` prints the report to stdout under a quiet-enabled env (`LARCH_QUIET_ACTIVE=1` set, `LARCH_QUIET_DISABLE` unset), not into the quiet log.
- Typing `p` or `progress` makes the hook emit `{decision:"block",reason:...}` with the report, so it renders without a model turn in `/implement` (ship-pr/review) and `/design` (plan-review).
- The new `python/test_progress_report.py` regression test fails if `quiet_init` is re-added to `report_main` (stdout empty plus report in the quiet log).
- Sibling audit completed: any same-bug command fixed inline or recorded as OOS; no unrelated `quiet_init` callers changed.
- Hook contract unchanged: fail-open preserved, no network or file writes, `{decision:"block"}` output shape unchanged. `SECURITY.md` needs no change.
- Repo gates pass: `make lint`, `make py-lint`, `make py-test`.

review_status: complete
rounds_completed: 1
diff_lines: 36
