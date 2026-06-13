## Goal
Implement issue #4192: [IMPLEMENTING] ASCII Gantt reviewer-timing charts in /design + /implement (final + progress).

## Implementation Plan
## Plan

## Approach

- Add one **generic ASCII Gantt renderer** in `python/gantt.py`.
- Keep all **reviewer-domain meaning** at call sites.
- Use one **absolute-time TSV contract** everywhere:
  - `start_s` and `end_s` are absolute clamped overlap bounds from `timing-ledger.tsv`.
  - `--window-start-s` and `--window-end-s` are matching absolute round bounds.
  - `render_gantt()` subtracts `window_start_s` internally for placement.
- Match the existing shell Gantt round-window contract everywhere:
  - round windows are aggregated from `type=round` rows by round number only,
  - round windows are not filtered by skill,
  - vendor rows are selected by overlap only,
  - vendor rows are not filtered by skill.
- Keep **timing-ledger lookup** separate from **round-dir lookup** in progress code.
  - `rounds_root` locates completed `round-N/` dirs and `panel-manifest.ndjson`.
  - `timing_ledger` is passed explicitly from the live skill tmpdir root.
  - Do not infer `timing-ledger.tsv` beside `rounds_root`.
- Replace Mermaid generation in `scripts/render-review-phase-detail.sh` with:
  - existing timing-ledger window extraction,
  - existing label attribution,
  - absolute clamped TSV rows,
  - tab-delimited sort by absolute start, end, then label,
  - cap after sorting,
  - guarded call to `python3 "$SCRIPT_DIR/../python/cli.py" gantt render`,
  - a plain fenced ASCII chart.
- Keep final-report chart rendering **best-effort under `set -euo pipefail`**.
  - Capture renderer output and exit status explicitly.
  - Redirect renderer stderr away from final-report output.
  - Never let renderer launch failure or non-zero exit abort the report.
  - Do not report “No reviewer timing tasks overlapped this round” when extracted vendor rows existed but rendering failed.
- Use **m:ss formatting** for chart title windows.
  - Do not reuse table `fmt_hms` output for chart titles.
- Keep final-report wrapper scripts unchanged except stale wording and test expectations.
  - `/implement` and `/design` already route through `scripts/render-review-phase-detail.sh`.
- Extend `python/progress_report.py` to keep using `--no-gantt` for the table, then append plain-fenced ASCII charts for every completed round by importing the same renderer.
- Pin **progress timing-ledger parsing** to the existing 13-column layout.
  - Prefer reusing the parser in `python/timing.py` if practical.
  - Otherwise use named constants and tests for the same mapping.
  - Match the existing parser layout for round rows at `parts[5..8]`.
  - Match the existing parser layout for vendor rows at `parts[5..10]`, including `start_s`, `end_s`, and output basename fields.
- Isolate progress chart generation with local best-effort handling.
  - Chart failures omit charts only.
  - They must not discard the already-rendered table or header.
- Do not fix task labels or outliers.

## Files to modify/create

### NEW: python/gantt.py

Implement a stdlib-only renderer with no larch reviewer domain knowledge.

- Add a small row type, for example `GanttRow(label: str, start_s: int, end_s: int)`.
- Add `render_gantt(window_start_s, window_end_s, rows, *, width=56) -> str`.
- Add or expose a small `format_mss(seconds: int) -> str` helper for axis labels and chart titles.
  - Format `0` as `0:00`.
  - Format `1020` as `17:00`.
  - Clamp display input to non-negative seconds.
- Treat labels as opaque text.
  - Preserve full labels.
  - Do not sanitize.
  - Do not truncate.
- Interpret `start_s` and `end_s` as absolute times in the same time base as the window.
- Clamp rows to the absolute window for placement and duration.
- Skip rows with no positive overlap after clamping.
- Use `span = max(1, window_end_s - window_start_s)`.
- Convert clamped absolute times to relative offsets by subtracting `window_start_s`.
- Render:
  - axis line above the box,
  - top border with exactly `width` interior cells,
  - one row per input row after filtering,
  - bottom border with exactly `width` interior cells.
