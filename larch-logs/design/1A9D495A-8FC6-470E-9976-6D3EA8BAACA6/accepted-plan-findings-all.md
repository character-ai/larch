### FINDING_1: Guard runs too early in the refresh staging flow
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-Run Log Guard, Codex-dyn-Run Log Guard
- **Severity**: major
- **Concern**: The pre-terminal check is still being placed before the refresh path has finished all of its final-summary rewrites and reconciliation steps. That can reject a recovered run too early, or miss a forbidden label that a later write reintroduces before commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: I-Outcome-1 still allows forbidden labels to reach git. Run the check once at the end of the refresh branch in `_stage_pre_commit`, or in `flush_logs_pre` after `_stage_pre_commit` returns and before `_commit_run`
  - From Cursor-Innovation: Pin pre-terminal guard after full refresh staging, not after the first _write_final_report. Scenario: _stage_pre_commit refresh writes final-summary twice and runs _reconcile_stalled_summary_backstop between writes; a guard immediately after the first write would ShipError on : stalled before backstop can rewrite manifest-only recoveries to pr-created/merged, breaking the existing recovery flow and blocking legitimate pre-push refresh
  - From Cursor-Pragmatic: Call the check once at the end of `flush_logs_pre` immediately after `_stage_pre_commit` returns and immediately before `_commit_run`, using the final on-disk `final-summary.md`; do not add the check inside `_commit_run` or `commit_larch_logs` so Step 18 teardown can still commit genuinely terminal stalled or bailed summaries
  - From Codex-Pragmatic: Move the check to the end of the refresh path, after the second final-report write and reconciliation, or re-read the settled `final-summary.md` just before `_commit_run()`.
  - From Cursor-dyn-Run Log Guard: Pin placement to the end of `_stage_pre_commit()` when `mode=="refresh"` (after lines 638-639), or immediately after the `_stage_pre_commit()` call in `flush_logs_pre()` (between 677 and 699), never right after the first `_write_final_report()`.
  - From Codex-dyn-Run Log Guard: Move the check out of `_stage_pre_commit()` and run it after `_stage_pre_commit()` returns, or at least after both reconciliation helpers have completed, then gate `_commit_run()`.


### FINDING_2: Existing flush regression tests still encode the old stalled-commit behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan updates the guard but does not rewrite the existing flush/recovery tests that currently expect the first strict flush to commit a stalled summary. Once the guard lands, those tests will fail unless the recovery expectations are updated too.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan step to rewrite affected tests in `python/tests/report/test_run_logs.py` (at minimum the stalled-recovery case) so first flush refuses commit and recovery still commits `pr-created`/`shipping`
  - From Cursor-Innovation: Add ### UPDATED: python/tests/report/test_run_logs.py: rewrite skip1 expectations so a pre-terminal : stalled/: bailed/: bailed-needs-user-input summary refuses commit (RefreshSkip or ShipError), and keep recovery assertions on the later refresh after state repair
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/report/test_run_logs.py; rewrite the recovery test so the first refresh returns a commit skip (for example REFRESH_SKIP_COMMIT_FAILED) while the on-disk summary may still say stalled, and keep the second refresh committing ": pr-created" after stall clears
  - From Cursor-Requirements: Add python/tests/report/test_run_logs.py to Files to modify/create and revise stalled-summary flush tests to expect refusal or neutral labels under I-Outcome-1 instead of committed stalled snapshots
  - From Codex-Requirements: Add `python/tests/report/test_run_logs.py` to the file list and rewrite the test to expect the new rejection or a neutral first flush before the later `pr-created` recovery.


