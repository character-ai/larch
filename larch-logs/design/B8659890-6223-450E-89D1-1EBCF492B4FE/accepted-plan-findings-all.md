### FINDING_1: Guard gantt CLI under set -euo pipefail
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan does not require guarding the new `python3 python/cli.py gantt render` subprocess under `set -euo pipefail`. A non-zero renderer exit or launch failure can abort the whole script before `exit 0`, breaking the documented best-effort final-report contract (today inline Mermaid generation never fails the script).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap the gantt CLI like existing token-cost calls (`2>/dev/null || true` or capture rc explicitly); on failure emit the existing per-round no-task note and continue


### FINDING_2: Plan omits wrapper harness updates for ASCII output
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-dyn-integration-parity
- **Severity**: important
- **Concern**: The plan omits updates to existing wrapper harness tests that still assert Mermaid timing output. After `render-review-phase-detail.sh` stops emitting Mermaid, `make test-write-final-report` and `make test-render-final-summary` will still require ```mermaid, `dateFormat X`, and `axisFormat %H:%M:%S`, so validation fails even if the feature works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update these wrapper tests in the plan to assert the ASCII timing section, plain fence, no Mermaid directives, and expected labels/durations
  - From Codex-Pragmatic: Add both wrapper harness files to the plan and replace the stale Mermaid assertions with plain-fence/ASCII/no-mermaid assertions matching the new renderer
  - From Codex-Requirements: Update the wrapper tests to assert plain fenced ASCII timing output and absence of Mermaid-specific directives
  - From Codex-dyn-integration-parity: Update both harness sections to assert the reviewer timing heading, a plain fence or ASCII chart content, and absence of mermaid directives


### FINDING_3: Minimum-width bar algorithm undone by post-force clamping
- **Reviewer(s)**: Codex-Arch, Codex-dyn-renderer-invariants
- **Severity**: important
- **Concern**: Minimum-width enforcement can be undone by clamping after forcing `end_col` greater than `start_col`. For a short positive row at the far right, both rounded columns can land at `width`; forcing then clamping both back to `width` yields a zero-cell bar, violating the one-cell minimum. Current chart input can produce right-edge rows because vendor rows are clamped to the round window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Apply clamping before the minimum-width repair, or repair after clamping by moving start_col to width - 1 and end_col to width for positive-overlap rows at the right edge
  - From Codex-dyn-renderer-invariants: Revise the renderer step to clamp start_col to [0, width - 1] for positive rows, then set end_col to min(width, max(start_col + 1, rounded_end))


### FINDING_5: Shell→CLI TSV time base undefined relative to window flags
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-renderer-invariants
- **Severity**: important
- **Concern**: The shell→CLI TSV contract is unspecified and conflicts with today's awk output. Today's gantt awk emits relative offsets (`cs-rstart`, `ce-rstart`), while the plan wires `gantt render --window-start-s/--window-end-s` to absolute round bounds (`gantt_start`/`gantt_end`) without changing the printf. Passing relative rows with absolute window bounds (or having `render_gantt` clamp rows against absolute window bounds) can filter or misplace every bar, yielding empty charts or no-task notes on final and progress paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `render-review-phase-detail.sh`, either emit absolute epoch `start_s`/`end_s` in the TSV (change the awk printf to `cs`/`ce`) or pass a zero-based window (`0`, `gw_end-gw_start`) with the existing relative rows. Document the chosen convention in `render-review-phase-detail.md` and cover it in `test-render-review-phase-detail.sh`
  - From Cursor-Requirements: Document the contract in python/gantt.md and align call sites: emit absolute clamped start_s/end_s in TSV and pass the matching round window, or pass window_start_s=0 window_end_s=span with round-relative rows; do not mix relative rows with absolute window bounds
  - From Cursor-dyn-renderer-invariants: In render-review-phase-detail.sh and python/gantt.md, require TSV start_s/end_s to be absolute clamped overlap bounds (cs, ce) matching timing-ledger columns 8-9, with --window-start-s/--window-end-s set to the round window (gw_start, gw_end). Document that render_gantt subtracts window_start_s internally for placement and duration.


### FINDING_6: Progress chart plan omits required plain fence
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The progress chart plan omits the required plain fence. If progress appends raw ASCII output, the progress surface violates the exact fence requirement even though final reports use plain fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Wrap each progress chart in a plain triple-backtick fence and add progress_report assertions for the plain fence and no mermaid fence
```

