## Goal
Implement issue #5662: [IMPLEMENTING] [BUG] Self-review commit-route false stall when snapshot is written after inline fix.

## Implementation Plan
## Summary

`write-pre-self-review-snapshot` silently accepts a dirty working tree, recording unstaged inline fixes as part of the snapshot baseline. When `checks-commit-route --commit-site step5-self-review` later calls `_collect_self_review_stage_paths`, `_path_matches_pre_self_review_snapshot` filters out those paths because their current diff equals the captured snapshot diff (nothing changed since the snapshot), leaving an empty delta set. The commit-route then seeds `BAIL_REASON=review-fix-commit-failed` ("no review delta paths") even though the working tree contains valid review fixes. The stall is a false positive caused entirely by snapshot-before-fix ordering not being enforced.

## Original report

In run AE9D07AF (implementing #5638), the self-review orchestrator applied an inline Edit fix to `skills/implement/scripts/step-5-review.md` (stale `exec` wording) as an unstaged working-tree change, then called `write-pre-self-review-snapshot`. The snapshot recorded the fix in the diff baseline for that file. The subsequent `checks-commit-route --commit-site step5-self-review` call returned `COMMIT_ROUTE_OUTCOME=seeded-stall` / `ERROR=no review delta paths` / `NEXT_ACTION=stall`. The fix was committed separately after the stall was classified and cleared, but the stall required manual intervention to resolve.

## Reproduction scenario

1. On a feature branch with a clean working tree, run `/implement --self-review <issue>`.
2. In Step 5 self-review, apply an inline Edit fix to a tracked file BEFORE calling `write-pre-self-review-snapshot`.
3. Call `write-pre-self-review-snapshot`.
4. Create `$IMPLEMENT_TMPDIR/self-review-accepted.md` to record the accepted finding.
5. Run `checks-commit-route --commit-site step5-self-review --checks-site step5-self-review`.
6. Observe `ERROR=no review delta paths` and `NEXT_ACTION=stall` despite the working-tree fix.

The key trigger: the Edit fix lands in the working tree before the snapshot. The snapshot stores `git diff <HEAD> -- <path>` for that file — which includes the fix — and the commit-route later sees the same diff, concluding the path is "unchanged since snapshot" and skipping it.

## Expected behavior

Either:
- `write-pre-self-review-snapshot` detects unstaged changes to tracked files and exits non-zero with a clear error instructing the orchestrator to commit or discard them before snapshotting; or
- the commit-route falls back to staging uncommitted working-tree changes when the committed-delta set is empty but `git status` reports modified tracked files.

## Observed behavior

`write-pre-self-review-snapshot` succeeds silently with `PRE_SELF_REVIEW_HEAD=<sha>` even when tracked files are modified. The snapshot captures those modifications as the baseline diff. The subsequent `checks-commit-route` call finds no delta paths because `_path_matches_pre_self_review_snapshot` considers the paths unchanged (snapshot diff == current diff). The commit-route seeds `BAIL_REASON=review-fix-commit-failed`, producing a false stall that requires manual classification and clearing.

## Root cause analysis

The defect is in `_write_pre_self_review_snapshot` and `_path_matches_pre_self_review_snapshot` in `python/larch/review/review_and_fix.py`.

`_write_pre_self_review_snapshot` (line 1033) calls `_capture_round_tracked_paths()` to get the pre-snapshot tracked-modified-paths set, then for each path it records:
- `git diff <HEAD> -- <path>` (working-tree diff)
- `git diff --cached <HEAD> -- <path>` (staged diff)

If a tracked file has an unstaged working-tree modification at snapshot time, both diffs are captured as non-empty — recording the change in the baseline.

`_path_matches_pre_self_review_snapshot` (line 1068) later compares the current diffs to those snapshots. Since nothing was committed between snapshot-write and commit-route invocation, the current diffs still match the snapshot exactly, and the path is excluded from deltas (`return True` → `continue` at line 1091).

`_self_review_delta_paths` (line 1080) uses `git diff --name-only <pre_head>` which DOES show working-tree modifications, but the `_path_matches_pre_self_review_snapshot` filter removes them when they were already dirty at snapshot time.

The self-review.md reference says "Capture a pre-edit tree snapshot BEFORE applying inline fixes" (step 4.5), but this constraint is not enforced by the helper itself. When the ordering is violated, the failure is silent and only manifests much later as a false stall.

## Evidence

- `python/larch/review/review_and_fix.py` line 1046: `head = _git_head()` — snapshot records current HEAD without checking for dirty tree.
- `python/larch/review/review_and_fix.py` line 1060: writes `git diff <head> -- <path>` for each tracked path — captures working-tree modifications into baseline.
- `python/larch/review/review_and_fix.py` line 1075-1076: `_path_matches_pre_self_review_snapshot` compares current diff to snapshot; if equal, path is silently excluded.
- `python/larch/review/review_and_fix.py` line 1088: `git diff --name-only pre_head` — correct, returns working-tree changes — but then filtered by snapshot parity check.
- `python/larch/review/review_and_fix.py` line 1091: `if ... _path_matches_pre_self_review_snapshot(...): continue` — the filter that silently drops snapshot-baseline modifications.
- Run AE9D07AF: `COMMIT_ROUTE_OUTCOME=seeded-stall`, `ERROR=no review delta paths`, `NEXT_ACTION=stall` — the false stall outcome.
- `skills/implement/references/self-review.md` step 4.5: "Capture a pre-edit tree snapshot before applying inline fixes" — the ordering constraint that was violated.

## Affected files

- `python/larch/review/review_and_fix.py` — `_write_pre_self_review_snapshot` (line 1033) needs a dirty-tree guard; `_collect_self_review_stage_paths` may need a fallback for the empty-delta case.
- `skills/implement/references/self-review.md` — step 4.5 ordering constraint may warrant a louder warning in prose.
- `python/test_review_and_fix.py` — add a test case where tracked files are modified before snapshot write and verify the guard fires or the fallback commits them.

## Suggested fix(es)

**Option A (preferred — early detection)**: Add a dirty-tree guard in `write_pre_self_review_snapshot`: if `git status --porcelain` returns any modified tracked files at snapshot time, print a visible warning (or exit non-zero) instructing the orchestrator to commit or discard changes before calling the snapshot helper. This catches the ordering violation at the point of mistake rather than silently recording a misleading baseline.

```python
dirty = _git_output(["status", "--porcelain"]).splitlines()
tracked_dirty = [l[3:] for l in dirty if l[:2] in (" M", "M ", "MM", " D", "D ", "AD", "DA")]
if tracked_dirty:
    _err(f"write-pre-self-review-snapshot: working tree has {len(tracked_dirty)} modified tracked file(s); commit or discard before snapshotting")
    return 1
```

**Option B (resilient fallback)**: In `_collect_self_review_stage_paths`, when `_self_review_delta_paths` returns an empty list, fall back to checking `git status --porcelain` for any modified tracked files and include them. This handles the ordering violation gracefully but may accidentally pick up pre-existing dirty files unrelated to the review.

Option A is preferred because it enforces the invariant at the source and provides a clear actionable error, while Option B may silently include unrelated modifications.

## Open questions

- Should `write-pre-self-review-snapshot` exit non-zero on dirty tree (fail-closed) or print a warning and continue (fail-open like the rest of the hook)? Fail-closed is safer but could break self-review runs where staged changes from an earlier step are legitimately present; the guard should check only unstaged (`git diff --name-only`, not `git diff --cached --name-only`).
- Should the self-review.md step 4.5 prose be strengthened with an explicit "if you have applied fixes already, commit them before calling this helper"?

## Test plan
(no test plan section in plan-file)