- Axis contract:
  - left axis label is literal `0:00`,
  - `0:00` starts under the first track cell,
  - right axis label is the window span formatted as `m:ss`,
  - right axis label is based on `window_end_s - window_start_s`, not the absolute epoch,
  - the final character of the right axis label ends under the last track cell.
- Use whole-cell bars only:
  - compute rounded columns from relative offsets,
  - clamp before the minimum-width repair,
  - for positive-overlap rows, clamp `start_col` to `[0, width - 1]`,
  - set `end_col = min(width, max(start_col + 1, rounded_end))`,
  - fill only with `█`.
- Format durations from clamped overlap as bare right-justified `Ns`.
- Add CLI helper:
  - `gantt render --window-start-s N --window-end-s N --rows-tsv PATH [--width N]`
  - TSV columns: `label<TAB>start_s<TAB>end_s`.
  - TSV times are absolute clamped overlap bounds.
  - Print only the chart body, no markdown fence.
  - Exit 0 with empty output if all rows are filtered out.
  - Return 2 for malformed CLI flags or unreadable rows.
  - Return non-zero without traceback for malformed rows.
  - Do not print tracebacks for malformed rows.

### NEW: python/gantt.md

Document the reusable renderer contract.

- State that the module is generic.
- State that labels are opaque caller input.
- Document the absolute-time TSV CLI shape for bash callers.
  - `start_s` and `end_s` must use the same absolute time base as `--window-start-s` and `--window-end-s`.
  - Shell callers should pass clamped absolute overlap bounds, not round-relative offsets.
- Document that `render_gantt()` subtracts `window_start_s` internally for placement.
- Document the `format_mss()` helper if exported.
  - It is for chart axes and chart title spans.
  - It is not the table duration formatter.
- Document the axis contract:
  - left label is `0:00`,
  - it starts under the first track cell,
  - right label is the window span as `m:ss`,
  - it ends under the last track cell.
- Include the four invariant checks:
  - right edges align,
  - left edges align,
  - track glyphs are only space or `█`,
  - bars contain no embedded spaces.
- State that `/review` should reuse this module or CLI when it adds timing charts.

### NEW: python/test_gantt.py

Add focused renderer tests.

- Alignment:
  - verify every `│`, `┌`, and `└` starts in the same column,
  - verify every right `│`, `┐`, and `┘` ends in the same column.
- Axis:
  - verify `0:00` starts under the first track cell,
  - verify the right label is based on `window_end_s - window_start_s`,
  - verify the right label ends under the last track cell,
  - verify an absolute window that does not start at zero still shows `0:00` on the left.
- Title-format helper:
  - verify `format_mss()` emits `m:ss`,
  - verify it does not emit table-style text such as `5m 00s`.
- Glyphs:
  - track interiors contain only spaces and `█`,
  - no partial block glyphs appear.
- Bar continuity:
  - each bar has one contiguous `█+` run,
  - no embedded spaces in the run.
- Scaling:
  - non-zero starts create offset bars,
  - very short positive durations still render one cell,
  - very short positive rows at the far right still render one cell,
  - rows crossing window boundaries clamp correctly.
- Time-base contract:
  - absolute rows with an absolute window render in the expected positions,
  - rows outside the absolute window are filtered.
- Labels:
  - long labels are not truncated,
  - punctuation and commas pass through unchanged.
- CLI:
  - valid absolute TSV renders the same chart as direct import,
  - malformed rows return a non-zero usage-style status without traceback.

### UPDATED: python/cli.py

Register the new CLI verb.

- Add `("gantt", "render"): ("gantt", "gantt_render_main")`.
- Do not add special machine-stdout handling unless the command emits key-value grammar.
- Keep import behavior consistent with other Python runtime modules.

### UPDATED: scripts/render-review-phase-detail.sh

Replace the Mermaid Gantt writer with ASCII output.

- Keep `--no-gantt`.
- Keep best-effort behavior.
- Keep chart placement after the table and before top reviewers.
- Keep the existing slot-map and basename fallback label attribution.
- Remove Mermaid-only label sanitization and truncation from the chart path.
- Resolve the Python CLI path from the script directory.
  - Use `python3 "$SCRIPT_DIR/../python/cli.py" gantt render ...`.
  - Do not depend on the caller running from the repo root.
