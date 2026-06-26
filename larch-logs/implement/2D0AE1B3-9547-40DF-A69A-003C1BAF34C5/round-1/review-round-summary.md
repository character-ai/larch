# Review Round 1

- Mode: `diff`
- 10 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: TEST_THRESHOLD stub misreports dropped-slot counters
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `TEST_THRESHOLD` stub in `python/review_test_support.py` hardcodes `FAILED_SLOTS=0` / `COUNTED_SLOTS=4` and sets `DROPPED_STATIC_SLOTS=1` whenever any `--dropped-slots-file` is passed, conflating static and dynamic straggler semantics. Harnesses passing a dynamic-only straggler dropped-slots file get `DROPPED_STATIC_SLOTS=1`, so review-core tests keyed off the stub cannot detect regressions in real threshold accounting (including `--intended-slots` from `SLOT_COUNT`, `--panel-manifest` forwarding, or `STRAGGLER_DROPPED_COUNT` append).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Compute stub DROPPED_STATIC_SLOTS from TSV row content or use real check-reviewer-failure-threshold in dynamic integration tests.
  - From codex-specialist-testing-output.txt: Either route the new integration coverage through the real check_reviewer_failure_threshold command, or extend the stub to compute FAILED_SLOTS, COUNTED_SLOTS, DROPPED_SLOTS, DROPPED_STATIC_SLOTS, DYNAMIC_FAILED_SLOTS, and DYNAMIC_DROPPED_SLOTS from the collector, dropped-slots, and reviewer-output inputs.


