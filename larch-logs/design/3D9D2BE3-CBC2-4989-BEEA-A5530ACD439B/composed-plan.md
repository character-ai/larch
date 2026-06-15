## Plan

Fix eight scoped Python and Markdown files. Route `MAIN_ADVANCED` through rebase, add rebase token sidecar fallback parity, fix research exit-code warnings, recognize live CI timing kinds, and filter CI rows from live Step 5 Gantt output.

### Files to modify/create

#### UPDATED: python/ship.py

Add explicit `MAIN_ADVANCED` handling in the merge-result branch.

- Split the current combined branch for `MERGE_RESULT_CI_NOT_READY` and `MERGE_RESULT_MAIN_ADVANCED`.
- Keep the existing review-required probe only for `MERGE_RESULT_CI_NOT_READY`.
- For `MERGE_RESULT_MAIN_ADVANCED`, run the same rebase sequence used by `monitor.goto_rebase`:
  - write ship state with `phase="rebase"`;
  - run the pre-rebase log flush;
  - fail with the same `STALLED` result when the flush skip reason is not allowed;
  - call `rebase.rebase_and_push(...)` with the existing arguments;
  - preserve `PrePushConflictHandoff` state writing;
  - increment `rebase_count`;
  - increment `iteration`;
  - write ship state with `phase="ci-initial"`;
  - continue the loop.
- Do not change merge retry policy for other merge results.

#### UPDATED: python/test_ship.py

Add a regression for the `MAIN_ADVANCED` merge path.

- Stub `ci_monitor.monitor` to return `action="merge"` and `goto_rebase=False`.
- Stub `merge.merge_pr` to return `MERGE_RESULT_MAIN_ADVANCED` once, then a post-merge success result after rebase.
- Stub `rebase.rebase_and_push` and assert it runs exactly once before the second merge attempt.
- Assert state returns to `phase="ci-initial"` after the rebase loop.
- Assert the test would fail if ship retries merge repeatedly without rebasing.

#### UPDATED: python/rebase.py

Add conflict-fixer token sidecar fallback parity for Codex and Cursor.

- Before each Codex or Cursor conflict-fix launch, remove the expected fallback sidecar path:
  - `Path(f"{output}.token-record").unlink(missing_ok=True)`.
- Do the pre-clear before `agents.launch_tier(...)`.
- Pass `allow_output_fallback=True` to `agents.ingest_launcher_token_sidecar(...)` for Codex and Cursor.
- Keep Claude unchanged.
- Keep the existing `seen_token_records` behavior.

#### UPDATED: python/test_rebase.py

Extend `make_conflict_launch_fn` coverage.

- Update the existing ingestion assertion to require `allow_output_fallback=True` for Cursor.
- Add the same assertion for Codex.
- Add a stale-sidecar test:
  - create `conflict-cursor.out.token-record` before launch;
  - have the fake launcher omit `TOKEN_RECORD=`;
  - assert the stale file was removed before ingestion.
- Add an output fallback test:
  - fake launcher writes only `${output}.token-record`;
  - fake stdout omits `TOKEN_RECORD=`;
  - use the real ingestion helper or a focused spy to prove fallback ingestion sees the expected path.

#### UPDATED: skills/research/references/research-phase.md

Fix both Bash warning snippets.

- Replace each `if ! command; then _rc=$?` pattern.
- Use the strict-mode safe pattern from discussion:
  - initialize `rc=0`;
  - run `command || rc=$?`;
  - branch on `(( rc != 0 ))`.
- Preserve the existing warning text.
- Preserve stderr temp-file handling.
- Keep `append-record` bound to `--tmpdir "$RESEARCH_TMPDIR"`.
- Keep active-ledger ingestion bound to `RESEARCH_TMPDIR`.

#### UPDATED: python/test_research.py

Add regression tests for the research-phase sidecar warning exit-code fix.

- Mock `cli.py token append-record` to exit non-zero with a fixed message.
- Assert the warning text contains the real exit code, not `0`.
- Repeat for `cli.py token record-vendor-sidecar`.

#### UPDATED: python/timing.py

Recognize live CI timing task kinds.

- Add these values to `TIMING_TASK_KINDS_ALLOWED`:
  - `codex-ci`
  - `cursor-ci`
  - `claude-ci`
- Keep existing `codex-ci-fix`, `cursor-ci-fix`, and `claude-ci-fix` values.
- Do not add a public timing API or exported CI-kind helper.

#### UPDATED: python/test_timing.py

Pin timing allowlist behavior.

