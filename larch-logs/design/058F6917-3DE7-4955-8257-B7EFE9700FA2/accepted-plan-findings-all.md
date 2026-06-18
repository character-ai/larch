### FINDING_1: MAV snapshot test incompatible with planned full-snapshot mav-apply setup
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan replaces MAV apply’s head-only `_write_mav_pre_coder_head_snapshot` setup with full `_ensure_pre_coder_snapshot`, but `test_mav_apply_writes_relocated_pre_coder_head_only` still asserts `pre-coder-tracked-paths.txt` and `pre-coder-untracked-paths.txt` are absent. A correct implementation of the planned mav-apply change will fail `make py-test` even if production behavior is otherwise correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan step under python/test_review_and_fix.py to rewrite this test for full-snapshot mav setup (expect tracked and untracked baseline files, or assert snapshot creation is delegated solely to apply_findings_with_coder if the mav prelude call is removed)
  - From Codex-Arch: Update or replace the existing MAV test to assert the new full relocated snapshot contract.
  - From Cursor-Innovation: Add updating or replacing that test (expect `pre-coder-tracked-paths.txt` and `pre-coder-untracked-paths.txt`) under **Files to modify/create** / **Testing strategy**
  - From Codex-Innovation: Update or rename this test to expect pre-coder-head.txt, pre-coder-tracked-paths.txt, and pre-coder-untracked-paths.txt after mav-apply
  - From Codex-Pragmatic: Update the MAV snapshot test to assert the new full relocated snapshot contract, or keep a MAV helper that writes the full snapshot and adjust the assertions to match.
  - From Cursor-Requirements: Add an explicit plan/testing step to update or replace `test_mav_apply_writes_relocated_pre_coder_head_only` so it asserts the full pre-coder snapshot trio exists after mav-apply setup
  - From Codex-Requirements: Update this existing test to expect pre-coder-tracked-paths.txt and pre-coder-untracked-paths.txt, and rename it away from head-only


### FINDING_2: `git reset --hard HEAD` cleanup can discard pre-existing tracked user changes
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The cleanup plan uses `git reset --hard HEAD` on the shared apply-findings path. `/review` apply-findings can run against an uncommitted working-tree diff. If Cursor is unavailable or fails, the proposed cleanup discards pre-existing tracked user changes, not just coder-introduced changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Restore the tracked pre-coder snapshot instead of HEAD-only reset, or constrain hard-reset cleanup to callers that prove the pre-coder tracked tree is clean.


### FINDING_4: Full MAV pre-coder snapshot conflicts with head-only carryover staging semantics (#3272)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: MAV apply is planned to use full `_ensure_pre_coder_snapshot` instead of head-only `_write_mav_pre_coder_head_snapshot`. `_collect_round_stage_paths` uses `pre-coder-tracked-paths.txt` and patch diffs to classify pre-dispatch tracked dirt as carryover and omit it from staging/commits. Prior design explicitly kept MAV head-only (#3272). Full snapshot on MAV can return `CODER_STATUS=applied` while coder fixes on already-dirty tracked paths stay unstaged, and conflicts with `test_mav_apply_writes_relocated_pre_coder_head_only`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Keep MAV head-only staging semantics: extend `_write_mav_pre_coder_head_snapshot` to also write `pre-coder-untracked-paths.txt` for cleanup, but do not write `pre-coder-tracked-paths.txt` or path-diff patches. Have `_ensure_pre_coder_snapshot` treat head+untracked-only as sufficient for MAV, or branch MAV setup separately from the Step 5 loop full snapshot


### FINDING_5: Cleanup failure is logged but the coder waterfall still proceeds
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: If `git reset --hard HEAD` or untracked deletion fails, the plan continues to Codex or returns `main-agent-required` with a dirty tree. The next rebase can hit the same abort this bug is meant to prevent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Make `_cleanup_failed_coder_attempt` return success after verifying no staged or unstaged tracked changes and no new untracked delta. If cleanup fails, stop the waterfall and return a stall or failed status instead of continuing.


### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:1287-1436
- **Concern**: [SCOPE-REDUCTION] Destructive cleanup is applied to every false coder result. Scenario: `_run_coder_cursor` returns False for unavailable/auth/model failures before editing. In direct `apply_findings` on a dirty tracked baseline, the planned `git reset --hard HEAD` can delete unrelated pre-existing work before Codex runs.
- **Proposed resolution**: Only run reset cleanup when a fresh pre-dispatch snapshot shows coder-created deltas, or require a clean tracked baseline before reset-hard. Otherwise preserve the pre-coder tracked state and avoid destructive cleanup.




### FINDING_1: Full-snapshot verification rejects lawful pre-coder staged carryover
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Cleanup verification requires an absolutely empty staged index, but full-snapshot mode intentionally preserves pre-existing staged carryover via `pre-coder-path-diffs/*.cached.patch`. After a failed coder attempt, cleanup must restore that staged baseline. The unconditional "no staged tracked changes" check makes `_cleanup_failed_coder_attempt` return False whenever the pre-coder baseline had staged edits, blocking the waterfall and leaving rc=2 stalls on the original rebase-blocking path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In full-snapshot mode verify each path in `pre-coder-tracked-paths.txt` with existing `_path_matches_pre_coder_snapshot(round_dir, pre_head, path)` instead of requiring an empty index; only require no staged paths outside that baseline set


