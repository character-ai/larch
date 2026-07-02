### OOS_1: [OUT_OF_SCOPE] Missing empty-corpus unit test
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Missing unit test for the empty corpus edge case specified in the plan. Empty design/implement scans may regress to crashes or malformed output without a headers-only contract test. Add a test monkeypatching `scan` to return empty `ScanResult` records and assert section headers with no data rows plus successful main exit.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Verified edge-case behaviors
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Implementation matches specified edge-case behavior: legacy cache-create handling via split buckets with combined fallback; scan-origin `skill` keeps homonymous steps separate across design/implement; malformed lane/`per_step`/`totals` input is skipped without aborting; all-zero rows are excluded from ranking and zero-read/nonzero-create rows rank first with `inf`; output is anchored under `ScanResult.repo_root`; TSV cells are sanitized and writes use `atomic_write` with `nofollow=True`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] `_measure_stamp()` does not sanitize `LARCH_MEASURE_DATE`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_measure_stamp()` reads `LARCH_MEASURE_DATE` without sanitization, so path segments in that env var can shift the output file (same pattern as other `measure-*` commands). Pre-existing helper, not introduced by this diff; operator-controlled env var.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Same-day TSV overwrite
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Same-day runs overwrite `larch-logs/measure-cache-efficiency/<date>.tsv` because the stamp is date-only. Inherited from sibling measurement commands; acceptable for measurement tooling.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Per-step `runs` incremented per contribution per plan
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Per-step `runs` counts every `per_step` entry, including zero-cache contributions in mixed groups, so `runs` can exceed runs with actual cache activity. Matches the plan’s “increment runs per contribution” rule; ratio math remains correct.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Verified testing and CI surface
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `("token", "measure-cache-efficiency")` is registered and `test_all_registry_targets_resolve_to_callable_mains` will resolve `measure_cache_efficiency_main` on full CI. New tests live in `python/tests/report/test_tokens.py` and are not excluded by existing Makefile `-k` filters for that file. No breaking changes (additive CLI verb and private helpers only). Top-level `report_tokens_models` import in `tokens.py` does not introduce a cycle (`report_tokens_scan` → `tokens` → `report_tokens_models`).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] No dedicated empty-corpus test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Plan edge case “empty corpora still write a valid TSV with section headers and no data rows” has no dedicated test. Code path is trivial (empty tuples still render headers); failure would be obvious on first smoke run and does not block shipping the measurement command.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Malformed `per_step` / missing `totals` skip behavior untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Malformed `per_step` / missing `totals` skip behavior is untested. Implementation uses explicit `isinstance` guards and `continue`; mirrors existing `report_tokens_scan` defensive patterns. A test would be nice hygiene but is not required for this feature’s stated acceptance.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] No dedicated registry assertion for measure-cache-efficiency
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: No registry assertion specifically for `("token", "measure-cache-efficiency")` (unlike some design/implement verbs). `test_all_registry_targets_resolve_to_callable_mains` already covers all registry entries generically; sibling `measure-md-cost` follows the same pattern without a dedicated assertion.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] `runs` counts `per_step` entries, not unique runs
- **Reviewer(s)**: dyn-dyn-cache-accounting
- **Severity**: latent
- **Concern**: `runs` counts `per_step` list entries, not unique runs. If a single run log ever contains duplicate step marks for the same `(skill, step, lane)`, `runs` can exceed the number of distinct runs without affecting ratio math.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cache-accounting: Track a per-group set of run identifiers (for example issue number plus `started_at`) and set `runs` to the cardinality of that set.

### OOS_11: [OUT_OF_SCOPE] No post-scan `repo_root` guard
- **Reviewer(s)**: dyn-dyn-cache-accounting
- **Severity**: latent
- **Concern**: `measure_cache_efficiency()` uses `repo_root` typed as `Path | None` without a post-scan guard; a future `scan()` change that returned `None` would fail at `out_path = repo_root / ...`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cache-accounting: Assert or raise if `repo_root is None` after the scan loop, mirroring fail-closed handling in sibling scan-backed commands.

