# .claude/skills/audit-runs/scripts/test-audit-runs.sh — contract

Offline unit test harness for `/larch:audit-runs` skill logic. Tests verbal-description parsing, "since last audit" error paths, concurrency guard, `--repo` enforcement, removed-flag rejection (`--no-fix-issues`), scan-time proposal-only recording, zero-findings short-circuit, frontmatter round-trip, and audit report title exclusion regex.

## Purpose

Validates the parsing and guard logic that the `/audit-runs` skill orchestrator applies before making any GitHub API calls. All tests are hermetic (no network calls, no real `gh` invocations).

## What is tested

- Verbal description parsing for all supported forms (`last N PRs`, `since last audit`, `since <ISO>`, `#N`, `PR #N`, empty → implicit `since last audit`)
- "since last audit" error cases: no prior report, malformed frontmatter, no new PRs (no report filed)
- Audit report close-prior filter (just-filed report is excluded from close-prior pass)
- Frontmatter YAML round-trip for all required fields
- Concurrency guard (fires when recent report exists; bypassed by `--allow-concurrent`)
- `--repo` enforcement (rejects pwd that doesn't match target repo remote)
- Test 13a: `--no-fix-issues` is rejected (flag removed from the skill)
- Test 13b: scan-time behavior records into `proposed_new_issues` / `proposed_augmentations` only (no auto-file path)
- Test 15: zero-findings short-circuit chat message and absence of the 3-way filing prompt when both proposal lists are empty; frontmatter lists `proposed_new_issues: []` and `proposed_augmentations: []`
- Audit report title self-exclusion prefix (`^\[Run Logs Audit Report` pattern prevents self-augmentation); note that the existing `has_report_prefix` pattern does NOT match audit report titles because the ISO timestamp follows "Report" inside the bracket — the `audit-report` GitHub label filter in `find-lock-issue.sh` is the primary /fix-issue exclusion guard
- `audit-scan-run.sh` `oos-silent-drop` scan pass/skip/fail and NDJSON jq-error fixtures (`test-audit-runs.sh` Test 60o)

## Run

```bash
bash .claude/skills/audit-runs/scripts/test-audit-runs.sh
```

## Wiring

Wired into `make lint` via the `test-audit-runs` target in the `Makefile` (same `harness-timer.sh` wrapper pattern as `test-find-lock-issue`). Listed in `docs/linting.md` harness inventory.

## Edit-in-sync

When the skill's verbal-description parsing, flag handling, or frontmatter schema changes, update this harness in the same PR.