### FINDING_2: Full-snapshot restore omits coder deltas and lacks specified restore procedure
- **Reviewer(s)**: Cursor-Innovation, Codex-Generic
- **Severity**: blocking
- **Concern**: Full-mode failed-coder cleanup only restores paths that were dirty before the coder, and `_restore_pre_coder_tracked_state` has no specified counterpart despite snapshot capture of wt/index patches. Nearby code records `pre-coder-path-diffs/*.patch` and `*.cached.patch` but does not restore them. A clean Step 5 repo yields an empty `pre-coder-tracked-paths.txt`; if the coder then edits a tracked file, cleanup does not revert that file. A naive `git checkout pre_head -- path` would also drop lawful pre-coder carryover and can leave staged residue, so verification fails or the tree stays dirty and the original rebase-blocking bug remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Spell out restore steps in the plan: for each path in pre-coder-tracked-paths.txt reset to pre_head then apply cached.patch to the index and .patch to the worktree (or one documented equivalent), and add a unit test that a carryover dirty path survives failed-coder cleanup in full-snapshot mode
  - From Codex-Generic: Make full-mode cleanup restore all current coder tracked delta paths to pre_head first, then reapply the stored working-tree and cached patches for paths that were dirty in the pre-coder snapshot


### FINDING_3: Head-only MAV cleanup leaves coder edits on carryover paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Head-only MAV cleanup skips checkout for attempt-baseline paths, so coder content edits on carryover files survive failure cleanup. After `git restore --staged .`, cleanup only unstages and checks out paths outside `attempt-pre-tracked-paths.txt`. Coder content changes on carryover paths remain; verification allows those paths to stay dirty vs `pre_head`; downstream Codex or rebase still sees extra dirty state beyond approved carryover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After git restore --staged ., restore each attempt-baseline path to its pre-attempt content (write attempt-pre path patches at dispatch, or compare against attempt snapshot); if content cannot be split from carryover, return cleanup False and rc=2 failed instead of continuing the waterfall


### FINDING_4: rc=2 failure path can exit with staged residue still present
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Cleanup verification failure can return rc=2 failed with staged residue still present. The plan stops the waterfall on verification failure without mandating best-effort unstaging, so STEP5 stall (`coder-failed`) can still leave staged changes and break step 4.r/7.r/8 rebases with the same cannot-rebase error the bug report describes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Before any rc=2 failed return, always run best-effort git restore --staged . even when full verification fails; log to coder-cleanup.log; add a test asserting no staged porcelain entries after rc=2




### FINDING_1: Head-only MAV snapshots misclassified as missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_snapshot_mode` requires both `pre-coder-head.txt` and `pre-coder-untracked-paths.txt` to classify a snapshot as `head_untracked`. Head-only MAV snapshots (head present, `pre-coder-tracked-paths.txt` absent) are treated as `missing`. That causes `_ensure_pre_coder_snapshot` to call `_write_pre_coder_snapshot`, upgrading MAV to a full tracked snapshot and changing carryover semantics mid-apply (#3272): stage-path classification shifts and pre-existing dirty tracked paths get snapshotted as lawful baseline. The same gap makes `_round_coder_untracked_delta_paths` treat every untracked file as a coder delta when the untracked baseline file is absent, so head-only cleanup can delete pre-existing untracked files or fail verification. Triggers include legacy head-only dirs, partial deploys, or untracked write failures before the extended writer lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Treat `pre-coder-head.txt` present and `pre-coder-tracked-paths.txt` absent as `head_untracked` even when `pre-coder-untracked-paths.txt` is missing; lazily seed an empty or freshly captured untracked baseline before cleanup/verify. Never upgrade MAV head-only snapshots to full mode inside `_ensure_pre_coder_snapshot`
  - From Cursor-Innovation: Classify head without `pre-coder-tracked-paths.txt` as `head_untracked` (empty untracked baseline when `pre-coder-untracked-paths.txt` is absent); only call `_write_pre_coder_snapshot` when `pre-coder-head.txt` is absent
  - From Cursor-Pragmatic: Classify head-only as `head_untracked` when `pre-coder-head.txt` exists and `pre-coder-tracked-paths.txt` is absent, treating a missing untracked list as empty; only call `_write_pre_coder_snapshot` when `pre-coder-head.txt` is also absent


### FINDING_2: Patch restore fails for staged additions absent at pre_head
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The proposed patch-restore path cannot safely restore pre-coder staged additions. When a pre-existing staged new file was captured in the full snapshot, then modified or re-staged by a failed coder, the path does not exist at `pre_head`. A `git checkout <pre_head> -- <path>` restore fails, and applying add patches over the coder's worktree copy can leave coder content in place or force rc=2 with dirty residue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Teach `_restore_path_from_patches` to detect paths absent at `pre_head`, clear the index and worktree copy for that path safely, then apply the stored cached and worktree patches. Cover this with the full-snapshot staged-carryover test using a staged addition.



