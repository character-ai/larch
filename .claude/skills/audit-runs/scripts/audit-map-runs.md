# .claude/skills/audit-runs/scripts/audit-map-runs.sh — contract

Maps each PR in `--pr-list` to its run-log directory under `larch-logs/implement/`.

## Output

TSV to stdout, one row per PR (no header):

```
pr_number<TAB>run_id<TAB>started_at<TAB>larch_version<TAB>closes_issue
```

Fields are empty strings when a PR cannot be mapped.

## Lookup strategy

1. **Primary**: on `gh pr view` failure, prints `MAP_GH_PR_VIEW_FAILED=true` with a `REASON=` fragment to stderr, then emits an empty mapping row (no manifest fallback on `gh` failure). On success, read the PR body, then derive `N` with **keyword-priority** closing lines: scan **Closes** `#…` first (case-insensitive); if none, **Fixes**; if none, **Resolves**. Within one keyword class, all matches must agree on a single issue number; if that class lists multiple distinct numbers, prints `MAP_PR_BODY_CLOSING_AMBIGUOUS=true` to stderr (with `KEYWORD=`) and does **not** use the PR body for mapping (falls through to manifest fallback when possible). When a single `N` resolves, match `parent-issue.md` files whose `ISSUE_NUMBER` equals `N`. When multiple run directories match, the newest `manifest.json` `started_at` wins; if that is still ambiguous, prints `MAP_PARENT_ISSUE_AMBIGUOUS=true` to stderr and leaves `run_id` empty.
2. **Fallback** (older runs with `pr_number` recorded in `manifest.json`): scan `larch-logs/implement/*/manifest.json` for `"pr_number": N`, choosing the **newest** row by `started_at` using ISO-8601 parsing (`jq` `fromdateiso8601`), not raw string ordering.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (map-runs section) when fallback or lookup behavior changes.
