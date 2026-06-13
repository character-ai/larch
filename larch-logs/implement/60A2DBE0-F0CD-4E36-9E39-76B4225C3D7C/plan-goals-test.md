## Goal
Implement issue #4215: [IMPLEMENTING] [OOS] render-review-phase-detail renderer + lint/migration doc drift — 5 items.

## Implementation Plan
## Plan

## Plan

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline as binding scope.
- Keep `scripts/render-review-phase-detail.sh` as the single timing-row owner.
- Do not change Item 5, including the `lint-retired-scripts` table row or `AGENTS.md`.

## Files to modify/create

### UPDATED: python/progress_report.py

- Remove the Python-only progress Gantt path:
  - `from gantt import GanttRow, format_mss, render_gantt`
  - timing/Gantt constants used only by progress charts
  - `_basename`
  - `_derive_progress_label`
  - `_progress_label_map`
  - `_parse_int`
  - `_timing_lines`
  - `_progress_round_windows`
  - `_progress_vendor_rows`
  - `_render_progress_timing_charts`
- Keep `_call_render_phase_detail_script` as the single delegate.
- Remove `--no-gantt` from the renderer argv so the shell renderer emits ASCII reviewer timing charts.
- Raise the shell delegate timeout above the current 6 seconds so the same call can cover table generation plus shell-owned Gantt rendering.
- Simplify `_render_review_detail` to return the shell delegate output only.
- Simplify `_render_design_review_detail` to return the shell delegate output only.
- Preserve existing best-effort behavior:
  - missing renderer returns `""`
  - renderer non-zero returns `""`
  - delegate timeout returns `""`
  - subprocess errors return `""`
  - markdown stripping still applies to renderer stdout

### UPDATED: python/test_progress_report.py

- Update `test_render_review_detail_argv`:
  - keep assertions for `--rounds-root`, `--timing-ledger`, and `--skill implement`
  - change the `--no-gantt` assertion to verify it is absent
  - assert the delegate subprocess timeout uses the raised value, not the old 6-second budget
- Update `test_design_detail_argv_uses_design_skill_and_rounds_root`:
  - keep assertions for design rounds root, timing ledger, and `--skill design`
  - change the `--no-gantt` assertion to verify it is absent
  - assert the delegate subprocess timeout uses the raised value, not the old 6-second budget
- Delete Python progress chart fixtures and tests:
  - `_write_progress_ledger`
  - `_assert_embedded_chart_invariants`
  - `test_progress_implement_appends_ascii_chart_from_explicit_live_ledger`
  - `test_progress_design_charts_ignore_skill_filters_and_use_13_column_layout`
  - `test_progress_chart_failure_preserves_detail`
  - `test_progress_round_windows_aggregate_multiple_rows`
  - `test_progress_multi_row_round_window_includes_vendor_and_title_span`
  - `test_progress_missing_ledger_preserves_detail_without_chart`
  - `test_progress_bad_ledger_preserves_detail_without_chart`
- Do not add replacement shell Gantt rendering tests. Existing `scripts/test-render-review-phase-detail.sh` owns chart content coverage.

### UPDATED: .github/workflows/ci.yaml

- In the `test-harnesses` job, remove the shard-12 Mermaid setup block:
  - shard-12 comment about `test-render-review-phase-detail`
  - `actions/setup-node`
  - node modules cache
  - Puppeteer cache
  - `Install Mermaid CLI (shard 12 renderer harness)`
- Keep the dedicated `lint-mermaid` job unchanged.
- Keep the test-harness matrix and `make test-harnesses-${{ matrix.shard }}` step unchanged.

### UPDATED: docs/linting.md

- In the Mermaid CLI linter row, remove the complete `test-render-review-phase-detail` generated-Mermaid claim.
  - Remove both the local-CLI clause and the GitHub Actions install clause for that harness.
  - Keep only the changed-Markdown Mermaid fence lint contract.
  - Do not leave wording that implies `mmdc` is required by `test-render-review-phase-detail`.
- In the CI usage bullet, remove the stale sentence that says `make test-harnesses-12` installs Mermaid before `test-render-review-phase-detail`.
- If there is a non-table linting prose mention that still says retired-script linting never matches bare basenames, update it to the scoped same-directory `.claude/skills/**/*.md` behavior described for `docs/python-migration.md`.
- Do not edit the `make lint-retired-scripts` table row. It is Item 5 and out of scope.

