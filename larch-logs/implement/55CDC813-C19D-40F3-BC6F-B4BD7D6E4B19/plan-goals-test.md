## Goal
Implement issue #5977: [IMPLEMENTING] md-to-py-XI: cache-efficiency outlier report (cache_create versus cache_read per step).

## Implementation Plan
## Plan

## Approach

- Draft from direct repo inspection. `approach-synthesis.txt` is `NO_SKETCHES`.
- Keep this measurement-only:
  - Do not change token capture.
  - Do not change `token-report.json` or `token-report-final.json` shape.
  - Do not add CI gates or ratchets.
- Add a new `measure_cache_efficiency()` helper in `python/larch/report/tokens.py`.
- Wire `python3 python/cli.py token measure-cache-efficiency`.
- Reuse `report_tokens_scan.scan()` with `resolve_repo=False` for `design` and `implement`.
  - Import it locally inside the new helper to avoid a top-level cycle, since `report_tokens_scan.py` imports `tokens.py`.
  - Use `ProcRunner()` from `larch.core.proc`.
  - Bind output path and `WROTE` relative path to `ScanResult.repo_root` from the first successful scan (consumer git root). Do not use `tokens._repo_root()` for scan-backed output; reserve `_repo_root()` for `__file__`-local measures such as `measure-md-cost`.
- Scan each skill separately and preserve scan-origin skill on every record:
  - `RunRecord` has no `skill` field and `report_tokens_scan._workflow` returns `""`.
  - Mirror `report_tokens_cli.py`: iterate `for skill in ("design", "implement")`, call `scan(runner, skill=skill, resolve_repo=False)`, and accumulate `list[tuple[Skill, RunRecord]]` (or an equivalent small tagged wrapper) before measurement.
  - Thread the scan `skill` through per-run row builders and `_cache_efficiency_step_rows_for_record`; never infer skill from `RunRecord`.
  - Per-run `skill` cells and per-step aggregation keys `(skill, step, lane)` must use this preserved binding so homonymous steps (e.g. design `3` vs implement `3`) stay separate.
- Analyze only Claude cache lanes in committed reports:
  - `claude`
  - `claude_sub`
- Effective cache-create rule (match `report_tokens_cost._aggregate_tokens` and `claude_sub_argv_from_buckets` legacy handling in `python/larch/report/report_tokens_cost.py`):
  - `split_sum = cache_create_5m + cache_create_1h`
  - `cache_create_effective = split_sum if split_sum > 0 else cache_create`
  - Apply the same rule for `VendorTotals` per-run lanes and raw per-step bucket mappings. Do not treat key presence as “split buckets exist”; zero split sums with nonzero combined `cache_create` are common on `claude_sub` and legacy per-step rows.
- For each `(skill, record)` pair:
  - Read per-run totals from `RunRecord.<lane>` (`record.claude`, `record.claude_sub`).
  - Read per-step items from `RunRecord.raw_report[<lane>]["per_step"]`.
  - For each per-step item, read `step` from `item["step"]` and bucket fields from `item["totals"]` (nested mapping shape from `tokens._per_step_json` and `report_tokens_scan._phase_rows`). Skip items with missing or non-object `totals`.
  - Compute `cache_create_effective` via `_cache_create_effective(...)`.
  - Compute per-run ratio as `cache_create_effective / cache_read`.
- Per-step aggregation (corpus-level, not per-run ratio averaging):
  - Group by `(skill, step, lane)` using the scan-origin `skill` threaded from each tagged record.
  - Sum raw `cache_create`, `cache_create_5m`, `cache_create_1h`, and `cache_read` across contributing runs for TSV columns.
  - Separately accumulate `effective_cache_create_sum` by applying `_cache_create_effective(...)` to each per-step contribution before adding (do not compute effective create only once on summed raw buckets).
  - Increment `runs`.
  - Compute one grouped ratio as `effective_cache_create_sum / summed_cache_read`.
