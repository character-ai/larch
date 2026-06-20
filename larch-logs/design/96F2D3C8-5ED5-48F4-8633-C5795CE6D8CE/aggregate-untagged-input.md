### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/final_report.py:515-536
- **Concern**: python/run_logs.py:1117-1122. Scenario: Strict post-ensure merge flush can stall on tracking-issue upsert after local artifacts are already correct
- **Proposed resolution**: Edge cases say tracking comment failure is warn-only, but `write_final_report` still returns rc=1 when `tracking-issue upsert-summary` fails after writing `run_dir/final-summary.md` and reconcile. `strict_final_report=True` maps any rc!=0 to `REFRESH_SKIP_RECOVERY_FAILED` and blocks merge even when the committed snapshot would be correct. Decouple local artifact success from API upsert for the post-ensure refresh path: add e.g. `skip_tracking_upsert` (or split local vs comment return codes) on `flush_logs_pre(strict_final_report=True)` / `write_final_report`, and keep upsert failure warn-only once reconcile succeeds.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/final_report.py:499-512
- **Concern**: python/run_logs.py:1209-1215. Scenario: Manifest reload must happen after reconcile on every `flush_logs_pre` path, not only strict mode
- **Proposed resolution**: Plan reloads manifest after `_stage_pre_commit` to preserve reconciled `step8=true`, but only explicitly in `flush_logs_pre` generally. If reload is gated on `strict_final_report`, pre-rebase merge-loop flushes (~ship.py:1675) could still clobber reconciled `step8` via the pre-reload `steps_update` snapshot. Apply the post-`_stage_pre_commit` `load_or_recover_manifest_checked` + step9a1-only delta merge on all `flush_logs_pre` invocations (plan text says "on all paths"; ensure implementation is not strict-only).

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:1675-1794
- **Concern**: Post-rebase merge-loop flushes keep suppressed final-report failures. Scenario: Plan applies `strict_final_report` only to the new post-`ensure_pr` flush. Existing `flush_logs_pre` calls on `goto_rebase` and `MERGE_RESULT_MAIN_ADVANCED` still run `_stage_pre_commit` with `suppress(ShipError)` around `_write_final_report` (`python/run_logs.py:1172-1173`). If `_reconcile_manifest_for_terminal_report` fails after `final-summary.md` is written, the flush can still git-commit a `pr-created` summary with unreconciled `steps_ran.step8=false` and `status=partial`, violating the issue acceptance that committed manifests must not stay `partial` when `final-summary.md` exists.
- **Proposed resolution**: `--merge` runs that rebase before squash-merge can land the same partial/step8 mismatch the bug reports, only with outcome upgraded to `pr-created`. Apply the same strict reconcile contract to merge-path pre-rebase flushes (pass `strict_final_report=True` and stall on `manifest-recovery-failed` / `commit-failed`), or document and test that post-`ensure_pr` is the only publisher and pre-rebase flushes cannot become the squash tip.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:671-674
- **Concern**: Outcome cascade fix is required even after PR exists. Scenario: Current code only emits `pr-created` when `not _truthy(merge)` (`python/stall_recovery.py:671-672`). A merge run with `PR_NUMBER` set still falls through to `bailed`. The plan correctly pairs post-`ensure_pr` flush with removing the `not merge` gate; omitting the cascade change would leave merge runs misrecorded as `bailed` even after the new flush sequencing.
- **Proposed resolution**: Implementing only the ship flush/push without the `stall_recovery.py` branch change reproduces the reported symptom whenever `MERGE=true` and `PR_NUMBER` is populated. Keep the planned `_has_pr_evidence` branch and explicitly gate the ship integration test on `MERGE=true` plus `PR_NUMBER` producing `pr-created`, not merely on absence of `bailed`.

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:659-674; python/ship.py:1612-1639
- **Concern**: The planned PR-evidence outcome branch is too broad for terminal post-PR failures. Scenario: A merge run can reach a needs-user terminal state after PR creation with empty MERGE_RESULT, for example ci-fix-exhausted. The planned branch would classify it as pr-created and success-classed instead of preserving a failed or needs-user outcome, corrupting run-log history.
- **Proposed resolution**: Limit the PR-evidence branch to healthy non-terminal merge states. Exclude PHASE=stalled or nonzero EXIT_CODE or BAIL_REASON before returning pr-created. Add a stall_recovery regression for MERGE=true, PR_NUMBER set, PHASE=stalled, BAIL_REASON=ci-fix-exhausted.