### UPDATED: scripts/render-review-phase-detail.md

- Update the `--timing-ledger` argv row to say per-round `type=round` rows supply:
  - the Time column through the `--skill`-filtered table window
  - per-round Cost attribution through the `--skill`-filtered table window
  - reviewer timing chart windows through the unfiltered Gantt window
- Update the **Time** data-source bullet:
  - say `type=round` rows are filtered by `--skill`
  - keep `max(end_s) - min(start_s)` per round
  - keep the missing-ledger fallback
- Update the **Cost** data-source bullet:
  - say per-round Cost attribution uses the same `--skill`-filtered table window as Time
  - do not imply Cost uses the unfiltered Gantt window
- Update the **Reviewer timing charts** data-source bullet:
  - say Gantt round windows aggregate `type=round` rows by round number without `--skill`
  - say vendor rows are selected by overlap and are not filtered by `--skill`
  - keep clamping, sorting, and cap language

### UPDATED: docs/python-migration.md

- Replace the “never matches repo-wide bare basenames” wording with the current behavior:
  - full repo-relative manifest paths still match everywhere
  - same-directory `$SCRIPT_DIR/<basename>.sh` forms still match
  - scoped bare-basename checks apply only in same-directory `.claude/skills/**/*.md` dev-skill docs when no live sibling `.sh` exists
  - repo-wide bare basenames outside that scoped branch are not matched

## Edge cases

- Progress reports may now show shell-rendered ASCII charts when timing data exists. This is intended.
- The raised delegate timeout reduces false-empty progress detail when shell Gantt rendering needs more than the old table-only budget.
- If the shell renderer cannot render charts, its existing degraded output remains the only source.
- `_strip_md_for_terminal` will continue stripping headings and table separators from the shell output.
- Design progress with mixed `implement` and `design` timing rows will rely on the shell split:
  - table Time uses `--skill`
  - table Cost uses `--skill`
  - Gantt windows ignore `--skill`

## Failure modes

- If `scripts/render-review-phase-detail.sh` is missing, exits non-zero, exceeds the raised timeout, or cannot run, progress detail remains empty.
- If the shell renderer has a Gantt extraction bug, progress reports inherit it. That is acceptable because the shell script is now the single owner.
- If tests still reference deleted private helpers, pytest will fail with attribute errors. Remove all such references in the same edit.

## Testing strategy

- Run focused Python tests:
  - `python3 -m pytest python/test_progress_report.py`
- Run renderer harness coverage:
  - `bash scripts/test-render-review-phase-detail.sh`
- Run repository relevant checks:
  - `bash scripts/relevant-checks.sh`
- If CI YAML or docs lint concerns remain, run:
  - `make lint-only`

diff_added: 18
diff_deleted: 332
mechanical_churn: true
diff_lines: 350


## Acceptance

- `python/progress_report.py` has no `_timing_lines`, `_progress_round_windows`, `_progress_vendor_rows`, `_render_progress_timing_charts`, or `from gantt import` line.
- `_call_render_phase_detail_script` no longer passes `--no-gantt` and uses a raised subprocess timeout (above 6 s).
- `_render_review_detail` and `_render_design_review_detail` return `_call_render_phase_detail_script(...)` directly.
- `python/test_progress_report.py` has no `_write_progress_ledger` or `_assert_embedded_chart_invariants` helpers and no `test_progress_*_chart*`, `test_progress_round_windows_*`, or `test_progress_missing_ledger_*` tests; argv tests assert `--no-gantt` absent and timeout raised.
- `.github/workflows/ci.yaml` shard-12 Mermaid steps removed; the dedicated `lint-mermaid` job is intact.
- `docs/linting.md`: no reference to `test-harnesses-12` installing Mermaid for the renderer harness; Mermaid CLI row has no generated-Mermaid renderer-harness claim.
- `scripts/render-review-phase-detail.md`: Time bullet says `type=round` rows filtered by `--skill`; Cost bullet says attribution uses the same filtered window; Gantt bullet says round windows not filtered by `--skill`.
- `docs/python-migration.md` describes the scoped `.claude/skills/**/*.md` basename check rather than claiming basenames are never matched.

## Test plan
(no test plan section in plan-file)
