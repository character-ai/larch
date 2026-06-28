## Goal
Implement issue #5678: [IMPLEMENTING] [BUG] Self-review commit residual: dirty tree after review fix commit stall.

## Implementation Plan
## Summary

A residual `/implement` Step-5 self-review commit failure: `COMMIT_OUTCOME=failed` with `ERROR=dirty tree after review fix commit`. This is the "residual-dirty-after-partial-commit" variant, distinct from the empty-delta variant (#5637 / #5638) that #5662 fixed. #5662's snapshot-hygiene guard mitigates the shared root cause, but a dedicated fix for this post-commit residual branch was not found (inference).

## Evidence (last 50 /implement run logs)

- Run `3B7C963B` (#5170, v52.1.2): `COMMITTED=true / SHA=2567a21… / ERROR=dirty tree after review fix commit / COMMIT_OUTCOME=failed`, which escalated the run to `stalled`.
- Distinct from the dominant `ERROR=no review delta paths` signature (#5637 / #5638) addressed by #5662.

## Root cause

In `python/larch/review/review_and_fix.py::_finish_stage_all_commit_success` (~lines 284-291), the `--only --pathspec-from-file` commit lands but leaves residual unstaged changes outside the captured delta set, so the post-commit dirty check fails and reports `COMMIT_OUTCOME=failed`. #5662 rejects a dirty tree at snapshot time (the upstream precondition), which should mitigate the root cause, but may not cover this specific post-commit residual branch.

## Suggested fix

After the `--only` commit, either include / re-stage residual delta paths in the commit, or treat residual-dirty-outside-delta as a non-fatal recorded note rather than `COMMIT_OUTCOME=failed`. Files: `python/larch/review/review_and_fix.py`.

## Severity

Low (1/50, older v52.1.2). Filed for tracking and regression coverage per operator direction.

## References

- #5662 (closed, commit `8a075d8a7`) fixed the empty-delta variant via snapshot hygiene.
- Surfaced by a post-merge audit of the last 50 `/implement` run logs.

## Test plan
(no test plan section in plan-file)
