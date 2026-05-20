# .claude/skills/audit-runs/scripts/test-audit-runs.sh — contract

Offline unit test harness for `/audit-runs` skill logic. Tests verbal-description parsing, "since last audit" error paths, concurrency guard, `--repo` enforcement, `--no-fix-issues` behavior, frontmatter round-trip, and audit report title exclusion regex.

## Purpose

Validates the parsing and guard logic that the `/audit-runs` skill orchestrator applies before making any GitHub API calls. All tests are hermetic (no network calls, no real `gh` invocations).

## What is tested

- Verbal description parsing for all supported forms (`last N PRs`, `since last audit`, `since <ISO>`, `#N`, `PR #N`, empty → usage error)
- "since last audit" error cases: no prior report, malformed frontmatter, no new PRs (no report filed)
- Audit report close-prior filter (just-filed report is excluded from close-prior pass)
- Frontmatter YAML round-trip for all required fields
- Concurrency guard (fires when recent report exists; bypassed by `--allow-concurrent`)
- `--repo` enforcement (rejects pwd that doesn't match target repo remote)
- `--no-fix-issues` flag suppresses bug filings and augmentations but still records in `proposed_issues_no_filing`
- Audit report title self-exclusion prefix (`^\[Run Logs Audit Report` pattern prevents self-augmentation); note that the existing `has_report_prefix` pattern does NOT match audit report titles because the ISO timestamp follows "Report" inside the bracket — the `audit-report` GitHub label filter in `find-lock-issue.sh` is the primary /fix-issue exclusion guard

## Run

```bash
bash .claude/skills/audit-runs/scripts/test-audit-runs.sh
```

## Wiring

Not yet wired into `make lint`. To add: follow the pattern of `test-find-lock-issue` in the `Makefile`.

## Edit-in-sync

When the skill's verbal-description parsing, flag handling, or frontmatter schema changes, update this harness in the same PR.
