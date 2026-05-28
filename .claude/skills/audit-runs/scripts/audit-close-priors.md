# .claude/skills/audit-runs/scripts/audit-close-priors.sh — contract

Requires `--skill <design|implement>`. Closes open audit-report issues whose titles match the skill via `audit-title-matcher.sh`.

Closes prior open `audit-report` issues after a new report is filed.

## Output (stdout)

```
CLOSED_NUMBER=<N>         (one line per successfully closed issue)
CLOSE_FAILED=<N><TAB>REASON=<msg>   (TAB between CLOSE_FAILED value and REASON; on per-issue failure)
ISSUE_LIST_FAILED=true
REASON=gh issue list failed
BODY_FILE_FAILED=true
REASON=mktemp failed
```

`ISSUE_LIST_FAILED` / `REASON` print to stdout (same stream as `CLOSED_NUMBER=`) when `gh issue list` fails, then the script exits non-zero. `BODY_FILE_FAILED` / `REASON` use the same stdout channel when the temporary `--body-file` setup fails before any comment/close calls, then the script exits non-zero.

## Behavior

1. Lists all open issues with label `audit-report` in `--repo`.
   Invalid `gh issue list` JSON is treated as a hard failure (`ISSUE_LIST_FAILED=true`, `REASON=gh issue list returned invalid JSON`).
2. Skips `--new-issue-number` (the just-filed report).
3. For each remaining issue: posts `Superseded by #N` from a temp file via `gh issue comment --body-file`, then closes via `gh issue close`.
4. Idempotent: already-closed issues are not listed by `gh issue list --state open`, so they are naturally skipped.

## Edit-in-sync

Update the close-priors section in `test-audit-runs.sh` when the stdout KV contract or `gh` call flow changes; the harness enforces the `--body-file` contract.
