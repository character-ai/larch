# Review Round 1

- Mode: `diff`
- 11 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: gc_run_logs.py naive `started_at` datetime comparison crashes `_plan`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: Manifest `started_at` values parsed with `datetime.fromisoformat()` can be timezone-naive (for example `2020-01-01T00:00:00`). Comparing them to a UTC-aware cutoff raises `TypeError`, aborting `gc-run-logs run` (including `--dry-run`) before `STATUS` KV emission. The retired bash path used ISO string ordering only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Normalize to UTC or fall back to string comparison on TypeError.
  - From codex-specialist-correctness-output.txt: Normalize naive datetimes to UTC or fall back to string comparison.
  - From cursor-specialist-edge-cases-output.txt: Normalize to UTC or catch TypeError and use the string cutoff fallback.
  - From codex-specialist-edge-cases-output.txt: Normalize parsed timestamps to UTC before comparing, or catch TypeError with ValueError and fall back to string comparison or skip handling.
  - From dyn-migration-parity-output.txt: Normalize parsed dates to UTC-aware before comparison, or catch `TypeError` and fall back to the existing string compare branch (`run_date >= cutoff_dt`).


### FINDING_3: pr_body.py `render_run_summary_main` lacks local `SystemExit` handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `render_run_summary_main` does not wrap `parse_args` in `try/except SystemExit` unlike peer CLI entrypoints. Direct in-process callers get an uncaught `SystemExit` instead of return code 2, and `STATUS=ok` may be emitted incorrectly on usage errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wrap parse_args in try/except SystemExit and return 2 before any STATUS=ok emission.


### FINDING_4: Missing post-revise round-meta harness coverage in `test-design-step3-review.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-retirement-hygiene-output.txt
- **Severity**: important
- **Concern**: Plan-required harness coverage for post-revise `round-meta.json` refresh is absent. The live loop was cut over to `python/cli.py progress write-design-round-meta`, but `make test-design-step3-review` has no default-path or `WRITE_DESIGN_ROUND_META_SH` override assertions. Regression to a stale `-x` gate, dropped override handling, or a missing Python meta-write path would not be caught by CI while embedded-loop pytest still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add default-path and WRITE_DESIGN_ROUND_META_SH override harness tests per plan.
  - From cursor-specialist-testing-output.txt: Add grep/runtime harness cases for default python3 cli.py progress write-design-round-meta and override stub invocation after revise.
  - From codex-specialist-testing-output.txt: Add default, override, and non-fatal failure cases to skills/design/scripts/test-design-step3-review.sh.
  - From dyn-retirement-hygiene-output.txt: Add the planned static or fixture-based assertions to `skills/design/scripts/test-design-step3-review.sh`, mirroring the override/default pattern already used for other Step 3 seams.


### FINDING_5: Missing `test_implement_round_meta_write_failure_does_not_block_flush`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required test `test_implement_round_meta_write_failure_does_not_block_flush` is missing. A #4038-class regression where `write_implement_round_meta` failure skips `flush_round_log_after_coder` would ship undetected, leaving committed run logs without per-round data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add monkeypatch test asserting flush still runs when write_implement_round_meta raises.
  - From cursor-specialist-testing-output.txt: Add test_implement_round_meta_write_failure_does_not_block_flush monkeypatching write_implement_round_meta to raise/return failure and asserting flush still runs.


### FINDING_6: Missing `render_run_summary_main` CLI contract tests in `test_pr_body.py`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `render_run_summary_main` CLI tests are missing. Missing or invalid required args could regress to emitting `STATUS=ok` or unknown summaries without pytest catching it. Consumers such as `write-final-report` may treat usage errors as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add parametrized usage-error tests for exit 2 and no stderr STATUS=ok.
  - From cursor-specialist-testing-output.txt: Add CLI tests calling render_run_summary_main with invalid/missing args (exit 2, no STATUS=ok) and one success case checking stderr STATUS=ok and OUTPUT_FILE.
  - From codex-specialist-testing-output.txt: Add render_run_summary_main tests for success stdout/stderr, note lines, cost-unavailable, and required-arg/invalid-value exit-code behavior.


### FINDING_7: Phase-detail Gantt omits non-complete vendor timing rows
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-gantt-roundmeta-output.txt
- **Severity**: important
- **Concern**: `_render_phase_gantt()` reuses `_progress_vendor_rows()`, which drops vendor timing rows whose status is not `complete` or `OK`. The retired `render-review-phase-detail.sh` Gantt had no status filter; it only required vendor rows with numeric start/end and window overlap. Timed-out or `signal` vendor rows with valid timestamps can be omitted, and the report can incorrectly show no overlapping reviewer timing tasks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Include signal/unknown rows for completed phase-detail Gantt, or add a mode that matches the retired bash behavior.
  - From dyn-gantt-roundmeta-output.txt: Give `_progress_vendor_rows()` a phase-detail mode (or a `require_complete_status=False` flag) and call that from `_render_phase_gantt()` so completed-round Gantt parity matches the retired bash contract, while keeping the stricter status filter for live inflight Gantt if that behavior is still desired there.


### FINDING_8: gc_run_logs.py escape symlink aborts slim mid-apply without rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: During slim apply, if one qualifying run dir succeeds and a later dir contains a child symlink resolving outside `larch-logs/`, `_is_under` raises and the operator is left on a GC branch with partial slim and `STATUS=error`, with no rollback or recovery guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip or preflight escape symlinks (count skipped); do not start apply until the plan is safe; emit explicit git checkout main recovery guidance on apply failure.


### FINDING_9: gc_run_logs.py destructive/safety paths lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_gc_run_logs.py` covers only a small set of scenarios. Plan-listed symlink enumeration, delete/slim apply, git date fallback, path-escape rejection, and destructive-boundary cases are untested. Symlink-follow, out-of-tree slim/delete, or escape bugs could reach operator `--delete` on main without CI catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expand test_gc_run_logs.py with symlink enumeration, destructive boundary rejection, slim/delete apply stubs, and remaining guard cases from the plan.
  - From codex-specialist-testing-output.txt: Add temp-repo tests with stubbed external commands for slim/delete apply paths, date fallback, symlink handling, target escape rejection, and path-limited staging.


### FINDING_10: Missing `write_design_round_meta` design-only path tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No tests cover `write_design_round_meta` design-only paths such as security OOS adjustment and panel-manifest materialization. Design post-revise `round-meta.json` could regress OOS counts or panel snapshot fields without failing implement-focused meta tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add write_design_round_meta fixtures asserting security OOS subtraction and panel-manifest/collector/revise fields.


### FINDING_11: Missing #4537 token-ledger dual-window assertion (Test 12)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing Test 12 token-ledger dual-window assertion for table Cost vs wider Gantt vendor window. Token cost could again be attributed to the wrong timing window, showing inflated table Cost while Gantt windows look correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add token-ledger fixture with in-window and out-of-window vendor spend; assert table Cost excludes out-of-window tokens and Gantt still shows wider-window vendor rows.


### FINDING_14: `render_findings_view()` treats empty `prose_body` as missing
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `render_findings_view()` maps missing `prose_body` via `str(prose) if prose else "(no prose body)"`, which also treats an explicit empty string as missing. The retired `render-findings-view.sh` used jq null-coalescing (`(.prose_body // "(no prose body)")`), which keeps `""` as empty output. Consumers that diff or hash findings views can see silent format drift on records with `"prose_body": ""`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Match jq null-coalescing: use `(no prose body)` only when `prose_body` is missing or `null`, not when it is `""`.


