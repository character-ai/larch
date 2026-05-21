# .claude/skills/audit-runs/scripts/audit-close-priors.sh — contract

Closes prior open `audit-report` issues after a new report is filed.

## Output (stdout)

```
CLOSED_NUMBER=<N>         (one line per successfully closed issue)
CLOSE_FAILED=<N>  REASON=<msg>   (on failure)
```

## Behavior

1. Lists all open issues with label `audit-report` in `--repo`.
2. Skips `--new-issue-number` (the just-filed report).
3. For each remaining issue: posts `Superseded by #N` comment, then closes via `gh issue close`.
4. Idempotent: already-closed issues are not listed by `gh issue list --state open`, so they are naturally skipped.

## Edit-in-sync

No unit tests (requires real `gh`); behavior is covered by integration testing during manual audit-runs invocations.
