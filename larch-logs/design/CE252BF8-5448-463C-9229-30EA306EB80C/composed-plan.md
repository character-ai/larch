## Plan

## Scope

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection. The approved outline is binding.

## Approach

- Replace user-facing em dash separators in emitted strings under `python/larch/report/` and `python/larch/git/`.
- Use `: ` for the run-summary H2 heading: `## /{skill} run {run_id}: {outcome}`.
- Keep parser behavior safe for historical committed summaries. Prefer accepting both the new `: stalled` heading and legacy stalled headings without re-emitting legacy punctuation.
- Replace placeholder-only `—` values in report output with `N/A` or `-`, matching nearby table style.
- Skip comments and docstrings unless a docstring is rendered to users.
- Update tests and fixtures that assert the old heading, cost lines, progress lines, fallback summaries, and stalled recovery.

## Files to modify/create

### UPDATED: python/larch/git/pr_body.py

- Change `render_run_summary()` output:
  - cost line separator.
  - issue, PR, and OOS URL separators.
  - H2 heading separator.
- Change Slack issue announcement title separator if it can be shown to users.
- Keep the run-summary sentinel unchanged.

### UPDATED: python/larch/git/gh.py

- Change CI-log pointer at line 1781: replace `— last {tail_lines} lines shown` with `: last {tail_lines} lines shown` (or equivalent colon/comma punctuation).

### MAY_UPDATE: python/tests/git/test_gh.py

- Update only if it asserts the CI-log pointer text.

### UPDATED: python/larch/report/report_tokens_cost.py

- Change the printed cost line from an em dash separator to a colon or comma separator.
- Update expected cost rendering tests.

### UPDATED: python/larch/report/run_logs.py

- Change failure-log suffix separators and the step heading separator in emitted markdown.
- Keep run-log record shape intact.

### UPDATED: python/larch/report/progress_report.py

- Change live progress headers for Step 3 and Step 5.
- Change top-reviewer score separators.
- Replace `—` missing-value placeholders in emitted tables with `N/A` or `-`.
- Keep regexes that must read old timing labels backward-compatible when needed.

### UPDATED: python/larch/report/_progress_report_live.py

- Change generic live status text separator.
- Replace `—` placeholder returns with `N/A` or `-`.

### UPDATED: python/larch/report/final_report.py

- Update stalled-heading detection for the new `: stalled` H2 (`endswith(": stalled")`).
- Preserve detection of legacy `— stalled` headings so historical committed logs still recover.
- Ensure `reconcile_stalled_summary_from_manifest` writes the new `: ` separator when rewriting stalled headings; do not re-emit the em-dash separator.
- Avoid adding any new em-dash emitting code.

### UPDATED: python/larch/report/run_log_flush.py

- Change session-transcript warning entry separators.

### UPDATED: python/larch/report/tokens.py

- Change rendered token summary separators and no-measurement text.
- Change review-lane measurement suffixes.

### UPDATED: python/larch/report/gc_run_logs.py

- Change emitted dirty-tree diagnostic punctuation.

### UPDATED: python/larch/report/cleanup_implement_logs.py

- Change emitted dry-run diagnostic punctuation.
- Leave comments and docstrings alone unless rendered.

### UPDATED: python/larch/design/design_summary.py

- Change degraded fallback H2 at line 646 to match the new run-summary heading format (`: ` separator).
- Change the enrich-degraded warning at line ~331 to use compliant punctuation (colon/comma instead of em dash).
- Change any other em-dash emitting line in this file.

### UPDATED: python/tests/git/test_pr_body.py

- Update run-summary fixtures and assertions for the new heading and separators.
- Keep sentinel assertions unchanged.

### UPDATED: python/tests/report/test_report_tokens_cost.py

- Update cost-line expectations.

### UPDATED: python/tests/report/test_run_logs.py

- Update final-summary fixtures, split helpers, and stalled recovery assertions.
- Add or keep coverage that old stalled summaries still recover if compatibility is implemented.

### UPDATED: python/tests/report/test_run_log_flush.py

- Update session-transcript warning expectations.

### UPDATED: python/tests/report/test_progress_report.py

- Update live progress, table placeholder, and top-reviewer expectations.