### FINDING_2: Plan-required regression tests missing from test_review_pipeline.py
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple plan-required threshold and dispatch regressions are absent from `python/test_review_pipeline.py`. CI can stay green while dynamic drop accounting, no-double-count guards, real-threshold review-core integration, prune+straggler WARN coexistence, duplicate dropped-slots dedupe, and related edge cases regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing tests from the plan acceptance checklist, prioritizing real-threshold review-core and FINDING_3 coverage.
  - From cursor-specialist-testing-output.txt: Add stubbed-dispatch + real-threshold review-core test per plan (#FINDING_6), or make TEST_THRESHOLD compute counters from supplied argv/inputs.
  - From cursor-specialist-testing-output.txt: Add threshold test: collector OK for manifest-mapped slot, dropped TSV row for same slot with basename resolution miss → FAILED_SLOTS=0, COUNTED_SLOTS=1, DYNAMIC_DROPPED_SLOTS=1.
  - From cursor-specialist-testing-output.txt: Add check-reviewer-failure-threshold test with empty collector and successful dyn-*-output.txt reviewer-output-files only.
  - From cursor-specialist-testing-output.txt: Add dispatch-panel fixture with prune WARN plus waterfall straggler drop; assert both WARN and WATERFALL_WARN on stdout.


### FINDING_3: Grandparent collector-results.env fallback reads stale data
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_failed_reviewers` in `python/progress_report.py` probes `round_dir.parent.parent` for `collector-results.env` despite per-round collectors living under `round-N/`. A stale grandparent collector from an earlier run (or unrelated `/tmp/collector-results.env`) can make a later implement round inherit foreign static failures and mislabel Reviewer slot failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Limit fallback probing to round_dir and round_dir.parent for implement round-* dirs, or gate parent.parent to design-only layouts.
  - From codex-specialist-correctness-output.txt: Remove the grandparent probe for implement runs, or gate it behind a legacy-layout check so only historical committed rounds can use it.


### FINDING_9: Synthetic fallback double-counts when panel manifest is missing
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `python/review_pipeline.py:1913-1959`, synthetic fallback for unresolved dynamic drops only checks `counted_slot_tools`, which is only filled from manifest reverse-maps. With a missing or malformed `panel-manifest`, a dynamic collector record and a later unresolved drop for the same slot/tool both count, inflating `FAILED_SLOTS` and `COUNTED_SLOTS` by one.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Record seen slot/tool pairs from collector records independently of the manifest, or derive them from the collector basename before synthetic fallback.


### FINDING_10: Plan-required E2E warn_count tests absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required E2E `warn_count` tests for dynamic vs static straggler drops are absent from `python/test_exec_issue_detail.py` and `python/test_final_report.py`. The primary #5499 symptom was `Warnings: 0` in final-summary despite a hung dynamic reviewer. Unit tests cover `_surface_dropped_reviewer_warning` in isolation but not the `execution-issues.md` → `count_load_result` → final-report Warnings path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add E2E tests asserting warn_count >= 1 after dynamic drop with THRESHOLD_OK=true, warn_count == 0 for static-only straggler, and warning persistence after successful degraded retry (#FINDING_5).


### FINDING_11: _failed_reviewers does not suppress dropped rows after collector OK
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_failed_reviewers()` in `python/progress_report.py:1004-1025` only treats collector records with non-OK status as seen, so a collector OK or `cap_hit` result does not suppress a matching dropped-slots row. A round with a successful collector record and a matching dropped-slots ledger entry still shows a non-zero Reviewer slot failures total.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Track every collector basename, not just substantive failures, and skip any dropped row whose normalized basename already appeared in collector results before incrementing the failure total.


### FINDING_12: Complexity baseline regressions block make lint
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: blocking
- **Concern**: The complexity baseline was lowered for unchanged `agents.py` symbols in `python/complexity-baseline.json:147-150`, so the branch fails the required complexity lint. `python/cli.py lint complexity-baseline` reports baseline regressions for `agents.py:cursor_auth_preflight`, `_review_launch_cursor`, `launch_cursor_implement_main`, plus a missing `review_and_fix.py:_run_coder_cursor` record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Regenerate `python/complexity-baseline.json` from the current branch with the repo command, or revert the unrelated `agents.py` baseline changes and restore the missing `review_and_fix.py` baseline row so `make lint` passes.


### FINDING_13: STRAGGLER_DROPPED_COUNT backstop false-positives on static stragglers
- **Reviewer(s)**: dyn-dyn-threshold-accounting-output.txt, dyn-dyn-retry-warnings-output.txt
- **Severity**: important
- **Concern**: `_dynamic_evidence_in_manifest` in `python/review_and_fix.py:2214-2280` returns true when the panel manifest lists any `dyn-*` slot or `dyn-*` output basename, not when a dropped/straggler event actually involved a dynamic reviewer. `_surface_dropped_reviewer_warning` uses this in the `STRAGGLER_DROPPED_COUNT` backstop (`has_dynamic_backstop = straggler > 0 and (... or _dynamic_evidence_in_manifest(...))`). `_run_round` always passes `panel_manifest=round_dir / "panel-manifest.ndjson"`. On panels with scout-selected dynamics, a static-only straggler leaves `DYNAMIC_FAILED_SLOTS=0` and `DYNAMIC_DROPPED_SLOTS=0`, but `STRAGGLER_DROPPED_COUNT=1` still satisfies the backstop because the manifest contains unrelated `dyn-*` rows. That emits a false "dynamic reviewer slot drop/failure" warning, violating pinned static-straggler suppression (#5047). The same bug can fire after a successful degraded retry when `_merge_dropped_reviewer_attempt` preserves `STRAGGLER_DROPPED_COUNT=1` while clearing dynamic counters. `test_surface_dropped_reviewer_warning_static_straggler_backstop_does_not_warn` passes only because it passes `panel_manifest=None`, not the production call shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-threshold-accounting-output.txt: Restrict the backstop to dynamic-qualified evidence only. Use `_dynamic_evidence_in_dropped_file(dropped_slots_file)` as the primary signal, or change `_dynamic_evidence_in_manifest` to return true only for manifest rows whose `(slot, tool)` appears in the dropped-slots TSV with a `dyn-*` slot (or whose output basename matches a dropped dynamic row). Do not treat mere presence of dynamic manifest rows as drop evidence.
  - From dyn-dyn-retry-warnings-output.txt: Restrict the backstop to dynamic-qualified evidence only. Prefer `_dynamic_evidence_in_dropped_file` (dyn-* rows in the dropped-slots TSV) and/or require `DYNAMIC_DROPPED_SLOTS > 0` / `DYNAMIC_FAILED_SLOTS > 0` from the merged accumulator; do not treat mere manifest presence of launched dynamic slots as drop evidence. If a manifest fallback is still needed when the TSV is missing, cross-reference dropped `STRAGGLER_DROPPED_COUNT` against manifest rows for slots that actually appear in the dropped ledger, or emit a separate `DYNAMIC_STRAGGLER_DROPPED_COUNT` from `agent_waterfall.py`. Add a regression test with a manifest containing `dyn-*` slots plus a static-only `straggler-dropped` TSV row and assert `surface_warning` is not called.


### FINDING_14: _preserve_drop_diagnostic follows symlinks without bounds check
- **Reviewer(s)**: dyn-dyn-run-log-drops-output.txt
- **Severity**: important
- **Concern**: `_preserve_drop_diagnostic` in `python/agent_waterfall.py:842-846` reads `.failure-diag` / `.launch-stderr` with `source.is_file()` and `read_text()` and does not reject symlinks. On Unix, `is_file()` is true for symlinks, so `read_text()` follows them. `write-round` skips symlink artifacts at commit time, but preservation may already have copied the symlink target into a regular `dropped-*-*.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-log-drops-output.txt: Reject symlink sources (`is_symlink()`), resolve under the round directory, and read only regular files whose resolved path stays under the review tmpdir.


### FINDING_16: dropped-* artifacts use weaker redaction than pre-flush scrub path
- **Reviewer(s)**: dyn-dyn-run-log-drops-output.txt
- **Severity**: important
- **Concern**: `dropped-*-*.txt` artifacts in `python/run_logs.py:3129-3138` use `redact.redact()` only at `write-round` staging. Pre-flush log commit uses the stronger `scrub_log_secrets()` path (`python/run_logs.py:1759-1769`), which also covers Cursor and other `_EXTRA_SECRET_FAMILIES`. Dropped diagnostics can retain scrub-only secret shapes in the run-log tree until flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-run-log-drops-output.txt: Run `scrub_log_secrets()` (fail-closed on residual) in `_stage_round_artifact` for `dropped-*-*.txt` and `*.dropped-slots`, or route these artifacts through `_redact_to_temp` / the same scrub path used before `larch-log` commit.


