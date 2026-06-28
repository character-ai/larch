## Goal
Implement issue #5715: [IMPLEMENTING] [BUG] Self-review commit-fixes reports `no review delta paths` as a Tool Failure when the tree is dirty but no review-delta paths are collected.

## Implementation Plan
#### Summary

`/implement` Step-5 self-review records a **Tool Failure** with `ERROR=no review delta paths` / `COMMIT_OUTCOME=failed` in a case that may be benign. In `python/larch/review/review_and_fix.py` `_commit_fixes_stage_all`, when `git status --porcelain` is **non-empty** (dirty tree) but `_collect_review_fix_stage_paths()` returns **no paths**, the code emits `outcome="failed"` and returns 1 (around `review_and_fix.py:313`). The empty-tree case just above it correctly returns `outcome="noop"`; the dirty-but-no-delta-paths case is the one in question.

#### Evidence

- 4 runs hit this: v51.3.19, v51.3.21, and 2 recent runs at **v52.1.4** (the runs for issues #5637 and #5638). All surface it under the `Tool Failures` execution-issues category.

#### Why this needs triage

Reaching this branch means the working tree IS dirty but none of the dirty files were recognized as review-delta paths. Two interpretations, both worth resolving:

- If the dirty files are **unrelated / pre-existing dirt**, classifying the commit as `failed` is wrong; it should be a `noop` or a `Warning`, not a `Tool Failure`.
- If the self-review **edits were not captured** by `_collect_review_fix_stage_paths`, that is a real lost-fix bug (accepted findings silently not committed).

#### Relationship to recent fixes

This is a third edge in the self-review-commit family alongside **#5662** (false stall when the snapshot is written after an inline fix) and **#5678** (dirty tree after review fix commit). Neither names the `no review delta paths` path; the `failed` classification still exists in current code.

#### Suggested fix

Determine whether a dirty tree with zero collected review-delta paths is benign. If benign, downgrade from `outcome=failed` / Tool Failure to `noop` / Warning. If it indicates uncaptured review edits, fix the path collection. Add a regression test that pins the chosen semantics.

## Test plan
(no test plan section in plan-file)
