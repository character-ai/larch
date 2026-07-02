### OOS_1: [OUT_OF_SCOPE] Pre-merge reconciliation leaves merged runs logged as pr-created
- **Reviewer(s)**: dyn-dyn-recovery-logs
- **Severity**: latent
- **Concern**: Pre-merge reconciliation rewrites a stalled summary to `pr-created` before `merge.merge_pr(..., post_flush=False)`. After a successful merge, `flush_logs_post` is tmpdir-only and does not commit a `merged` heading. Committed logs for merged runs can therefore show `pr-created` instead of `merged`, and the new test `test_recovered_open_pr_premerge_reconciles_stalled_summary_before_merge` appears to encode that behavior intentionally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-recovery-logs: A post-merge committing flush (without reintroducing the #5217 double-flush) would close that audit gap.

### OOS_2: [OUT_OF_SCOPE] Manifest backstop can leave status in_progress after pr-created reconciliation
- **Reviewer(s)**: dyn-dyn-recovery-logs
- **Severity**: latent
- **Concern**: After manifest-only backstop reconciliation, `_reconcile_terminal_manifest_from_ctx` can still set manifest `status=in_progress` when normalized outcome is `pr-created`, which can diverge from a manifest-only rewrite to `merged` on a later touch. Low frequency because the backstop requires absent ship/finalize state files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-recovery-logs: (no explicit fix direction provided in source finding)