### FINDING_4: Guard exceptions need a structured RefreshSkip envelope
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-Run Log Guard
- **Severity**: major
- **Concern**: If the guard raises `ShipError` after staging, the public refresh path will bubble an exception instead of emitting the existing structured skip result. That would turn a recoverable refusal into a CLI crash or an unstructured traceback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Catch ShipError around flush_logs_pre here and map it to REFRESH_SKIP_RUN_LOG_INCOMPLETE, or have flush_logs_pre convert this guard into a RefreshSkip with that reason.
  - From Codex-Innovation: Pre-terminal guard exceptions are uncaught in the public refresh CLI. Scenario: A forbidden stalled or bailed summary will make flush_logs_pre raise ShipError, and refresh_run_logs_main does not catch it, so python/cli.py run-log refresh will crash with a traceback instead of emitting REFRESH_COMMITTED=false REASON=run-log-incomplete.
  - From Cursor-Pragmatic: After _stage_pre_commit, parse the final-summary label and on forbidden pre-terminal labels return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_COMMIT_FAILED, error=...) instead of raising through flush_logs_pre; reserve direct ShipError for strict_final_report staging failures only if that matches existing contract
  - From Codex-Pragmatic: The new ShipError path is not translated back into a structured `RefreshSkip` for non-strict refreshes.. Scenario: `python3 python/cli.py run-log refresh` depends on `refresh_run_logs_main()` to emit `REFRESH_*` KVs, and direct callers like `step_7a` expect a return value. An uncaught ShipError would drop the wire output and turn a recoverable refresh into a crash.
  - From Cursor-dyn-Run Log Guard: Uncaught `ShipError` if the guard sits between `_stage_pre_commit()` and `_commit_run()`. Scenario: Plan step 3 has the helper raise `ShipError`. Today only `_stage_pre_commit()` is inside the `try/except ShipError` block in `flush_logs_pre()` (669-681). A check placed after that block would propagate unless wrapped, breaking callers that expect a `RefreshSkip` envelope (`refresh_run_logs_main`, Step 7a, ship refresh helpers).


### FINDING_5: The guard also needs to cover the standalone run-log flush entry point
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The current plan only describes the refresh path, but `larch_log_flush_main` bypasses `flush_logs_pre`. That leaves a separate commit path able to publish a stale stalled or bailed summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Factor a shared pre-terminal check (parse run_dir/final-summary.md when present, then call _check_preterminal_outcome_label) and invoke it from flush_logs_pre and larch_log_flush_main immediately before _commit_run; keep finalize teardown commit_larch_logs unguarded per terminal carve-out


### FINDING_1: Step 7a direct run-log commit bypasses the pre-terminal guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: Step 7a still runs `run-log commit` after `flush_logs_pre()` reports the pre-terminal refusal/skip, so a staged stalled/bailed `final-summary.md` can still be published through the direct commit path instead of being blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the shared parse/check helper to larch_log_commit_main (python/larch/report/run_log_commit.py) immediately before _commit_run: when the staged implement run_dir final-summary.md parses to a forbidden label, refuse commit with a bounded warning and non-zero exit. Keep finalize teardown commit_larch_logs unguarded. Add a regression test in python/tests/report/test_run_logs.py (or test_run_log_flush.py) that seeds a forbidden heading under log_root and asserts larch_log_commit_main does not commit. List python/larch/report/run_log_commit.py under ### UPDATED: if the guard lives there.
  - From Codex-Arch: Skip the commit call when `refresh.reason == config.REFRESH_SKIP_COMMIT_FAILED`, or gate the commit on `not refresh.skipped` after the flush result is checked.
  - From Cursor-Innovation: Add python/larch/implement/step_7a.py to the plan: call the shared _preterminal_outcome_refresh_skip (or equivalent) before run-log commit and skip commit when it fires; update skills/implement/scripts/test-step-7a.sh so pre-terminal refusal does not fall through to commit.
  - From Cursor-Pragmatic: Add the same shared pre-terminal check to larch_log_commit_main in python/larch/report/run_log_commit.py (skip commit with bounded warning, mirroring larch_log_flush_main), or teach step_7a to skip run-log commit when the refresh skip was caused by a forbidden label. List run_log_commit.py (and step_7a.py if branching there) under Files to modify/create and add a Step 7a regression test.
  - From Codex-Pragmatic: Add a firm plan step to guard the Step 7a direct commit path, either by applying the same pre-terminal label check in larch_log_commit_main() for implement tmpdirs before _commit_run(), or by making Step 7a skip the direct commit after this specific pre-terminal refusal, with a focused regression for that path.


### FINDING_2: Pre-terminal heading parser should target the run-summary line
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The new label parser could misread the first `##` section instead of the canonical `## /...` run heading in `final-summary.md`, which would let forbidden labels slip through or block neutral ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify that _parse_preterminal_outcome_label scans all lines for startswith("## /") (same contract as final_report._summary_stalled_heading_index), extracts the trailing label after : or em-dash, and add a unit test with prefixed ## Architectural sections before the run heading.


### FINDING_3: `capture_transcript_main()` also needs the pre-terminal guard
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The public `run-log capture-transcript` path can still commit a run tree whose `final-summary.md` is stalled/bailed when `--defer-commit false`, bypassing the new invariant outside the refresh/flush paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Apply the same pre-terminal guard before `_commit_run()` here too, or force this CLI onto the no-commit path whenever `final-summary.md` is present.


