# .claude/skills/audit-runs/scripts/audit-map-runs.sh — contract

Maps each PR in `--pr-list` to its run-log directory under `larch-logs/implement/`.

## Output

TSV to stdout, one row per PR (no header):

```
pr_number<TAB>run_id<TAB>started_at<TAB>larch_version<TAB>closes_issue
```

Fields are empty strings when a PR cannot be mapped.

## Lookup strategy

1. **Primary**: grep `larch-logs/implement/*/manifest.json` for `"pr_number": N`.
2. **Fallback** (pre-merge commit pattern, `pr_number: null`): read PR body for `Closes #N`, then scan `*/parent-issue.md` files for matching `ISSUE_NUMBER`.

## Edit-in-sync

Update tests in `test-audit-runs.sh` (map-runs section) when fallback or lookup behavior changes.