- Ranking (per-run and per-step sections):
  - Exclude rows with `cache_create_effective == 0` and `cache_read == 0` (per-run uses row-level effective create; per-step uses grouped `effective_cache_create_sum` and summed `cache_read`).
  - Sort rows with nonzero create and zero read first.
  - Then sort by descending ratio.
  - Tie-break by descending effective create, then descending `cache_read`, then stable labels.
- Output:
  - Write `larch-logs/measure-cache-efficiency/<date>.tsv` under `ScanResult.repo_root`.
  - Print `WROTE\t<relpath>`, matching sibling `measure-*` commands.
  - Use two TSV sections in one file:
    - `# per_run`
    - `# per_step`
  - Include explicit columns so downstream readers do not infer:
    - per-run: `rank`, `skill`, `issue`, `started_at`, `lane`, `cache_create`, `cache_create_5m`, `cache_create_1h`, `cache_read`, `ratio`, `title`
    - per-step: `rank`, `skill`, `step`, `lane`, `runs`, `cache_create`, `cache_create_5m`, `cache_create_1h`, `cache_read`, `ratio`
  - Render infinite ratio as `inf`.

## Files to modify/create

### UPDATED: python/larch/report/tokens.py

Add small frozen dataclasses near the existing measurement helpers:
- `CacheEfficiencyTotals`
- `CacheEfficiencyRunRow`
- `CacheEfficiencyStepRow`

Add helper functions:
- `_cache_create_effective(*, cache_create: int, cache_create_5m: int, cache_create_1h: int) -> int`
  - Return `split_sum if split_sum > 0 else cache_create`
  - Overloads or thin wrappers for `VendorTotals` and per-step `Mapping[str, object]` bucket dicts; both call the same scalar rule.
- `_cache_ratio_sort_key(...)`
- `_cache_ratio_text(...)`
- `_cache_lane_totals_from_mapping(...)`
- `_cache_efficiency_step_rows_for_record(*, skill: Skill, record: RunRecord, lane: Literal["claude", "claude_sub"]) -> ...`
  - Iterate `raw_report[lane]["per_step"]` when present and list-shaped.
  - For each item, read `step = str(item.get("step") or "unknown")`.
  - Pass `_as_mapping(item.get("totals"))` into `_cache_lane_totals_from_mapping`; skip rows with missing or non-object `totals`.
  - Emit per-step bucket contributions tagged with the caller-supplied scan-origin `skill`; no per-run ratio here.
- `_measure_cache_efficiency_records(*, tagged_records: Sequence[tuple[Skill, RunRecord]]) -> ...`
  - Accept tagged `(skill, record)` pairs only; do not accept a flat `RunRecord` list.
  - Build per-run rows from each pair’s `skill`, `record.claude`, and `record.claude_sub` using `_cache_create_effective`.
  - Build per-step rows by summing raw buckets and `effective_cache_create_sum` per `(skill, step, lane)`, then computing grouped ratios from those accumulators.
- `_render_cache_efficiency_tsv(...)`

Add `measure_cache_efficiency() -> Path`:
- Create `runner = ProcRunner()`.
- Initialize `tagged_records: list[tuple[Skill, RunRecord]] = []` and `repo_root: Path | None = None`.
- For each `skill in ("design", "implement")`:
  - `scan_result = report_tokens_scan.scan(runner, skill=skill, resolve_repo=False)` (local import).
  - Capture `repo_root = scan_result.repo_root` from the first scan when still unset.
  - Extend `tagged_records` with `(skill, record)` for each `record in scan_result.records`.
- Use captured `repo_root` for `out_path = repo_root / "larch-logs" / "measure-cache-efficiency" / f"{_measure_stamp()}.tsv"`.
- Call `_measure_cache_efficiency_records(tagged_records=tagged_records)`.
- Write the TSV with `_atomic_text`.
- Return the output path (under consumer `repo_root`).