- Add a parametrized test for `codex-ci`, `cursor-ci`, and `claude-ci`.
- Call `TimingLedger.record_vendor_task(...)` for each kind.
- Assert stderr does not contain `unknown task-kind`.

#### UPDATED: python/progress_report.py

Filter live inflight Gantt rows.

- Add a private `_is_ci_gantt_row(kind: str, output: str) -> bool` helper.
- Apply case normalization: lower `kind`, derive `bn = Path(output).name.lower()` when output is truthy.
- Mirror `scripts/render-review-phase-detail.sh` Gantt skip behavior:
  - skip exact task kinds `codex-ci`, `cursor-ci`, `claude-ci`;
  - skip exact task kinds `codex-ci-fix`, `cursor-ci-fix`, `claude-ci-fix`;
  - skip task kinds matching `*-ci`, `*-ci-fix`, or `*-ci-test`;
  - skip output basenames `ci.out`, `*-ci.out`, and `ci-fix-*.out`;
  - skip probe output basenames `claude.out`, `codex.out`, and `cursor.out`.
- Add `skip_ci: bool = False` to `_progress_vendor_rows(...)`.
- When `skip_ci` is true, skip matching rows before label derivation.
- Pass `skip_ci=True` from `_render_inflight_gantt(...)`.
- Leave the default unfiltered path unchanged for existing callers and tests.

#### UPDATED: python/test_progress_report.py

Add live Gantt filtering regressions.

- Add a mixed-row `_progress_vendor_rows(..., skip_ci=True)` test:
  - include one normal reviewer row;
  - include CI task-kind rows;
  - include CI output-basename rows;
  - include probe basename rows;
  - include a full-path CI output row (tests basename normalization);
  - assert only the normal reviewer row remains.
- Add an inflight Step 5 test where the timing ledger contains only CI rows.
- Assert the report still says the round is in progress.
- Assert it does not render reviewer timing Gantt output.

### Edge cases

- `MAIN_ADVANCED` can come from merge-state lag, admin failure, version advancement, or force-push recovery. All cases should force one rebase before another merge attempt.
- `CI_NOT_READY` must still wait and retry as it does today.
- Rebase fallback ingestion must not read a stale `${output}.token-record` from a prior attempt.
- A missing fallback sidecar must remain a no-op.
- Research warning paths must preserve stderr details when the failing command writes diagnostics.
- Live Gantt filtering must not hide normal reviewer rows with ordinary output names.
- Full-path output values in the timing ledger must be handled by basename normalization.

### Failure modes

- If pre-rebase log flush skips for a disallowed reason after `MAIN_ADVANCED`, return the same stalled shape as the existing `goto_rebase` path.
- If sidecar pre-clear fails due to permissions or filesystem errors, fail closed before launching the conflict fixer.
- If the progress filter drifts from the shell committed-report filter, the new mixed-row test should catch the visible CI-row leak.

### Testing strategy

Run focused tests first.

```bash
python3 -m pytest python/test_ship.py -k 'main_advanced or rebase'
python3 -m pytest python/test_rebase.py -k 'conflict_launch_fn'
python3 -m pytest python/test_timing.py python/test_progress_report.py
```

Then run repository gates.

```bash
make py-lint
make py-test
make lint
```

### Acceptance

- `MERGE_RESULT_MAIN_ADVANCED` calls `rebase.rebase_and_push(...)` before any next merge attempt.
- `MERGE_RESULT_CI_NOT_READY` behavior stays unchanged.
- Codex and Cursor conflict-fix launches pre-clear `${output}.token-record`.
- Codex and Cursor conflict-fix token ingestion passes `allow_output_fallback=True`.
- Research sidecar warning snippets report the real failing exit code.
- `codex-ci`, `cursor-ci`, and `claude-ci` produce no timing unknown-kind warning.
- Live Step 5 inflight Gantt excludes CI and probe rows.
- Focused tests and full gates pass.

## Acceptance

- `MERGE_RESULT_MAIN_ADVANCED` calls `rebase.rebase_and_push(...)` before any next merge attempt.
- `MERGE_RESULT_CI_NOT_READY` behavior stays unchanged.
- Codex and Cursor conflict-fix launches pre-clear `${output}.token-record`.
- Codex and Cursor conflict-fix token ingestion passes `allow_output_fallback=True`.
- Research sidecar warning snippets report the real failing exit code.
- `codex-ci`, `cursor-ci`, and `claude-ci` produce no timing unknown-kind warning.
- Live Step 5 inflight Gantt excludes CI and probe rows.
- Focused tests and full gates pass.

review_status: complete
rounds_completed: 3
diff_lines: 250
