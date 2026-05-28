# .claude/skills/audit-runs/scripts/audit-title-matcher.sh — contract

Centralized helpers for audit-report issue titles plus design run-log PR titles.

## Audit-report CLI / function

```
match_audit_report_title --skill <design|implement> --title "<string>"
```

Exit **0** when the title matches the skill’s allowed shapes; **1** otherwise.

## Per-skill shapes

| `--skill` | Matches |
|---|---|
| `implement` | `^\[(Run Logs Audit \|Implement Run Logs Audit ).* Report\]` (legacy + new implement prefix) |
| `design` | `^\[Design Run Logs Audit .* Report\]` |

## Design run-log helpers

```
match_design_run_log_pr_title "<title>"
extract_design_run_log_pr_id "<title>"
```

Design PR titles must match:

`^chore\(larch-logs\): design run [0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$`

That UUID segment is uppercase-only by contract.

## Consumers

- `audit-resolve-prs.sh` (prior-report discovery for `since last audit`)
- `audit-close-priors.sh` (which open reports to supersede)
- `audit-map-runs.sh` (design PR title → run-id extraction)
- `/audit-runs` SKILL.md bug-search noise exclusion should reference this helper contract rather than copying the regex verbatim

## Edit-in-sync

Update `test-audit-title-matcher.sh` when regex behavior changes.