- Keep the existing round-window discovery semantics for Gantt charts:
  - aggregate `type=round` rows by round number,
  - use min start and max end for the round window,
  - do not filter round windows by `--skill`.
- Select chart rows from `type=vendor` rows by overlap only.
  - Do not filter vendor rows by `--skill`.
  - This preserves `/design` charts when timing-ledger skill values differ from the selected skill.
- Emit absolute clamped TSV rows for the CLI:
  - `label<TAB>cs<TAB>ce`,
  - `cs = max(row_start_s, round_start_s)`,
  - `ce = min(row_end_s, round_end_s)`,
  - pass `--window-start-s "$round_start_s"` and `--window-end-s "$round_end_s"`.
- Do not pass round-relative row offsets with absolute window flags.
- Sort emitted TSV rows before capping:
  - sort by `start_s`, then `end_s`, then `label`,
  - use a tab delimiter because the label is column 1 and may contain spaces,
  - use `LC_ALL=C sort -t $'\t' -k2,2n -k3,3n -k1,1` or an equivalent tab-delimited sort,
  - apply `head -n 25` after sorting.
- Guard the CLI subprocess under `set -euo pipefail`.
  - Capture output and status explicitly.
  - Use a pattern that does not trigger `set -e` aborts, such as an `if chart=$(...)` branch or temporarily disabling `errexit` around the call.
  - Redirect renderer stderr away from final report output.
  - On renderer launch failure or non-zero renderer exit, omit the chart or emit a neutral chart-unavailable note.
  - Do not emit the no-task note when overlapping TSV rows were extracted but renderer execution failed.
  - Reserve the no-task note for an empty extracted row set, or for a successful renderer run that returns empty output after filtering.
  - Never let a renderer failure abort the whole final-report script.
- Emit one section per round:
  - `### Round N reviewer timing`
  - blank line
  - plain fenced block,
  - optional first line: `Round N reviewer timing  ·  window 0:00-M:SS (Ns)`,
  - output from `python3 "$SCRIPT_DIR/../python/cli.py" gantt render`.
- Format the title window span as `m:ss`.
  - Do not use the table `fmt_hms` formatter for chart titles.
- If the renderer returns empty output for a usable round window and the renderer exited 0, keep the existing no-task note.
- Keep final reports covered by this one script for both `/design` and `/implement`.

### UPDATED: scripts/render-review-phase-detail.md

Update the renderer contract.

- Replace the "Mermaid timing format" section with "ASCII timing format".
- Document that charts use a plain fence, not `mermaid`.
- Document that the Python renderer owns bars, axis, and box drawing.
- Document that the shell script owns:
  - timing-ledger extraction,
  - round windowing,
  - row cap,
  - sorting,
  - label attribution,
  - absolute clamping before TSV emission,
  - best-effort subprocess failure handling.
- Document the shell Gantt timing contract:
  - round windows aggregate `type=round` rows by round number only,
  - round windows are not filtered by skill,
  - vendor rows are selected by overlap only,
  - vendor rows are not filtered by skill.
- Document the shell-to-CLI time-base contract:
  - TSV `start_s` and `end_s` are absolute clamped overlap bounds,
  - window flags are absolute round bounds,
  - relative offsets are not accepted at this call site.
- Document sort order:
  - sort by absolute `start_s`,
  - then absolute `end_s`,
  - then label,
  - use a tab-delimited sort because label is the first TSV field,
  - cap to 25 after sorting.
- Document best-effort renderer failure handling.
  - Renderer non-zero status, unreadable CLI path, or missing `python3` must not abort the report.
  - The no-task note means no overlapping rows, or a successful renderer returned no rows.
  - Renderer failure must not be misreported as no overlapping tasks.
- Document that chart title windows use `m:ss`, not table `fmt_hms` output.
- Remove references to Mermaid ids, `dateFormat`, `axisFormat`, and Mermaid validation.
- Keep the out-of-scope task-label note.

### UPDATED: python/progress_report.py

Append ASCII timing charts to live progress detail.

