## Proposed Design Outline

### Goals
- Add frozen dataclass result types and module-level typed callable entry points for all four report modules.
- Keep every `*_main` wrapper emitting identical KV-stdout.
- Add tests for the new typed callables and result types.

### Non-goals
- Changing KV-stdout output format of any existing CLI entry point.
- Modifying out-of-scope callers (e.g., `design_pause.py`, `finalize.py`, `final_report.py`) except where the return type change is backward-safe.
- Touching `timing.py` class internals beyond adding module-level wrappers.

### Approach sketch
- Add `@dataclass(frozen=True)` result types in each of the four source modules (no new files).
- `progress_file.py`: add `PersistedRunResult` dataclass and `resolve_persisted_run()` typed callable; existing `resolve_persisted_repo_root()` stays unchanged.
- `statusline_install.py`: replace `install_statusline` `bool` return with `StatuslineInstallResult`; out-of-scope callers either discard the result or call via subprocess.
- `tokens.py`: add `BudgetCheckResult`, `ClaudeSourceResult`, `PrLineCountResult` dataclasses; change `check_step_token_budget`, `token_claude_source`, and `compute_pr_line_counts` to return them; add `token_mark()` module-level typed callable; update internal callers and `*_main` wrappers in-file; note `final_report.py` as MAY_UPDATE.
- `timing.py`: add `TimingMarkResult`, `VendorTaskResult`, `RoundResult`, `TimingReportResult` dataclasses; add module-level typed entry points `mark()`, `record_vendor_task()`, `record_round()`, `render_report()`; update `*_main` wrappers to delegate to them.

### Surfaces in scope
- `python/larch/report/progress_file.py`
- `python/larch/report/statusline_install.py`
- `python/larch/report/tokens.py`
- `python/larch/report/timing.py`
- `python/tests/report/test_progress_statusline.py`
- `python/tests/report/test_tokens.py`
- `python/tests/report/test_report_tokens_cli.py`
- `python/tests/report/test_timing.py`
- `python/larch/report/final_report.py` (MAY_UPDATE: adapt `compute_pr_line_counts` call site)

### Open questions
- None.
