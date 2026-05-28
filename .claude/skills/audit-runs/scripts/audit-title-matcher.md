# .claude/skills/audit-runs/scripts/audit-title-matcher.sh — contract

Centralized matcher for audit-report issue titles, keyed by `--skill`.

## CLI / function

```
match_audit_report_title --skill <design|implement> --title "<string>"
```

Exit **0** when the title matches the skill’s allowed shapes; **1** otherwise.

## Per-skill shapes

| `--skill` | Matches |
|---|---|
| `implement` | `^\[(Run Logs Audit \|Implement Run Logs Audit ).* Report\]` (legacy + new implement prefix) |
| `design` | `^\[Design Run Logs Audit .* Report\]` |

## Consumers

- `audit-resolve-prs.sh` (prior-report discovery for `since last audit`)
- `audit-close-priors.sh` (which open reports to supersede)
- `/audit-runs` SKILL.md noise-exclusion for bug-issue keyword search

## Edit-in-sync

Update `test-audit-title-matcher.sh` when regex behavior changes.