**Merge summary**

| Merged into | Source slots | Rationale |
|---|---|---|
| FINDING_2 | 4 Codex slots | Same files, same stale-Mermaid assertion gap |
| FINDING_3 | Codex-Arch + Codex-dyn-renderer-invariants | Same right-edge min-width/clamp ordering bug |
| FINDING_5 | 3 Cursor slots | Same relative-vs-absolute TSV/window contract gap |

**Kept separate**

- **FINDING_1** — subprocess failure under `set -e` (integration risk, not chart logic)
- **FINDING_4** — architectural duplication vs shell reuse (different fix from FINDING_5 contract alignment)
- **FINDING_6** — progress output fencing (formatting), distinct from FINDING_5 time-base semantics

No scope-reduction findings were supplied; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).




### FINDING_1: Progress chart helpers must match shell gantt round-window contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Progress chart helpers omit the shell gantt timing contract for per-round windows and vendor selection. Reimplementing ledger parsing without the documented rules will drop rows (skill-filtered round windows) or filter vendor rows by skill, so progress charts disagree with final reports. `/design` progress can omit vendor rows whose timing-ledger skill column disagrees with `--skill design`; shell Test 12 and the design fixture rely on wider unfiltered round overlap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match scripts/render-review-phase-detail.sh gantt_rrange and vendor overlap rules: union type=round rows by round number without --skill filtering; select type=vendor rows by overlap only (no $4 skill filter); clamp/sort/cap 25; reuse _review_rounds_root(implement_tmpdir, run_id) for implement rounds_root
  - From Cursor-Pragmatic: When building per-round chart windows in progress_report.py, aggregate type=round rows by round number only (min start_s, max end_s), matching render-review-phase-detail.sh gantt_rrange; do not filter round windows by skill


### FINDING_2: Vendor-row sort keys wrong after absolute TSV format change
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits re-keying the vendor-row sort after switching `tasks_file` from relative `start/end/label` to `label/start_s/end_s` absolute TSV. Keeping the existing `sort -n -k1,1 -k2,2 -k3,3` sorts alphabetically by label instead of by start then end, violating the binding spec and compressing or misordering bars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After emitting `label<TAB>cs<TAB>ce`, sort with `sort -n -k2,2 -k3,3 -k1,1` (or equivalent) before `head -n 25`, and document that ordering in render-review-phase-detail.md


### FINDING_3: Axis placement (`0:00` left, window-span `m:ss` right) not fully planned or tested
- **Reviewer(s)**: Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The rendering spec requires a left axis label of literal `0:00` under the first track cell and a right `m:ss` label for the window span. The plan documents only the right axis label (or axis behavior generally) without an explicit left-tick contract or tests. An implementer may format the left tick from absolute window start or omit it, place `0:00` outside the first track cell, or format the right axis from the absolute epoch instead of round duration, producing axis text that does not match the required example/spec even when border, glyph, and bar tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit contract bullet and a unit test that the axis line begins with `0:00` aligned under the first track column while the right label shows window span as `m:ss`
  - From Codex-Generic: Add minimal renderer logic and tests asserting 0:00 starts at the first track cell and the right m:ss label is based on window_end_s - window_start_s and ends under the last track cell




### FINDING_1: Bind timing-ledger path separately from rounds_root
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan does not require an explicit `timing-ledger.tsv` path tied to the skill tmpdir root, separate from `rounds_root`. After run-log flush, `_review_rounds_root()` can resolve to `larch-logs/implement/<RUN_ID>` while the live ledger remains at `$IMPLEMENT_TMPDIR/timing-ledger.tsv` (same pattern for design tmpdir vs `plan-review/`). Chart helpers that infer the ledger beside `rounds_root` will miss data and emit table-only progress with no charts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass an explicit `timing_ledger` path from `implement_tmpdir / "timing-ledger.tsv"` or `design_tmpdir / "timing-ledger.tsv"` into chart helpers; use `rounds_root` only for `round-N/` dirs and `panel-manifest.ndjson`.


