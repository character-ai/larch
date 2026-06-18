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


