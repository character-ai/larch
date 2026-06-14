# Review Round 5

- Mode: `diff`
- 16 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 7a diagram failure aborts with exit 1 instead of degraded exit 0
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: Diagram generation failure sets `STEP_7A_BAIL_REASON=diagram-failed` and returns exit 1. Bash treated diagram failure as non-fatal degradation (exit 0, empty bail reason, warning append) per `step-7a.md` and `test-step-7a.sh`. Python aborts Step 7a and can block the pre-ship flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Set DIAGRAM_STATUS=failed append warning clear stale artifacts leave bail empty return 0.
  - From dyn-migration-parity-output.txt: Drop the bail/exit-1 path for diagram generation failures; append the warning/tool-failure row like the old helper; always exit `0` unless argv validation fails or the `7a.r` rebase probe returns non-zero.


### FINDING_10: write_final_report no longer derives summary fields from run-log data
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Python `write_final_report` no longer derives fields the deleted bash writer computed live. Runs with `oos-issues.ndjson`, review tally JSON, or a PR number but without pre-populated summary keys in `ship-pr-state.sh` render `OOS filed: 0`, review lines as `N/A`, and PR line counts as `N/A` even though run-log data exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Recreate the old derivation in `write_final_report`: compute PR line counts, read review tally JSON files, derive OOS count and URLs from `oos-issues.ndjson`, and pass the derived values into `render_run_summary`.


### FINDING_11: file_oos issue-cap lacks parity with oos-issue-cap.sh
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: Python hardcodes `OOS_EXCERPT_MAX_CHARS = 800`, ignores `OOS_ISSUE_CAP_EXCERPT_MAX` (bash default `200`), uses a different rollup body (no cap/script attribution, no per-item file-ref extraction), and does not renumber surviving `### OOS_<N>:` headings after compaction. Live callers (`file-design-oos.sh`, Step 9a.1) hit the Python path; capped batches can exceed intended issue-body size and differ from documented `/issue` input shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Port the bash cap algorithm: honor and validate `OOS_ISSUE_CAP_EXCERPT_MAX`, reuse the excerpt truncation rules (UTF-8-safe), emit the same rollup description block, and renumber kept headings before atomic write.


### FINDING_12: final-report step18b always returns process exit 0 on write failure
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `final-report step18b` always returns exit 0 even when `write_final_report` fails (`wfr_rc != 0`). Bash wrapper reads `WFR_RC` from stdout; callers that check only CLI exit code treat failed final-report render as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Return `wfr_rc` (or `2` on validation failure) from `step18b_final_report_main`, matching `write_final_report_main` semantics while still emitting `EMIT_BODY`, `WFR_RC`, and related KVs.


### FINDING_13: implement-finalize returns exit 1 for expected stall tails
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `implement-finalize postbump`/`postmerge`/`teardown` return CLI exit 1 whenever `result.outcome != Outcome.OK`. Legacy bash kept process exit 0 on expected stall tails (`rebase-failed`, `push-failed`, etc.) and encoded failure in `STATUS=`. `scripts/ship-pr.sh` records a Tool Failure whenever `rc != 0` before routing on `STATUS`, so normal postbump stalls produce spurious failure noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Emit the same KV tails but return exit `0` for expected stall statuses (reserve non-zero for argv/state validation errors), matching the bash best-effort contract.


### FINDING_16: ship-pr-exit-matrix.md still references stall-recovery-report.sh
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Exit 6 transient-retry cap and ship-pr escalation ledger handoffs still tell the orchestrator to invoke `stall-recovery-report.sh` (`seed-terminal-state`, `record-escalation`), while live `/implement` and `/design` callers use `python/cli.py stall-recovery`. On `LARCH_SHIP_PR_IMPL=bash`, Step 8+ exit handling can follow stale bash paths after the Python migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Update `ship-pr-exit-matrix.md` to the same `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery …` argv shapes used elsewhere, and align any orchestrator prose that still names `stall-recovery-report.sh`.


