### [Plan Review] FINDING_2

### FINDING_2: Post-reconcile manifest reload must run on every `flush_logs_pre` path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan reloads manifest after `_stage_pre_commit` to preserve reconciled `step8=true`, but if that reload is gated on `strict_final_report`, merge-loop pre-rebase flushes (e.g. `ship.py` ~1675) can still clobber reconciled `step8` via the pre-reload `steps_update` snapshot taken from stale manifest state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan reloads manifest after `_stage_pre_commit` to preserve reconciled `step8=true`, but only explicitly in `flush_logs_pre` generally. If reload is gated on `strict_final_report`, pre-rebase merge-loop flushes (~ship.py:1675) could still clobber reconciled `step8` via the pre-reload `steps_update` snapshot. Apply the post-`_stage_pre_commit` `load_or_recover_manifest_checked` + step9a1-only delta merge on all `flush_logs_pre` invocations (plan text says "on all paths"; ensure implementation is not strict-only).


### [Plan Review] FINDING_3

### FINDING_3: Merge-loop pre-rebase flushes can still commit partial manifests under suppressed final-report handling
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan applies `strict_final_report` only to the new post-`ensure_pr` flush. Existing `flush_logs_pre` calls on `goto_rebase` and `MERGE_RESULT_MAIN_ADVANCED` still run `_stage_pre_commit` with `suppress(ShipError)` around `_write_final_report`. If `_reconcile_manifest_for_terminal_report` fails after `final-summary.md` is written, the flush can still git-commit a `pr-created` summary with unreconciled `steps_ran.step8=false` and `status=partial`, violating acceptance that committed manifests must not stay `partial` when `final-summary.md` exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `--merge` runs that rebase before squash-merge can land the same partial/step8 mismatch the bug reports, only with outcome upgraded to `pr-created`. Apply the same strict reconcile contract to merge-path pre-rebase flushes (pass `strict_final_report=True` and stall on `manifest-recovery-failed` / `commit-failed`), or document and test that post-`ensure_pr` is the only publisher and pre-rebase flushes cannot become the squash tip.


