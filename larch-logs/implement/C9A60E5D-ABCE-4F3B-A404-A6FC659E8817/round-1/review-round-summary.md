# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: `_lint_fix_delta_paths` drops index-only lint deltas vs `pre_lint_head`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-delta-boundary-output.txt
- **Severity**: important
- **Concern**: `_lint_fix_delta_paths` filters reported paths using a working-tree-only check (`git diff --name-only pre_lint_head`). When lint reports a path via `unioned_delta_paths` but the fix is staged-only relative to `pre_lint_head` (index differs, working tree matches the pre-lint snapshot), that path is excluded from `commit_paths` even though it remains in the reported set. Step 5 can then pass checks while staged lint fixes are left uncommitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use _tracked_paths_vs_ref(pre_lint_head) for current-state checks or add staged-only regression if checks.run_lint_fix can produce that state.
  - From codex-specialist-edge-cases-output.txt: Union git diff --name-only <pre_lint_head> with git diff --cached --name-only <pre_lint_head>, and add a staged-only regression.
  - From dyn-delta-boundary-output.txt: When validating reported paths, treat a path as current if it appears in either `git diff --name-only pre_lint_head` or `git diff --cached --name-only pre_lint_head`, mirroring `_tracked_paths_vs_ref` at `python/review_and_fix.py:498-502`.


### FINDING_5: `_collect_round_stage_paths` accepts partial full snapshot as valid baseline
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_collect_round_stage_paths` treats a partial full snapshot as valid when `pre-coder-tracked-paths.txt` exists but `pre-coder-untracked-paths.txt` is missing (or other required full-snapshot artifacts are absent). An interrupted snapshot write can let pre-existing untracked or unrelated dirty paths be returned and staged with coder changes, contrary to the plan's valid-baseline requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Require both tracked and untracked full-snapshot files before collecting full snapshot paths, or return an empty path list when a required full-snapshot baseline file is absent.
  - From codex-specialist-edge-cases-output.txt: Validate full snapshot artifacts before full-mode collection, or downgrade partial snapshots to safe no-stage behavior.


### FINDING_7: Full-snapshot partial cleanup test does not assert working-tree rollback
- **Reviewer(s)**: dyn-cleanup-regression-output.txt
- **Severity**: important
- **Concern**: The new full-snapshot partial cleanup regression (`python/test_review_and_fix.py:1868-1907`) checks index cleanliness and coder fallback blocking, but never asserts that coder working-tree edits were rolled back to the pre-coder baseline. Because `_path_matches_pre_coder_snapshot` is monkeypatched to always return `False` for `tracked.txt`, verification fails regardless of restore outcome; a broken restore path that clears the index but leaves `"cursor\n"` unstaged would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-regression-output.txt: After the failure assertions, add `(repo / "tracked.txt").read_text(encoding="utf-8") == "user edit\n"` (and optionally `assert "cursor" not in ...` or a porcelain check that excludes only pre-existing baseline dirt). Narrow the monkeypatch so it returns `False` only when the live tree still differs from the snapshotted patches, or restore first and then force mismatch on a second path, so the test proves mechanical cleanup ran before fallback was blocked.