Add `measure_cache_efficiency_main(argv: list[str] | None = None) -> int`:
- Ignore argv, matching sibling command wrappers.
- Call `measure_cache_efficiency()`.
- Print `WROTE\t<path.relative_to(repo_root)>` where `repo_root` is the parent chain anchor from the returned path’s repo root (derive from the returned `Path` by walking to the `larch-logs` parent’s parent, or return `(path, repo_root)` tuple internally; do not call `tokens._repo_root()`).
- Return `0`.

Reuse `_as_mapping` locally or import the same helper pattern used in `report_tokens_scan._phase_rows`.

### UPDATED: python/larch/cli.py

Register:
- `("token", "measure-cache-efficiency"): ("larch.report.tokens", "measure_cache_efficiency_main")`

Keep it near the sibling `token measure-*` registrations.

### UPDATED: python/tests/report/test_tokens.py

Add focused unit coverage:
- `test_measure_cache_efficiency_writes_ranked_sections`
  - Monkeypatch `report_tokens_scan.scan` or the local helper seam so no git or `gh` command runs.
  - Return synthetic `ScanResult` values per skill with a tmp `repo_root`.
  - Build synthetic `RunRecord` values with `claude` and `claude_sub` cache buckets, including one `claude_sub` row with `cache_create > 0`, `cache_create_5m = 0`, `cache_create_1h = 0`, and `cache_read = 0` (legacy combined-only create).
  - Assert the output starts with `# per_run`.
  - Assert it also contains `# per_step`.
  - Assert the zero-read, nonzero-create `claude_sub` row ranks before finite ratios.
  - Assert all-zero cache rows are excluded.
- `test_cache_create_effective_uses_legacy_when_split_zero`
  - Direct unit coverage of `_cache_create_effective` (or via a small exported test seam): nonzero `cache_create` with zero split buckets yields combined `cache_create`, not zero.
- `test_measure_cache_efficiency_aggregates_steps_by_skill_step_and_lane`
  - Create two tagged records with the same scan-origin `skill`, same `step`, and same lane but different cache buckets.
  - Use nested per-step items shaped as `{"step": "...", "totals": {...}}`.
  - Assert `runs` increments and raw cache bucket columns sum.
  - Assert `ratio` equals the sum of per-contribution `_cache_create_effective(...)` values divided by summed `cache_read` (not an average of per-run ratios).
  - Extend with one split-bucket contribution plus one legacy combined-only contribution in the same `(skill, step, lane)` group; assert grouped ratio uses `effective_cache_create_sum`, not post-sum split fallback that drops legacy combined creates.
- `test_measure_cache_efficiency_separates_homonymous_steps_across_skills`
  - Build design and implement tagged records that share the same step label (e.g. `"3"`) and lane but different cache buckets.
  - Assert two distinct `# per_step` rows keyed by `skill`, not one fused row.
- `test_measure_cache_efficiency_main_prints_relative_path`
  - Monkeypatch `measure_cache_efficiency()` to return a path under a synthetic consumer repo root (not `tokens._repo_root()`).
  - Assert return code `0` and `WROTE\tlarch-logs/measure-cache-efficiency/...`.

Reuse existing local helpers where practical:
- `_tsv_rows` can parse each section after splitting on `# per_run` / `# per_step`.
- Existing monkeypatch style in the measurement tests is sufficient.

### UPDATED: docs/run-log-cli.md

Add a `token measure-cache-efficiency` section in the run-log CLI docs (acceptance requirement):
- Command:
  - `python3 python/cli.py token measure-cache-efficiency`
- Purpose:
  - Ranks committed run-log cache-create versus cache-read outliers per run and per step.