### FINDING_2: Isolate chart append from report_main's broad exception swallow
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Per-round chart append in the progress report is not isolated from `report_main()`'s broad `except Exception: return 0` at `python/progress_report.py:805-815`. A bug or bad input in new chart code can abort `_report()` and return an empty progress report, discarding the table/header that already rendered successfully. This conflicts with the plan's stated failure mode of charts-only omission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap chart generation in local best-effort handling (try/except or equivalent) that omits charts and preserves the existing detail text; do not rely on the top-level swallow.
  - From Cursor-Pragmatic: Wrap chart generation in local best-effort handling (try/except or equivalent) that omits charts and preserves the existing detail text; do not rely on the top-level swallow.
  - From Cursor-Requirements: Wrap chart assembly in progress-only try/except (or a helper that returns "" on failure) inside _render_step5 and _render_design_plan_review after the stripped detail; never let chart errors propagate to report_main


### FINDING_3: Chart title window must use m:ss, not fmt_hms
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The chart title window must use `m:ss` (e.g. `0:00-17:00`), not `fmt_hms`. The rendering spec requires a title line like `window 0:00-M:SS (Ns)`. `fmt_hms` emits values like `5m 00s` for the table Time column. Reusing it for the chart title breaks the rendering spec and planned axis/harness checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a small m:ss span formatter for chart titles (or reuse the same helper gantt.py uses for the right axis label) in the shell and progress call sites; keep fmt_hms for table Time only.


### FINDING_4: TSV sort must be tab-delimited for label-first rows
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned label-first TSV sort omits a tab delimiter. A label containing spaces makes plain `sort` treat label words as separate fields, so `start_s`/`end_s` keys are read from the label instead of TSV columns 2/3. Rows can be ordered incorrectly and the 25-row cap can retain the wrong tasks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Use a tab-delimited sort for the generated TSV, for example LC_ALL=C sort -t $'\t' -k2,2n -k3,3n -k1,1, or sort with numeric keys before re-emitting label<TAB>start_s<TAB>end_s.




### FINDING_1: Final-report gantt render must stay best-effort under `set -e` and must not misreport empty rounds
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The planned `python3 … gantt render` integration in `render-review-phase-detail.sh` runs under `set -euo pipefail` while the script is contractually best-effort (`exit 0` must survive chart failures). A non-zero renderer exit can abort the whole final-report section. A cwd-relative CLI path can fail when the script runs outside the repo root. If renderer failure is treated like an empty task set, the report can emit “No reviewer timing tasks overlapped this round” even when overlapping vendor rows were extracted, silently falsifying the report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use `chart=$(python3 … 2>/dev/null) || chart=""` (or capture `$?` separately) before emitting each round; keep the existing no-task fallback when output is empty
  - From Cursor-Pragmatic: Use python3 "$SCRIPT_DIR/../python/cli.py" gantt render with explicit best-effort rc capture like token cost
  - From Codex-Generic: Reserve the no-task note for an empty extracted row set or empty successful renderer output; on renderer launch/non-zero failure, omit the chart or emit a neutral chart-unavailable note


### FINDING_2: Progress chart timing-ledger parsing must pin the 13-column vendor/round layout
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `python/progress_report.py` is planned to re-parse `timing-ledger.tsv` for per-round Gantt rows without pinning the 13-column vendor/round layout already enforced in `python/timing.py`. An off-by-one field read (round `start_s`/`end_s`, vendor `start_s`/`end_s`, output basename) can yield empty or mis-placed bars while the shell final-report path stays correct; regressions are easy because two parsers must stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document the exact column mapping in the helper (match `timing._parse_rows`: round `parts[5..8]`, vendor `parts[5..10]`) or import/reuse `timing._parse_rows` instead of ad-hoc splitting