### FINDING_1: Empty untracked baseline breaks head-only no-edit skip
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: When `pre-coder-untracked-paths.txt` is absent (legacy MAV head-only dirs), `_read_pre_coder_untracked_baseline` returns empty, so `_round_coder_untracked_delta_paths` treats every pre-existing untracked file as a coder delta. `_has_coder_worktree_deltas` stays true on a no-edit `False` return, and cleanup may delete pre-existing untracked files or run destructive restore unnecessarily.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Capture `attempt-pre-untracked-paths.txt` in `_write_attempt_pre_tracked_paths` (head_untracked only) and base untracked delta / no-edit detection on attempt-pre vs post-attempt diff, not global empty baseline alone


### FINDING_3: rc=2 finalize leaves unstaged tracked edits that block rebase
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: rc=2 cleanup-verification failure only best-effort unstages. `_finalize_failed_cleanup` runs only `git restore --staged .`. If restore/verify failed while leaving unstaged tracked diffs, the next 4.r/7.r/8 rebase can still fail with the same dirty-tree error as the reported bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Have `_finalize_failed_cleanup` (or its caller) run the same best-effort tracked/untracked restore path used in `_cleanup_failed_coder_attempt` before unstaging, then re-check porcelain; or explicitly stall with diagnostics that unstaged dirt may still block rebase


### FINDING_4: No-changes gate uses absolute git status instead of coder deltas
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Successful coder attempts still use absolute git status for the no-changes gate. The plan preserves pre-coder tracked and untracked baselines, but a successful no-op coder with pre-existing baseline dirt makes `_git_status_porcelain` non-empty. Step 5 then tries to commit zero collected coder paths, falls through the waterfall, and can end as main-agent-required instead of no-changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: After submodule revert, branch on mode-aware coder deltas or `_collect_round_stage_paths` rather than raw git status. If no coder-stage paths exist, return no-changes. Only commit when coder-stage paths are non-empty.


### FINDING_5: Untracked cleanup fails on directory-shaped porcelain entries
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Untracked cleanup does not handle new directories from coder residue. Current untracked capture uses git status porcelain, which can report a new directory as `?? newdir/`. A failed coder that creates or stages `newdir/file.py` can leave `newdir/` after `git restore --staged`; `Path.unlink`-style deletion fails on the directory, verification fails, and the waterfall stops with untracked residue instead of cleanly falling through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Capture untracked deltas with `git ls-files --others --exclude-standard`, preferably NUL-delimited, so cleanup deletes leaf files. Then safely prune empty parent directories inside the repo, or add explicit safe recursive handling for directory entries. Add one regression with a failed coder creating a new untracked directory.




### FINDING_2: `_collect_round_stage_paths` not mode-aware for `head_untracked` staging and no-changes gate
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan claims `_collect_round_stage_paths` is mode-aware for the FINDING_4 no-changes gate and commit staging, but the file list never updates it (or `_round_coder_delta_paths`) for `head_untracked`. The helper still calls `_round_coder_delta_paths` and `_round_coder_untracked_delta_paths` globally. On MAV/legacy head-only snapshots without `pre-coder-tracked-paths.txt`, every path dirty vs `pre_head` is treated as a coder delta; pre-MAV carryover and pre-existing untracked files are misclassified as stage/commit scope. A successful no-edit coder can skip the no-changes path and `git add` or commit pre-existing untracked files. Test 10 covers False-return skip only, not this True no-edit path. Cleanup may use attempt-relative untracked deltas while staging still keys on the global baseline, causing inconsistent behavior during waterfall retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit ### UPDATED step for _collect_round_stage_paths: in head_untracked mode stage only attempt-relative tracked deltas (paths whose wt or index differ from attempt-pre-path-diffs vs pre_head) plus _round_attempt_untracked_delta_paths; in full mode keep current pre-coder baseline logic. Add test 13: legacy head-only snapshot, pre-existing untracked, fake coder returns True with no edits, assert no-changes and no git add of the pre-existing file.
  - From Cursor-Pragmatic: Add an explicit plan step: branch `_collect_round_stage_paths` on `_snapshot_mode`; in `head_untracked` derive tracked stage paths from attempt-baseline patches (new `_round_attempt_tracked_delta_paths` or equivalent) and untracked from `_round_attempt_untracked_delta_paths`, mirroring the attempt-relative logic already specified for `_has_coder_worktree_deltas`
  - From Cursor-Pragmatic: Wire `_collect_round_stage_paths` to `_round_attempt_untracked_delta_paths` when mode is `head_untracked`; keep global baseline only for `full` mode


### FINDING_5: `_verify_post_cleanup_state` omits unexpected cached delta check
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Cleanup verification omits unexpected cached deltas. Full-mode verification can pass with index-only staged residue outside the pre-coder baseline if `git restore --staged .` fails or a hook leaves cached changes. `apply_findings_with_coder` may then continue or return rc=4 with a dirty index, reproducing the rebase failure the bug fix targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: In _verify_post_cleanup_state, compare git diff --cached --name-only pre_head against pre-coder tracked paths that match their cached patches, and fail verification on any unexpected cached path.