- Inputs:
  - Existing committed `token-report.json` and `token-report-final.json` under consumer `larch-logs/<skill>/*/`.
  - Existing ledger fallback through `report_tokens_scan.py` where available.
  - Consumer repo root from `report_tokens_scan.scan()` (`ScanResult.repo_root`), not the plugin checkout.
  - `larch-logs/measure-cache-efficiency/<date>.tsv` under the consumer repo.
  - Stdout: `WROTE\t<relative-path>`.
  - Two sections: `# per_run` and `# per_step`.
- Scope note:
  - Measurement only.
  - No capture-path changes.
  - No CI gate.
- Behavior note:
  - Scans `design` and `implement` separately; per-run and per-step rows preserve the scan-origin skill so homonymous step labels do not fuse across skills.
  - Per-step ratios aggregate effective cache-create contributions per run before dividing by summed cache-read.

## Edge cases

- A row with nonzero effective create and zero `cache_read` gets ratio `inf` and ranks first.
- A row with zero effective create and zero `cache_read` is omitted.
- `cache_create_effective` uses split sum when `cache_create_5m + cache_create_1h > 0`, otherwise falls back to `cache_create`. This covers `claude_sub` vendor rows and per-step dicts where split keys are present but zero while combined `cache_create` is nonzero.
- Per-step grouped ratios sum per-contribution effective creates (`effective_cache_create_sum`) and divide by summed `cache_read`; do not apply `_cache_create_effective` only once to summed raw buckets after mixing split and legacy rows.
- Per-step bucket reads must use each item’s nested `totals` mapping; passing the row object itself yields zero cache fields.
- Per-step ratios use summed buckets across runs; do not rank on averaged per-run ratios.
- Legacy rows with only combined `cache_create` still count when split buckets are absent or zero.
- Design and implement records with the same step label remain separate because aggregation keys include scan-origin `skill`.
- Malformed reports, symlinked run dirs, symlinked reports, and missing reports keep the existing `report_tokens_scan` behavior.
- Empty corpora still write a valid TSV with section headers and no data rows.
- Design runs without `token-report-final.json` can still be recovered through the existing committed-ledger fallback when available.

## Failure modes

- If `git rev-parse` fails inside `report_tokens_scan.scan`, the command should fail the same way sibling scan-backed analysis fails.
- If a report contains non-object lane or `per_step` data, skip that malformed subsection rather than failing the whole measurement.
- If a per-step item lacks object `totals`, skip that item rather than treating the row wrapper as bucket data.
- If output writing fails, let the existing atomic writer exception surface.
- If scan-backed output were anchored on `tokens._repo_root()`, the TSV would land in the plugin checkout while reads target consumer `larch-logs`; binding to `ScanResult.repo_root` prevents that split-brain failure.
- If merged records lose scan-origin `skill`, homonymous steps fuse and outlier ranks corrupt both TSV sections.

## Testing strategy

Run only changed Python tests and relevant checks:
- `python3 -m pytest python/tests/report/test_tokens.py`
- `make py-lint`
- `python3 python/cli.py checks run-relevant`

Manual smoke check, optional after unit tests:
- `python3 python/cli.py token measure-cache-efficiency`
- Confirm it prints `WROTE\tlarch-logs/measure-cache-efficiency/<date>.tsv` relative to the consumer repo cwd.
- Inspect the TSV headers and top ranked rows, including any `claude_sub` legacy-create outliers and separate design versus implement rows for the same step label.

## Acceptance

Run only changed Python tests and relevant checks:
- `python3 -m pytest python/tests/report/test_tokens.py`
- `make py-lint`
- `python3 python/cli.py checks run-relevant`

Manual smoke check, optional after unit tests:
- `python3 python/cli.py token measure-cache-efficiency`
- Confirm it prints `WROTE\tlarch-logs/measure-cache-efficiency/<date>.tsv` relative to the consumer repo cwd.
- Inspect the TSV headers and top ranked rows, including any `claude_sub` legacy-create outliers and separate design versus implement rows for the same step label.

diff_added: 295
diff_deleted: 0
mechanical_churn: false
diff_lines: 295

## Test plan
(no test plan section in plan-file)