### MAY_UPDATE: python/tests/report/test_final_report.py

- Update only if existing tests assert specific heading text that changes. Stalled recovery is primarily covered in `test_run_logs.py` and `test_ship.py`; add targeted `: stalled` detection tests here only when they cover gaps not covered there.

### UPDATED: python/tests/report/test_tokens.py

- Update token summary and no-measurement expectations.

### UPDATED: python/tests/design/test_design_summary.py

- Update design final-summary heading fixtures and fallback expectations.

### UPDATED: python/tests/design/test_design_pause.py

- Update paused design summary fixture and assertions.

### UPDATED: python/tests/implement/test_ship.py

- Update ship final-summary heading fixtures and heading parsing helpers.
- Keep stalled-summary correction coverage intact.

### MAY_UPDATE: python/tests/report/test_gc_run_logs.py

- Update only if it asserts the dirty-tree diagnostic text.

### MAY_UPDATE: python/tests/report/test_cleanup_implement_logs.py

- Update only if it asserts dry-run output.

### UPDATED: python/tests/report/test_run_log_tolerance.py

- Update both summary heading fixtures from the old em-dash separator to the new colon separator. Keep existing assertions intact.

### MAY_UPDATE: python/tests/issue/test_audit_runs.py

- Update heading fixtures only if audit-run parsing expects the old separator.

### MAY_UPDATE: python/tests/report/test_retro_fix_cursor.py

- Update heading fixture only if the test reads current summary heading format.

## Edge cases

- Historical committed `final-summary.md` files may still contain old headings. Do not break stalled recovery or tolerance scans.
- Some em dash literals are in comments, docstrings, regex compatibility, or test legacy fixtures. Do not treat those as emitted output unless the code renders them.
- Timing labels and step names may be wire-like data. Do not rename timing ledger labels unless the output itself is the target.
- Table placeholders should stay readable and parse-safe. Prefer `N/A` for missing values in markdown tables.

## Failure modes

- A downstream stalled-summary parser may miss stalled summaries if it only checks the old H2 suffix.
- A broad punctuation replacement may alter wire labels, test fixture setup, or committed-log compatibility.
- Replacing placeholders inconsistently may make round-summary tests fail or reduce table readability.

## Testing strategy

- Run focused unit tests:
  - `python -m pytest python/tests/git/test_pr_body.py`
  - `python -m pytest python/tests/report/test_report_tokens_cost.py python/tests/report/test_run_logs.py python/tests/report/test_run_log_flush.py`
  - `python -m pytest python/tests/report/test_progress_report.py python/tests/report/test_final_report.py python/tests/report/test_tokens.py`
  - `python -m pytest python/tests/design/test_design_summary.py python/tests/design/test_design_pause.py`
  - `python -m pytest python/tests/implement/test_ship.py`
- Run targeted greps after edits:
  - `git grep -n $'\u2014' -- python/larch/report python/larch/git python/larch/design/design_summary.py`
  - Review each remaining hit and confirm it is a comment, docstring, legacy parser compatibility, or non-emitted fixture.
- Render one implement summary and one design summary through existing unit helpers or CLIs, then assert their run-summary blocks contain no em dash.

## Acceptance

- Run focused unit tests:
  - `python -m pytest python/tests/git/test_pr_body.py`
  - `python -m pytest python/tests/report/test_report_tokens_cost.py python/tests/report/test_run_logs.py python/tests/report/test_run_log_flush.py`
  - `python -m pytest python/tests/report/test_progress_report.py python/tests/report/test_final_report.py python/tests/report/test_tokens.py`
  - `python -m pytest python/tests/design/test_design_summary.py python/tests/design/test_design_pause.py`
  - `python -m pytest python/tests/implement/test_ship.py`
- Run targeted greps after edits:
  - `git grep -n $'\u2014' -- python/larch/report python/larch/git python/larch/design/design_summary.py`
  - Review each remaining hit and confirm it is a comment, docstring, legacy parser compatibility, or non-emitted fixture.
- Render one implement summary and one design summary through existing unit helpers or CLIs, then assert their run-summary blocks contain no em dash.

difficulty: MODERATE
mechanical_churn: false
diff_lines: 180
