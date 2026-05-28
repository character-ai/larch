# .claude/skills/audit-runs/scripts/audit-title.sh — contract

Requires `--skill <design|implement>`. Emits `[Implement Run Logs Audit …]` or `[Design Run Logs Audit …]` title prefixes.

Generates the audit report title string from a PR list and timestamp.

## Output KV (stdout)

```
TITLE=[Implement Run Logs Audit <timestamp> Report] PRs #X-#Y
TITLE=[Design Run Logs Audit <timestamp> Report] PRs #X, #Y, #Z
```

## Title rules

- **Single PR**: `PRs #N`
- **Contiguous range** (`last - first + 1 == count`): `PRs #X-#Y`
- **Non-contiguous** (any count): `PRs #X, #Y, #Z, ...` (explicit sorted list; PR numbers are printed in canonical decimal form, with no leading zeros, even if `--pr-list` tokens included leading zeros)

## Edit-in-sync

Update tests in `test-audit-runs.sh` (title section) when title format changes.