- Keep `_call_render_phase_detail_script(... --no-gantt)` so the table remains the shared summary source.
- Keep **round dirs** and **timing ledger** as separate inputs.
- For `/implement`:
  - use `_review_rounds_root(implement_tmpdir, run_id)` only for completed `round-N/` dirs and `panel-manifest.ndjson`,
  - pass `implement_tmpdir / "timing-ledger.tsv"` explicitly to chart helpers.
- For `/design`:
  - keep the parallel `plan-review/round-N` root behavior for completed round dirs,
  - pass `design_tmpdir / "timing-ledger.tsv"` explicitly to chart helpers.
- Do not infer `timing-ledger.tsv` from `rounds_root`.
  - This preserves charts after run-log flush when `_review_rounds_root()` resolves under `larch-logs/...`.
- Add small progress-only helpers to:
  - find completed `round-N` dirs with `round-meta.json`,
  - read the explicitly passed `timing_ledger`,
  - parse the 13-column timing-ledger layout consistently with `python/timing.py`,
  - build absolute round windows from `type=round` rows,
  - aggregate round windows by round number only with min start and max end,
  - avoid skill filtering for round windows,
  - read overlapping `type=vendor` rows,
  - select vendor rows by overlap only,
  - avoid skill filtering for vendor rows,
  - clamp vendor rows to absolute round bounds,
  - sort by start, end, label,
  - cap to 25 rows after sorting,
  - map output basenames through `panel-manifest.ndjson`,
  - use a simple fallback label when no map entry exists.
- Reuse the existing timing parser if practical.
  - If reusing `python/timing.py` is not practical, define named column constants.
  - Document that round rows use the `parts[5..8]` timing fields from the existing parser.
  - Document that vendor rows use the `parts[5..10]` timing and output-basename fields from the existing parser.
  - Treat rows with fewer than the required 13 columns as malformed.
  - Skip malformed rows locally instead of propagating parser errors to `report_main()`.
- Import `gantt.render_gantt`.
- Reuse `gantt.format_mss()` or an equivalent `m:ss` helper for chart title windows.
  - Do not reuse table `fmt_hms` output for chart title windows.
- Append one plain-fenced ASCII chart for each completed round after the stripped review detail.
- Include the same optional chart title line used by final reports.
- Wrap chart assembly in local best-effort handling.
  - Add a helper that returns `""` on chart failure, or use a local `try/except` around chart generation.
  - Append charts only when generation succeeds.
  - Never let chart errors propagate to `report_main()`.
  - Preserve existing detail text, headers, and tables if charts fail.
- Preserve current behavior for in-flight-only roots.
- Return no chart when the timing ledger is missing, malformed, or lacks usable windows.
- Keep `/design` and `/implement` paths parallel.

### UPDATED: python/test_progress_report.py

Add progress-report tests.

- Update argv assertions to keep `--no-gantt`.
- Add an `/implement` completed-round fixture with:
  - completed `round-N/` dirs under a rounds root,
  - `timing-ledger.tsv` under the implement tmpdir root,
  - a rounds root that can differ from the ledger parent.
- Assert implement progress still finds the explicitly passed live ledger and renders a plain fenced ASCII chart.
- Add a `/design` completed-round fixture with:
  - `plan-review/round-N`,
  - `timing-ledger.tsv` under the design tmpdir root,
  - timing-ledger skill values that would be dropped by skill filtering.
- Assert the design chart still includes overlapping vendor rows.
- Add a 13-column ledger layout regression.
  - Use rows whose round `start_s` and `end_s` depend on the existing `parts[5..8]` mapping.
  - Use vendor rows whose `start_s`, `end_s`, and output basename depend on the existing `parts[5..10]` mapping.
  - Assert bars render in the expected positions.
  - Assert label attribution uses the expected output basename field.
  - Assert malformed short rows are skipped without raising.
