## Plan

See plan.txt for full content. Summary: fix the false `panel-failed` secondary gate in `review-core.sh` when `collector_success_count==0` but parseable output exists; commit `collector-results.env` and `review-core-threshold.env` to run logs; emit a loud operator warning when a `--merge` run is silently downgraded to `pr-created` after panel-failed recovery.

## Acceptance

- `review-core.sh` secondary gate only fires when BOTH `launched_success_count==0` AND no parseable output present (`findings.md` and `oos.md` both empty).
- `collector-results.env` and `review-core-threshold.env` appear in round-N/ of committed run logs.
- `IMPLEMENT_MERGE_DOWNGRADED=true` is emitted and rendered in the final summary when a `--merge` run ends as `pr-created` due to panel-failed recovery.
- All existing tests pass; new regression tests added for each fix surface.

review_status: complete
rounds_completed: 5
diff_lines: 410
