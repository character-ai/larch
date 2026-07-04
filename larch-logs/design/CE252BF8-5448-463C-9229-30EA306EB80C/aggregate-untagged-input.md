### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1781-1782
- **Concern**: `run_logs_failed()` still emits a user-visible CI-log pointer with an em dash, but the plan does not list `gh.py`. Scenario: The issue acceptance grep targets all of `python/larch/git/`; leaving this string untouched fails the stated no-em-dash acceptance even after the planned `pr_body.py` edits
- **Proposed resolution**: Add `### UPDATED: python/larch/git/gh.py` to replace the pointer separator (for example `--- CI log (run …): last …`) and update any `test_gh.py` assertions if present

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:331
- **Concern**: The enrich-degraded warning appended to `final-summary.md` still uses an em dash and is not called out in the `design_summary.py` step. Scenario: A narrow implementation of the listed bullets (646-647 fallback only) leaves this user-facing summary line unchanged and the post-change `git grep` over `design_summary.py` still finds an emitted em dash
- **Proposed resolution**: Extend the `design_summary.py` step to scrub the enrich-degraded warning at line 331 (for example `**⚠ Enrich degraded: exec issue detail unavailable.**`) and update design-summary fixtures if they assert that text

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1772-1784,1848
- **Concern**: run_logs_failed still emits a CI-log pointer with an em dash. Scenario: Calling `cli.py gh run-logs` on a failed workflow still prints `--- CI log ... — last ... lines shown`, so the git package still violates the no-em-dash contract.
- **Proposed resolution**: Add `python/larch/git/gh.py` and `python/tests/git/test_gh.py` to the plan, replace the pointer separator with compliant punctuation, and assert the rendered prefix has no em dash.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/retro_fix_cursor.py:2,132; python/larch/report/retro_v3_sweep.py:2,90
- **Concern**: CLI help still inherits em dashes from the module docstrings used as argparse descriptions. Scenario: Running `python3 python/cli.py retro-fix-cursor --help` or `retro-v3-sweep --help` will still emit noncompliant punctuation, so the report-package sweep is incomplete.
- **Proposed resolution**: Add both scripts to the update set, rewrite the docstring headlines with compliant punctuation, and add a small help-output check.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/git/gh.py:1781-1782
- **Concern**: Missed emitted CI log pointer in python/larch/git/. Scenario: `run_logs_failed()` still prints `--- CI log (run …) — last …` to stdout via `gh run-logs`. The plan only lists `pr_body.py` under `python/larch/git/`, so the post-change `git grep` acceptance sweep on `python/larch/git/` fails and operator-facing CI log snippets keep em dashes.
- **Proposed resolution**: Add `### UPDATED: python/larch/git/gh.py` to replace the pointer separator (colon/comma). Update `python/tests/git/test_gh.py` only if a new assertion on the pointer line is added.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1780-1782
- **Concern**: CI-log pointer still hard-codes an em dash, and the file is absent from the planned sweep. Scenario: gh run-logs still prints a user-facing pointer with the banned separator, so the git/report surface is not fully scrubbed
- **Proposed resolution**: Add python/larch/git/gh.py to the plan and change the pointer separator to colon or comma punctuation

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:669-676
- **Concern**: Legacy stalled-summary rewrites still preserve the em dash separator. Scenario: When a manifest-only stalled summary is repaired to merged, the rewrite path can re-emit a heading like -- merged, so a newly written recovery summary still violates the no-em-dash contract
- **Proposed resolution**: Normalize the rewritten heading to the new colon form before writing, while still accepting legacy headings for detection

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/_progress_report_live.py:322-324
- **Concern**: Generic live progress echoes timing-ledger step labels verbatim, so em dashes in marks such as Step 2 — implementation still reach users after separator-only edits. Scenario: Plan changes the trailing — started separator and forbids renaming ledger labels, but _render_generic replays cols[4] labels unchanged. Post-edit source grep can pass while runtime progress lines and existing test_progress_report _write_mark fixtures still contain em dashes, violating acceptance that report-layer emitted strings contain none
- **Proposed resolution**: Add display-time U+2014 normalization when rendering step_label in _render_generic (and any other progress echo path), without mutating timing-ledger rows; extend the testing strategy with one live-progress helper assertion, not only run-summary renders

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1781
- **Concern**: The plan misses the CI log pointer emitted by `run_logs_failed`, which still hard-codes an em dash.. Scenario: A failed `gh run view` still prints `—`, so the no-em-dash contract remains broken on a shipped user-facing path.
- **Proposed resolution**: Change the separator in `python/larch/git/gh.py:1781` to colon or comma, and add or update the `run_logs_failed` coverage in `python/tests/git/test_gh.py`.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1781
- **Concern**: `run_logs_failed` CI log pointer still uses an em dash but is absent from the plan file list. Scenario: The post-edit grep and acceptance rule cover all of `python/larch/git/`; this stdout string is user-facing when `gh run-logs` runs, so the sweep can fail or the hit can be misclassified as non-emitted
- **Proposed resolution**: Add `### UPDATED: python/larch/git/gh.py` to replace the pointer separator (for example `: last` instead of `— last`); extend `python/tests/git/test_gh.py` only if an assertion is added for the pointer text

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/design/design_summary.py:331
- **Concern**: Enrich-degraded append text is not named separately from the degraded-fallback block at 646-647. Scenario: On the enrich write-failure path, `final-summary.md` can still gain `**⚠ Enrich degraded — …**` even after the main renderer and 646-647 fallback are fixed, violating the fresh `/design` run-summary acceptance bullet
- **Proposed resolution**: Add an explicit bullet under `design_summary.py` to rewrite the enrich-degraded message at line 331; assert no em dash in the enrich-failure path in `python/tests/design/test_design_summary.py` if that path is not already covered

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:1772-1787
- **Concern**: run_logs_failed still emits an em dash in the CI-log pointer line, but this file is not in the planned sweep.. Scenario: `python/cli.py gh run-logs` will still print `— last N lines shown`, so the promised no-em-dash cleanup remains incomplete and the feature acceptance grep will keep finding a live emitter.
- **Proposed resolution**: Add `python/larch/git/gh.py` to the firm edit list, replace the separator with colon/comma/period punctuation, and add or update a focused test for `run_logs_main` output.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-Summary Parser Compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:331
- **Concern**: Plan omits enrich-degraded final-summary append path. Scenario: When post-publish enrich fails and issue-detail is unavailable, the code writes `**⚠ Enrich degraded — exec issue detail unavailable.**` into `final-summary.md`. That path is outside the plan bullets for degraded fallback H2/prose (lines 646-647), so a design run can still ship an em dash in the primary summary artifact.
- **Proposed resolution**: Add line 331 to `### UPDATED: python/larch/design/design_summary.py` (colon/comma separator) and extend `python/tests/design/test_design_summary.py` with a degrade-enrich assertion if the plan mandates that fixture.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-Summary Parser Compat
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/git/gh.py:1781
- **Concern**: `python/larch/git/gh.py` emit site missing from plan. Scenario: Acceptance and the post-edit grep target all of `python/larch/git/`, but only `pr_body.py` is listed. `run_logs_failed()` still emits `--- CI log (run …) — last …` to operators; the verification grep will flag this hit with no assigned fix.
- **Proposed resolution**: Add `### UPDATED: python/larch/git/gh.py` (colon/comma in the CI-log pointer) or document an explicit grep exception; add/adjust `python/tests/git/test_gh.py` if it asserts that string. ## Findings ### 1. correctness — `python/larch/design/design_summary.py:331` The plan updates degraded fallback output at lines 646-647 but not the enrich-degraded branch at line 331: degraded_body = ( degraded_body.rstrip("\n") + "\n\n**⚠ Enrich degraded — exec issue detail unavailable.**\n" ) That text is written to `final-summary.md` on the design publish path, so it is user-facing run-summary output. Without a plan step here, design summaries can still contain a literal em dash after the rest of the scrub lands. **Suggested revision:** Add the line 331 string to the `design_summary.py` update list and cover it in `test_design_summary.py` if the plan requires that fixture. ### 2. completeness — `python/larch/git/gh.py:1781` Issue acceptance and the planned grep sweep cover all of `python/larch/git/`, but the plan only lists `pr_body.py` under `git/`: pointer = ( f"--- CI log (run {run_id}, repo {repo}) — last {tail_lines} lines shown. " f"Full log: https://github.com/{repo}/actions/runs/{run_id} ---" ) `run_logs_failed()` returns this pointer to operators during CI failures. The planned `git grep` over `python/larch/git/` will surface this line with no assigned fix. **Suggested revision:** Add `gh.py` to the firm file list (or document a deliberate grep exception) and update `test_gh.py` if it asserts this text. --- **Plan coverage that looks sound (no finding):** - **Parser compatibility:** `final_report.py` stalled detection (`summary_heading_is_stalled`, `_summary_stalled_heading_index`) and `reconcile_stalled_summary_from_manifest` are in scope; `run_log_tolerance.py` matches outcome tokens at line end, so both `— stalled` and `: stalled` headings keep working. - **Primary emitters:** `pr_body.render_run_summary()` is the implement heading source; design uses `render run-summary` with fallback at 646-647. - **Tests:** Implement paths (`test_pr_body.py`, `test_ship.py`, `test_run_logs.py`, proposed `test_final_report.py` stalled cases) and design paths (`test_design_summary.py`, `test_design_pause.py`) are listed; stalled recovery fixtures in `test_run_logs.py` and `test_ship.py` are slated for separator updates including `split("—")` helpers.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-Summary Parser Compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:128-130; python/tests/report/test_run_log_tolerance.py:15-28; python/larch/report/run_log_tolerance.py:37-56
- **Concern**: Plan leaves `python/tests/report/test_run_log_tolerance.py` on MAY_UPDATE even though its stalled and bailed fixtures still hard-code the old em-dash heading separator.. Scenario: The new `: stalled` and `: bailed` run-summary format would ship without coverage on the committed-summary compatibility path, so the parser-facing contract is not fully verified.
- **Proposed resolution**: Move `python/tests/report/test_run_log_tolerance.py` to UPDATED and switch both summary fixtures to colon-headed summaries while keeping the existing assertions.