- Assert charts appear after detail text.
- Assert charts are wrapped in plain fences.
- Assert output does not contain:
  - ` ```mermaid`,
  - Mermaid directives,
  - `dateFormat`,
  - `axisFormat`.
- Assert charts include expected labels and bare `Ns` durations.
- Add a round-window aggregation regression.
  - Include multiple `type=round` rows for one round.
  - Assert the chart uses min start and max end by round number.
  - Assert the window is not narrowed by skill filtering.
- Add a vendor-overlap regression.
  - Include vendor rows with mismatched skill values.
  - Assert rows are selected by overlap only.
- Add a title-format regression.
  - Assert the chart title uses `0:00-M:SS`.
  - Assert it does not use table-style `fmt_hms` output.
- Add an in-flight-only regression.
  - Assert no detail or chart is rendered when all round dirs lack `round-meta.json`.
- Add a malformed-ledger regression.
  - Assert progress still renders the table/header without raising.
  - Assert charts are omitted only.
- Add a chart-helper exception regression.
  - Force chart generation to raise.
  - Assert the already-rendered detail text remains in output.
  - Assert `report_main()` does not return an empty report because of chart failure.
- Assert chart invariants on the embedded progress chart using helper checks shared inside the test file.

### UPDATED: scripts/test-render-review-phase-detail.sh

Replace Mermaid assertions with ASCII chart assertions.

- Remove `assert_mermaid_valid` and related optional Mermaid CLI setup.
- In the main Gantt test:
  - assert no ` ```mermaid` fence,
  - assert a plain ` ``` ` fence exists,
  - assert no `gantt`, `dateFormat`, or `axisFormat` directives,
  - assert expected labels appear unchanged,
  - assert expected duration suffixes are bare `Ns`,
  - assert no parenthesized ranges appear.
- Add a regression for the absolute-time CLI contract:
  - create a round window whose epoch does not start at zero,
  - include a vendor row that overlaps that window,
  - assert the row renders instead of becoming an empty chart.
- Add a regression for absolute TSV sort order:
  - emit labels in an order that differs from start-time order,
  - include labels with spaces,
  - assert rendered rows follow start, then end, then label,
  - assert the 25-row cap applies after sorting,
  - assert sorting is tab-delimited and does not treat label words as sort fields.
- Add a regression for the shell Gantt round-window contract:
  - include round rows that would be dropped by skill filtering,
  - assert the chart uses the unfiltered aggregate round window,
  - include vendor rows with mismatched skill values,
  - assert overlapping vendor rows still render.
- Add a renderer failure regression.
  - Force the CLI path or renderer invocation to fail.
  - Assert the script still exits successfully.
  - Assert already-rendered table content remains.
  - Assert the report does not say “No reviewer timing tasks overlapped this round” when overlapping TSV rows existed.
  - Assert the chart is omitted or a neutral unavailable note is emitted.
- Add a cwd regression.
  - Run the script from outside the repo root.
  - Assert the renderer still launches through `"$SCRIPT_DIR/../python/cli.py"`.
- Add a chart-title regression.
  - Assert the title uses `window 0:00-M:SS (Ns)`.
  - Assert it does not use table-style duration text such as `5m 00s`.
- Add the four required invariant checks against each rendered chart:
  - left edge alignment,
  - right edge alignment,
  - only space and `█` in tracks,
  - no embedded spaces inside any `█` run.
- Add axis checks against each rendered chart:
  - `0:00` starts under the first track cell,
  - the right axis label is the round span,
  - the right axis label ends under the last track cell.
- Keep the tests for:
  - chart placement after table and before top reviewers,
  - `--no-gantt`,
  - design skill timing despite vendor skill mismatch,
  - 25-row cap,
  - malformed timing rows,
  - unfiltered Gantt preservation.
- Update label expectations to match unsanitized labels where the existing fixture contains punctuation.

### UPDATED: scripts/test-render-review-phase-detail.md

Update harness prose.

- Replace generated Mermaid validation wording with ASCII invariant checks.
- Remove Mermaid CLI and CI setup references.
- State that the harness validates plain fenced ASCII charts and `--no-gantt`.
- State that the harness validates:
  - absolute TSV sort order,
  - tab-delimited sorting for label-first TSV rows,
  - unfiltered round-window aggregation,
  - vendor overlap selection without skill filtering,
  - best-effort renderer failure handling under `set -e`,
  - renderer launch from outside the repo root,
  - chart title `m:ss` formatting,
  - axis placement.

### UPDATED: skills/implement/scripts/write-final-report.md

Update stale final-report prose only.

- Replace "optional reviewer timing Mermaid Gantt charts" with "optional reviewer timing ASCII Gantt charts".
- Keep the statement that final reports do not pass `--no-gantt`.

### UPDATED: skills/design/scripts/render-final-summary.md

Update stale design final-summary prose only.

- Replace "reviewer timing Gantt charts" wording with "reviewer timing ASCII Gantt charts".
- Keep the statement that final summaries do not pass `--no-gantt`.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

Update wrapper harness assertions for `/implement`.

- Replace stale Mermaid assertions with ASCII timing assertions.
- Assert the final report contains the reviewer timing heading.
- Assert it contains a plain fenced ASCII chart.
- Assert it does not contain:
  - ` ```mermaid`,
  - `dateFormat X`,
  - `axisFormat %H:%M:%S`,
  - Mermaid `gantt` timing directives.
