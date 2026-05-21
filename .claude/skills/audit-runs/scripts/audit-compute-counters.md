# .claude/skills/audit-runs/scripts/audit-compute-counters.sh — contract

Sums scan-result deltas across PRs and adds to prior cumulative totals from a report's YAML frontmatter.

## Input

- `--scan-results-dir DIR`: directory containing `scan-results-NNNN.ndjson` files (one per PR, written by `audit-scan-run.sh`).
- `--prior-frontmatter FILE` (optional): path to prior audit-report body (YAML frontmatter between `---` markers). When absent, prior totals default to 0.

## Output KV (stdout)

```
EXON_MISCLASSIFICATIONS=103
EXON_DELTA=0
OOS_CATEGORIES_MANGLED=55
OOS_MANGLED_DELTA=12
OOS_CATEGORIES_CLEAN=316
OOS_CLEAN_DELTA=151
OOS_CATEGORIES_BLANK=83
OOS_BLANK_DELTA=26
NS_RETRIES_CURSOR_SPECIALIST=10
NS_RETRIES_DELTA=5
CHANGELOG_REBASE_CONFLICTS=3
CHANGELOG_DELTA=1
```

## Edit-in-sync

Update tests in `test-audit-runs.sh` (compute-counters section) when counter field names or arithmetic change. Update frontmatter YAML key names in `SKILL.md` in the same PR.