### FINDING_17: oos-pipeline.md cites dead ship-pr.sh routing
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Docs claim `ship-pr.sh` `pr-prep` refuses all-clear when `security-oos-observations.md` is non-empty, and cite `run_oos_disposition_gate_if_required_before_oos_pending_false` for accepted-file ordering. `scripts/ship-pr.sh` has no `oos` / `OOS_PENDING` references; `run_pr_prep_phase` only builds the PR body. That symbol is not defined on this branch or on `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Drop or rewrite those references to match real call sites (`skills/implement/scripts/step-8-oos-checkpoint.sh` → `python/cli.py oos disposition-checkpoint`, and `python/ship.py:1323-1332` on the default Python driver). Wire `pr-prep` behavior in code if the contract is still required.


### FINDING_18: oos materialize-manifest not invoked at ship pre-trigger
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Docs retargeted manifest materialization to `python/cli.py oos materialize-manifest` "at Step 2 complete and again at ship pre-trigger," but the only live materialize caller is `step2-implement.sh`. Neither `scripts/ship-pr.sh` nor `python/ship.py` invokes materialize. Post-review manifest OOS can stay unmerged into accepted-OOS files if Step 2 materialize failed open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Add a ship pre-trigger `oos materialize-manifest` call in `run_pr_prep_phase` and/or the Python ship pre-PR path, or remove "again at ship pre-trigger" from the updated docs.


### FINDING_19: Dual OOS disposition checkpoint/gate bash path remains live
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Live Step 8+ path calls `python/cli.py oos disposition-checkpoint`, but retained bash checkpoint still invokes `oos-disposition-gate.sh` (`oos-disposition-checkpoint.sh:195`). `oos-disposition-checkpoint.md` still documents the bash script as the orchestrator entry. Direct invocation or doc-following can hit a second implementation after the Python cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Delete or thin-wrap the bash checkpoint/gate pair, point `oos-disposition-checkpoint.md` at `step-8-oos-checkpoint.sh` / the Python CLI, and drop the parallel bash gate path.


### FINDING_2: Step 7a missing stale diagram artifact cleanup on skip/failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: Python omits `compose_summary_diagrams()` cleanup from bash. On skipped/failed generation, stale `code-flow-section.md` and `code-flow-diagram.md` can remain; a resumed tmpdir may trigger diagrams upsert after a failed/skipped run. `test-step-7a.sh` expects those files removed on `diagram-rejected` / `diagram-generation-failure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Delete both files unless generation succeeded; only write section from fresh ok diagram.
  - From dyn-migration-parity-output.txt: After generation, mirror bash: always clear `code-flow-section.md`; keep/copy `code-flow-diagram.md` only when `diagram_status == "ok"`, otherwise unlink stale diagram artifacts.


### FINDING_20: Makefile CI still runs legacy bash harnesses for ported C4c surfaces
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: C4c surfaces were ported to pytest (`test_pr_body.py`, `test_finalize.py`) but CI shards still run legacy bash harnesses (`test-post-tracking-issue`, `test-generate-code-flow-diagram`, `test-step-18b-final-report`, `test-implement-cleanup-script`) against retired script contracts. Production paths use Python equivalents. CI can stay green on bash-only behavior while production routing drifts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Repoint those Makefile targets to the pytest modules (as done for `test-stall-recovery-report-*`) and delete the bash harnesses per the plan.


### FINDING_21: migrated-scripts.tsv missing C4c retired-path rows
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Plan requires every deleted C4c shell surface to be listed for `make lint-retired-scripts`. Branch retires many helpers in practice (dual live/bash+Python paths remain) but adds no manifest rows for paths such as `stall-recovery-report.sh`, `implement-finalize.sh`, `materialize-manifest-oos.sh`, or `oos-disposition-checkpoint.sh`. Stale-reference enforcement for the migration is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Append full repo-relative retired paths with the C4c tracking issue id, finish call-site cutover and script deletion, then run `make lint-retired-scripts`.


### FINDING_3: Step 7a pre-ship flush order diverges from bash contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Pre-ship flush runs post-transcript execution-issues flush before `capture-transcript` and skips `flush_logs_pre` staging when `no_logs_commit=true`. With `--no-logs-commit`, transcript warnings and vendor/token/timing batches never flush; post-transcript flush always precedes capture. Bash order: stage reports/vendor, capture transcript, post-transcript flush, then optional commit; staging happens even when commit is skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore bash order: stage reports/vendor capture transcript post-transcript flush then optional commit; stage even when no_logs_commit skips commit only.


### FINDING_6: Pytest Step 7a coverage gaps vs bash harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/test_step_7a.py` omits diagram failure, stale cleanup, `no-logs-commit`, and stdout-relay cases covered by `test-step-7a.sh`. Step 7a regressions can merge with green `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port the corresponding cases from test-step-7a.sh.


### FINDING_8: stall_recovery clear-stall / seed-terminal-state break state contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `clear_stall()` only deletes local artifacts and emits `CLEARED=true`, leaving `STALL_TRACKING=true` in `ship-pr-state.sh` so `normalize-outcome` still reports stalled. `seed_terminal_state()` is a stub: wrong flag names, ignores `--stall-step`, overwrites `ship-pr-state.sh` with only three keys, drops `EXIT_CODE`, `BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, and lacks `SEED_MODE` and bash validation. Step 18a calls `python/cli.py stall-recovery seed-terminal-state --stall-step N`; Python sets `STALL_STEP=unknown`, breaking classify/compose-report and terminal routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port cmd_seed_terminal_state from stall-recovery-report.sh (rewrite vs seed, --stall-step, preserved keys, symlink/malformed guards, SEED_MODE).
  - From codex-generic-output.txt: Port the old state-file rewrite logic: validate state files, reject symlinks or malformed files, preserve existing keys, clear `STALL_TRACKING`/`STALL_STEP` on clear, and seed defaults plus `EXIT_CODE=4` while accepting `--stall-step`.


### FINDING_9: OOS disposition gate CI has only four pytest cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Makefile OOS disposition gate CI target runs only four pytest cases after replacing the thousand-line bash harness. Regression in checkpoint ndjson discovery, legacy-header counting, or Tool Failures logging would not fail CI on the Python ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port test-oos-disposition-gate.sh scenarios into python/test_file_oos.py or run both until parity is proven


