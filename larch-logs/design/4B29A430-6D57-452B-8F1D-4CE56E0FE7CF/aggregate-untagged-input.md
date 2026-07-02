### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/tokens.py
- **Concern**: Merged scan records must carry scan skill; RunRecord has no skill field. Scenario: `RunRecord` (`report_tokens_models.py`) stores issue metadata and vendor totals but not skill; `report_tokens_scan._workflow` always returns `""`. The plan concatenates design and implement `ScanResult.records` and groups per-step rows by `(skill, step, lane)`, yet helper signatures omit a `skill` argument. Shared step labels such as `0`, `3`, and `5` exist in both skills, so omitting skill merges unrelated steps, corrupts summed buckets and `runs`, and mis-ranks outliers in both TSV sections.
- **Proposed resolution**: Mirror `report_tokens_cli.py`: iterate each `scan(runner, skill=..., resolve_repo=False)` separately and thread `skill` into `_cache_efficiency_step_rows_for_record` / `_measure_cache_efficiency_records` (e.g. `(skill, record)` pairs). Emit per-run `skill` from that binding, not from `RunRecord`. Add a unit test with the same step name in design and implement asserting separate per-step rows.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py (plan.txt:28-32)
- **Concern**: Per-step aggregation drops legacy create tokens when a group mixes split and combined schemas. Scenario: The plan computes effective create from summed raw buckets. If any run in a `(skill, step, lane)` group has `cache_create_5m + cache_create_1h > 0`, combined-only legacy `cache_create` from other runs in that same group is discarded, so committed mixed-history groups get under-ranked.
- **Proposed resolution**: Sum raw TSV columns as planned, but also accumulate an effective-create contribution per per-step record using `_cache_create_effective`; compute the grouped ratio from `sum_effective_create / sum_cache_read`.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py (plan.txt:69-75)
- **Concern**: Bare `RunRecord` concatenation loses the scan skill label. Scenario: The plan says to concatenate scan records, but `RunRecord` has no `skill` field. After merging `design` and `implement` records as bare records, per-run `skill` output and `(skill, step, lane)` grouping cannot be computed correctly.
- **Proposed resolution**: Carry records as `(skill, RunRecord)` pairs, or an equivalent small wrapper, from each scan through `_measure_cache_efficiency_records`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Scan skill must be threaded into row builders; RunRecord has no skill field. Scenario: The plan says to concatenate records from design and implement scans and to group per-step rows by (skill, step, lane), but RunRecord only carries issue metadata and token buckets. A flat concat loses which scan produced each record, so per-run skill cells can be blank or wrong and implement Step 5 rows can merge with design Step 5 rows when step labels collide.
- **Proposed resolution**: Iterate each scan with its skill label (for skill, scan_result in (("design", design_scan), ("implement", implement_scan)): for record in scan_result.records: ...) or build list[tuple[Skill, RunRecord]] before _measure_cache_efficiency_records; pass skill into per-run and per-step builders. Add a unit assertion that design and implement records with the same step name stay in separate per_step groups.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py
- **Concern**: Per-step bucket reads must use each per_step item totals sub-mapping. Scenario: Committed reports store per_step as {"step": "...", "totals": {...}} (see tokens._per_step_json and report_tokens_scan._phase_rows). The plan points at raw_report[lane]["per_step"] but does not require drilling into totals. Passing the row object into _cache_lane_totals_from_mapping yields zero cache fields and drops or mis-ranks every per_step outlier.
- **Proposed resolution**: In _cache_efficiency_step_rows_for_record, read step from item["step"] and pass _as_mapping(item.get("totals")) into _cache_lane_totals_from_mapping; skip rows with missing/non-object totals. Extend the per-step aggregation test to use nested totals dicts.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:planned-lines-28-32
- **Concern**: Prior cache-effective fixes are incomplete for mixed legacy and split per-step groups.. Scenario: The plan sums raw cache_create, cache_create_5m, and cache_create_1h, then applies split_sum if split_sum > 0 else cache_create. If one run for the same skill, step, and lane has split buckets and another legacy run has only combined cache_create, the legacy create tokens are dropped from the per-step ratio and ranking.
- **Proposed resolution**: For per-step groups, accumulate an effective_create_sum by applying _cache_create_effective to each contribution before adding it. Keep raw bucket sums for TSV columns. Compute ratio and sort from effective_create_sum over summed cache_read. Update the aggregate test to mix one split row with one legacy combined-only row.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_models.py:57-79
- **Concern**: Merged scan records must carry the scan skill; RunRecord has no skill field. Scenario: The plan concatenates design and implement `ScanResult.records` and groups per-step rows by `(skill, step, lane)`, but `RunRecord` stores no skill (`workflow` is always empty from `report_tokens_scan._workflow`). An implementation that merges bare records and groups only by `(step, lane)` would fuse homonymous steps such as design `3` and implement `3`, corrupting `runs`, bucket sums, and outlier ranks.
- **Proposed resolution**: When merging scans, bind each record with the `skill` argument passed to `report_tokens_scan.scan()` (e.g. `list[tuple[Skill, RunRecord]]`); thread that `skill` through `_cache_efficiency_step_rows_for_record`, per-run row construction, and per-step aggregation; add a unit test with the same step label under both skills asserting two distinct per-step rows.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_models.py:56-79
- **Concern**: Merging bare RunRecord values loses the scan skill needed for required output. Scenario: The plan says to concatenate design and implement scan records, but RunRecord has no skill field. Per-run skill cells and per-step grouping by skill can become missing, guessed, or collapsed across design and implement rows with the same step and lane.
- **Proposed resolution**: Carry the scan skill with each record, for example list[tuple[Skill, RunRecord]], and build both per-run rows and per-step aggregation keys from that preserved skill.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:measure_cache_efficiency
- **Concern**: RunRecord has no skill field; plan never binds scan skill when merging design and implement results. Scenario: `RunRecord` only carries issue metadata and vendor totals (`python/larch/report/report_tokens_models.py`); `report_tokens_scan.scan()` takes `skill` but does not store it on records. The plan says to concatenate both scans and aggregate per-step by `(skill, step, lane)` with per-run `skill` columns, yet `measure_cache_efficiency()` only says "Concatenate records from both scans" and `_cache_efficiency_step_rows_for_record` has no `skill` parameter. Implementations that flatten records lose skill, so identical step labels (e.g. implement Step 3 vs design Step 3) merge and rank on the wrong combined cache buckets.
- **Proposed resolution**: In `measure_cache_efficiency()`, iterate `for skill in ("design", "implement")`, scan each skill, and accumulate tagged pairs such as `(skill, record)` (or an internal row type carrying `skill`). Pass `skill` into `_cache_efficiency_step_rows_for_record` and per-run row builders so every emitted row and bucket key includes the scan-origin skill before `(skill, step, lane)` aggregation.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:437-446
- **Concern**: Per-step effective-create aggregation drops legacy combined creates when a group also has split-bucket rows. Scenario: The plan sums cache_create, cache_create_5m, and cache_create_1h across runs, then applies split_sum if split_sum > 0 else cache_create. Existing committed reports can mix split rows and legacy combined-only rows for the same skill, step, and lane. Once split_sum is positive, the ratio numerator ignores the legacy combined-only cache_create tokens and under-ranks real outliers.
- **Proposed resolution**: Keep summing raw bucket columns for TSV output, but add a separate effective_cache_create_sum accumulator. For each per-step contribution, compute split_sum if split_sum > 0 else cache_create, add that to the accumulator, and compute the per-step ratio from effective_cache_create_sum divided by summed cache_read. Extend the aggregation test with one split contribution plus one legacy combined-only contribution in the same group.