- Assert expected labels and bare `Ns` durations appear.
- Assert the axis contains `0:00` and the expected round-span label.
- Assert the chart title uses `window 0:00-M:SS (Ns)`.
- Keep existing wrapper coverage that final reports do not pass `--no-gantt`.

### UPDATED: skills/implement/scripts/test-write-final-report.md

Update harness prose.

- Replace Mermaid timing expectations with plain-fenced ASCII timing expectations.
- State that `make test-write-final-report` verifies wrapper integration still includes reviewer timing charts.

### UPDATED: skills/design/scripts/test-render-final-summary.sh

Update wrapper harness assertions for `/design`.

- Replace stale Mermaid assertions with ASCII timing assertions.
- Assert the final summary contains the reviewer timing heading.
- Assert it contains a plain fenced ASCII chart.
- Assert it does not contain:
  - ` ```mermaid`,
  - `dateFormat X`,
  - `axisFormat %H:%M:%S`,
  - Mermaid `gantt` timing directives.
- Assert expected labels and bare `Ns` durations appear.
- Assert the axis contains `0:00` and the expected round-span label.
- Assert the chart title uses `window 0:00-M:SS (Ns)`.
- Keep existing wrapper coverage that final summaries do not pass `--no-gantt`.

### UPDATED: skills/design/scripts/test-render-final-summary.md

Update harness prose.

- Replace Mermaid timing expectations with plain-fenced ASCII timing expectations.
- State that `make test-render-final-summary` verifies wrapper integration still includes reviewer timing charts.

## Edge cases

- Empty or missing timing ledger: no charts.
- Progress rounds root under flushed run logs while live ledger remains under the skill tmpdir root: charts still render because `timing_ledger` is explicit.
- Round window with no overlapping vendor rows: keep the no-task note.
- Renderer launch failure or non-zero status with extracted overlapping rows: omit the chart or emit a neutral unavailable note, not the no-task note.
- Round windows spanning multiple `type=round` rows: aggregate by round number with min start and max end.
- Round and vendor ledger rows with mismatched skill values: chart selection still uses round number and overlap only.
- Malformed timing rows: skip bad rows and keep rendering other content.
- Timing-ledger rows with fewer than the required 13 columns: skip them in progress chart parsing.
- Zero or negative row duration after clamping: skip that row.
- Very short positive duration: render one cell.
- Very short positive duration at the right edge: render one cell ending at the right border.
- Long labels: preserve full label and allow wide lines.
- Labels containing spaces: preserve them and sort TSV with an explicit tab delimiter.
- Missing `python3`, CLI launch failure, wrong working directory, or renderer non-zero status in the shell script: degrade best-effort without aborting.
- Progress chart helper exceptions: omit charts and preserve already-rendered progress detail.
- Progress reports with only in-flight rounds: keep current header-only behavior.
- Multiple completed rounds: render a chart for each completed round.
- Absolute windows that do not start at zero: bars still place correctly and the left axis still says `0:00`.
- Wide chart lines: accept them per spec.

## Failure modes

- If the new renderer raises unexpectedly in final-report shell generation, `render-review-phase-detail.sh` must not fail the final report.
- If the renderer subprocess exits non-zero under `set -euo pipefail`, capture the status locally and continue.
- If extracted overlapping vendor rows exist but rendering fails, do not emit the no-task note.
- If `render-review-phase-detail.sh` runs outside the repo root, the renderer path still resolves via `SCRIPT_DIR`.
- If the new renderer or chart helper raises unexpectedly in progress generation, local progress chart handling must return no charts and preserve existing progress text.
- Do not rely on `report_main()`'s broad `except Exception: return 0` for chart failures.
- If the shell chart subprocess fails, `render-review-phase-detail.sh` must not fail the final report.
- If progress timing-ledger parsing drifts from the 13-column layout in `python/timing.py`, tests must fail before bars are silently misplaced.
- If label fallback differs between final and progress paths, bars still render correctly.
  - Treat label parity fixes as out of scope unless a test depends on them.
- If a chart line becomes very wide, accept it per spec.
- If a progress helper cannot parse the ledger contract, omit charts and preserve existing progress text.

## Testing strategy

Run focused tests first:

```bash
python3 -m pytest python/test_gantt.py
python3 -m pytest python/test_progress_report.py
bash scripts/test-render-review-phase-detail.sh
make test-write-final-report
make test-render-final-summary
```

Then run the repo-relevant checks:

```bash
bash scripts/relevant-checks.sh
```

If time permits, run:

```bash
make py-test
make test-render-review-phase-detail
```

## Validation checklist

- Final `/implement` report contains plain ASCII timing charts when timing data exists.
- Final `/design` summary contains plain ASCII timing charts when timing data exists.
- `p` / `progress` contains plain-fenced ASCII timing charts for completed review rounds.
- Progress chart helpers receive an explicit live `timing_ledger` path separate from `rounds_root`.
- Progress charts still render when `rounds_root` points at flushed run logs and the ledger remains under the skill tmpdir.
- Progress chart parsing matches the existing 13-column timing-ledger layout in `python/timing.py`.
- Progress chart tests cover round fields at `parts[5..8]` and vendor fields at `parts[5..10]`.
- Progress chart failures omit charts only and preserve already-rendered detail text.
- No Mermaid timing fence remains in generated reviewer timing sections.
- Wrapper harnesses no longer assert Mermaid timing output.
- `--no-gantt` still suppresses timing charts only.
- The shell-to-CLI TSV contract uses absolute clamped row bounds with absolute window flags.
- TSV rows sort with a tab delimiter by absolute start, then end, then label before the 25-row cap.
- Labels containing spaces do not break TSV sort ordering.
- Round windows are aggregated from `type=round` rows by round number without skill filtering.
- Vendor rows are selected by overlap without skill filtering.
- Chart titles use `window 0:00-M:SS (Ns)`, not table `fmt_hms`.
- Axis left label is literal `0:00` under the first track cell.
- Axis right label is the round span as `m:ss` and ends under the last track cell.
- Right-edge short bars still render at least one cell.
- Renderer subprocess failures do not abort final-report generation.
- Renderer subprocess failures do not produce a false no-task note when rows existed.
- The renderer CLI path works when `render-review-phase-detail.sh` runs outside the repo root.
- The renderer contains no reviewer labels, vendors, skills, phases, or hard-coded sections.


## Acceptance

- [ ] `python/gantt.py` exists; contains `render_gantt()` and `format_mss()` with no larch domain knowledge.
- [ ] `python3 python/cli.py gantt render --window-start-s N --window-end-s N --rows-tsv PATH` exits 0 and prints an ASCII chart.
- [ ] `render-review-phase-detail.sh` emits a plain fenced ASCII chart (no `mermaid` fence, no `dateFormat`/`axisFormat` directives).
- [ ] `progress_report.py` appends ASCII charts for completed review rounds (still passes `--no-gantt` for the table call).
- [ ] All four chart invariants pass: left edges aligned, right edges aligned, only space/`█` in tracks, no embedded spaces in bars.
- [ ] `python3 -m pytest python/test_gantt.py` passes.
- [ ] `python3 -m pytest python/test_progress_report.py` passes.
- [ ] `bash scripts/test-render-review-phase-detail.sh` passes (no Mermaid assertions, 4 invariant checks added).
- [ ] `bash scripts/relevant-checks.sh` passes.

diff_lines: 880

## Test plan
(no test plan section in plan-file)
