# .claude/skills/audit-runs/scripts/audit-map-runs.sh — contract

Maps each PR in `--pr-list` to its run-log directory under `larch-logs/implement/`.

## Output

TSV to stdout, one row per PR (no header):

```
pr_number<TAB>run_id<TAB>started_at<TAB>larch_version<TAB>closes_issue
```

Fields are empty strings when a PR cannot be mapped.

## Lookup strategy

1. **Primary**: scan `larch-logs/implement/*/manifest.json` for `"pr_number": N`, choosing the **newest** row by `started_at` using ISO-8601 parsing (`jq` `fromdateiso8601`), not raw string ordering.
2. **Fallback** (pre-merge commit pattern, `pr_number: null`): read PR body for `Closes #N` via `gh pr view` (on failure, prints `MAP_GH_PR_VIEW_FAILED=true` with a `REASON=` fragment to stderr, then emits an empty mapping row). When multiple `parent-issue.md` files match the same `ISSUE_NUMBER`, the newest `manifest.json` `started_at` wins; if that is still ambiguous, prints `MAP_PARENT_ISSUE_AMBIGUOUS=true` to stderr and leaves `run_id` empty.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (map-runs section) when fallback or lookup behavior changes.
