# Review Round 1

- Mode: `diff`
- 4 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: `commit-fixes --stage-all` breaks `--self-review`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_collect_review_fix_stage_paths` only unions paths from `round-*` dirs with a non-empty `pre-coder-head.txt`. Self-review skips the review loop, so it never creates those rounds. After narrowing `--stage-all` to pathspec-only staging, self-review Step 5 item 7 hits porcelain with inline fixes, gets `paths=[]`, exits `1` with `ERROR=no review delta paths`, and leaves fixes uncommitted until Step 8 dirty-tree handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a self-review path (e.g. collect paths from `git diff` against merge-base, or a dedicated self-review snapshot) before reusing the pathspec-only `--stage-all` logic; or keep a narrow `git add -A` fallback only when no review rounds exist.
  - From cursor-specialist-edge-cases-output.txt: Add self-review snapshot/delta collection or a no-round fallback that stages diff/porcelain paths without git add -A.
  - From cursor-specialist-testing-output.txt: Teach `_collect_review_fix_stage_paths()` a self-review fallback (porcelain paths when `self-review-accepted.md` exists and no round snapshots), or snapshot self-review deltas before commit; add pytest coverage.
  - From codex-specialist-testing-output.txt: Add a self-review snapshot or pass explicit edited pathspecs, with regression coverage.


### FINDING_6: Lint-fix `no-changes` path can miss in-place edits to pre-dirty files
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 5 lint-fix only commits after `LINT_FIX_STATUS=applied`. If a file was dirty before lint-fix and the fixer changes it in place, `checks.run_lint_fix` can return `no-changes` because baseline-tracked paths are excluded; recheck may pass, no commit runs, and the lint fix stays dirty for a later ship stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: When a pre-lint snapshot exists and recheck passes, compare current diffs to the snapshot even for no-changes, or make `_run_lint_fix_loop` report snapshot-diverged pre-dirty tracked paths.
  - From codex-specialist-edge-cases-output.txt: When `pre_lint_head` exists, compare current diffs against the pre-lint snapshot after every fixer return, including no-changes, and commit diverged paths before successful break.


### FINDING_7: MAV head-only snapshots let `stage-all` sweep pre-existing dirty files
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-delta-scope-output.txt
- **Severity**: important
- **Concern**: MAV rounds write only `pre-coder-head.txt` via `_write_mav_pre_coder_head_snapshot`, not the per-path wt/index patches `_path_matches_pre_coder_snapshot` needs. `_collect_review_fix_stage_paths` still treats those rounds as eligible; with an empty `pre_tracked_set` and no patch files, every `git diff --name-only <pre_head>` path can be staged. Unchanged pre-existing dirty tracked or untracked files present at MAV handoff can therefore ride into `commit-fixes --stage-all` / Step 7 pathspec commits, including unrelated local or secret content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Use the full pre-coder snapshot machinery for MAV rounds, including tracked diff and untracked baselines, before applying MAV fixes.
  - From codex-specialist-testing-output.txt: Use the full pre-coder snapshot for mav-apply and add a regression with unrelated pre-dirty content.
  - From dyn-delta-scope-output.txt: Either call `_write_pre_coder_snapshot` (or a shared helper that captures tracked + per-path diffs) before MAV `mav-apply`, or teach `_collect_review_fix_stage_paths` to skip MAV head-only rounds and use a MAV-specific delta collector with the same snapshot exclusion semantics as the coder path.


### FINDING_9: Step 7 `stage-all` unions stale deltas across all prior rounds
- **Reviewer(s)**: dyn-delta-scope-output.txt
- **Severity**: important
- **Concern**: Step 7 `commit-fixes --stage-all` unions `_collect_round_stage_paths` across all prior `round-*` dirs keyed to each round’s original `pre_head`, not “uncommitted review deltas since last commit.” A path committed in an earlier round can remain in later deltas whenever `git diff <old-pre-head>` still names it and snapshot exclusion fails. New unrelated local edits on that path before Step 7 can therefore ride into the review-fix commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-delta-scope-output.txt: Restrict collection to rounds with uncommitted deltas since each round’s last successful review commit (for example compare against `post-coder-head.txt` / HEAD at handoff), or snapshot at Step 7 entry and stage only paths whose wt/index diverge from that handoff snapshot.


