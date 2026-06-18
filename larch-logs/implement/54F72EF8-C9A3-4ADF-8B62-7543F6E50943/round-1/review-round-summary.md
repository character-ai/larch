# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_apply_patch_file` ignores `git apply` exit codes; failed restore can leave dirty tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cleanup-safety-output.txt
- **Severity**: important
- **Concern**: `_apply_patch_file` calls `git apply` / `git apply --cached` via `_run` and does not check the return code. `_restore_path_from_patches` and full/head restore paths depend on this for rollback. A failed or partial apply leaves the tree intermediate while cleanup continues; `_verify_post_cleanup_state` may then fail and route to `_finalize_failed_cleanup`, which logs remaining porcelain but does not re-verify or guarantee a rebase-safe tree after best-effort restore. Staged-new-file carryover patches can fail to re-apply after partial revert. Silent failures can leave unstaged tracked coder residue and cause Step 4.r/7.r/8 rebase aborts on the rc=2 stall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check _run returncode in _apply_patch_file; fail verification on apply errors; add last-resort tracked revert in finalize
  - From cursor-specialist-edge-cases-output.txt: Re-run _verify_post_cleanup_state (or equivalent) after finalize; check git apply return codes; fail closed if coder deltas or staged residue remain.
  - From cursor-specialist-edge-cases-output.txt: Check return codes and log/abort restore on failure.
  - From dyn-cleanup-safety-output.txt: Check the `_run(...)` return code, append failures to `round_dir/coder-cleanup.log`, and treat apply failure as restore failure for that path (continue best-effort, but do not assume the patch landed).


### FINDING_2: `_remove_untracked_delta_paths` follows symlinks and can delete tracked targets
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_remove_untracked_delta_paths` resolves untracked paths with `Path.resolve()` before unlinking, so symlinks are followed and the target can be deleted. If a failed coder creates `leak -> tracked.txt`, cleanup deletes `tracked.txt` instead of the symlink, can leave the link behind, and may return failed with unstaged deletion residue that blocks rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Validate containment without following the final path component, then unlink the original repo-relative path using lstat-aware handling.
  - From codex-specialist-edge-cases-output.txt: Validate containment without following the final symlink, then unlink the original repo-relative path itself.


### FINDING_5: Cleanup-verification-failure test does not assert full working-tree cleanliness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `test_apply_findings_with_coder_cleanup_verification_failure_stops_without_staged_residue` only asserts the staged index is empty (`_git_cached_names(repo) == ""`), not full working-tree cleanliness. The test can pass while unstaged tracked coder residue remains after finalize, missing regression for the acceptance criterion the feature claims.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Assert _git_porcelain(repo) == "" (or explicitly allowed carryover only) after forced verification failure.


### FINDING_6: `head_untracked` stale `pre_head` and outside-path logic mishandle lawful carryover
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-cleanup-safety-output.txt, dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: Cleanup binds `pre_head` once from `pre-coder-head.txt`; `_ensure_pre_coder_snapshot` only writes when mode is `missing` and never refreshes an existing snapshot. On direct `apply-findings` with a reused `review_tmpdir` where `HEAD != pre_head`, failed cleanup can `git checkout <stale-pre_head> -- <path>` over legitimately committed work. In `head_untracked` mode, `_verify_post_cleanup_state` flags any tracked path dirty vs `pre_head` but outside `attempt-pre-tracked-paths.txt` as failure, with no exemption for carryover already dirty before dispatch and unchanged by the attempt; `_restore_attempt_baseline_tracked_state` resets those outside paths to `pre_head`. Attempt baseline capture and outside verification use different diff bases and only align when `HEAD == pre_head`. Stale snapshots or intervening commits make lawful carryover look like outside dirt, trigger false verification failure, stop the waterfall at rc=2, or wipe carryover during finalize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Refresh or validate pre_head before cleanup; key attempt snapshots off current HEAD; exempt unchanged outside carryover from revert/verify.
  - From dyn-cleanup-safety-output.txt: Before the waterfall, if `_git_head() != pre_head`, either refresh the snapshot (respecting the no-upgrade rule for MAV/head-only) or fail closed with rc=2; do not run mode-aware restore against a stale `pre_head`.
  - From dyn-cleanup-safety-output.txt: Compare outside paths only against attempt-relative tracked deltas (same logic as `_round_attempt_tracked_delta_paths`), or record a pre-dispatch "carryover outside attempt" set and exclude unchanged paths from the outside check and from `_restore_path_to_ref` in the outside loop.
  - From dyn-waterfall-contract-output.txt: Restrict the `outside` check to paths with attempt-relative deltas, skip restore for pre-attempt carryover paths, and add the plan's MAV carryover regression test.


### FINDING_7: Missing plan-required MAV `head_untracked` carryover regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: Plan-required regression test #6 (MAV head-only cleanup preserves carryover) is missing from the diff. Only full-snapshot carryover is tested (`test_apply_findings_with_coder_full_snapshot_preserves_staged_carryover`). The `head_untracked` restore/verify path that MAV `mav-apply` depends on is unguarded: a failed Cursor attempt in MAV/head-only mode could regress by unstaging or wiping pre-existing tracked carryover without any test catching it before a rebase stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a head_untracked/MAV test: seed carryover, fail Cursor after staging, assert carryover bytes and staging state survive and coder residue is cleared.
  - From codex-specialist-testing-output.txt: Add a head-only snapshot test with pre-existing tracked carryover, failed Cursor staging or editing that path, and assertions that cleanup preserves carryover and removes coder residue.
  - From dyn-waterfall-contract-output.txt: Add the planned MAV carryover test: pre-dispatch dirty tracked carryover, failed coder with staged edits, assert carryover preserved, coder staging removed, and waterfall continues.


### FINDING_10: Submodule violation cleanup failure loses `rc=3` / `submodule-violation` contract
- **Reviewer(s)**: dyn-waterfall-contract-output.txt
- **Severity**: important
- **Concern**: On a submodule violation, if post-revert `_cleanup_failed_coder_attempt` fails, the code returns `CoderResult(2, …, status="failed")` instead of the terminal `rc=3` / `status="submodule-violation"` contract. Step 5 derives `STALL_REASON` from `result.coder.status`, so cleanup failure is classified as `coder-failed` even when `SUBMODULE_REVERT_COUNT > 0`, losing the submodule-specific stall signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-contract-output.txt: When `revert_count > 0` and cleanup fails, still emit `rc=3` / `status="submodule-violation"` (optionally add a distinct cleanup-failed flag), or map `STALL_REASON=submodule-violation` whenever `SUBMODULE_REVERT_COUNT > 0` regardless of `CODER_STATUS`.


